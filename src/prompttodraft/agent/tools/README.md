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

See `gemini_cli_tool.md` for complete Gemini CLI specifications.

## Tool Design

### Core Tool Pattern

All tools follow a consistent design:

- **Inherit from `CoreTool`** - Base class ensures consistent interface
- **Define metadata** - Name, description, inputs, output type
- **Implement `execute()`** - Business logic using backend primitives
- **Return `ToolOutputModel`** - Structured Pydantic models, not strings
- **Zero framework dependencies** - Works with any AI framework

### Tool Structure Example

```python
from prompttodraft.agent.tools.base_tool import CoreTool
from prompttodraft.agent.tools.metadata import ToolMetadata
from prompttodraft.agent.backends.execution_backend import ExecutionBackend
from prompttodraft.agent.outputs.models import ToolOutputModel, TextOutputModel

class ExampleTool(CoreTool):
    # Metadata for framework adapters
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
        super().__init__(backend=backend)

    def execute(self, param1: str) -> ToolOutputModel:
        # 1. Validate inputs
        # 2. Use backend for primitive operations
        result = self.backend.execute_command(f"echo {param1}")
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
from prompttodraft.agent.backends.local_backend import LocalBackend
from prompttodraft.agent.backends.state_manager import GitStateManager
from prompttodraft.agent.tools.read_file_tool import ReadFileTool

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

1. **Create tool class** inheriting from `CoreTool`:

```python
from prompttodraft.agent.tools.base_tool import CoreTool
from prompttodraft.agent.tools.metadata import ToolMetadata
from prompttodraft.agent.outputs.models import TextOutputModel

class MyTool(CoreTool):
    metadata = ToolMetadata(
        name="my_tool",
        description="Does something useful",
        inputs={"param": {"type": "string", "description": "...", "nullable": False}},
        output_type="string"
    )

    def execute(self, param: str) -> ToolOutputModel:
        result = self.backend.execute_command(f"echo {param}")
        return TextOutputModel(content=result.output)
```

2. **Add wrappers** to framework integration files:
   - `smolagent_agent.py` - smolagents `Tool` wrapper
   - `pydantic_ai_agent.py` - Pydantic-AI tool definition
   - `langchain_agent.py` - LangChain tool wrapper

3. **Tool automatically works** in all environments (local, Docker, E2B)

## See Also

- [../README.md](../README.md) - Extension guide, framework integration
- [../outputs/README.md](../outputs/README.md) - Output model documentation
- [gemini_cli_tool.md](gemini_cli_tool.md) - Gemini CLI specifications
