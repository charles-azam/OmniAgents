#!/usr/bin/env python3
"""
Unit tests for the Replace tool.

These tests verify that the Replace tool continues to produce the expected output
for standard inputs, effectively "locking in" the current behavior.
"""

import os
import json

from prompttodraft.smolcc.tools.replace_tool import write_tool


def test_create_new_file(temp_dir: str) -> None:
    """Test creating a new text file."""
    # Mock data
    file_path = os.path.join(temp_dir, "test_replace.txt")
    content = "This is a test file\nCreated by the Replace tool"
    expected_patterns = [
        "File created successfully",
        "test_replace.txt"
    ]

    # Remove the file if it exists
    if os.path.exists(file_path):
        os.remove(file_path)

    # Run the tool
    result = write_tool.forward(file_path=file_path, content=content)

    # Verify the output contains expected patterns
    for pattern in expected_patterns:
        assert pattern in result

    # Verify the file was created with the correct content
    with open(file_path, 'r') as f:
        actual_content = f.read()
        assert actual_content == content


def test_create_complex_json_file(temp_dir: str) -> None:
    """Test creating a complex JSON file."""
    # Mock data
    file_path = os.path.join(temp_dir, "test_replace_complex.json")
    content = json.dumps({
        "name": "test-file",
        "version": "1.0.0",
        "description": "A test JSON file with nested structure",
        "dependencies": {
            "typescript": "^4.9.5",
            "react": "^18.2.0"
        },
        "scripts": {
            "start": "node dist/index.js",
            "build": "tsc",
            "test": "jest"
        },
        "config": {
            "port": 3000,
            "debug": True,
            "environments": ["development", "staging", "production"]
        }
    }, indent=2)
    expected_patterns = [
        "File created successfully",
        "test_replace_complex.json"
    ]

    # Remove the file if it exists
    if os.path.exists(file_path):
        os.remove(file_path)

    # Run the tool
    result = write_tool.forward(file_path=file_path, content=content)

    # Verify the output contains expected patterns
    for pattern in expected_patterns:
        assert pattern in result

    # Verify the file was created with the correct content
    with open(file_path, 'r') as f:
        actual_content = f.read()
        assert actual_content == content

    # Verify the file can be parsed as valid JSON
    with open(file_path, 'r') as f:
        parsed_json = json.load(f)
        assert parsed_json["name"] == "test-file"
        assert parsed_json["version"] == "1.0.0"
        assert parsed_json["dependencies"]["typescript"] == "^4.9.5"
        assert parsed_json["dependencies"]["react"] == "^18.2.0"
