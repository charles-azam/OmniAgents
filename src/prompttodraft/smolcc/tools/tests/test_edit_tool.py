#!/usr/bin/env python3
"""
Unit tests for the Edit tool.

These tests verify that the Edit tool continues to produce the expected output
for standard inputs, effectively "locking in" the current behavior.
"""

import os

from prompttodraft.smolcc.tools.edit_tool import file_edit_tool


def test_create_new_file(temp_dir: str) -> None:
    """Test creating a new file with the Edit tool."""
    # Mock data
    file_path = os.path.join(temp_dir, "test_edit.txt")
    old_string = ""
    new_string = "This is a test file\nCreated by the Edit tool"
    expected_patterns = [
        "has been updated",
        "This is a test file",
        "Created by the Edit tool"
    ]

    # Make sure the file doesn't exist before the test
    if os.path.exists(file_path):
        os.remove(file_path)

    # Run the tool
    result = file_edit_tool.forward(
        file_path=file_path,
        old_string=old_string,
        new_string=new_string
    )

    # Check that the result contains expected patterns
    for pattern in expected_patterns:
        assert pattern in result

    # Check that the file was actually created with the right content
    assert os.path.exists(file_path)
    with open(file_path, 'r') as f:
        content = f.read()
        assert content == new_string


def test_modify_file_with_context(temp_dir: str) -> None:
    """Test modifying an existing file."""
    # Mock data
    file_path = os.path.join(temp_dir, "test_edit_modify.txt")
    old_string = "function sayHello() {\n  console.log('Hello');\n}\n\nsayHello();"
    new_string = "function sayHello(name) {\n  console.log(`Hello ${name}`);\n}\n\nsayHello('World');"
    expected_patterns = [
        "has been updated",
        "function sayHello(name)",
        "console.log(`Hello ${name}`)",
        "sayHello('World')"
    ]

    # Create test file with initial content
    with open(file_path, 'w') as f:
        f.write(old_string)

    # Run the tool
    result = file_edit_tool.forward(
        file_path=file_path,
        old_string=old_string,
        new_string=new_string
    )

    # Check that the result contains expected patterns
    for pattern in expected_patterns:
        assert pattern in result

    # Check that the file was actually modified with the right content
    with open(file_path, 'r') as f:
        content = f.read()
        assert content == new_string
