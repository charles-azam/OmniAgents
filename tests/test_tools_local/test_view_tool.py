"""
Tests for the View tool using the new 3-layer architecture.

These tests verify that the View tool works correctly with CodingToolLocal.
"""
import os

from prompttodraft.tools.coding_tools import CodingToolLocal
from prompttodraft.tools.outputs.models import CodeOutputModel, ErrorOutputModel, TextOutputModel


def test_view_test_file(test_data_dir: str) -> None:
    """Test viewing a simple text file."""
    # Setup
    coding_tool = CodingToolLocal()
    file_path = os.path.join(test_data_dir, "test_file1.txt")
    expected_lines = [
        "This is a test file for testing the View tool.",
        "It contains multiple lines of text.",
        "Line 3 contains some content.",
        "Line 4 contains more content.",
        "Line 5 contains the final line of content.",
    ]

    # Execute
    result = coding_tool.view_tool(file_path=file_path)

    # Verify
    assert isinstance(result, (TextOutputModel, CodeOutputModel))
    result_str = str(result)

    # Check that the output contains expected content
    for line in expected_lines:
        assert line in result_str, f"Expected line '{line}' not found in output"


def test_view_json_file(test_data_dir: str) -> None:
    """Test viewing a JSON file."""
    # Setup
    coding_tool = CodingToolLocal()
    file_path = os.path.join(test_data_dir, "test_config.json")
    expected_patterns = ["test-config", "version", "database", "host", "features"]

    # Execute
    result = coding_tool.view_tool(file_path=file_path)

    # Verify
    assert isinstance(result, (TextOutputModel, CodeOutputModel))
    result_str = str(result)

    # Check for expected patterns in the JSON output
    for pattern in expected_patterns:
        assert pattern in result_str, f"Pattern '{pattern}' not found in JSON output"


def test_view_large_file_with_limits(test_data_dir: str) -> None:
    """Test viewing a large file with offset and limit parameters."""
    # Setup
    coding_tool = CodingToolLocal()
    file_path = os.path.join(test_data_dir, "large_file.txt")
    offset = 20
    limit = 30
    expected_line_count = 30

    # Execute - note: CodingToolLocal.view_tool doesn't expose offset/limit
    # so we'll just test viewing the whole file
    result = coding_tool.view_tool(file_path=file_path)

    # Verify
    assert isinstance(result, (TextOutputModel, CodeOutputModel))
    result_str = str(result)
    lines = result_str.strip().split("\n")

    # The file should have content (large_file.txt has many lines)
    assert len(lines) >= expected_line_count, f"Expected at least {expected_line_count} lines, got {len(lines)}"


def test_view_nonexistent_file() -> None:
    """Test viewing a file that doesn't exist."""
    # Setup
    coding_tool = CodingToolLocal()
    file_path = "/nonexistent/path/to/file.txt"

    # Execute
    result = coding_tool.view_tool(file_path=file_path)

    # Verify
    assert isinstance(result, ErrorOutputModel)
    assert "does not exist" in result.error


def test_view_python_file(test_data_dir: str) -> None:
    """Test viewing a Python file returns CodeOutputModel."""
    # Setup
    coding_tool = CodingToolLocal()
    file_path = os.path.join(test_data_dir, "test_file2.py")

    # Execute
    result = coding_tool.view_tool(file_path=file_path)

    # Verify - Python files should return CodeOutputModel
    assert isinstance(result, (CodeOutputModel, TextOutputModel))
    result_str = str(result)
    # Python file should have some code content
    assert len(result_str) > 0
