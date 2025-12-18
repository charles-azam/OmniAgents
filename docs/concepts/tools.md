# Tools

Tools are the building blocks that AI agents use to interact with code. Omniagents provides 10 core tools inspired by Gemini CLI.

## Tool Catalog

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `WriteFileTool` | Create or overwrite files | `absolute_path`, `content` |
| `ReadFileTool` | Read text, images, PDFs | `absolute_path` |
| `ListDirectoryTool` | List directory contents | `absolute_path`, `recursive` |
| `GlobTool` | Find files matching patterns | `pattern`, `absolute_path` |
| `SearchFileContentTool` | Regex search (grep) | `pattern`, `absolute_path` |
| `ReplaceTool` | Precise text replacement | `absolute_path`, `old_text`, `new_text` |
| `RunShellCommandTool` | Execute shell commands | `command`, `timeout` |
| `ReadManyFilesTool` | Read multiple files at once | `absolute_paths` |
| `SaveMemoryTool` | Persistent key-value storage | `key`, `value` |
| `UVTool` | UV package manager commands | `uv_command` |

## Using Tools Directly

Tools can be used without an AI agent:

```python
from omniagents.backends.local_backend import LocalBackend
from omniagents.backends.state_manager import NoOpStateManager
from omniagents.tools.write_file_tool import WriteFileTool
from omniagents.tools.read_file_tool import ReadFileTool
from omniagents.tools.run_shell_command_tool import RunShellCommandTool

# Setup backend
backend = LocalBackend(project_id="demo", state_manager=NoOpStateManager())
backend.start()

# Write a file
write_tool = WriteFileTool(backend=backend)
result = write_tool.execute(
    absolute_path="script.py",
    content="print('Hello, World!')"
)

# Read it back
read_tool = ReadFileTool(backend=backend)
result = read_tool.execute(absolute_path="script.py")
print(result.content)

# Run it
shell_tool = RunShellCommandTool(backend=backend)
result = shell_tool.execute(command="python script.py")
print(result.content)  # "Hello, World!"

backend.shutdown()
```

## Tool Details

### WriteFileTool

Creates or overwrites files. Automatically creates parent directories.

```python
from omniagents.tools.write_file_tool import WriteFileTool

tool = WriteFileTool(backend=backend)
result = tool.execute(
    absolute_path="src/utils/helpers.py",
    content="def add(a, b):\n    return a + b"
)
```

### ReadFileTool

Reads text files, images, and PDFs. Images and PDFs are returned as base64.

```python
from omniagents.tools.read_file_tool import ReadFileTool

tool = ReadFileTool(backend=backend)

# Text files
result = tool.execute(absolute_path="main.py")
print(result.content)

# Images (returns MediaOutputModel)
result = tool.execute(absolute_path="diagram.png")
print(result.media_type)  # "image/png"
print(result.base64_data)  # base64-encoded
```

### ListDirectoryTool

Lists directory contents with optional recursion.

```python
from omniagents.tools.list_directory_tool import ListDirectoryTool

tool = ListDirectoryTool(backend=backend)
result = tool.execute(
    absolute_path="/workspace",
    recursive=True
)
for item in result.items:
    print(f"{item.type}: {item.path}")
```

### GlobTool

Finds files matching glob patterns. Respects `.gitignore`.

```python
from omniagents.tools.glob_tool import GlobTool

tool = GlobTool(backend=backend)
result = tool.execute(
    pattern="**/*.py",
    absolute_path="/workspace"
)
for file in result.files:
    print(file)
```

### SearchFileContentTool

Searches file contents using regex. Like grep.

```python
from omniagents.tools.search_file_content_tool import SearchFileContentTool

tool = SearchFileContentTool(backend=backend)
result = tool.execute(
    pattern="def.*test",
    absolute_path="/workspace"
)
print(result.content)  # Matching lines with context
```

### ReplaceTool

Precise text replacement with context validation.

```python
from omniagents.tools.replace_tool import ReplaceTool

tool = ReplaceTool(backend=backend)
result = tool.execute(
    absolute_path="config.py",
    old_text="DEBUG = True",
    new_text="DEBUG = False"
)
```

!!! warning "Exact Match Required"
    The `old_text` must match exactly, including whitespace. If no match is found or multiple matches exist, the tool returns an error.

### RunShellCommandTool

Executes bash commands with optional timeout.

```python
from omniagents.tools.run_shell_command_tool import RunShellCommandTool

tool = RunShellCommandTool(backend=backend)
result = tool.execute(
    command="pip install requests && python -c 'import requests; print(requests.__version__)'",
    timeout=60
)
print(result.content)
```

### ReadManyFilesTool

Reads multiple files in one call. Supports glob patterns.

```python
from omniagents.tools.read_many_files_tool import ReadManyFilesTool

tool = ReadManyFilesTool(backend=backend)
result = tool.execute(
    absolute_paths=["main.py", "utils.py", "config.py"]
)
for file_content in result.files:
    print(f"=== {file_content.path} ===")
    print(file_content.content)
```

### SaveMemoryTool

Persists key-value pairs as markdown files in the workspace.

```python
from omniagents.tools.save_memory_tool import SaveMemoryTool

tool = SaveMemoryTool(backend=backend)
result = tool.execute(
    key="project_notes",
    value="Remember to add error handling to the API endpoints"
)
# Creates: .memory/project_notes.md
```

### UVTool

Runs UV package manager commands. Installs UV if needed.

```python
from omniagents.tools.uv_tool import UVTool

tool = UVTool(backend=backend)

# Add a dependency
result = tool.execute(uv_command="add requests")

# Run a script
result = tool.execute(uv_command="run python main.py")
```

## Output Models

All tools return structured Pydantic models:

| Model | Used By | Key Fields |
|-------|---------|------------|
| `TextOutputModel` | Most tools | `content` |
| `CodeOutputModel` | ReadFile | `content`, `language` |
| `FileListOutputModel` | ListDirectory, Glob | `items` or `files` |
| `ErrorOutputModel` | All (on error) | `error_type`, `message` |
| `MediaOutputModel` | ReadFile (images) | `media_type`, `base64_data` |

See [Output Models API](../api/outputs.md) for details.
