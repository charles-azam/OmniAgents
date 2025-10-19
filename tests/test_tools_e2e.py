"""
E2E tests for the new 3-layer tools architecture.

This test verifies that:
1. Output models work correctly
2. LocalBackend executes primitive operations
3. Core tools combine backend + business logic
4. Smolagents adapters work correctly
5. ToolFactory creates tools properly
6. CodingToolLocal integrates everything
"""
import os
import tempfile
import pytest

from prompttodraft.tools.factory import ToolFactory
from prompttodraft.tools.coding_tools import CodingToolLocal
from prompttodraft.tools.outputs.models import (
    TextOutputModel,
    CodeOutputModel,
    FileListOutputModel,
    ErrorOutputModel,
)


def test_factory_creates_smolagents_tools():
    """Test that the factory creates smolagents tools."""
    tools = ToolFactory.create_smolagents_tools(environment="local")

    # Should have 8 tools
    assert len(tools) == 8

    # Check tool names
    tool_names = {tool.name for tool in tools}
    expected_names = {"Bash", "View", "Edit", "Replace", "GlobTool", "GrepTool", "LS", "UserInput"}
    assert tool_names == expected_names


def test_coding_tool_local_bash():
    """Test CodingToolLocal bash command execution."""
    coding_tool = CodingToolLocal()

    # Test simple echo command
    result = coding_tool.bash_tool(command="echo 'Hello World'", timeout=None)

    # Should return TextOutputModel
    assert isinstance(result, TextOutputModel)
    assert "Hello World" in result.content


def test_coding_tool_local_file_operations():
    """Test CodingToolLocal file operations (write, read, edit)."""
    coding_tool = CodingToolLocal()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")

        # Test replace (write) tool
        result = coding_tool.replace_tool(file_path=test_file, content="Hello\nWorld\n")
        assert isinstance(result, TextOutputModel)
        assert "created successfully" in result.content

        # Test view tool
        result = coding_tool.view_tool(file_path=test_file)
        assert isinstance(result, (TextOutputModel, CodeOutputModel))
        assert "Hello" in str(result)

        # Test edit tool
        result = coding_tool.edit_tool(
            file_path=test_file,
            old_string="Hello\nWorld\n",
            new_string="Goodbye\nWorld\n"
        )
        assert isinstance(result, TextOutputModel)
        assert "has been updated" in result.content

        # Verify edit worked
        result = coding_tool.view_tool(file_path=test_file)
        assert "Goodbye" in str(result)


def test_coding_tool_local_glob():
    """Test CodingToolLocal glob tool."""
    coding_tool = CodingToolLocal()

    # Search for Python files in the current directory
    result = coding_tool.glob_tool(pattern="*.py", path=os.getcwd())

    # Should return FileListOutputModel or TextOutputModel
    assert isinstance(result, (FileListOutputModel, TextOutputModel))


def test_coding_tool_local_ls():
    """Test CodingToolLocal ls tool."""
    coding_tool = CodingToolLocal()

    # List current directory
    result = coding_tool.ls_tool(path=os.getcwd())

    # Should return FileListOutputModel
    assert isinstance(result, FileListOutputModel)
    assert len(result.files) > 0


def test_coding_tool_local_grep():
    """Test CodingToolLocal grep tool."""
    coding_tool = CodingToolLocal()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file
        test_file = os.path.join(tmpdir, "test.py")
        coding_tool.replace_tool(
            file_path=test_file,
            content="def hello():\n    print('Hello World')\n"
        )

        # Search for "hello" in the temp directory
        result = coding_tool.grep_tool(pattern="hello", include="*.py", path=tmpdir)

        # Should find the match
        assert isinstance(result, (FileListOutputModel, CodeOutputModel, TextOutputModel))


def test_error_handling():
    """Test that tools return ErrorOutputModel for invalid inputs."""
    coding_tool = CodingToolLocal()

    # Test viewing non-existent file
    result = coding_tool.view_tool(file_path="/nonexistent/file.txt")
    assert isinstance(result, ErrorOutputModel)
    assert "does not exist" in result.error

    # Test banned command
    result = coding_tool.bash_tool(command="curl http://example.com", timeout=None)
    assert isinstance(result, ErrorOutputModel)
    assert "banned" in result.error.lower()


def test_output_model_serialization():
    """Test that output models can be serialized to JSON."""
    # Test TextOutputModel
    text_output = TextOutputModel(content="Hello")
    json_str = text_output.model_dump_json()
    assert "Hello" in json_str

    # Test FileListOutputModel
    from prompttodraft.tools.outputs.models import FileInfo
    file_list = FileListOutputModel(
        files=[
            FileInfo(name="test.py", path="/test.py", is_dir=False, size=100)
        ],
        path="/",
        total_count=1,
        truncated=False
    )
    json_str = file_list.model_dump_json()
    assert "test.py" in json_str


def test_smolagents_adapter_integration():
    """Test that smolagents adapters work correctly."""
    tools = ToolFactory.create_smolagents_tools(environment="local")

    # Get the bash tool
    bash_tool = next(t for t in tools if t.name == "Bash")

    # Execute a command
    result = bash_tool.forward(command="echo 'test'")

    # Should return a string (smolagents compatibility)
    assert isinstance(result, str)
    assert "test" in result
