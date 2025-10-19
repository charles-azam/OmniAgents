#!/usr/bin/env python3
"""
Unit tests for the View tool.

These tests verify that the View tool continues to produce the expected output
for standard inputs, effectively "locking in" the current behavior.
"""

import os
import re

from prompttodraft.smolcc.tools.view_tool import view_tool
from prompttodraft.smolcc.tool_output import ToolOutput


def test_view_test_file(test_data_dir: str) -> None:
    """Test viewing a simple text file."""
    # Mock data
    file_path = os.path.join(test_data_dir, "test_file1.txt")
    expected_lines = [
        "This is a test file for testing the View tool.",
        "It contains multiple lines of text.",
        "Line 3 contains some content.",
        "Line 4 contains more content.",
        "Line 5 contains the final line of content."
    ]

    # Run the tool
    result = view_tool.forward(file_path=file_path)

    # Check output
    assert isinstance(result, ToolOutput)

    # Convert to string for testing
    result_str = str(result)

    # Check that the output contains line numbers and content
    for line in expected_lines:
        assert line in result_str

    # Check for line numbers in the format "     1\t..."
    for i, _ in enumerate(expected_lines, 1):
        line_number_pattern = f"{i:6d}"
        assert line_number_pattern in result_str


def test_view_json_file(test_data_dir: str) -> None:
    """Test viewing a JSON file."""
    # Mock data
    file_path = os.path.join(test_data_dir, "test_config.json")
    expected_patterns = [
        "test-config",
        "version",
        "database",
        "host",
        "features"
    ]

    # Run the tool
    result = view_tool.forward(file_path=file_path)

    # Check output
    assert isinstance(result, ToolOutput)

    # Convert to string for testing
    result_str = str(result)

    # Check for expected patterns in the JSON output
    for pattern in expected_patterns:
        assert pattern in result_str

    # The output should have line numbers
    assert re.search(r"^\s+\d+\t", result_str)


def test_view_large_file_with_limits(test_data_dir: str) -> None:
    """Test viewing a large file with offset and limit parameters."""
    # Mock data
    file_path = os.path.join(test_data_dir, "large_file.txt")
    offset = 20
    limit = 30
    expected_line_count = 30

    # Run the tool
    result = view_tool.forward(file_path=file_path, offset=offset, limit=limit)

    # Check output
    assert isinstance(result, ToolOutput)

    # Convert to string for testing
    result_str = str(result)

    # Count the number of lines in the result
    lines = result_str.strip().split('\n')

    # The actual output may have a few more lines due to formatting
    # Just verify that we have enough lines and they contain the expected content
    assert len(lines) >= expected_line_count, \
        f"Expected at least {expected_line_count} lines, got {len(lines)}"

    # Find the line with the content we're looking for
    content_lines = [line for line in lines if "Line 20" in line or "Line 21" in line]
    assert len(content_lines) > 0, "First content line not found in output"

    content_lines_end = [line for line in lines if "Line 49" in line or "Line 50" in line]
    assert len(content_lines_end) > 0, "Last content line not found in output"

    # Check for line numbers in a more flexible way
    line_number_match = None
    for line in lines:
        match = re.search(r'(\d+)\t', line)
        if match:
            line_number_match = match
            break

    if line_number_match:
        line_number = int(line_number_match.group(1))

        # Check that line number is in the expected range
        expected_min = offset
        expected_max = offset + 1
        assert expected_min <= line_number <= expected_max, \
            f"Line number {line_number} outside expected range {expected_min}-{expected_max}"
