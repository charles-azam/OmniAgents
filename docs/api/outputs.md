# Output Models API Reference

Tools return structured Pydantic models that adapt to different display modes.

## Display Modes

Set via `DISPLAY_MODE` environment variable:

| Mode | Behavior | Use Case |
|------|----------|----------|
| `console` | Rich terminal output, returns string | CLI applications |
| `api` | Returns dict (no printing) | REST APIs, FastAPI |
| `hybrid` | Prints AND returns dict | Debugging |

```python
import os
os.environ["DISPLAY_MODE"] = "api"  # For web backends
```

## ToolOutputModel (Base)

All output models inherit from this base:

```python
class ToolOutputModel(BaseModel, ABC):
    @abstractmethod
    def handle_console(self) -> str:
        """Format for terminal display."""

    @abstractmethod
    def handle_api(self) -> dict:
        """Format for JSON response."""

    def handle(self) -> str | dict:
        """Route to appropriate handler based on DISPLAY_MODE."""
```

---

## TextOutputModel

Simple text content.

```python
from omniagents.outputs.outputs import TextOutputModel

output = TextOutputModel(content="Operation completed successfully")
result = output.handle()
```

| Field | Type | Description |
|-------|------|-------------|
| `content` | `str` | Text content |

**Console output**: Plain text

**API output**:
```json
{
  "type": "text",
  "content": "Operation completed successfully"
}
```

---

## CodeOutputModel

Code with syntax highlighting.

```python
from omniagents.outputs.outputs import CodeOutputModel

output = CodeOutputModel(
    content="def hello():\n    print('world')",
    language="python"
)
result = output.handle()
```

| Field | Type | Description |
|-------|------|-------------|
| `content` | `str` | Code content |
| `language` | `str` | Language for syntax highlighting |

**Console output**: Syntax-highlighted code (via Rich)

**API output**:
```json
{
  "type": "code",
  "content": "def hello():\n    print('world')",
  "language": "python"
}
```

---

## FileListOutputModel

List of files or directories.

```python
from omniagents.outputs.outputs import FileListOutputModel, FileInfo, FileType

output = FileListOutputModel(
    items=[
        FileInfo(name="main.py", path="/workspace/main.py", type=FileType.FILE),
        FileInfo(name="src", path="/workspace/src", type=FileType.DIRECTORY),
    ]
)
result = output.handle()
```

| Field | Type | Description |
|-------|------|-------------|
| `items` | `list[FileInfo]` | List of file/directory info |

**Console output**: Formatted file tree

**API output**:
```json
{
  "type": "file_list",
  "items": [
    {"name": "main.py", "path": "/workspace/main.py", "type": "file"},
    {"name": "src", "path": "/workspace/src", "type": "directory"}
  ]
}
```

---

## ErrorOutputModel

Error messages with context.

```python
from omniagents.outputs.outputs import ErrorOutputModel

output = ErrorOutputModel(
    error_type="FileNotFoundError",
    message="File '/workspace/missing.py' does not exist"
)
result = output.handle()
```

| Field | Type | Description |
|-------|------|-------------|
| `error_type` | `str` | Error classification |
| `message` | `str` | Detailed error message |
| `context` | `dict \| None` | Additional context |

**Console output**: Red-highlighted error message

**API output**:
```json
{
  "type": "error",
  "error_type": "FileNotFoundError",
  "message": "File '/workspace/missing.py' does not exist",
  "context": null
}
```

---

## MediaOutputModel

Base64-encoded images and PDFs.

```python
from omniagents.outputs.outputs import MediaOutputModel

output = MediaOutputModel(
    media_type="image/png",
    base64_data="iVBORw0KGgo..."
)
result = output.handle()
```

| Field | Type | Description |
|-------|------|-------------|
| `media_type` | `str` | MIME type (e.g., `image/png`, `application/pdf`) |
| `base64_data` | `str` | Base64-encoded content |
| `filename` | `str \| None` | Original filename |

**Console output**: Shows media type and size

**API output**:
```json
{
  "type": "media",
  "media_type": "image/png",
  "base64_data": "iVBORw0KGgo...",
  "filename": "diagram.png"
}
```

---

## TableOutputModel

Tabular data.

```python
from omniagents.outputs.outputs import TableOutputModel

output = TableOutputModel(
    headers=["Name", "Type", "Size"],
    rows=[
        ["main.py", "file", "1.2KB"],
        ["utils.py", "file", "0.8KB"],
    ]
)
result = output.handle()
```

| Field | Type | Description |
|-------|------|-------------|
| `headers` | `list[str]` | Column headers |
| `rows` | `list[list[str]]` | Table rows |

**Console output**: Rich table

**API output**:
```json
{
  "type": "table",
  "headers": ["Name", "Type", "Size"],
  "rows": [
    ["main.py", "file", "1.2KB"],
    ["utils.py", "file", "0.8KB"]
  ]
}
```

---

## Usage in Tools

Tools return output models from their `execute` method:

```python
class MyTool(CoreBackendTool[MyInput, TextOutputModel]):
    def execute(self, inputs: MyInput) -> TextOutputModel:
        # On success
        return TextOutputModel(content="Done!")

        # On error
        return ErrorOutputModel(
            error_type="ValidationError",
            message="Invalid input"
        )
```

---

## Usage in FastAPI

```python
from fastapi import FastAPI
from omniagents.tools.read_file_tool import ReadFileTool
import os

os.environ["DISPLAY_MODE"] = "api"

app = FastAPI()

@app.post("/read")
def read_file(path: str) -> dict:
    tool = ReadFileTool(backend=backend)
    result = tool.execute(absolute_path=path)
    return result.handle()  # Returns dict for JSON response
```

Response:
```json
{
  "type": "code",
  "content": "print('hello')",
  "language": "python"
}
```
