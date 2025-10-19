"""
Tests for the Grep tool using the new 3-layer architecture.

These tests verify that the Grep tool works correctly with CodingToolLocal.
"""
from prompttodraft.tools.coding_tools import CodingToolLocal
from prompttodraft.tools.outputs.models import CodeOutputModel, FileListOutputModel, TextOutputModel


def verify_grep_results(
    result: FileListOutputModel | CodeOutputModel | TextOutputModel,
    expected_count: int,
    expected_files: list[str],
) -> None:
    """
    Verify that the grep result contains the expected files.

    Args:
        result: The result from the grep tool
        expected_count: Expected number of files to find
        expected_files: List of expected filenames (without full paths)
    """
    result_text = str(result)

    # Check if we found files
    if isinstance(result, FileListOutputModel):
        found_count = len(result.files)
        # Verify count matches
        assert (
            found_count == expected_count
        ), f"Expected {expected_count} files, but found {found_count}"

        # Check that each expected file is in the results
        for expected_file in expected_files:
            found = any(expected_file in file.path or expected_file == file.name for file in result.files)
            assert found, f"File '{expected_file}' was not found in grep results"
    else:
        # For CodeOutputModel or TextOutputModel, check the string representation
        # Check that each expected file is mentioned in the output
        for expected_file in expected_files:
            assert expected_file in result_text, f"File '{expected_file}' was not found in grep results"


def test_search_for_function(test_data_dir: str) -> None:
    """Test searching for 'function' keyword."""
    # Setup
    coding_tool = CodingToolLocal()
    pattern = "function"
    path = test_data_dir
    include = "*.{js,jsx,ts,tsx,py}"
    expected_count = 3
    expected_files = ["test_component.jsx", "test_typescript_file.ts", "test_js_file.js"]

    # Execute
    result = coding_tool.grep_tool(pattern=pattern, path=path, include=include)

    # Verify
    assert isinstance(result, (FileListOutputModel, CodeOutputModel, TextOutputModel))
    verify_grep_results(result=result, expected_count=expected_count, expected_files=expected_files)


def test_search_for_class(test_data_dir: str) -> None:
    """Test searching for class definitions."""
    # Setup
    coding_tool = CodingToolLocal()
    pattern = "class\\s+\\w+"
    path = test_data_dir
    include = "*.{js,jsx,ts,tsx,py}"
    expected_count = 3
    expected_files = ["test_js_file.js", "test_typescript_file.ts", "test_component.jsx"]

    # Execute
    result = coding_tool.grep_tool(pattern=pattern, path=path, include=include)

    # Verify
    assert isinstance(result, (FileListOutputModel, CodeOutputModel, TextOutputModel))
    verify_grep_results(result=result, expected_count=expected_count, expected_files=expected_files)


def test_search_for_exports(test_data_dir: str) -> None:
    """Test searching for export statements."""
    # Setup
    coding_tool = CodingToolLocal()
    pattern = "export\\s+"
    path = test_data_dir
    include = "**/*.{js,jsx,ts,tsx}"
    expected_count = 2
    expected_files = ["test_typescript_file.ts", "test_component.jsx"]

    # Execute
    result = coding_tool.grep_tool(pattern=pattern, path=path, include=include)

    # Verify
    assert isinstance(result, (FileListOutputModel, CodeOutputModel, TextOutputModel))
    verify_grep_results(result=result, expected_count=expected_count, expected_files=expected_files)


def test_search_for_react_hooks(test_data_dir: str) -> None:
    """Test searching for React hooks."""
    # Setup
    coding_tool = CodingToolLocal()
    pattern = "use[A-Z]\\w+"
    path = test_data_dir
    include = "**/*.{js,jsx,tsx}"
    expected_count = 1
    expected_files = ["test_component.jsx"]

    # Execute
    result = coding_tool.grep_tool(pattern=pattern, path=path, include=include)

    # Verify
    assert isinstance(result, (FileListOutputModel, CodeOutputModel, TextOutputModel))
    verify_grep_results(result=result, expected_count=expected_count, expected_files=expected_files)


def test_search_no_matches(test_data_dir: str) -> None:
    """Test grep with a pattern that matches no files."""
    # Setup
    coding_tool = CodingToolLocal()
    pattern = "nonexistentpattern123456789"
    path = test_data_dir
    include = "*.{js,jsx,ts,tsx,py}"

    # Execute
    result = coding_tool.grep_tool(pattern=pattern, path=path, include=include)

    # Verify - should return a message indicating no matches
    result_str = str(result)
    assert "No matches found" in result_str or "No files found" in result_str or len(result_str) == 0
