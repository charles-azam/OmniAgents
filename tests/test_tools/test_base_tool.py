"""
Simple tests for base_tool.py Generic typing functionality.

Tests the helper methods (get_input_model, get_output_model, get_input_schema)
using fake tools created just for testing.
"""
from pydantic import BaseModel, Field
import pytest

from prompttodraft.tools.base_tool import CoreTool, CoreBackendTool
from prompttodraft.outputs.outputs import TextOutputModel, ToolOutputModel
from prompttodraft.backends.local_backend import LocalBackend
from prompttodraft.backends.state_manager import NoOpStateManager


# =============================================================================
# Fake Tools for Testing
# =============================================================================

class FakeInput(BaseModel):
    """Fake input model for testing."""
    message: str = Field(description="A test message")
    count: int = Field(default=1, description="Repeat count")


class FakeTool(CoreBackendTool[FakeInput, TextOutputModel]):
    """Fake tool for testing Generic typing."""
    name = "fake_tool"
    description = "A fake tool for testing"

    def execute(self, inputs: FakeInput) -> TextOutputModel:
        result = inputs.message * inputs.count
        return TextOutputModel(content=result)


# =============================================================================
# Tests
# =============================================================================

def test_get_input_model():
    """Test that get_input_model() extracts the correct type."""
    input_model = FakeTool.get_input_model()

    assert input_model is FakeInput
    assert input_model.__name__ == "FakeInput"


def test_get_output_model():
    """Test that get_output_model() extracts the correct type."""
    output_model = FakeTool.get_output_model()

    assert output_model is TextOutputModel
    assert output_model.__name__ == "TextOutputModel"


def test_get_input_schema():
    """Test that get_input_schema() returns valid JSON Schema."""
    schema = FakeTool.get_input_schema()

    assert isinstance(schema, dict)
    assert "properties" in schema
    assert "message" in schema["properties"]
    assert "count" in schema["properties"]
    assert schema["properties"]["message"]["type"] == "string"
    assert schema["properties"]["count"]["type"] == "integer"


def test_tool_execution_with_correct_types():
    """Test that the tool executes correctly with proper types."""
    backend = LocalBackend(project_id="test", state_manager=NoOpStateManager())
    backend.start()

    try:
        tool = FakeTool(backend=backend)

        # Execute with proper input
        inputs = FakeInput(message="Hello", count=3)
        result = tool.execute(inputs=inputs)

        # Check result type and content
        assert isinstance(result, TextOutputModel)
        assert result.content == "HelloHelloHello"

    finally:
        backend.shutdown()




if __name__ == "__main__":
    print("Running base_tool.py tests...\n")

    print("1. Testing get_input_model()...")
    test_get_input_model()
    print("   ✓ Passed\n")

    print("2. Testing get_output_model()...")
    test_get_output_model()
    print("   ✓ Passed\n")

    print("3. Testing get_input_schema()...")
    test_get_input_schema()
    print("   ✓ Passed\n")

    print("4. Testing tool execution with correct types...")
    test_tool_execution_with_correct_types()
    print("   ✓ Passed\n")

    print("="*60)
    print("✅ All base_tool.py tests passed!")
    print("="*60)
