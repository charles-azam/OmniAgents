"""
Tests for the LS tool using the new 3-layer architecture.

These tests verify that the LS tool works correctly with CodingToolLocal.
"""
import os

from prompttodraft.tools.coding_tools import CodingToolLocal
from prompttodraft.tools.outputs.models import ErrorOutputModel, FileListOutputModel


def verify_ls_results(
    result: FileListOutputModel, expected_files: list[str], should_not_contain: list[str] | None = None
) -> None:
    """
    Verify that the LS result contains the expected files and directories.

    Args:
        result: The result from the LS tool
        expected_files: List of expected filenames or directory names (with trailing / for dirs)
        should_not_contain: List of files that should not be in the result
    """
    assert isinstance(result, FileListOutputModel)

    # Get file names from the result
    file_names = [file.name for file in result.files]
    is_dirs = [file.is_dir for file in result.files]

    # Create a combined list of files with trailing slashes for directories
    formatted_names = []
    for i, name in enumerate(file_names):
        if is_dirs[i]:
            formatted_names.append(f"{name}/")
        else:
            formatted_names.append(name)

    # Check that each expected file is in the results
    for expected_file in expected_files:
        expected_basename = os.path.basename(expected_file.rstrip("/"))
        expected_is_dir = expected_file.endswith("/")

        found = False

        # Check if the file exists in the formatted names
        if expected_file in formatted_names:
            found = True
        # Check if it exists in the base names list
        elif expected_basename in file_names:
            found = True
        # For directories, check without trailing slash
        elif expected_is_dir and any(name == expected_basename for name in file_names):
            found = True
        # Check if the directory is correctly identified
        elif expected_is_dir:
            for i, name in enumerate(file_names):
                if name == expected_basename and is_dirs[i]:
                    found = True
                    break

        assert found, f"Expected file/dir '{expected_file}' not found in LS output. Found: {formatted_names}"

    # Check that none of the excluded files are in the results
    if should_not_contain:
        for excluded_file in should_not_contain:
            excluded_basename = os.path.basename(excluded_file.rstrip("/"))

            found = False

            # Check if the file exists in the formatted names
            if excluded_file in formatted_names:
                found = True
            # Check if it exists in the base names list
            elif excluded_basename in file_names:
                found = True

            assert not found, f"Excluded file '{excluded_file}' was found in LS output"


def test_list_test_directory(test_data_dir: str) -> None:
    """Test listing the test directory."""
    # Setup
    coding_tool = CodingToolLocal()
    path = test_data_dir
    expected_files = [
        "large_file.txt",
        "subfolder1/",
        "test_config.json",
        "test_file1.txt",
        "test_file2.py",
        "test_js_file.js",
        "test_typescript_file.ts",
    ]

    # Execute
    result = coding_tool.ls_tool(path=path)

    # Verify
    verify_ls_results(result=result, expected_files=expected_files)


def test_list_subfolder(test_data_dir: str) -> None:
    """Test listing a subfolder."""
    # Setup
    coding_tool = CodingToolLocal()
    path = os.path.join(test_data_dir, "subfolder1")
    expected_files = ["subfolder2/", "test_component.jsx", "test_file3.txt"]

    # Execute
    result = coding_tool.ls_tool(path=path)

    # Verify
    verify_ls_results(result=result, expected_files=expected_files)


def test_list_nonexistent_directory() -> None:
    """Test listing a directory that doesn't exist."""
    # Setup
    coding_tool = CodingToolLocal()
    path = "/nonexistent/path/to/directory"

    # Execute
    result = coding_tool.ls_tool(path=path)

    # Verify
    assert isinstance(result, ErrorOutputModel)
    assert "does not exist" in result.error or "not found" in result.error.lower()


def test_list_shows_directories(test_data_dir: str) -> None:
    """Test that directories are correctly identified in the listing."""
    # Setup
    coding_tool = CodingToolLocal()
    path = test_data_dir

    # Execute
    result = coding_tool.ls_tool(path=path)

    # Verify
    assert isinstance(result, FileListOutputModel)

    # Find the subfolder1 entry
    subfolder_entry = next((file for file in result.files if file.name == "subfolder1"), None)
    assert subfolder_entry is not None, "subfolder1 not found in results"
    assert subfolder_entry.is_dir is True, "subfolder1 should be marked as a directory"

    # Verify some files are marked as files (not directories)
    file_entry = next((file for file in result.files if file.name == "test_file1.txt"), None)
    assert file_entry is not None, "test_file1.txt not found in results"
    assert file_entry.is_dir is False, "test_file1.txt should be marked as a file"
