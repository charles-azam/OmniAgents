#!/usr/bin/env python3
"""
Unit tests for the Bash tool.

These tests verify that the Bash tool continues to produce the expected output
for standard inputs, effectively "locking in" the current behavior.
"""

from prompttodraft.smolcc.tools.bash_tool import bash_tool
from prompttodraft.smolcc.tool_output import ToolOutput


def test_simple_command() -> None:
    """Test a simple echo command."""
    # Mock data
    command = "echo 'Hello, world!'"
    timeout = 5000
    expected = "Hello, world\\!"

    # Run the tool
    result = bash_tool.forward(command=command, timeout=timeout)

    # Check output
    assert isinstance(result, ToolOutput)
    assert str(result) == expected


def test_environment_variables() -> None:
    """Test environment variable persistence."""
    # Mock data
    command = "export TEST_VAR='hello world' && echo $TEST_VAR"
    timeout = 5000
    expected = "hello world"

    # Run the tool
    result = bash_tool.forward(command=command, timeout=timeout)

    # Check output
    assert isinstance(result, ToolOutput)
    assert str(result) == expected


def test_complex_command_pipeline(test_data_dir: str) -> None:
    """Test a more complex command with piping."""
    # Mock data
    command = f"find {test_data_dir} -type f -name '*.json' | wc -l"
    timeout = 10000
    expected = "       1"

    # Run the tool
    result = bash_tool.forward(command=command, timeout=timeout)

    # Check output
    assert isinstance(result, ToolOutput)
    assert str(result) == expected


def test_directory_listing_with_details(test_data_dir: str) -> None:
    """Test listing a directory with details."""
    # Mock data
    command = f"ls -la {test_data_dir} | head -n 20"
    timeout = 5000
    expected_files = [
        "test_file1.txt",
        "test_file2.py",
        "test_js_file.js",
        "test_typescript_file.ts",
        "test_config.json"
    ]

    # Run the tool
    result = bash_tool.forward(command=command, timeout=timeout)

    # Check output
    assert isinstance(result, ToolOutput)

    # Instead of comparing specific lines which may vary, check for expected files
    all_actual_lines = str(result).strip().split('\n')

    # These should be unique files from the test data directory
    for file in expected_files:
        found = any(file in line for line in all_actual_lines)
        assert found, f"File '{file}' not found in directory listing results"
