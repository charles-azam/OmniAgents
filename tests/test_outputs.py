"""
Test output models handle methods.

Tests all output models' handle(), handle_console(), and handle_api() methods
with different DISPLAY_MODE environment variable values.
"""
import os

from prompttodraft.tools.outputs.models import (
    TextOutputModel,
    CodeOutputModel,
    FileInfo,
    FileListOutputModel,
    TableOutputModel,
    ErrorOutputModel,
    MediaOutputModel,
    DisplayMode,
)


def test_text_output_console_mode():
    """Test TextOutputModel in console mode."""
    os.environ["DISPLAY_MODE"] = "console"

    model = TextOutputModel(content="Hello, World!")
    result = model.handle()

    assert isinstance(result, str)
    assert result == "Hello, World!"


def test_text_output_api_mode():
    """Test TextOutputModel in API mode."""
    os.environ["DISPLAY_MODE"] = "api"

    model = TextOutputModel(content="Hello, World!", metadata={"tool": "test"})
    result = model.handle()

    assert isinstance(result, dict)
    assert result["type"] == "text"
    assert result["content"] == "Hello, World!"
    assert result["metadata"]["tool"] == "test"


def test_text_output_hybrid_mode():
    """Test TextOutputModel in hybrid mode."""
    os.environ["DISPLAY_MODE"] = "hybrid"

    model = TextOutputModel(content="Hybrid test")
    result = model.handle()

    assert isinstance(result, dict)
    assert result["type"] == "text"
    assert result["content"] == "Hybrid test"


def test_code_output_console_mode():
    """Test CodeOutputModel in console mode."""
    os.environ["DISPLAY_MODE"] = "console"

    code = "def hello():\n    print('world')"
    model = CodeOutputModel(content=code, language="python", line_numbers=True)
    result = model.handle()

    assert isinstance(result, str)
    assert result == code


def test_code_output_api_mode():
    """Test CodeOutputModel in API mode."""
    os.environ["DISPLAY_MODE"] = "api"

    code = "const x = 42;"
    model = CodeOutputModel(content=code, language="javascript", line_numbers=False)
    result = model.handle()

    assert isinstance(result, dict)
    assert result["type"] == "code"
    assert result["content"] == code
    assert result["language"] == "javascript"
    assert result["line_numbers"] is False


def test_file_list_output_console_mode():
    """Test FileListOutputModel in console mode."""
    os.environ["DISPLAY_MODE"] = "console"

    files = [
        FileInfo(name="test.py", path="/path/test.py", is_dir=False, size=1024),
        FileInfo(name="src", path="/path/src", is_dir=True, size=0),
    ]
    model = FileListOutputModel(files=files, path="/path", total_count=2)
    result = model.handle()

    assert isinstance(result, str)
    assert "2 items in /path" in result


def test_file_list_output_api_mode():
    """Test FileListOutputModel in API mode."""
    os.environ["DISPLAY_MODE"] = "api"

    files = [
        FileInfo(name="test.py", path="/path/test.py", is_dir=False, size=1024),
        FileInfo(name="data.txt", path="/path/data.txt", is_dir=False, size=512),
    ]
    model = FileListOutputModel(files=files, path="/path", total_count=2, truncated=False)
    result = model.handle()

    assert isinstance(result, dict)
    assert result["type"] == "file_list"
    assert len(result["files"]) == 2
    assert result["files"][0]["name"] == "test.py"
    assert result["files"][0]["is_dir"] is False
    assert result["files"][0]["size"] == 1024
    assert result["path"] == "/path"
    assert result["total_count"] == 2
    assert result["truncated"] is False


def test_table_output_console_mode():
    """Test TableOutputModel in console mode."""
    os.environ["DISPLAY_MODE"] = "console"

    model = TableOutputModel(
        rows=[["Alice", "30"], ["Bob", "25"]],
        headers=["Name", "Age"]
    )
    result = model.handle()

    assert isinstance(result, str)
    assert "Table with 2 rows" in result


def test_table_output_api_mode():
    """Test TableOutputModel in API mode."""
    os.environ["DISPLAY_MODE"] = "api"

    rows = [["Alice", "30"], ["Bob", "25"]]
    headers = ["Name", "Age"]
    model = TableOutputModel(rows=rows, headers=headers)
    result = model.handle()

    assert isinstance(result, dict)
    assert result["type"] == "table"
    assert result["rows"] == rows
    assert result["headers"] == headers


def test_error_output_console_mode():
    """Test ErrorOutputModel in console mode."""
    os.environ["DISPLAY_MODE"] = "console"

    model = ErrorOutputModel(
        error="File not found",
        error_type="FileNotFoundError",
        traceback="Traceback..."
    )
    result = model.handle()

    assert isinstance(result, str)
    assert "FileNotFoundError: File not found" in result


def test_error_output_api_mode():
    """Test ErrorOutputModel in API mode."""
    os.environ["DISPLAY_MODE"] = "api"

    model = ErrorOutputModel(
        error="Division by zero",
        error_type="ZeroDivisionError",
        traceback="line 10"
    )
    result = model.handle()

    assert isinstance(result, dict)
    assert result["type"] == "error"
    assert result["error"] == "Division by zero"
    assert result["error_type"] == "ZeroDivisionError"
    assert result["traceback"] == "line 10"


def test_media_output_console_mode():
    """Test MediaOutputModel in console mode."""
    os.environ["DISPLAY_MODE"] = "console"

    model = MediaOutputModel(
        filename="image.png",
        mime_type="image/png",
        base64_data="iVBORw0KGgo...",
        size_bytes=2048
    )
    result = model.handle()

    assert isinstance(result, str)
    assert "Media file: image.png (image/png)" in result


def test_media_output_api_mode():
    """Test MediaOutputModel in API mode."""
    os.environ["DISPLAY_MODE"] = "api"

    base64_data = "iVBORw0KGgo..."
    model = MediaOutputModel(
        filename="video.mp4",
        mime_type="video/mp4",
        base64_data=base64_data,
        size_bytes=1024000
    )
    result = model.handle()

    assert isinstance(result, dict)
    assert result["type"] == "media"
    assert result["filename"] == "video.mp4"
    assert result["mime_type"] == "video/mp4"
    assert result["base64_data"] == base64_data
    assert result["size_bytes"] == 1024000


def test_text_output_with_multiline_content():
    """Test TextOutputModel with multiline content in console mode."""
    os.environ["DISPLAY_MODE"] = "console"

    content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    model = TextOutputModel(content=content)
    result = model.handle()

    assert isinstance(result, str)
    assert result == content


def test_file_list_output_with_large_list():
    """Test FileListOutputModel with more than 10 files in console mode."""
    os.environ["DISPLAY_MODE"] = "console"

    files = [
        FileInfo(name=f"file{i}.txt", path=f"/path/file{i}.txt", is_dir=False, size=100)
        for i in range(15)
    ]
    model = FileListOutputModel(files=files, path="/path", total_count=15)
    result = model.handle()

    assert isinstance(result, str)
    assert "15 items in /path" in result


def test_file_list_output_with_size_formatting():
    """Test FileListOutputModel size formatting."""
    os.environ["DISPLAY_MODE"] = "api"

    files = [
        FileInfo(name="small.txt", path="/path/small.txt", is_dir=False, size=512),
        FileInfo(name="medium.txt", path="/path/medium.txt", is_dir=False, size=51200),
        FileInfo(name="large.txt", path="/path/large.txt", is_dir=False, size=5242880),
    ]
    model = FileListOutputModel(files=files, path="/path", total_count=3)
    result = model.handle()

    assert isinstance(result, dict)
    assert result["files"][0]["size"] == 512
    assert result["files"][1]["size"] == 51200
    assert result["files"][2]["size"] == 5242880


def test_error_output_without_traceback():
    """Test ErrorOutputModel without traceback."""
    os.environ["DISPLAY_MODE"] = "api"

    model = ErrorOutputModel(error="Simple error", error_type="Error")
    result = model.handle()

    assert isinstance(result, dict)
    assert result["traceback"] is None


def test_code_output_with_long_content():
    """Test CodeOutputModel with long content in console mode."""
    os.environ["DISPLAY_MODE"] = "console"

    code = "\n".join([f"line_{i} = {i}" for i in range(20)])
    model = CodeOutputModel(content=code, language="python")
    result = model.handle()

    assert isinstance(result, str)
    assert result == code


def test_table_output_without_headers():
    """Test TableOutputModel without headers."""
    os.environ["DISPLAY_MODE"] = "api"

    rows = [["value1", "value2"], ["value3", "value4"]]
    model = TableOutputModel(rows=rows)
    result = model.handle()

    assert isinstance(result, dict)
    assert result["headers"] is None
    assert len(result["rows"]) == 2


def test_display_mode_enum():
    """Test DisplayMode enum values."""
    assert DisplayMode.CONSOLE.value == "console"
    assert DisplayMode.API.value == "api"
    assert DisplayMode.HYBRID.value == "hybrid"


def test_output_model_str_methods():
    """Test __str__ methods for all output models."""
    text_model = TextOutputModel(content="test")
    assert str(text_model) == "test"

    code_model = CodeOutputModel(content="code", language="python")
    assert str(code_model) == "code"

    file_list_model = FileListOutputModel(files=[], path="/path")
    assert "0 items in /path" in str(file_list_model)

    table_model = TableOutputModel(rows=[["a", "b"]], headers=["A", "B"])
    assert "Table with 1 rows" in str(table_model)

    error_model = ErrorOutputModel(error="test error", error_type="TestError")
    assert "TestError: test error" in str(error_model)

    media_model = MediaOutputModel(
        filename="test.png",
        mime_type="image/png",
        base64_data="data"
    )
    assert "Media file: test.png (image/png)" in str(media_model)


if __name__ == "__main__":
    print("Testing TextOutputModel...")
    test_text_output_console_mode()
    test_text_output_api_mode()
    test_text_output_hybrid_mode()
    test_text_output_with_multiline_content()

    print("Testing CodeOutputModel...")
    test_code_output_console_mode()
    test_code_output_api_mode()
    test_code_output_with_long_content()

    print("Testing FileListOutputModel...")
    test_file_list_output_console_mode()
    test_file_list_output_api_mode()
    test_file_list_output_with_large_list()
    test_file_list_output_with_size_formatting()

    print("Testing TableOutputModel...")
    test_table_output_console_mode()
    test_table_output_api_mode()
    test_table_output_without_headers()

    print("Testing ErrorOutputModel...")
    test_error_output_console_mode()
    test_error_output_api_mode()
    test_error_output_without_traceback()

    print("Testing MediaOutputModel...")
    test_media_output_console_mode()
    test_media_output_api_mode()

    print("Testing DisplayMode enum...")
    test_display_mode_enum()

    print("Testing __str__ methods...")
    test_output_model_str_methods()

    print("\n" + "="*80)
    print("✅ ALL OUTPUT TESTS PASSED!")
    print("="*80)
