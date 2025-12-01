# Test tool calling with the different frameworks, huggingface and openai
# test that each framework as expected
from prompttodraft.tools.base_tool import CoreBackendTool, CoreTool
from prompttodraft.backends.execution_backend import ExecutionBackend


def test_smolagent_tool_created_correctly():

    class SimpleInput(BaseModel):
        path: str
    
    class SimpleOutput(BaseModel):
        content: str
    
    class SimpleTool(CoreTool[SimpleInput, SimpleOutput]):
        name = "simple_tool"
        description = "Does something"
        
        def execute(self, inputs: SimpleInput) -> SimpleOutput:
            return SimpleOutput(content="done")
    
    tool = SimpleTool()
    smolagent_tool = tool.to_smolagents_tool()
    assert isinstance(smolagent_tool, SmolagentsTool    )

def test_smolagent_tool_backend_created_correctly():
    pass