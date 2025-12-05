# Test tool calling with the different frameworks, huggingface and openai
# test that each framework as expected
import os
import pytest
from pydantic import BaseModel
from smolagents import Tool as SmolagentsTool
from smolagents import ToolCallingAgent
from smolagents.models import OpenAIModel, InferenceClientModel

from anyagents.tools.base_tool import CoreBackendTool, CoreTool
from anyagents.backends.local_backend import LocalBackend
from anyagents.backends.state_manager import NoOpStateManager
from pydantic import Field
import random
from anyagents.agents.smolagent_agent import get_smolagents_model_example

def test_smolagent_tool_created_correctly():
    """Test that CoreTool converts correctly to smolagents tool with proper attributes and execution."""

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

    # Convert to smolagents tool
    smolagent_instance = tool.to_smolagents_tool()

    # Verify tool is created with correct type and attributes
    assert isinstance(smolagent_instance, SmolagentsTool)
    assert smolagent_instance.name == "simple_tool"
    assert smolagent_instance.description == "Does something simple"
    assert smolagent_instance.output_type == "string"

    # Verify input schema is properly set in smolagents format
    assert isinstance(smolagent_instance.inputs, dict)
    assert "path" in smolagent_instance.inputs
    assert "count" in smolagent_instance.inputs
    assert smolagent_instance.inputs["path"]["type"] == "string"
    assert smolagent_instance.inputs["count"]["type"] == "integer"
    assert "description" in smolagent_instance.inputs["path"]
    assert "description" in smolagent_instance.inputs["count"]

    # Test execution through forward method
    result = smolagent_instance.forward(path="/test/path", count=5)
    assert isinstance(result, SimpleOutput)
    assert result.content == "Processed /test/path"
    assert result.processed == 10



def test_smolagent_tool_backend_created_correctly():
    """Test that CoreBackendTool converts correctly to smolagents tool with backend support."""

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

    # Convert to smolagents tool
    smolagent_instance = tool.to_smolagents_tool()

    # Verify tool structure
    assert isinstance(smolagent_instance, SmolagentsTool)
    assert smolagent_instance.name == "backend_tool"
    assert smolagent_instance.description == "Tool that uses backend"

    # Test execution with backend
    result = smolagent_instance.forward(command="ls -la")
    assert isinstance(result, BackendOutput)
    assert result.result == "Executed ls -la"
    assert "LocalBackend" in result.status

    
def test_smolagents_tool_backend_works_correctly():
    """Test that CoreBackendTool converts correctly to smolagents tool and can use backend to write files."""
    from anyagents.tools.write_file_tool import WriteFileTool
    from anyagents.outputs.outputs import TextOutputModel

    # Create local backend with NoOp state manager for testing
    state_manager = NoOpStateManager()
    backend = LocalBackend(project_id="test_smolagents_tool_backend_works_correctly", state_manager=state_manager)

    try:
        # Start backend
        backend.start()
        working_dir = str(backend.get_working_directory())

        # Create a real backend tool (WriteFileTool)
        write_tool = WriteFileTool(backend=backend)

        # Convert to smolagents tool
        smolagents_write_tool = write_tool.to_smolagents_tool()

        # Verify tool structure
        assert isinstance(smolagents_write_tool, SmolagentsTool)
        assert smolagents_write_tool.name == "write_file"
        assert "write" in smolagents_write_tool.description.lower()

        # Test execution with backend - write a file
        random_number = random.randint(1, 1000000)
        content = f"# Test file written by smolagents tool\nprint('Hello from backend! {random_number}')\n"
        test_file = f"{working_dir}/test_backend.py"
        result = smolagents_write_tool.forward(
            file_path=test_file,
            content=content
        )

        # Verify the result
        assert isinstance(result, TextOutputModel)
        assert "created" in result.content.lower() or "wrote" in result.content.lower()

        # Verify the file was actually written to the backend
        assert backend.file_exists(path=backend.convert_to_path(path=test_file))
        file_content = backend.read_file(file_path=backend.convert_to_path(path=test_file))
        assert content in file_content
        assert "Hello from backend!" in file_content

        # Test overwriting the file
        updated_content = f"# Updated content\nprint('Updated! {random_number}')\n"
        result = smolagents_write_tool.forward(
            file_path=test_file,
            content=updated_content
        )
        assert isinstance(result, TextOutputModel)
        assert "overwrote" in result.content.lower()

        # Verify the file was overwritten
        file_content = backend.read_file(file_path=backend.convert_to_path(path=test_file))
        assert updated_content in file_content
        assert "Updated!" in file_content
        assert "Hello from backend!" not in file_content

    finally:
        # Clean up
        backend.shutdown()
        backend.cleanup_state_manager()

def test_tool_schemas_extracted_correctly():
    """Test that tool schemas are correctly extracted from Generic parameters."""

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

    # Test schema generation
    input_schema = SchemaTool.get_input_schema()
    output_schema = SchemaTool.get_output_schema()

    assert "properties" in input_schema
    assert "name" in input_schema["properties"]
    assert input_schema["properties"]["name"]["description"] == "The name of the person"
    assert "age" in input_schema["properties"]
    assert input_schema["properties"]["age"]["description"] == "The age of the person"
    assert "active" in input_schema["properties"]
    assert input_schema["properties"]["active"]["description"] == "Whether the person is active"
    assert input_schema["properties"]["name"]["type"] == "string"
    assert input_schema["properties"]["age"]["type"] == "integer"
    assert input_schema["properties"]["active"]["type"] == "boolean"

    assert "properties" in output_schema
    assert "message" in output_schema["properties"]

    # Test complete tool definition
    tool_def = SchemaTool.get_tool_definition()
    assert tool_def["name"] == "schema_tool"
    assert tool_def["description"] == "Tool for schema testing"
    assert tool_def["input_schema"] == input_schema
    assert tool_def["output_schema"] == output_schema

@pytest.mark.llm
def test_smolagents_agent_with_llm():
    """
    E2E test: Run a complete smolagents CodeAgent with gpt-5-mini.

    Tests that our tools work correctly in a real agent workflow:
    1. Create tools using CoreTool
    2. Convert to smolagents format
    3. Create agent with gpt-5-mini
    4. Run agent on a task
    5. Verify correct output
    """

    # Define test tools
    class CalculatorInput(BaseModel):
        operation: str
        a: float
        b: float

    metadata = dict(CalculatorOutput=0, GreeterOutput=0, TextJoinerOutput=0)

    class CalculatorOutput(BaseModel):
        result: float
        operation_performed: str

        def has_been_called(self) -> bool:
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

            return str(calculator_output)

    class GreeterInput(BaseModel):
        name: str
        language: str

    class GreeterOutput(BaseModel):
        greeting: str

        def has_been_called(self) -> bool:
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

    class TextJoinerInput(BaseModel):
        items: list[str] = Field(description="List of text items to join") # smolagents handles array differently
        format_type: str = Field(description="Format type: 'comma', 'numbered', or 'bullets'")
        additional_context: str | None = Field(default=None, description="Additional context to add to the formatted text, should almost always be empty") # smolagents handles optional differently

    class TextJoinerOutput(BaseModel):
        formatted_text: str
        item_count: int

        def has_been_called(self) -> bool:
            metadata["TextJoinerOutput"] += 1

    class TextJoinerTool(CoreTool[TextJoinerInput, TextJoinerOutput]):
        name = "text_joiner"
        description = "Takes a list of text items and formats them. Supports 'comma' (comma-separated), 'numbered' (numbered list), or 'bullets' (bullet points)."

        def execute(self, inputs: TextJoinerInput) -> TextJoinerOutput:
            if inputs.format_type == "comma":
                formatted = ", ".join(inputs.items)
            elif inputs.format_type == "numbered":
                formatted = "\n".join([f"{i+1}. {item}" for i, item in enumerate(inputs.items)])
            elif inputs.format_type == "bullets":
                formatted = "\n".join([f"• {item}" for item in inputs.items])
            else:
                formatted = " ".join(inputs.items)

            text_joiner_output = TextJoinerOutput(
                formatted_text=formatted,
                item_count=len(inputs.items)
            )
            text_joiner_output.has_been_called()
            return text_joiner_output

    # Create tool instances
    calculator = CalculatorTool()
    greeter = GreeterTool()
    text_joiner = TextJoinerTool()

    # Convert to smolagents tools
    calculator_tool = calculator.to_smolagents_tool()
    greeter_tool = greeter.to_smolagents_tool()
    text_joiner_tool = text_joiner.to_smolagents_tool()

    # Create agent with gpt-5-mini model
    agent = ToolCallingAgent(
        tools=[calculator_tool, greeter_tool, text_joiner_tool],
        model=get_smolagents_model_example(),
        max_steps=2
    )

    # Test 1: Math task
    result = agent.run(task="What is 15 multiplied by 3?")
    assert "45" in str(result) or "45.0" in str(result), f"Expected result to contain 45, got: {result}"
    assert metadata["CalculatorOutput"] == 1
    assert metadata["GreeterOutput"] == 0
    assert metadata["TextJoinerOutput"] == 0

    # Test 2: Greeting task
    result = agent.run(task="Greet Alice in Spanish")
    assert "Hola" in str(result) and "Alice" in str(result), f"Expected Spanish greeting for Alice, got: {result}"
    assert metadata["CalculatorOutput"] == 1
    assert metadata["GreeterOutput"] == 1
    assert metadata["TextJoinerOutput"] == 0

    # Test 3: List processing task - test that list[str] input works correctly
    result = agent.run(task="Format these grocery items as a numbered list: milk, eggs, bread, cheese")
    result_str = str(result)
    # Check that the text joiner was called
    assert metadata["TextJoinerOutput"] == 1, f"Expected TextJoinerTool to be called, but it wasn't"
    # Check that result contains the items formatted
    assert ("milk" in result_str and "eggs" in result_str and "bread" in result_str and "cheese" in result_str), f"Expected all grocery items in result, got: {result}"
    pass

if __name__ == "__main__":
    test_smolagent_tool_created_correctly()
    test_smolagent_tool_backend_created_correctly()
    test_tool_schemas_extracted_correctly()
    test_smolagents_tool_backend_works_correctly()
    test_smolagents_agent_with_llm()
