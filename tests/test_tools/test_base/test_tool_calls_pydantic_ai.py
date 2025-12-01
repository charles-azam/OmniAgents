# Test tool calling with Pydantic AI
# test that the framework works as expected
import os
import random
from pydantic import BaseModel, Field
from pydantic_ai import Agent, Tool as PydanticAITool
from pydantic_ai.models.huggingface import HuggingFaceModel
from pydantic_ai.providers.huggingface import HuggingFaceProvider


from prompttodraft.tools.base_tool import CoreBackendTool, CoreTool
from prompttodraft.backends.local_backend import LocalBackend
from prompttodraft.backends.state_manager import NoOpStateManager


# MONKEY-PATCH: Fix pydantic_ai HuggingFace adapter bug where tool call arguments
# are lost during serialization. The bug is that _map_tool_call uses
# ChatCompletionInputToolCall (which has ChatCompletionInputFunctionDefinition
# without 'arguments' field) instead of ChatCompletionOutputToolCall (which has
# ChatCompletionOutputFunctionDefinition with 'arguments' field).
# This patch should be removed once pydantic_ai fixes this upstream.
def _patch_pydantic_ai_huggingface() -> None:
    from pydantic_ai.messages import ToolCallPart
    from pydantic_ai._utils import guard_tool_call_id as _guard_tool_call_id
    from huggingface_hub.inference._generated.types.chat_completion import (
        ChatCompletionOutputToolCall,
        ChatCompletionOutputFunctionDefinition,
    )

    @staticmethod  # type: ignore[misc]
    def _map_tool_call_fixed(t: ToolCallPart) -> ChatCompletionOutputToolCall:
        return ChatCompletionOutputToolCall(
            id=_guard_tool_call_id(t=t),
            type="function",
            function=ChatCompletionOutputFunctionDefinition(
                name=t.tool_name,
                arguments=t.args_as_json_str(),
            ),
        )

    HuggingFaceModel._map_tool_call = _map_tool_call_fixed


_patch_pydantic_ai_huggingface()


def test_pydantic_ai_tool_created_correctly():
    """Test that CoreTool converts correctly to pydantic_ai tool with proper attributes and execution."""

    # Mock data - define test inputs and expected outputs
    class SimpleInput(BaseModel):
        path: str
        count: int

    class SimpleOutput(BaseModel):
        content: str
        processed: int

    class SimpleTool(CoreTool[SimpleInput, SimpleOutput]):
        name = "simple_tool"
        description = "Does something simple"

        def execute(self, inputs: SimpleInput) -> SimpleOutput:
            return SimpleOutput(
                content=f"Processed {inputs.path}",
                processed=inputs.count * 2
            )

    # Create tool instance
    tool = SimpleTool()

    # Convert to pydantic_ai tool
    pydantic_ai_tool = tool.to_pydantic_ai_tool()

    # Verify tool is created with correct type and attributes
    assert isinstance(pydantic_ai_tool, PydanticAITool)
    assert pydantic_ai_tool.name == "simple_tool"
    assert pydantic_ai_tool.description == "Does something simple"

    # Test execution through the tool's function
    result = pydantic_ai_tool.function(path="/test/path", count=5)
    assert isinstance(result, SimpleOutput)
    assert result.content == "Processed /test/path"
    assert result.processed == 10


def test_pydantic_ai_tool_backend_created_correctly():
    """Test that CoreBackendTool converts correctly to pydantic_ai tool with backend support."""

    # Mock data
    class BackendInput(BaseModel):
        command: str

    class BackendOutput(BaseModel):
        result: str
        status: str

    class BackendTool(CoreBackendTool[BackendInput, BackendOutput]):
        name = "backend_tool"
        description = "Tool that uses backend"

        def execute(self, inputs: BackendInput) -> BackendOutput:
            # Use backend in execution
            backend_type = self.backend.__class__.__name__
            return BackendOutput(
                result=f"Executed {inputs.command}",
                status=f"Using {backend_type}"
            )

    # Create local backend with NoOp state manager for testing
    state_manager = NoOpStateManager()
    backend = LocalBackend(project_id="test_project", state_manager=state_manager)
    tool = BackendTool(backend=backend)

    # Convert to pydantic_ai tool
    pydantic_ai_tool = tool.to_pydantic_ai_tool()

    # Verify tool structure
    assert isinstance(pydantic_ai_tool, PydanticAITool)
    assert pydantic_ai_tool.name == "backend_tool"
    assert pydantic_ai_tool.description == "Tool that uses backend"

    # Test execution with backend
    result = pydantic_ai_tool.function(command="ls -la")
    assert isinstance(result, BackendOutput)
    assert result.result == "Executed ls -la"
    assert "LocalBackend" in result.status


def test_pydantic_ai_tool_backend_works_correctly():
    """Test that CoreBackendTool converts correctly to pydantic_ai tool and can use backend to write files."""
    from prompttodraft.tools.write_file_tool import WriteFileTool
    from prompttodraft.outputs.outputs import TextOutputModel

    # Create local backend with NoOp state manager for testing
    state_manager = NoOpStateManager()
    backend = LocalBackend(project_id="test_pydantic_ai_tool_backend_works_correctly", state_manager=state_manager)

    try:
        # Start backend
        backend.start()
        working_dir = backend.get_working_directory()

        # Create a real backend tool (WriteFileTool)
        write_tool = WriteFileTool(backend=backend)

        # Convert to pydantic_ai tool
        pydantic_ai_write_tool = write_tool.to_pydantic_ai_tool()

        # Verify tool structure
        assert isinstance(pydantic_ai_write_tool, PydanticAITool)
        assert pydantic_ai_write_tool.name == "write_file"
        assert "write" in pydantic_ai_write_tool.description.lower()

        # Test execution with backend - write a file
        random_number = random.randint(1, 1000000)
        content = f"# Test file written by pydantic_ai tool\nprint('Hello from backend! {random_number}')\n"
        test_file = f"{working_dir}/test_backend.py"
        result = pydantic_ai_write_tool.function(
            file_path=test_file,
            content=content
        )

        # Verify the result
        assert isinstance(result, TextOutputModel)
        assert "created" in result.content.lower() or "wrote" in result.content.lower()

        # Verify the file was actually written to the backend
        assert backend.file_exists(path=test_file)
        file_content = backend.read_file(file_path=test_file)
        assert content in file_content
        assert "Hello from backend!" in file_content

        # Test overwriting the file
        updated_content = f"# Updated content\nprint('Updated! {random_number}')\n"
        result = pydantic_ai_write_tool.function(
            file_path=test_file,
            content=updated_content
        )
        assert isinstance(result, TextOutputModel)
        assert "overwrote" in result.content.lower()

        # Verify the file was overwritten
        file_content = backend.read_file(file_path=test_file)
        assert updated_content in file_content
        assert "Updated!" in file_content
        assert "Hello from backend!" not in file_content

    finally:
        # Clean up
        backend.shutdown()
        backend.cleanup()


def test_pydantic_ai_tool_schemas_extracted_correctly():
    """Test that tool schemas are correctly extracted from Generic parameters for pydantic_ai."""

    class SchemaInput(BaseModel):
        name: str = Field(description="The name of the person")
        age: int = Field(description="The age of the person")
        active: bool = Field(description="Whether the person is active")

    class SchemaOutput(BaseModel):
        message: str

    class SchemaTool(CoreTool[SchemaInput, SchemaOutput]):
        name = "schema_tool"
        description = "Tool for schema testing"

        def execute(self, inputs: SchemaInput) -> SchemaOutput:
            return SchemaOutput(message=f"{inputs.name} is {inputs.age}")

    # Test input/output model extraction
    input_model = SchemaTool.get_input_model()
    output_model = SchemaTool.get_output_model()

    assert input_model == SchemaInput
    assert output_model == SchemaOutput

    # Verify the schema itself
    schema = SchemaInput.model_json_schema()
    assert "properties" in schema
    assert "name" in schema["properties"]
    assert schema["properties"]["name"]["description"] == "The name of the person"
    assert "age" in schema["properties"]
    assert schema["properties"]["age"]["description"] == "The age of the person"
    assert "active" in schema["properties"]
    assert schema["properties"]["active"]["description"] == "Whether the person is active"


def test_pydantic_ai_agent_with_llm():
    """
    E2E test: Run a complete Pydantic AI agent with gpt-4o-mini.

    Tests that our tools work correctly in a real agent workflow:
    1. Create tools using CoreTool
    2. Convert to pydantic_ai format
    3. Create agent with gpt-4o-mini
    4. Run agent on a task
    5. Verify tools can be invoked through the agent
    """

    # Define test tools with metadata tracking
    metadata = dict(CalculatorOutput=0, GreeterOutput=0)

    class CalculatorInput(BaseModel):
        operation: str = Field(description="The operation to perform: add, subtract, multiply, or divide")
        a: float = Field(description="The first number")
        b: float = Field(description="The second number")

    class CalculatorOutput(BaseModel):
        result: float
        operation_performed: str

        def has_been_called(self) -> None:
            metadata["CalculatorOutput"] += 1

    class CalculatorTool(CoreTool[CalculatorInput, CalculatorOutput]):
        name = "calculator"
        description = "Performs basic arithmetic operations (add, subtract, multiply, divide). Use 'add', 'subtract', 'multiply', or 'divide' as operation."

        def execute(self, inputs: CalculatorInput) -> CalculatorOutput:
            if inputs.operation == "add":
                result = inputs.a + inputs.b
            elif inputs.operation == "subtract":
                result = inputs.a - inputs.b
            elif inputs.operation == "multiply":
                result = inputs.a * inputs.b
            elif inputs.operation == "divide":
                if inputs.b == 0:
                    result = float('inf')
                else:
                    result = inputs.a / inputs.b
            else:
                result = 0.0

            calculator_output = CalculatorOutput(
                result=result,
                operation_performed=f"{inputs.a} {inputs.operation} {inputs.b}"
            )
            calculator_output.has_been_called()
            return calculator_output

    class GreeterInput(BaseModel):
        name: str = Field(description="The name of the person to greet")
        language: str = Field(description="The language for greeting: english, spanish, or french")

    class GreeterOutput(BaseModel):
        greeting: str

        def has_been_called(self) -> None:
            metadata["GreeterOutput"] += 1

    class GreeterTool(CoreTool[GreeterInput, GreeterOutput]):
        name = "greeter"
        description = "Greets a person in different languages. Supports 'english', 'spanish', 'french'."

        def execute(self, inputs: GreeterInput) -> GreeterOutput:
            greetings = {
                "english": f"Hello, {inputs.name}!",
                "spanish": f"¡Hola, {inputs.name}!",
                "french": f"Bonjour, {inputs.name}!"
            }
            greeting = greetings.get(inputs.language.lower(), f"Hi, {inputs.name}!")
            greeter_output = GreeterOutput(greeting=greeting)
            greeter_output.has_been_called()
            return greeter_output

    # Create tool instances
    calculator = CalculatorTool()
    greeter = GreeterTool()

    # Convert to pydantic_ai tools
    calculator_tool = calculator.to_pydantic_ai_tool()
    greeter_tool = greeter.to_pydantic_ai_tool()

    # Create agent with gpt-4o-mini model
    agent = Agent(
        model=HuggingFaceModel(model_name="openai/gpt-oss-120b", provider=HuggingFaceProvider(api_key=os.environ["HF_TOKEN"], provider_name='groq')),
        tools=[calculator_tool, greeter_tool],
        system_prompt="You are a helpful assistant. Use the provided tools to answer questions."
    )

    # Test 1: Math task
    result = agent.run_sync(user_prompt="What is 15 multiplied by 3? you must use the calculator tool to answer the question")
    assert "45" in str(result.output) or "45.0" in str(result.output), f"Expected result to contain 45, got: {result.output}"
    assert metadata["CalculatorOutput"] == 1
    assert metadata["GreeterOutput"] == 0

    # Test 2: Greeting task
    result = agent.run_sync(user_prompt="Greet Alice in Spanish")
    assert "Hola" in str(result.output) and "Alice" in str(result.output), f"Expected Spanish greeting for Alice, got: {result.output}"
    assert metadata["CalculatorOutput"] == 1
    assert metadata["GreeterOutput"] == 1


if __name__ == "__main__":
    test_pydantic_ai_tool_created_correctly()
    test_pydantic_ai_tool_backend_created_correctly()
    test_pydantic_ai_tool_schemas_extracted_correctly()
    test_pydantic_ai_agent_with_llm()
