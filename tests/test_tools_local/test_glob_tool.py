"""
Tests for the Glob tool using the new 3-layer architecture.

These tests verify that the Glob tool works correctly with CodingToolLocal.
"""
import os

from prompttodraft.tools.coding_tools import CodingToolLocal
from prompttodraft.tools.outputs.models import FileListOutputModel, TextOutputModel


def verify_glob_results(
    result: FileListOutputModel | TextOutputModel, expected_files: list[str], test_data_dir: str
) -> None:
    """
    Verify that the glob result contains the expected files.

    Args:
        result: The result from the glob tool
        expected_files: List of expected filenames (without full paths)
        test_data_dir: The test data directory path
    """
    # Handle FileListOutputModel
    if isinstance(result, FileListOutputModel):
        found_files = [file.name for file in result.files]
        found_paths = [file.path for file in result.files]
    else:
        # TextOutputModel - might be "No files found"
        result_str = str(result)
        if "No files found" in result_str:
            found_files = []
            found_paths = []
        else:
            found_files = result_str.strip().split("\n")
            found_paths = found_files

    # Verify we found the right number of files
    assert len(found_files) == len(
        expected_files
    ), f"Expected {len(expected_files)} files, but found {len(found_files)}: {found_files}"

    # Check that each expected file is in the results
    for expected_file in expected_files:
        found = False
        expected_basename = os.path.basename(expected_file)

        # Try exact match on basename
        if expected_basename in found_files:
            found = True
        # Try path contains check
        elif any(expected_file in path for path in found_paths):
            found = True
        # Try basename contains check on all paths
        elif any(expected_basename in os.path.basename(path) for path in found_paths):
            found = True

        assert found, f"File '{expected_file}' was not found in glob results: {found_files}"


def test_find_text_files(test_data_dir: str) -> None:
    """Test finding text files with a simple pattern."""
    # Setup
    coding_tool = CodingToolLocal()
    pattern = "*.txt"
    path = test_data_dir
    expected_files = ["test_file1.txt", "large_file.txt"]

    # Execute
    result = coding_tool.glob_tool(pattern=pattern, path=path)

    # Verify
    assert isinstance(result, (FileListOutputModel, TextOutputModel))
    verify_glob_results(result=result, expected_files=expected_files, test_data_dir=test_data_dir)


def test_find_all_recursively(test_data_dir: str) -> None:
    """Test finding all files recursively."""
    # Setup
    coding_tool = CodingToolLocal()
    pattern = "**/*.*"
    path = test_data_dir
    expected_files = [
        "test_file1.txt",
        "large_file.txt",
        "test_config.json",
        "test_file2.py",
        "test_js_file.js",
        "test_typescript_file.ts",
        "test_file3.txt",
        "test_component.jsx",
        "test_config.yml",
    ]

    # Execute
    result = coding_tool.glob_tool(pattern=pattern, path=path)

    # Verify
    assert isinstance(result, (FileListOutputModel, TextOutputModel))
    verify_glob_results(result=result, expected_files=expected_files, test_data_dir=test_data_dir)


def test_find_config_files(test_data_dir: str) -> None:
    """Test finding config files with a complex pattern."""
    # Setup
    coding_tool = CodingToolLocal()
    pattern = "**/*config*.*"
    path = test_data_dir
    expected_files = ["test_config.json", "test_config.yml"]

    # Execute
    result = coding_tool.glob_tool(pattern=pattern, path=path)

    # Verify
    assert isinstance(result, (FileListOutputModel, TextOutputModel))
    verify_glob_results(result=result, expected_files=expected_files, test_data_dir=test_data_dir)


def test_find_no_matches(test_data_dir: str) -> None:
    """Test glob with a pattern that matches no files."""
    # Setup
    coding_tool = CodingToolLocal()
    pattern = "*.nonexistent"
    path = test_data_dir

    # Execute
    result = coding_tool.glob_tool(pattern=pattern, path=path)

    # Verify
    assert isinstance(result, TextOutputModel)
    assert "No files found" in str(result)
