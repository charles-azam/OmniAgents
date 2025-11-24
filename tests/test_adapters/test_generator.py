"""
Tests for the automatic adapter generator.

These tests verify that the adapter generators correctly create
framework-specific tool wrappers from core tools.
"""
import pytest
from dataclasses import dataclass
from unittest.mock import MagicMock

from prompttodraft.adapters.generator import (
    generate_smolagents_tools,
    generate_langchain_tools,
    generate_pydantic_ai_tools,
    get_all_core_tool_classes,
    get_python_type_for_input,
    extract_parameter_info,
    _type_to_str,
)
from prompttodraft.tools.metadata import ToolMetadata
from prompttodraft.backends.execution_backend import ExecutionBackend


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_backend() -> MagicMock:
    """Create a mock execution backend for testing."""
    backend = MagicMock(spec=ExecutionBackend)
    backend.get_working_directory.return_value = "/tmp/test"
    backend.write_file.return_value = None
    backend.read_file.return_value = "file content"
    backend.file_exists.return_value = None
    return backend


@dataclass
class TestDependencies:
    """Test dependencies for Pydantic-AI adapter testing."""
    backend: ExecutionBackend


# =============================================================================
# Test Utility Functions
# =============================================================================

def test_get_python_type_for_input_string():
    """Test type conversion for string inputs."""
    input_spec = {"type": "string", "description": "A string"}
    result = get_python_type_for_input(input_spec)
    assert result is str


def test_get_python_type_for_input_number():
    """Test type conversion for number inputs."""
    input_spec = {"type": "number", "description": "A number"}
    result = get_python_type_for_input(input_spec)
    assert result is int


def test_get_python_type_for_input_boolean():
    """Test type conversion for boolean inputs."""
    input_spec = {"type": "boolean", "description": "A boolean"}
    result = get_python_type_for_input(input_spec)
    assert result is bool


def test_get_python_type_for_input_nullable():
    """Test type conversion for nullable inputs."""
    input_spec = {"type": "string", "nullable": True}
    result = get_python_type_for_input(input_spec)
    # Should be str | None
    assert str in result.__args__
    assert type(None) in result.__args__


def test_get_python_type_for_input_array():
    """Test type conversion for array inputs."""
    input_spec = {"type": "array", "items": {"type": "string"}}
    result = get_python_type_for_input(input_spec)
    assert result == list[str]


def test_extract_parameter_info():
    """Test parameter extraction from tool metadata."""
    metadata = ToolMetadata(
        name="test_tool",
        description="A test tool",
        inputs={
            "required_param": {"type": "string", "description": "Required"},
            "optional_param": {"type": "number", "nullable": True, "description": "Optional"},
        },
        output_type="string",
    )

    params = extract_parameter_info(metadata)

    # Required params should come first
    assert len(params) == 2
    assert params[0][0] == "required_param"
    assert params[0][2] is ...  # No default (required)
    assert params[1][0] == "optional_param"
    assert params[1][2] is None  # Default is None (optional)


def test_type_to_str_basic():
    """Test type to string conversion for basic types."""
    assert _type_to_str(str) == "str"
    assert _type_to_str(int) == "int"
    assert _type_to_str(bool) == "bool"
    assert _type_to_str(list) == "list"


def test_type_to_str_union():
    """Test type to string conversion for union types."""
    result = _type_to_str(str | None)
    assert "str" in result
    assert "None" in result


def test_type_to_str_generic_list():
    """Test type to string conversion for generic list types."""
    result = _type_to_str(list[str])
    assert result == "list[str]"


# =============================================================================
# Test Core Tool Discovery
# =============================================================================

def test_get_all_core_tool_classes():
    """Test that all core tool classes are discovered."""
    tool_classes = get_all_core_tool_classes()

    assert len(tool_classes) == 10

    tool_names = [tc.__name__ for tc in tool_classes]
    assert "WriteFileTool" in tool_names
    assert "ReadFileTool" in tool_names
    assert "ListDirectoryTool" in tool_names
    assert "GlobTool" in tool_names
    assert "SearchFileContentTool" in tool_names
    assert "ReplaceTool" in tool_names
    assert "RunShellCommandTool" in tool_names
    assert "ReadManyFilesTool" in tool_names
    assert "SaveMemoryTool" in tool_names
    assert "UVTool" in tool_names


# =============================================================================
# Test smolagents Adapter Generation
# =============================================================================

def test_generate_smolagents_tools_all(mock_backend: MagicMock):
    """Test generating all smolagents tools."""
    tools = generate_smolagents_tools(backend=mock_backend)

    assert len(tools) == 10

    # Check that each tool has required attributes
    for tool in tools:
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert hasattr(tool, "inputs")
        assert hasattr(tool, "output_type")
        assert hasattr(tool, "forward")


def test_generate_smolagents_tools_subset(mock_backend: MagicMock):
    """Test generating a subset of smolagents tools."""
    from prompttodraft.tools.write_file_tool import WriteFileTool
    from prompttodraft.tools.read_file_tool import ReadFileTool

    tools = generate_smolagents_tools(
        backend=mock_backend,
        tool_classes=[WriteFileTool, ReadFileTool],
    )

    assert len(tools) == 2

    tool_names = [t.name for t in tools]
    assert "write_file" in tool_names
    assert "read_file" in tool_names


def test_generate_smolagents_tool_execution(mock_backend: MagicMock):
    """Test that generated smolagents tools can execute."""
    from prompttodraft.tools.write_file_tool import WriteFileTool

    tools = generate_smolagents_tools(
        backend=mock_backend,
        tool_classes=[WriteFileTool],
    )

    tool = tools[0]

    # Execute the tool
    result = tool.forward(file_path="/tmp/test.txt", content="hello")

    # Verify backend was called
    mock_backend.file_exists.assert_called_once()
    mock_backend.write_file.assert_called_once_with(
        file_path="/tmp/test.txt",
        content="hello",
    )

    # Result should be a string
    assert isinstance(result, str)


# =============================================================================
# Test LangChain Adapter Generation
# =============================================================================

def test_generate_langchain_tools_all(mock_backend: MagicMock):
    """Test generating all LangChain tools."""
    tools = generate_langchain_tools(backend=mock_backend)

    assert len(tools) == 10

    # Check that each tool has required attributes and can be invoked
    for tool in tools:
        assert hasattr(tool, "invoke")
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")


def test_generate_langchain_tools_subset(mock_backend: MagicMock):
    """Test generating a subset of LangChain tools."""
    from prompttodraft.tools.write_file_tool import WriteFileTool
    from prompttodraft.tools.read_file_tool import ReadFileTool

    tools = generate_langchain_tools(
        backend=mock_backend,
        tool_classes=[WriteFileTool, ReadFileTool],
    )

    assert len(tools) == 2


def test_generate_langchain_tool_execution(mock_backend: MagicMock):
    """Test that generated LangChain tools can execute."""
    from prompttodraft.tools.write_file_tool import WriteFileTool

    tools = generate_langchain_tools(
        backend=mock_backend,
        tool_classes=[WriteFileTool],
    )

    tool = tools[0]

    # Execute the tool via invoke
    result = tool.invoke({"file_path": "/tmp/test.txt", "content": "hello"})

    # Verify backend was called
    mock_backend.write_file.assert_called_once()

    # Result should be a string
    assert isinstance(result, str)


# =============================================================================
# Test Pydantic-AI Adapter Generation
# =============================================================================

def test_generate_pydantic_ai_tools_all():
    """Test generating all Pydantic-AI tools."""
    tools = generate_pydantic_ai_tools(
        deps_type=TestDependencies,
        backend_attr="backend",
    )

    assert len(tools) == 10

    # Check that each tool has required attributes
    for tool in tools:
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert tool.takes_ctx is True


def test_generate_pydantic_ai_tools_subset():
    """Test generating a subset of Pydantic-AI tools."""
    from prompttodraft.tools.write_file_tool import WriteFileTool
    from prompttodraft.tools.read_file_tool import ReadFileTool

    tools = generate_pydantic_ai_tools(
        deps_type=TestDependencies,
        backend_attr="backend",
        tool_classes=[WriteFileTool, ReadFileTool],
    )

    assert len(tools) == 2

    tool_names = [t.name for t in tools]
    assert "write_file" in tool_names
    assert "read_file" in tool_names


# =============================================================================
# Test Tool Metadata Preservation
# =============================================================================

def test_smolagents_preserves_metadata(mock_backend: MagicMock):
    """Test that smolagents adapter preserves tool metadata."""
    from prompttodraft.tools.write_file_tool import WriteFileTool

    tools = generate_smolagents_tools(
        backend=mock_backend,
        tool_classes=[WriteFileTool],
    )

    tool = tools[0]
    original_metadata = WriteFileTool.metadata

    assert tool.name == original_metadata.name
    assert tool.description == original_metadata.description
    assert tool.output_type == original_metadata.output_type

    # Check inputs match
    for input_name in original_metadata.inputs:
        assert input_name in tool.inputs


def test_langchain_preserves_metadata(mock_backend: MagicMock):
    """Test that LangChain adapter preserves tool metadata."""
    from prompttodraft.tools.write_file_tool import WriteFileTool

    tools = generate_langchain_tools(
        backend=mock_backend,
        tool_classes=[WriteFileTool],
    )

    tool = tools[0]
    original_metadata = WriteFileTool.metadata

    assert tool.name == original_metadata.name
    assert tool.description == original_metadata.description


def test_pydantic_ai_preserves_metadata():
    """Test that Pydantic-AI adapter preserves tool metadata."""
    from prompttodraft.tools.write_file_tool import WriteFileTool

    tools = generate_pydantic_ai_tools(
        deps_type=TestDependencies,
        backend_attr="backend",
        tool_classes=[WriteFileTool],
    )

    tool = tools[0]
    original_metadata = WriteFileTool.metadata

    assert tool.name == original_metadata.name
    assert tool.description == original_metadata.description


# =============================================================================
# E2E Test: Full Tool Generation and Execution
# =============================================================================

def test_e2e_smolagents_write_and_read(mock_backend: MagicMock):
    """E2E test: Generate smolagents tools and execute write then read."""
    from prompttodraft.tools.write_file_tool import WriteFileTool
    from prompttodraft.tools.read_file_tool import ReadFileTool
    from prompttodraft.backends.execution_backend import FileType

    # Setup mock for file operations
    mock_backend.file_exists.return_value = FileType.FILE
    mock_backend.read_file.return_value = "test content"

    # Generate tools
    tools = generate_smolagents_tools(
        backend=mock_backend,
        tool_classes=[WriteFileTool, ReadFileTool],
    )

    write_tool = next(t for t in tools if t.name == "write_file")
    read_tool = next(t for t in tools if t.name == "read_file")

    # Write a file (file_exists returns FileType.FILE so it appears to exist)
    write_result = write_tool.forward(file_path="/tmp/test.txt", content="test content")
    assert "Successfully" in write_result

    # Read the file
    read_result = read_tool.forward(path="/tmp/test.txt")
    assert "test content" in read_result


def test_e2e_langchain_write_and_read(mock_backend: MagicMock):
    """E2E test: Generate LangChain tools and execute write then read."""
    from prompttodraft.tools.write_file_tool import WriteFileTool
    from prompttodraft.tools.read_file_tool import ReadFileTool
    from prompttodraft.backends.execution_backend import FileType

    # Setup mock for file operations
    mock_backend.file_exists.return_value = FileType.FILE
    mock_backend.read_file.return_value = "test content"

    # Generate tools
    tools = generate_langchain_tools(
        backend=mock_backend,
        tool_classes=[WriteFileTool, ReadFileTool],
    )

    write_tool = next(t for t in tools if t.name == "write_file")
    read_tool = next(t for t in tools if t.name == "read_file")

    # Write a file
    write_result = write_tool.invoke({"file_path": "/tmp/test.txt", "content": "test content"})
    assert "Successfully" in write_result

    # Read the file
    read_result = read_tool.invoke({"path": "/tmp/test.txt"})
    assert "test content" in read_result
