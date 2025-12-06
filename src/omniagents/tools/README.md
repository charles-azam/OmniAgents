# Core Tools API Reference

Framework-agnostic coding tools based on Gemini CLI. Each tool uses backends for primitive operations and returns structured output models.

## Tool Catalog

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| **list_directory** | List directory contents | `absolute_path`, `recursive` |
| **read_file** | Read text, images, PDFs | `absolute_path` |
| **write_file** | Write content to files | `absolute_path`, `content` |
| **glob** | Find files matching patterns | `pattern`, `absolute_path` |
| **search_file_content** | Regex search (grep) | `pattern`, `absolute_path` |
| **replace** | Precise text replacement | `absolute_path`, `old_text`, `new_text` |
| **run_shell_command** | Execute shell commands | `command`, `timeout` |
| **read_many_files** | Read multiple files | `absolute_paths` |
| **save_memory** | Persistent memory | `key`, `value` |
| **uv** | Execute uv commands | `uv_command` |

See `gemini_cli_tool.md` for complete Gemini CLI specifications (if available).

## Tool Design

### Core Tool Pattern

All tools follow a consistent design:

- **Inherit from `CoreBackendTool`** - Base class ensures consistent interface
- **Define name and description** - Tool identification
- **Use Pydantic for inputs** - Type-safe input validation
- **Implement `execute()`** - Business logic using backend primitives
- **Return `ToolOutputModel`** - Structured Pydantic models, not strings
- **Zero framework dependencies** - Works with any AI framework

### Tool Structure Example

```python
from omniagents.tools.base_tool import CoreBackendTool
from omniagents.backends.execution_backend import ExecutionBackend
from omniagents.outputs.outputs import TextOutputModel
from pydantic import BaseModel, Field

class ExampleToolInput(BaseModel):
    param1: str = Field(description="Parameter description")

class ExampleTool(CoreBackendTool[ExampleToolInput, TextOutputModel]):
    name = "example_tool"
    description = "What this tool does"

    def execute(self, inputs: ExampleToolInput) -> TextOutputModel:
        # 1. Inputs are already validated by Pydantic
        # 2. Use backend for primitive operations
        result = self.backend.execute_command(f"echo {inputs.param1}")
        # 3. Return output model
        return TextOutputModel(content=result.output)
```

### Key Benefits

- **Environment-agnostic**: Same tool code runs on local, Docker, or E2B
- **Framework-agnostic**: Integrates with smolagents, Pydantic-AI, LangChain
- **Testable**: Mock backend for unit testing
- **Reusable**: Write once, use everywhere

## Output Models

Tools return structured Pydantic models:

- **TextOutputModel** - Plain text
- **CodeOutputModel** - Code with syntax highlighting
- **FileListOutputModel** - List of files/directories
- **ErrorOutputModel** - Error messages
- **MediaOutputModel** - Base64-encoded images/PDFs

See [`../outputs/README.md`](../outputs/README.md) for details.

## Usage Example

```python
from omniagents.backends.local_backend import LocalBackend
from omniagents.backends.state_manager import GitStateManager
from omniagents.tools.read_file_tool import ReadFileTool

backend = LocalBackend(project_id="my-project", state_manager=GitStateManager())
backend.start()

tool = ReadFileTool(backend=backend)
result = tool.execute(absolute_path="/path/to/file.py")
output = result.handle()  # Adapts to DISPLAY_MODE env var
```

## Gemini CLI Reference

These tools are based on Gemini CLI specifications. See `gemini_cli_tool.md` for:
- Complete tool specifications
- Parameter details
- Expected behaviors
- Differences from original Gemini CLI

## Creating a New Tool

1. **Create tool class** inheriting from `CoreBackendTool`:

```python
from omniagents.tools.base_tool import CoreBackendTool
from omniagents.outputs.outputs import TextOutputModel
from pydantic import BaseModel, Field

class MyToolInput(BaseModel):
    param: str = Field(description="Parameter description")

class MyTool(CoreBackendTool[MyToolInput, TextOutputModel]):
    name = "my_tool"
    description = "Does something useful"

    def execute(self, inputs: MyToolInput) -> TextOutputModel:
        result = self.backend.execute_command(f"echo {inputs.param}")
        return TextOutputModel(content=result.output)
```

2. **Use with any agent via `extra_tool_classes`**:
   ```python
   from omniagents.agents.langchain_agent import LangChainAgent

   agent = LangChainAgent(
       backend=backend,
       model=model,
       preset=PythonUVPreset(),
       extra_tool_classes=[MyTool],
   )
   ```

3. **Tool automatically works** in all environments (local, Docker, E2B) and frameworks (LangChain, Pydantic-AI, smolagents)

## See Also

- [../README.md](../README.md) - Extension guide, framework integration
- [../outputs/README.md](../outputs/README.md) - Output model documentation
- [gemini_cli_tool.md](gemini_cli_tool.md) - Gemini CLI specifications
