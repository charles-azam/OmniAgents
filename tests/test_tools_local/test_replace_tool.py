"""
Tests for the Replace tool using the new 3-layer architecture.

These tests verify that the Replace tool works correctly with CodingToolLocal.
"""
import json
import os

from prompttodraft.tools.coding_tools import CodingToolLocal
from prompttodraft.tools.outputs.models import TextOutputModel


def test_create_new_file(temp_dir: str) -> None:
    """Test creating a new text file."""
    # Setup
    coding_tool = CodingToolLocal()
    file_path = os.path.join(temp_dir, "test_replace.txt")
    content = "This is a test file\nCreated by the Replace tool"
    expected_patterns = ["created successfully", "test_replace.txt"]

    # Remove the file if it exists
    if os.path.exists(file_path):
        os.remove(file_path)

    # Execute
    result = coding_tool.replace_tool(file_path=file_path, content=content)

    # Verify
    assert isinstance(result, TextOutputModel)
    result_str = str(result)

    # Verify the output contains expected patterns
    for pattern in expected_patterns:
        assert pattern in result_str, f"Pattern '{pattern}' not found in result"

    # Verify the file was created with the correct content
    with open(file_path, "r") as f:
        actual_content = f.read()
        assert actual_content == content


def test_create_complex_json_file(temp_dir: str) -> None:
    """Test creating a complex JSON file."""
    # Setup
    coding_tool = CodingToolLocal()
    file_path = os.path.join(temp_dir, "test_replace_complex.json")
    content = json.dumps(
        {
            "name": "test-file",
            "version": "1.0.0",
            "description": "A test JSON file with nested structure",
            "dependencies": {"typescript": "^4.9.5", "react": "^18.2.0"},
            "scripts": {"start": "node dist/index.js", "build": "tsc", "test": "jest"},
            "config": {
                "port": 3000,
                "debug": True,
                "environments": ["development", "staging", "production"],
            },
        },
        indent=2,
    )
    expected_patterns = ["created successfully", "test_replace_complex.json"]

    # Remove the file if it exists
    if os.path.exists(file_path):
        os.remove(file_path)

    # Execute
    result = coding_tool.replace_tool(file_path=file_path, content=content)

    # Verify
    assert isinstance(result, TextOutputModel)
    result_str = str(result)

    # Verify the output contains expected patterns
    for pattern in expected_patterns:
        assert pattern in result_str, f"Pattern '{pattern}' not found in result"

    # Verify the file was created with the correct content
    with open(file_path, "r") as f:
        actual_content = f.read()
        assert actual_content == content

    # Verify the file can be parsed as valid JSON
    with open(file_path, "r") as f:
        parsed_json = json.load(f)
        assert parsed_json["name"] == "test-file"
        assert parsed_json["version"] == "1.0.0"
        assert parsed_json["dependencies"]["typescript"] == "^4.9.5"
        assert parsed_json["dependencies"]["react"] == "^18.2.0"


def test_overwrite_existing_file(temp_dir: str) -> None:
    """Test overwriting an existing file."""
    # Setup
    coding_tool = CodingToolLocal()
    file_path = os.path.join(temp_dir, "test_replace_overwrite.txt")
    initial_content = "Original content"
    new_content = "New content that replaces the old"

    # Create file with initial content
    with open(file_path, "w") as f:
        f.write(initial_content)

    # Execute
    result = coding_tool.replace_tool(file_path=file_path, content=new_content)

    # Verify
    assert isinstance(result, TextOutputModel)

    # Verify the file was overwritten with the new content
    with open(file_path, "r") as f:
        actual_content = f.read()
        assert actual_content == new_content
        assert actual_content != initial_content
