"""
Tests for the Bash tool using the new 3-layer architecture.

These tests verify that the Bash tool works correctly with CodingToolLocal.
"""
from prompttodraft.tools.coding_tools import CodingToolLocal
from prompttodraft.tools.outputs.models import ErrorOutputModel, TextOutputModel


def test_simple_command() -> None:
    """Test a simple echo command."""
    # Setup
    coding_tool = CodingToolLocal()
    command = "echo 'Hello, world!'"
    timeout = 5000

    # Execute
    result = coding_tool.bash_tool(command=command, timeout=timeout)

    # Verify
    assert isinstance(result, TextOutputModel)
    assert "Hello, world" in str(result)


def test_environment_variables() -> None:
    """Test environment variable persistence."""
    # Setup
    coding_tool = CodingToolLocal()
    command = "export TEST_VAR='hello world' && echo $TEST_VAR"
    timeout = 5000

    # Execute
    result = coding_tool.bash_tool(command=command, timeout=timeout)

    # Verify
    assert isinstance(result, TextOutputModel)
    assert "hello world" in str(result)


def test_complex_command_pipeline(test_data_dir: str) -> None:
    """Test a more complex command with piping."""
    # Setup
    coding_tool = CodingToolLocal()
    command = f"find {test_data_dir} -type f -name '*.json' | wc -l"
    timeout = 10000

    # Execute
    result = coding_tool.bash_tool(command=command, timeout=timeout)

    # Verify - should find at least 1 JSON file
    assert isinstance(result, TextOutputModel)
    result_str = str(result).strip()
    # Extract number from output (handling various formats of wc)
    count = int(result_str.split()[-1])
    assert count >= 1, f"Expected at least 1 JSON file, got {count}"


def test_directory_listing_with_details(test_data_dir: str) -> None:
    """Test listing a directory with details."""
    # Setup
    coding_tool = CodingToolLocal()
    command = f"ls -la {test_data_dir} | head -n 20"
    timeout = 5000
    expected_files = [
        "test_file1.txt",
        "test_file2.py",
        "test_js_file.js",
        "test_typescript_file.ts",
        "test_config.json",
    ]

    # Execute
    result = coding_tool.bash_tool(command=command, timeout=timeout)

    # Verify
    assert isinstance(result, TextOutputModel)
    result_str = str(result)
    all_actual_lines = result_str.strip().split("\n")

    # Check that expected files are in the output
    for file in expected_files:
        found = any(file in line for line in all_actual_lines)
        assert found, f"File '{file}' not found in directory listing results"


def test_banned_command() -> None:
    """Test that banned commands are rejected."""
    # Setup
    coding_tool = CodingToolLocal()
    command = "curl http://example.com"
    timeout = 5000

    # Execute
    result = coding_tool.bash_tool(command=command, timeout=timeout)

    # Verify - should return ErrorOutputModel
    assert isinstance(result, ErrorOutputModel)
    assert "banned" in result.error.lower()
