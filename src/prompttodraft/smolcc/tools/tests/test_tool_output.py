#!/usr/bin/env python3
"""
Tests for the ToolOutput classes.

These tests demonstrate how each output class works and help understand
the different formatting options available for tool results.
"""

from io import StringIO

from rich.console import Console

from prompttodraft.smolcc.tool_output import (
    ToolOutput,
    ToolCallOutput,
    TextOutput,
    CodeOutput,
    TableOutput,
    FileListOutput,
    AssistantOutput,
    convert_to_tool_output,
)


def test_tool_output_basic() -> None:
    """
    Test the basic ToolOutput class.

    ToolOutput is the base class that stores data and provides
    a simple string representation and display method.
    """
    # Create a basic ToolOutput with simple data
    data = "Hello, World!"
    output = ToolOutput(data=data)

    # Test that data is stored correctly
    assert output.data == "Hello, World!"

    # Test string representation
    assert str(output) == "Hello, World!"

    # Test display to console (StringIO for assertions)
    console = Console(file=StringIO(), width=80)
    output.display(console=console)
    result = console.file.getvalue()

    # Should contain the data with the result indicator
    assert "Hello, World!" in result
    assert "⎿" in result

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_tool_output_basic:[/cyan]")
    output.display(console=terminal_console)


def test_tool_call_output_with_dict_params() -> None:
    """
    Test ToolCallOutput with dictionary parameters.

    ToolCallOutput formats tool calls to show what function is being
    called with what parameters - useful for logging/debugging.
    """
    # Create a tool call with dictionary parameters
    tool_name = "bash_tool"
    params = {"command": "ls -la", "timeout": 5000}
    output = ToolCallOutput(tool_name=tool_name, params=params)

    # Test that tool name and params are stored
    assert output.tool_name == "bash_tool"
    assert output.params == params

    # Test string representation contains function call format
    assert "bash_tool" in str(output)
    assert "command" in str(output)
    assert "ls -la" in str(output)

    # Test display to console (StringIO for assertions)
    console = Console(file=StringIO(), width=80)
    output.display(console=console)
    result = console.file.getvalue()

    # Should show the tool call with indicator
    assert "⏺" in result
    assert "bash_tool" in result

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_tool_call_output_with_dict_params:[/cyan]")
    output.display(console=terminal_console)


def test_tool_call_output_with_long_params() -> None:
    """
    Test ToolCallOutput with very long parameters.

    Long tool calls are truncated to keep console output readable.
    """
    # Create a tool call with very long parameters
    tool_name = "edit_tool"
    params = {
        "file_path": "/very/long/path/to/some/file/that/goes/on/and/on.py",
        "old_string": "A" * 100,
        "new_string": "B" * 100
    }
    output = ToolCallOutput(tool_name=tool_name, params=params)

    # String representation should be truncated
    output_str = str(output)
    assert len(output_str) <= 80
    assert "..." in output_str

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_tool_call_output_with_long_params:[/cyan]")
    output.display(console=terminal_console)


def test_text_output_single_line() -> None:
    """
    Test TextOutput with a single line of text.

    TextOutput is for simple text results, formatted nicely in the console.
    """
    # Create a single line text output
    text = "File created successfully"
    output = TextOutput(data=text)

    # Test data storage
    assert output.data == text

    # Test display to console (StringIO for assertions)
    console = Console(file=StringIO(), width=80)
    output.display(console=console)
    result = console.file.getvalue()

    # Should contain the text with result indicator
    assert "File created successfully" in result
    assert "⎿" in result

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_text_output_single_line:[/cyan]")
    output.display(console=terminal_console)


def test_text_output_multiline_short() -> None:
    """
    Test TextOutput with a few lines of text.

    Short multiline text (3 lines or less) is displayed in full.
    """
    # Create multiline text (3 lines)
    text = "Line 1\nLine 2\nLine 3"
    output = TextOutput(data=text)

    # Test display shows all lines
    console = Console(file=StringIO(), width=80)
    output.display(console=console)
    result = console.file.getvalue()

    assert "Line 1" in result
    assert "Line 2" in result
    assert "Line 3" in result

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_text_output_multiline_short:[/cyan]")
    output.display(console=terminal_console)


def test_text_output_multiline_long() -> None:
    """
    Test TextOutput with many lines of text.

    Long multiline text (>3 lines) shows first line + count of remaining lines.
    """
    # Create multiline text with many lines
    lines = [f"Line {i}" for i in range(1, 11)]
    text = "\n".join(lines)
    output = TextOutput(data=text)

    # Test display shows summary
    console = Console(file=StringIO(), width=80)
    output.display(console=console)
    result = console.file.getvalue()

    # Should show first line and a count
    assert "Line 1" in result
    assert "..." in result
    assert "lines" in result

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_text_output_multiline_long:[/cyan]")
    output.display(console=terminal_console)


def test_code_output_short() -> None:
    """
    Test CodeOutput with a short code snippet.

    CodeOutput provides syntax highlighting for code, making it easier to read.
    """
    # Create a short Python code snippet
    code = "def hello():\n    print('Hello, World!')\n    return True"
    output = CodeOutput(code=code, language="python", theme="monokai", line_numbers=True)

    # Test data storage
    assert output.data == code
    assert output.language == "python"
    assert output.theme == "monokai"
    assert output.line_numbers is True

    # Test display to console
    console = Console(file=StringIO(), width=80)
    output.display(console=console)
    result = console.file.getvalue()

    # Should contain the code (syntax highlighted)
    assert "hello" in result
    assert "⎿" in result

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_code_output_short:[/cyan]")
    output.display(console=terminal_console)


def test_code_output_long() -> None:
    """
    Test CodeOutput with a long code file.

    Long code (>10 lines) shows first 3 lines + count of remaining lines.
    """
    # Create a long code snippet
    lines = [f"# Line {i}\nprint({i})" for i in range(1, 20)]
    code = "\n".join(lines)
    output = CodeOutput(code=code, language="python")

    # Test display shows summary
    console = Console(file=StringIO(), width=80)
    output.display(console=console)
    result = console.file.getvalue()

    # Should show preview and count
    assert "..." in result
    assert "more lines" in result

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_code_output_long:[/cyan]")
    output.display(console=terminal_console)


def test_table_output_with_headers() -> None:
    """
    Test TableOutput with column headers.

    TableOutput formats data as a nice table with optional headers.
    """
    # Create table data with headers
    headers = ["Name", "Age", "City"]
    data = [
        ["Alice", "30", "New York"],
        ["Bob", "25", "San Francisco"],
        ["Charlie", "35", "Los Angeles"]
    ]
    output = TableOutput(data=data, headers=headers)

    # Test data storage
    assert output.data == data
    assert output.headers == headers

    # Test display to console
    console = Console(file=StringIO(), width=80)
    output.display(console=console)
    result = console.file.getvalue()

    # Should contain headers and data
    assert "Name" in result
    assert "Age" in result
    assert "City" in result
    assert "Alice" in result
    assert "Bob" in result
    assert "Charlie" in result

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_table_output_with_headers:[/cyan]")
    output.display(console=terminal_console)


def test_table_output_without_headers() -> None:
    """
    Test TableOutput without column headers.

    Tables can work without headers - columns are auto-generated.
    """
    # Create table data without headers
    data = [
        ["Value1", "Value2", "Value3"],
        ["Value4", "Value5", "Value6"]
    ]
    output = TableOutput(data=data, headers=None)

    # Test data storage
    assert output.data == data
    assert output.headers is None

    # Test display to console
    console = Console(file=StringIO(), width=80)
    output.display(console=console)
    result = console.file.getvalue()

    # Should contain the data
    assert "Value1" in result
    assert "Value6" in result

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_table_output_without_headers:[/cyan]")
    output.display(console=terminal_console)


def test_file_list_output_with_files() -> None:
    """
    Test FileListOutput with file information.

    FileListOutput formats file listings with names, types, and sizes.
    """
    # Create file list data
    files = [
        {"name": "document.txt", "is_dir": False, "size": 1024},
        {"name": "images", "is_dir": True, "size": 0},
        {"name": "script.py", "is_dir": False, "size": 2048},
    ]
    path = "/home/user/documents"
    output = FileListOutput(files=files, path=path)

    # Test data storage
    assert output.data == files
    assert output.path == path

    # Test display to console
    console = Console(file=StringIO(), width=80)
    output.display(console=console)
    result = console.file.getvalue()

    # Should show directory path and file info
    assert "/home/user/documents" in result
    assert "document.txt" in result
    assert "images" in result
    assert "script.py" in result
    assert "[DIR]" in result
    assert "[FILE]" in result
    assert "KB" in result  # Size formatting

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_file_list_output_with_files:[/cyan]")
    output.display(console=terminal_console)


def test_file_list_output_many_files() -> None:
    """
    Test FileListOutput with many files.

    Long file lists (>10 items) show first 10 + count of remaining items.
    """
    # Create a long file list
    files = [{"name": f"file_{i}.txt", "is_dir": False, "size": 100} for i in range(1, 21)]
    output = FileListOutput(files=files)

    # Test display shows summary
    console = Console(file=StringIO(), width=80)
    output.display(console=console)
    result = console.file.getvalue()

    # Should show first 10 and count of remaining
    assert "file_1.txt" in result
    assert "file_10.txt" in result
    assert "..." in result
    assert "more items" in result

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_file_list_output_many_files:[/cyan]")
    output.display(console=terminal_console)


def test_assistant_output() -> None:
    """
    Test AssistantOutput for assistant messages.

    AssistantOutput displays messages from the AI assistant.
    """
    # Create assistant message
    message = "I've completed the task successfully!"
    output = AssistantOutput(data=message)

    # Test data storage
    assert output.data == message

    # Test display to console
    console = Console(file=StringIO(), width=80)
    output.display(console=console)
    result = console.file.getvalue()

    # Should contain the message
    assert "I've completed the task successfully!" in result

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_assistant_output:[/cyan]")
    output.display(console=terminal_console)


def test_convert_to_tool_output_already_tool_output() -> None:
    """
    Test convert_to_tool_output with existing ToolOutput.

    If input is already a ToolOutput, it should be returned as-is.
    """
    # Create a ToolOutput
    original = TextOutput(data="test")

    # Convert should return the same object
    result = convert_to_tool_output(result=original)

    assert result is original

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_convert_to_tool_output_already_tool_output:[/cyan]")
    result.display(console=terminal_console)


def test_convert_to_tool_output_simple_string() -> None:
    """
    Test convert_to_tool_output with a simple string.

    Simple strings are converted to TextOutput.
    """
    # Simple string
    text = "Hello, World!"

    # Should convert to TextOutput
    result = convert_to_tool_output(result=text)

    assert isinstance(result, TextOutput)
    assert result.data == text

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_convert_to_tool_output_simple_string:[/cyan]")
    result.display(console=terminal_console)


def test_convert_to_tool_output_code_string() -> None:
    """
    Test convert_to_tool_output with code-like string.

    Strings that look like code are converted to CodeOutput.
    """
    # Code-like string
    code = "def hello():\n    print('Hello')\n    return True"

    # Should convert to CodeOutput
    result = convert_to_tool_output(result=code)

    assert isinstance(result, CodeOutput)
    assert result.data == code

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_convert_to_tool_output_code_string:[/cyan]")
    result.display(console=terminal_console)


def test_convert_to_tool_output_table_list() -> None:
    """
    Test convert_to_tool_output with list of lists.

    List of lists (table data) is converted to TableOutput.
    """
    # Table data
    table_data = [
        ["A", "B", "C"],
        ["D", "E", "F"]
    ]

    # Should convert to TableOutput
    result = convert_to_tool_output(result=table_data)

    assert isinstance(result, TableOutput)
    assert result.data == table_data

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_convert_to_tool_output_table_list:[/cyan]")
    result.display(console=terminal_console)


def test_convert_to_tool_output_file_list() -> None:
    """
    Test convert_to_tool_output with list of file dicts.

    List of dicts with 'name' key is converted to FileListOutput.
    """
    # File list data
    files = [
        {"name": "file1.txt", "size": 100},
        {"name": "file2.txt", "size": 200}
    ]

    # Should convert to FileListOutput
    result = convert_to_tool_output(result=files)

    assert isinstance(result, FileListOutput)
    assert result.data == files

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_convert_to_tool_output_file_list:[/cyan]")
    result.display(console=terminal_console)


def test_convert_to_tool_output_other() -> None:
    """
    Test convert_to_tool_output with other data types.

    Other types (numbers, etc.) are converted to TextOutput.
    """
    # Number
    number = 42

    # Should convert to TextOutput
    result = convert_to_tool_output(result=number)

    assert isinstance(result, TextOutput)
    assert result.data == number

    # Display to actual terminal for debugging
    terminal_console = Console()
    terminal_console.print("\n[cyan]test_convert_to_tool_output_other:[/cyan]")
    result.display(console=terminal_console)


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Running ToolOutput Tests with Visual Output")
    print("="*70)

    test_tool_output_basic()
    test_tool_call_output_with_dict_params()
    test_tool_call_output_with_long_params()
    test_text_output_single_line()
    test_text_output_multiline_short()
    test_text_output_multiline_long()
    test_code_output_short()
    test_code_output_long()
    test_table_output_with_headers()
    test_table_output_without_headers()
    test_file_list_output_with_files()
    test_file_list_output_many_files()
    test_assistant_output()
    test_convert_to_tool_output_already_tool_output()
    test_convert_to_tool_output_simple_string()
    test_convert_to_tool_output_code_string()
    test_convert_to_tool_output_table_list()
    test_convert_to_tool_output_file_list()
    test_convert_to_tool_output_other()

    print("\n" + "="*70)
    print("All tests passed! ✓")
    print("="*70 + "\n")
