# Test tool calling with the different frameworks, huggingface and openai
# test that each framework as expected
import os
from pydantic import BaseModel
from smolagents import Tool as SmolagentsTool
from smolagents import ToolCallingAgent
from smolagents.models import OpenAIModel, InferenceClientModel

from prompttodraft.tools.base_tool import CoreBackendTool, CoreTool
from prompttodraft.backends.local_backend import LocalBackend
from prompttodraft.backends.state_manager import NoOpStateManager
from pydantic import Field

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
    SmolagentsToolClass = tool.to_smolagents_tool(use_string_outputs=True)
    smolagent_instance = SmolagentsToolClass()

    # Verify tool is created with correct type and attributes
    assert issubclass(SmolagentsToolClass, SmolagentsTool)
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
    SmolagentsToolClass = tool.to_smolagents_tool(use_string_outputs=True)
    smolagent_instance = SmolagentsToolClass(backend=backend)

    # Verify tool structure
    assert issubclass(SmolagentsToolClass, SmolagentsTool)
    assert smolagent_instance.name == "backend_tool"
    assert smolagent_instance.description == "Tool that uses backend"
    assert hasattr(smolagent_instance, "backend")
    assert smolagent_instance.backend == backend

    # Test execution with backend
    result = smolagent_instance.forward(command="ls -la")
    assert isinstance(result, BackendOutput)
    assert result.result == "Executed ls -la"
    assert "LocalBackend" in result.status


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
        
    metadata = dict(CalculatorOutput=0, GreeterOutput=0)

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

    # Create tool instances
    calculator = CalculatorTool()
    greeter = GreeterTool()
    
    # Convert to smolagents tools
    CalculatorSmolagentsTool = calculator.to_smolagents_tool(use_string_outputs=True)
    GreeterSmolagentsTool = greeter.to_smolagents_tool(use_string_outputs=True)

    # Create tool instances for the agent
    calculator_tool = CalculatorSmolagentsTool()
    greeter_tool = GreeterSmolagentsTool()

    # Create agent with gpt-5-mini model
    model = InferenceClientModel(model_id="openai/gpt-oss-120b", provider="cerebras")
    agent = ToolCallingAgent(
        tools=[calculator_tool, greeter_tool],
        model=model,
        max_steps=2
    )

    # Test 1: Math task
    result = agent.run(task="What is 15 multiplied by 3?")
    assert "45" in str(result) or "45.0" in str(result), f"Expected result to contain 45, got: {result}"
    assert metadata["CalculatorOutput"] == 1
    assert metadata["GreeterOutput"] == 0

    # Test 2: Greeting task
    result = agent.run(task="Greet Alice in Spanish")
    assert "Hola" in str(result) and "Alice" in str(result), f"Expected Spanish greeting for Alice, got: {result}"
    assert metadata["CalculatorOutput"] == 1
    assert metadata["GreeterOutput"] == 1
    pass

if __name__ == "__main__":
    test_smolagent_tool_created_correctly()
    test_smolagent_tool_backend_created_correctly()
    test_tool_schemas_extracted_correctly()
    test_smolagents_agent_with_llm()
