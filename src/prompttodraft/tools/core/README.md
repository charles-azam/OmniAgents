# Core Tools

Framework-agnostic coding tools **reverse-engineered from Gemini CLI**. Each tool contains business logic, uses backends for primitive operations, and returns structured output models.

## Gemini CLI Tools

Nine tools based on Gemini CLI:

1. **`list_directory`** - List directory contents with filtering
2. **`read_file`** - Read text, images, and PDFs
3. **`write_file`** - Write content to files
4. **`glob`** - Find files matching patterns
5. **`search_file_content`** - Search with regex (grep)
6. **`replace`** - Precise text replacement with context
7. **`run_shell_command`** - Execute shell commands
8. **`read_many_files`** - Read multiple files at once
9. **`save_memory`** - Persistent memory across sessions

See `gemini_cli_tool.md` for complete Gemini CLI specifications.

---

## Tool Structure

All tools follow this pattern:

```python
from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend
from prompttodraft.tools.outputs.models import ToolOutputModel

class ExampleTool:
    # Tool metadata for framework adapters
    metadata = ToolMetadata(
        name="example_tool",
        description="What this tool does",
        inputs={
            "param1": {
                "type": "string",
                "description": "Parameter description",
                "nullable": False
            }
        },
        output_type="string"
    )

    def __init__(self, backend: ExecutionBackend):
        self.backend = backend

    def execute(self, param1: str) -> ToolOutputModel:
        # 1. Validate inputs
        # 2. Use backend for primitive operations
        # 3. Apply business logic
        # 4. Return output model
        pass
```

## Output Models

Tools return these output types:

- **`TextOutputModel`**: Plain text
- **`CodeOutputModel`**: Code with syntax highlighting
- **`FileListOutputModel`**: List of files/directories
- **`ErrorOutputModel`**: Error messages
- **`MediaOutputModel`**: Base64-encoded images/PDFs

See [`outputs/README.md`](../outputs/README.md) for details.

## Gemini CLI Reference

These tools are reverse-engineered from Gemini CLI. See `gemini_cli_tool.md` for the complete Gemini CLI specification.

**Key differences** from Gemini CLI:
- Python instead of TypeScript
- Backend abstraction for multi-environment support
- Structured output models instead of strings
- Framework-agnostic design

**Planned features** from Gemini CLI not yet implemented:
- User confirmation for `write_file` and `replace`
- Interactive shell commands in `run_shell_command`
- Background process support in `run_shell_command`
- Multi-stage edit correction in `replace`
- Git-aware search optimization in `search_file_content`

## Creating a New Tool

1. **Create tool file** in `core/`:

```python
class NewTool:
    metadata = ToolMetadata(
        name="new_tool",
        description="Tool description",
        inputs={...},
        output_type="string"
    )

    def __init__(self, backend: ExecutionBackend):
        self.backend = backend

    def execute(self, **kwargs) -> ToolOutputModel:
        # Implementation
        pass
```

2. **Create framework adapter** (e.g., in `adapters/smolagents_adapter.py`)

3. **Add to factory** in `factory.py`

The tool will automatically work in all execution environments (local, Docker, E2B).
