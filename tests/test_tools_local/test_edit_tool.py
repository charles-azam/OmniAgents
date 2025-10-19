"""
Tests for the Edit tool using the new 3-layer architecture.

These tests verify that the Edit tool works correctly with CodingToolLocal.
"""
import os

from prompttodraft.tools.coding_tools import CodingToolLocal
from prompttodraft.tools.outputs.models import ErrorOutputModel, TextOutputModel


def test_create_new_file(temp_dir: str) -> None:
    """Test creating a new file with the Edit tool."""
    # Setup
    coding_tool = CodingToolLocal()
    file_path = os.path.join(temp_dir, "test_edit.txt")
    old_string = ""
    new_string = "This is a test file\nCreated by the Edit tool"
    expected_patterns = ["has been updated", "This is a test file", "Created by the Edit tool"]

    # Make sure the file doesn't exist before the test
    if os.path.exists(file_path):
        os.remove(file_path)

    # Execute
    result = coding_tool.edit_tool(file_path=file_path, old_string=old_string, new_string=new_string)

    # Verify
    assert isinstance(result, TextOutputModel)
    result_str = str(result)

    # Check that the result contains expected patterns
    for pattern in expected_patterns:
        assert pattern in result_str, f"Pattern '{pattern}' not found in result"

    # Check that the file was actually created with the right content
    assert os.path.exists(file_path), "File was not created"
    with open(file_path, "r") as f:
        content = f.read()
        assert content == new_string


def test_modify_file_with_context(temp_dir: str) -> None:
    """Test modifying an existing file."""
    # Setup
    coding_tool = CodingToolLocal()
    file_path = os.path.join(temp_dir, "test_edit_modify.txt")
    old_string = "function sayHello() {\n  console.log('Hello');\n}\n\nsayHello();"
    new_string = "function sayHello(name) {\n  console.log(`Hello ${name}`);\n}\n\nsayHello('World');"
    expected_patterns = [
        "has been updated",
        "function sayHello(name)",
        "console.log(`Hello ${name}`)",
        "sayHello('World')",
    ]

    # Create test file with initial content
    with open(file_path, "w") as f:
        f.write(old_string)

    # Execute
    result = coding_tool.edit_tool(file_path=file_path, old_string=old_string, new_string=new_string)

    # Verify
    assert isinstance(result, TextOutputModel)
    result_str = str(result)

    # Check that the result contains expected patterns
    for pattern in expected_patterns:
        assert pattern in result_str, f"Pattern '{pattern}' not found in result"

    # Check that the file was actually modified with the right content
    with open(file_path, "r") as f:
        content = f.read()
        assert content == new_string


def test_edit_nonexistent_file() -> None:
    """Test editing a file that doesn't exist."""
    # Setup
    coding_tool = CodingToolLocal()
    file_path = "/nonexistent/path/to/file.txt"
    old_string = "old content"
    new_string = "new content"

    # Execute
    result = coding_tool.edit_tool(file_path=file_path, old_string=old_string, new_string=new_string)

    # Verify
    assert isinstance(result, ErrorOutputModel)
    assert "does not exist" in result.error


def test_edit_string_not_found(temp_dir: str) -> None:
    """Test editing when the old_string is not found."""
    # Setup
    coding_tool = CodingToolLocal()
    file_path = os.path.join(temp_dir, "test_edit_not_found.txt")
    initial_content = "This is the original content"
    old_string = "nonexistent string"
    new_string = "new content"

    # Create test file with initial content
    with open(file_path, "w") as f:
        f.write(initial_content)

    # Execute
    result = coding_tool.edit_tool(file_path=file_path, old_string=old_string, new_string=new_string)

    # Verify
    assert isinstance(result, ErrorOutputModel)
    assert "not found" in result.error.lower()
