"""
Comprehensive E2E tests for the 3-layer tools architecture.

Tests the complete workflow of creating, editing, searching, and managing files
using the tools architecture with mock data setup at the beginning and
verification at the end.
"""
import os
import tempfile
from pathlib import Path

from prompttodraft.tools.coding_tools import CodingToolLocal
from prompttodraft.tools.factory import ToolFactory
from prompttodraft.tools.outputs.models import (
    CodeOutputModel,
    ErrorOutputModel,
    FileListOutputModel,
    TextOutputModel,
)
from prompttodraft.tools.outputs.renderers import APIRenderer


def test_complete_development_workflow():
    """
    E2E test simulating a complete development workflow:
    1. Create a project structure with multiple files
    2. View and verify file contents
    3. Edit files to fix issues
    4. Search for patterns across files
    5. List and glob to find files
    6. Verify all operations completed successfully
    """
    # Setup: Create mock project structure
    coding_tool = CodingToolLocal()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock data: Create a simple Python project
        main_file = os.path.join(tmpdir, "main.py")
        utils_file = os.path.join(tmpdir, "utils.py")
        test_file = os.path.join(tmpdir, "test_utils.py")
        readme_file = os.path.join(tmpdir, "README.md")

        main_content = """def main():
    print("Hello World")
    calculate_sum(1, 2)

if __name__ == "__main__":
    main()
"""

        utils_content = """def calculate_sum(a, b):
    return a + b

def calculate_product(a, b):
    # TODO: implement this
    pass
"""

        test_content = """from utils import calculate_sum

def test_calculate_sum():
    result = calculate_sum(2, 3)
    assert result == 5
"""

        readme_content = """# My Project

A simple calculator project.

## Features
- Addition
- Multiplication (coming soon)
"""

        # Step 1: Create all files using replace_tool
        main_result = coding_tool.replace_tool(file_path=main_file, content=main_content)
        utils_result = coding_tool.replace_tool(file_path=utils_file, content=utils_content)
        test_result = coding_tool.replace_tool(file_path=test_file, content=test_content)
        readme_result = coding_tool.replace_tool(file_path=readme_file, content=readme_content)

        # Step 2: List directory to verify all files created
        ls_result = coding_tool.ls_tool(path=tmpdir)

        # Step 3: View Python files to verify content
        view_main = coding_tool.view_tool(file_path=main_file)
        view_utils = coding_tool.view_tool(file_path=utils_file)
        view_readme = coding_tool.view_tool(file_path=readme_file)

        # Step 4: Edit utils.py to implement the TODO
        edit_result = coding_tool.edit_tool(
            file_path=utils_file,
            old_string="def calculate_product(a, b):\n    # TODO: implement this\n    pass\n",
            new_string="def calculate_product(a, b):\n    return a * b\n",
        )

        # Step 5: Verify the edit by viewing again
        view_utils_after_edit = coding_tool.view_tool(file_path=utils_file)

        # Step 6: Search for all functions using grep
        grep_functions = coding_tool.grep_tool(pattern="def ", include="*.py", path=tmpdir)

        # Step 7: Find all Python files using glob
        glob_python = coding_tool.glob_tool(pattern="*.py", path=tmpdir)

        # Step 8: Search for TODO comments (should not find any after edit)
        grep_todos = coding_tool.grep_tool(pattern="TODO", include="*.py", path=tmpdir)

        # Verification: Check all results
        # Files were created successfully
        assert isinstance(main_result, TextOutputModel)
        assert "created successfully" in main_result.content
        assert isinstance(utils_result, TextOutputModel)
        assert "created successfully" in utils_result.content
        assert isinstance(test_result, TextOutputModel)
        assert isinstance(readme_result, TextOutputModel)

        # Directory listing shows all files
        assert isinstance(ls_result, FileListOutputModel)
        assert ls_result.total_count == 4
        file_names = {file.name for file in ls_result.files}
        assert file_names == {"main.py", "utils.py", "test_utils.py", "README.md"}

        # View operations returned code for Python files
        assert isinstance(view_main, (CodeOutputModel, TextOutputModel))
        assert "Hello World" in str(view_main)
        assert isinstance(view_utils, (CodeOutputModel, TextOutputModel))
        assert "calculate_sum" in str(view_utils)

        # Readme is text
        assert isinstance(view_readme, (CodeOutputModel, TextOutputModel))
        assert "My Project" in str(view_readme)

        # Edit was successful
        assert isinstance(edit_result, TextOutputModel)
        assert "has been updated" in edit_result.content

        # After edit, the TODO is gone
        assert isinstance(view_utils_after_edit, (CodeOutputModel, TextOutputModel))
        assert "return a * b" in str(view_utils_after_edit)
        assert "TODO" not in str(view_utils_after_edit)

        # Grep found functions
        assert isinstance(grep_functions, (FileListOutputModel, CodeOutputModel, TextOutputModel))
        if isinstance(grep_functions, FileListOutputModel):
            # Check that files were found
            assert len(grep_functions.files) > 0
        else:
            grep_str = str(grep_functions)
            assert "calculate_sum" in grep_str or "def " in grep_str

        # Glob found Python files
        assert isinstance(glob_python, (FileListOutputModel, TextOutputModel))
        if isinstance(glob_python, FileListOutputModel):
            file_names = {file.name for file in glob_python.files}
            assert "main.py" in file_names
            assert "utils.py" in file_names
            assert "test_utils.py" in file_names
        else:
            # If it's TextOutputModel (no matches), that's also valid
            glob_str = str(glob_python)
            assert "main.py" in glob_str or "utils.py" in glob_str or "test_utils.py" in glob_str

        # No TODOs found after edit
        if isinstance(grep_todos, FileListOutputModel):
            # If matches found, fail (we shouldn't have TODOs)
            assert len(grep_todos.files) == 0, "Found TODO comments but shouldn't have any"
        else:
            # Should be TextOutputModel with no matches
            grep_todos_str = str(grep_todos)
            assert "No files found" in grep_todos_str or "No matches found" in grep_todos_str


def test_three_layer_architecture_integration():
    """
    E2E test verifying the three-layer architecture works correctly:
    1. Backend layer executes primitives
    2. Core layer adds business logic
    3. Adapter layer transforms for frameworks
    """
    # Setup: Create test environment
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        test_content = "print('Hello from test')\n"

        # Layer 1: Core tools with backend
        coding_tool = CodingToolLocal()
        coding_tool.replace_tool(file_path=test_file, content=test_content)

        # Layer 2: Core tools return proper output models
        view_result = coding_tool.view_tool(file_path=test_file)

        # Layer 3: Smolagents adapter transforms to string
        smolagents_tools = ToolFactory.create_smolagents_tools(environment="local")
        view_tool_adapter = next(t for t in smolagents_tools if t.name == "View")
        adapter_result = view_tool_adapter.forward(file_path=test_file)

        # Verification
        # Core tool returns OutputModel
        assert isinstance(view_result, (CodeOutputModel, TextOutputModel))
        assert "Hello from test" in str(view_result)

        # Adapter returns string for smolagents compatibility
        assert isinstance(adapter_result, str)
        assert "Hello from test" in adapter_result

        # Both return same content
        assert str(view_result) in adapter_result or adapter_result in str(view_result)


def test_output_models_and_renderers():
    """
    E2E test for output models and renderers:
    1. Tools return typed output models
    2. Models can be serialized to JSON
    3. Renderers can format outputs differently
    """
    # Setup
    coding_tool = CodingToolLocal()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        code_file = os.path.join(tmpdir, "example.py")
        code_content = "def greet(name: str) -> str:\n    return f'Hello {name}'\n"
        coding_tool.replace_tool(file_path=code_file, content=code_content)

        # Execute different tools to get different output types
        bash_result = coding_tool.bash_tool(command="echo 'test output'", timeout=None)
        view_result = coding_tool.view_tool(file_path=code_file)
        ls_result = coding_tool.ls_tool(path=tmpdir)
        error_result = coding_tool.view_tool(file_path="/nonexistent/file.txt")

        # Create API renderer for testing
        api_renderer = APIRenderer()

        # Test serialization
        bash_json = bash_result.model_dump_json()
        view_json = view_result.model_dump_json()
        ls_json = ls_result.model_dump_json()
        error_json = error_result.model_dump_json()

        # Verification
        # Correct model types
        assert isinstance(bash_result, TextOutputModel)
        assert isinstance(view_result, (CodeOutputModel, TextOutputModel))
        assert isinstance(ls_result, FileListOutputModel)
        assert isinstance(error_result, ErrorOutputModel)

        # JSON serialization works
        assert "test output" in bash_json
        assert "greet" in view_json
        assert "example.py" in ls_json
        assert "does not exist" in error_json

        # API renderer returns JSON strings
        api_bash = api_renderer.render(output=bash_result)
        api_view = api_renderer.render(output=view_result)
        api_ls = api_renderer.render(output=ls_result)
        api_error = api_renderer.render(output=error_result)

        assert isinstance(api_bash, str)
        assert isinstance(api_view, str)
        assert isinstance(api_ls, str)
        assert isinstance(api_error, str)

        # Content preserved in API rendering
        assert "test output" in api_bash
        assert "greet" in api_view
        assert "example.py" in api_ls
        assert "does not exist" in api_error


def test_error_handling_and_validation():
    """
    E2E test for error handling across all tools:
    1. Invalid inputs return ErrorOutputModel
    2. Banned operations are rejected
    3. Missing files are handled gracefully
    """
    # Setup
    coding_tool = CodingToolLocal()

    with tempfile.TemporaryDirectory() as tmpdir:
        existing_file = os.path.join(tmpdir, "exists.txt")
        coding_tool.replace_tool(file_path=existing_file, content="test content\n")

        # Test various error scenarios
        nonexistent_file = "/this/path/does/not/exist/file.txt"

        # 1. View nonexistent file
        view_error = coding_tool.view_tool(file_path=nonexistent_file)

        # 2. Edit nonexistent file
        edit_error = coding_tool.edit_tool(
            file_path=nonexistent_file, old_string="old", new_string="new"
        )

        # 3. Banned bash command
        banned_command = coding_tool.bash_tool(command="curl http://example.com", timeout=None)

        # 4. Edit with string not found
        edit_not_found = coding_tool.edit_tool(
            file_path=existing_file, old_string="nonexistent string", new_string="new"
        )

        # 5. List nonexistent directory
        ls_error = coding_tool.ls_tool(path=nonexistent_file)

        # Verification: All return ErrorOutputModel with appropriate messages
        assert isinstance(view_error, ErrorOutputModel)
        assert "does not exist" in view_error.error

        assert isinstance(edit_error, ErrorOutputModel)
        assert "does not exist" in edit_error.error

        assert isinstance(banned_command, ErrorOutputModel)
        assert "banned" in banned_command.error.lower()

        assert isinstance(edit_not_found, ErrorOutputModel)
        assert "not found" in edit_not_found.error.lower()

        assert isinstance(ls_error, ErrorOutputModel)
        assert "does not exist" in ls_error.error or "not found" in ls_error.error.lower()


def test_factory_creates_all_tools_correctly():
    """
    E2E test for ToolFactory:
    1. Factory creates all 8 smolagents tools
    2. Each tool has correct metadata
    3. Tools are functional and can execute operations
    """
    # Setup: Create smolagents tools via factory
    tools = ToolFactory.create_smolagents_tools(environment="local")

    # Expected tool names
    expected_names = {"Bash", "View", "Edit", "Replace", "GlobTool", "GrepTool", "LS", "UserInput"}

    # Extract actual tool names
    actual_names = {tool.name for tool in tools}

    # Verify all tools created
    assert len(tools) == 8
    assert actual_names == expected_names

    # Verify each tool has required attributes
    for tool in tools:
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert hasattr(tool, "inputs")
        assert hasattr(tool, "output_type")
        assert tool.name != ""
        assert tool.description != ""
        assert isinstance(tool.inputs, dict)

    # Test that tools are functional
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "functional_test.txt")

        # Get specific tools
        bash_tool = next(t for t in tools if t.name == "Bash")
        replace_tool = next(t for t in tools if t.name == "Replace")
        view_tool = next(t for t in tools if t.name == "View")

        # Execute operations
        bash_output = bash_tool.forward(command="echo 'factory test'")
        replace_output = replace_tool.forward(file_path=test_file, content="factory content\n")
        view_output = view_tool.forward(file_path=test_file)

        # Verification: Tools execute and return results
        assert isinstance(bash_output, str)
        assert "factory test" in bash_output

        assert isinstance(replace_output, str)
        assert "created successfully" in replace_output

        assert isinstance(view_output, str)
        assert "factory content" in view_output

if __name__ == "__main__":
    test_complete_development_workflow()
    test_three_layer_architecture_integration()
    test_output_models_and_renderers()
    test_error_handling_and_validation()
    test_factory_creates_all_tools_correctly()