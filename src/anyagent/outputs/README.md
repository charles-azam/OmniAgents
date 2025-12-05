# Tool Output Models

All tool outputs inherit from `ToolOutputModel` and handle their own display logic based on the `DISPLAY_MODE` environment variable.

## Quick Start

```python
from anyagent.outputs.outputs import TextOutputModel

# Create an output
output = TextOutputModel(content="Hello, world!")

# Handle it - automatically adapts based on DISPLAY_MODE env var
result = output.handle()
```

## Display Modes

Set via `DISPLAY_MODE` environment variable:

- **`console`** (default): Prints to terminal with Rich formatting, returns string
- **`api`**: Returns dict for JSON (no printing), perfect for FastAPI
- **`hybrid`**: Prints to terminal AND returns dict (debugging)

## Available Models

All models inherit from `ToolOutputModel`:

- **`TextOutputModel`** - Simple text content
- **`CodeOutputModel`** - Code with syntax highlighting
- **`FileListOutputModel`** - Lists of files/directories
- **`TableOutputModel`** - Tabular data
- **`ErrorOutputModel`** - Error messages
- **`MediaOutputModel`** - Images, PDFs (base64-encoded)

## Usage in Tools

Tools should return instances of these models:

```python
class ReadFileTool:
    def execute(self, absolute_path: str) -> ToolOutputModel:
        # ... read file ...
        return CodeOutputModel(
            content=content,
            language="python",
        )
```

## Usage in CLI

```python
from anyagent.tools.read_file_tool import ReadFileTool

tool = ReadFileTool(backend=backend)
result = tool.execute(absolute_path="/path/to/file.py")

# In console mode, this prints to terminal
output = result.handle()
```

## Usage in FastAPI

```python
from fastapi import FastAPI

app = FastAPI()

@app.post("/read")
def read_file(path: str) -> dict:
    tool = ReadFileTool(backend=backend)
    result = tool.execute(absolute_path=path)

    # In API mode, returns dict for JSON response
    return result.handle()
```

**API Response:**
```json
{
  "type": "code",
  "content": "def hello():\n    print('world')",
  "language": "python",
  "line_numbers": true,
  "metadata": null
}
```

## Architecture

```
ToolOutputModel (base class)
├── TextOutputModel
├── CodeOutputModel
├── FileListOutputModel
├── TableOutputModel
├── ErrorOutputModel
└── MediaOutputModel
```

Each model knows how to:
- Display itself in console (`handle_console()`)
- Serialize for API (`handle_api()`)
- Route based on environment (`handle()`)

Simple and clean!
