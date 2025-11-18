# AI Coding Agent Tools

A flexible toolkit for building AI coding agents. Run **Gemini CLI-inspired tools** across multiple execution environments (local, Docker, E2B) and AI frameworks (smolagents, Pydantic-AI, LangChain).

## 10 Core Tools

The toolkit implements these tools from Gemini CLI:

| Tool | Purpose |
|------|---------|
| **list_directory** | List directory contents with filtering |
| **read_file** | Read text files, images, and PDFs |
| **write_file** | Write content to files |
| **glob** | Find files matching glob patterns |
| **search_file_content** | Search files with regex (grep) |
| **replace** | Precise text replacement with context |
| **run_shell_command** | Execute shell commands with timeout |
| **read_many_files** | Read multiple files at once |
| **save_memory** | Persistent memory across sessions |
| **uv** | Execute uv package manager commands |

See `core/gemini_cli_tool.md` for complete Gemini CLI specifications.

## Quick Start

### Using Core Tools Directly

```python
from prompttodraft.agent.backends.local_backend import LocalBackend
from prompttodraft.agent.backends.state_manager import GitStateManager
from prompttodraft.agent.tools.read_file_tool import ReadFileTool

# Create backend
backend = LocalBackend(project_id="my-project", state_manager=GitStateManager())
backend.start()

# Use tool
tool = ReadFileTool(backend=backend)
result = tool.execute(absolute_path="/path/to/file.py")
output = result.handle()  # Automatically formats based on DISPLAY_MODE
```

### Using with AI Frameworks

#### smolagents

```python
from prompttodraft.agent.smolagent_agent import SmolAgentAgent
from prompttodraft.agent.backends.local_backend import LocalBackend
from prompttodraft.agent.backends.state_manager import GitStateManager

backend = LocalBackend(project_id="my-project", state_manager=GitStateManager())
backend.start()

agent = SmolAgentAgent(
    backend=backend,
    provider="huggingface",
    model_id="Qwen/Qwen2.5-Coder-32B-Instruct"
)

result = agent.run("List all Python files")
```

#### Pydantic-AI

```python
from prompttodraft.agent.pydantic_ai_agent import PydanticAIAgent

agent = PydanticAIAgent(backend=backend, model="openai:gpt-4")
result = agent.run("Create a FastAPI server")
```

#### LangChain

```python
from prompttodraft.agent.langchain_agent import create_langchain_tools
from langchain.agents import create_react_agent

tools = create_langchain_tools(backend=backend)
agent = create_react_agent(llm, tools, prompt)
```

## Framework Comparison

| Framework | File | Integration Style | Best For |
|-----------|------|------------------|----------|
| **smolagents** | `smolagent_agent.py` | Manual `Tool` wrappers | HuggingFace models |
| **Pydantic-AI** | `pydantic_ai_agent.py` | Type-safe tool definitions | OpenAI, Anthropic |
| **LangChain** | `langchain_agent.py` | LangChain tool format | Complex chains |

## Output Models

Tools return `ToolOutputModel` instances that adapt to the environment:

```python
import os
os.environ["DISPLAY_MODE"] = "console"  # Rich terminal output (default)
os.environ["DISPLAY_MODE"] = "api"      # JSON for web APIs
os.environ["DISPLAY_MODE"] = "hybrid"   # Both console + JSON

result = tool.execute(...)
output = result.handle()  # Adapts based on DISPLAY_MODE
```

### Available Models

- **TextOutputModel** - Plain text content
- **CodeOutputModel** - Code with syntax highlighting
- **FileListOutputModel** - Lists of files/directories
- **ErrorOutputModel** - Error messages with details
- **MediaOutputModel** - Base64-encoded images/PDFs

See [`outputs/README.md`](outputs/README.md) for details.

## Execution Backends

All tools work across any execution environment:

| Backend | Environment | Best For |
|---------|-------------|----------|
| **LocalBackend** | Host machine | Development |
| **DockerBackend** | Docker container | Isolated testing |
| **E2BBackend** | Cloud sandbox | Production |

```python
from prompttodraft.agent.backends.docker_backend import DockerBackend
from prompttodraft.agent.backends.e2b_backend import E2BBackend

# Same tools, different environment
backend = DockerBackend(project_id="my-project", state_manager=GitStateManager())
# backend = E2BBackend(project_id="my-project", state_manager=GitStateManager())
```

See [`backends/README.md`](backends/README.md) for backend API reference.

## State Persistence

Backends support persistent state across sessions:

### Git Storage (Default)

```python
from prompttodraft.agent.backends.state_manager import GitStateManager

backend = LocalBackend(project_id="my-project", state_manager=GitStateManager())
backend.start()  # Loads from GitHub branch
# ... do work ...
backend.shutdown()  # Saves to GitHub branch
```

- Uses GitHub branches (e.g., `state/my-project`)
- Free, version controlled, easy to inspect
- Requires `gh` CLI

### GCS Storage

```python
from prompttodraft.agent.backends.state_manager import GCSStateManager

backend = LocalBackend(project_id="my-project", state_manager=GCSStateManager())
```

- Timestamped snapshots in GCS bucket
- Enterprise-grade, handles large files
- Requires GCP credentials

### No Persistence

```python
from prompttodraft.agent.backends.state_manager import NoOpStateManager

backend = LocalBackend(project_id="my-project", state_manager=NoOpStateManager())
```

## Directory Structure

```
agent/
├── backends/              # Execution environments (Local, Docker, E2B)
├── core/                  # Framework-agnostic tools
├── outputs/               # Output models (Text, Code, FileList, etc.)
├── smolagent_agent.py     # smolagents integration
├── pydantic_ai_agent.py   # Pydantic-AI integration
└── langchain_agent.py     # LangChain integration
```

## Extension Guide

### Adding a New Tool

1. **Create tool file** in `core/`:

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
        # Business logic using self.backend
        result = self.backend.execute_command(f"echo {param}")
        return TextOutputModel(content=result.output)
```

2. **Add wrappers** to framework integration files:
   - Add to `smolagent_agent.py` as a `Tool` class
   - Add to `pydantic_ai_agent.py` as a Pydantic-AI tool
   - Add to `langchain_agent.py` as a LangChain tool

3. **Tool automatically works** in all execution environments (local, Docker, E2B)

### Adding a New Framework

To integrate a new AI framework:

1. **Create agent file** (e.g., `myframework_agent.py`)

2. **Wrap each of the 10 core tools** in framework-specific format:

```python
from prompttodraft.agent.tools.read_file_tool import ReadFileTool

class MyFrameworkReadFileTool:
    """Framework-specific wrapper for ReadFileTool"""
    def __init__(self, backend):
        self.core_tool = ReadFileTool(backend=backend)

    def __call__(self, absolute_path: str):
        result = self.core_tool.execute(absolute_path=absolute_path)
        # Convert ToolOutputModel to framework-specific format
        return result.handle()
```

3. **See reference**: `smolagent_agent.py` for complete example

**Pattern**: Each framework integration wraps core tools and handles framework-specific calling conventions.

## Design Patterns

This toolkit uses several key patterns:

- **Strategy Pattern**: Swappable backends (Local, Docker, E2B) and state managers (Git, GCS, None)
- **Adapter Pattern**: Framework integrations adapt core tools to framework-specific APIs
- **Abstract Base Class**: `CoreTool` ensures consistent tool interface
- **Separation of Concerns**: Data (Pydantic models) vs. Presentation (display modes)

## Data Flow

```
User Request
    ↓
Framework Agent (smolagents/pydantic-ai/langchain)
    ↓
Core Tool (e.g., ReadFileTool)
    ↓
Backend (Local/Docker/E2B)
    ↓
Execution Environment
    ↓
ToolOutputModel (formatted result)
    ↓
Framework Response
```

## See Also

- [backends/README.md](backends/README.md) - Backend API reference, creating custom backends
- [core/README.md](core/README.md) - Core tools implementation details
- [outputs/README.md](outputs/README.md) - Output models documentation
