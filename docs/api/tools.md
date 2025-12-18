# Tools API Reference

All tools inherit from `CoreBackendTool` and share a common interface.

## Base Class

```python
class CoreBackendTool(ABC, Generic[TInput, TOutput]):
    name: str                    # Tool identifier
    description: str             # Tool description for LLM

    def __init__(self, backend: ExecutionBackend):
        self.backend = backend

    @abstractmethod
    def execute(self, inputs: TInput) -> TOutput:
        """Execute the tool with validated inputs."""
```

---

## WriteFileTool

Create or overwrite files.

```python
from omniagents.tools.write_file_tool import WriteFileTool

tool = WriteFileTool(backend=backend)
result = tool.execute(
    absolute_path="src/main.py",
    content="print('hello')"
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `absolute_path` | `str` | Path to file (relative to workspace) |
| `content` | `str` | File content to write |

**Returns**: `TextOutputModel`

**Behavior**:

- Creates parent directories automatically
- Overwrites existing files

---

## ReadFileTool

Read text files, images, and PDFs.

```python
from omniagents.tools.read_file_tool import ReadFileTool

tool = ReadFileTool(backend=backend)
result = tool.execute(absolute_path="main.py")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `absolute_path` | `str` | Path to file |

**Returns**:

- `CodeOutputModel` for text files
- `MediaOutputModel` for images/PDFs (base64 encoded)
- `ErrorOutputModel` if file not found

---

## ListDirectoryTool

List directory contents.

```python
from omniagents.tools.list_directory_tool import ListDirectoryTool

tool = ListDirectoryTool(backend=backend)
result = tool.execute(
    absolute_path="/workspace",
    recursive=False
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `absolute_path` | `str` | Required | Directory path |
| `recursive` | `bool` | `False` | Include subdirectories |

**Returns**: `FileListOutputModel` with list of `FileInfo`

---

## GlobTool

Find files matching glob patterns.

```python
from omniagents.tools.glob_tool import GlobTool

tool = GlobTool(backend=backend)
result = tool.execute(
    pattern="**/*.py",
    absolute_path="/workspace"
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pattern` | `str` | Required | Glob pattern |
| `absolute_path` | `str` | Workspace root | Directory to search |

**Returns**: `FileListOutputModel` with matching file paths

**Behavior**:

- Respects `.gitignore`
- Sorted by modification time (newest first)

---

## SearchFileContentTool

Search file contents using regex.

```python
from omniagents.tools.search_file_content_tool import SearchFileContentTool

tool = SearchFileContentTool(backend=backend)
result = tool.execute(
    pattern="def test_.*",
    absolute_path="/workspace"
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pattern` | `str` | Required | Regex pattern |
| `absolute_path` | `str` | Workspace root | Directory or file to search |

**Returns**: `TextOutputModel` with matching lines and context

**Behavior**:

- Uses `git grep` when in a git repo (faster)
- Falls back to recursive grep otherwise

---

## ReplaceTool

Precise text replacement with validation.

```python
from omniagents.tools.replace_tool import ReplaceTool

tool = ReplaceTool(backend=backend)
result = tool.execute(
    absolute_path="config.py",
    old_text="DEBUG = True",
    new_text="DEBUG = False"
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `absolute_path` | `str` | Path to file |
| `old_text` | `str` | Text to find (exact match) |
| `new_text` | `str` | Replacement text |

**Returns**:

- `TextOutputModel` on success
- `ErrorOutputModel` if no match or multiple matches

**Behavior**:

- Requires exact match (including whitespace)
- Fails if text appears multiple times (use `replace_all` context)
- Returns error with context if match is ambiguous

---

## RunShellCommandTool

Execute shell commands.

```python
from omniagents.tools.run_shell_command_tool import RunShellCommandTool

tool = RunShellCommandTool(backend=backend)
result = tool.execute(
    command="pip install requests && python main.py",
    timeout=60
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `command` | `str` | Required | Bash command |
| `timeout` | `int` | `120` | Timeout in seconds |

**Returns**: `TextOutputModel` with command output

---

## ReadManyFilesTool

Read multiple files at once.

```python
from omniagents.tools.read_many_files_tool import ReadManyFilesTool

tool = ReadManyFilesTool(backend=backend)
result = tool.execute(
    absolute_paths=["main.py", "utils.py", "config.py"]
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `absolute_paths` | `list[str]` | Paths to read |

**Returns**: `MultiFileOutputModel` with content of each file

---

## SaveMemoryTool

Persist key-value data across sessions.

```python
from omniagents.tools.save_memory_tool import SaveMemoryTool

tool = SaveMemoryTool(backend=backend)
result = tool.execute(
    key="project_notes",
    value="Remember to handle edge cases in auth"
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Memory key (becomes filename) |
| `value` | `str` | Content to store |

**Returns**: `TextOutputModel`

**Behavior**:

- Stores as `.memory/{key}.md`
- Overwrites existing keys
- Persists via StateManager

---

## UVTool

Run UV package manager commands.

```python
from omniagents.tools.uv_tool import UVTool

tool = UVTool(backend=backend)

# Add dependency
result = tool.execute(uv_command="add requests")

# Run script
result = tool.execute(uv_command="run python main.py")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `uv_command` | `str` | UV command (without `uv` prefix) |

**Returns**: `TextOutputModel` with command output

**Behavior**:

- Installs UV if not present
- Prepends `uv` to command automatically

---

## Output Models

All tools return Pydantic models inheriting from `ToolOutputModel`:

| Model | Fields | Used By |
|-------|--------|---------|
| `TextOutputModel` | `content: str` | Most tools |
| `CodeOutputModel` | `content: str`, `language: str` | ReadFile |
| `FileListOutputModel` | `items: list[FileInfo]` | ListDirectory, Glob |
| `ErrorOutputModel` | `error_type: str`, `message: str` | All (on error) |
| `MediaOutputModel` | `media_type: str`, `base64_data: str` | ReadFile (images) |

See [Output Models API](outputs.md) for details.
