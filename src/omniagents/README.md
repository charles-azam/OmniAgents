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
from anyagents.backends.local_backend import LocalBackend
from anyagents.backends.state_manager import GitStateManager
from anyagents.tools.read_file_tool import ReadFileTool

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
from anyagents.agents.smolagents_agent import SmolagentsAgent
from anyagents.backends.local_backend import LocalBackend
from anyagents.backends.state_manager import GitStateManager
from anyagents.presets.python import PythonUVPreset
from smolagents import HfApiModel

backend = LocalBackend(project_id="my-project", state_manager=GitStateManager())
backend.start()

model = HfApiModel(model_id="Qwen/Qwen2.5-Coder-32B-Instruct")
agent = SmolagentsAgent(
    backend=backend,
    model=model,
    preset=PythonUVPreset(),
)

result = agent.run("List all Python files")
```

#### Pydantic-AI

```python
from anyagents.agents.pydantic_ai_agent import PydanticAIAgent
from pydantic_ai.models.openai import OpenAIModel

model = OpenAIModel("gpt-4")
agent = PydanticAIAgent(backend=backend, model=model, preset=PythonUVPreset())
result = agent.run("Create a FastAPI server")
```

#### LangChain

```python
from anyagents.agents.langchain_agent import LangChainAgent
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4")
agent = LangChainAgent(backend=backend, model=model, preset=PythonUVPreset())
result = agent.run("Create a FastAPI server")
```

## Framework Comparison

| Framework | File | Integration Style | Best For |
|-----------|------|------------------|----------|
| **smolagents** | `agents/smolagents_agent.py` | AgentFactory with Tool wrappers | HuggingFace models |
| **Pydantic-AI** | `agents/pydantic_ai_agent.py` | AgentFactory with type-safe tools | OpenAI, Anthropic |
| **LangChain** | `agents/langchain_agent.py` | AgentFactory with LangChain tools | Complex chains |

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
from anyagents.backends.docker_backend import DockerBackend
from anyagents.backends.e2b_backend import E2BBackend

# Same tools, different environment
backend = DockerBackend(project_id="my-project", state_manager=GitStateManager())
# backend = E2BBackend(project_id="my-project", state_manager=GitStateManager())
```

See [`backends/README.md`](backends/README.md) for backend API reference.

## State Persistence

Backends support persistent state across sessions:

### Git Storage (Default)

```python
from anyagents.backends.state_manager import GitStateManager

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
from anyagents.backends.state_manager import GCSStateManager

backend = LocalBackend(project_id="my-project", state_manager=GCSStateManager())
```

- Timestamped snapshots in GCS bucket
- Enterprise-grade, handles large files
- Requires GCP credentials

### No Persistence

```python
from anyagents.backends.state_manager import NoOpStateManager

backend = LocalBackend(project_id="my-project", state_manager=NoOpStateManager())
```

## Directory Structure

```
anyagents/
├── agents/                # AI framework integrations (AgentFactory implementations)
├── backends/              # Execution environments (Local, Docker, E2B)
├── presets/               # Language/runtime presets (Python, generic, etc.)
├── tools/                 # Framework-agnostic tools
├── outputs/               # Output models (Text, Code, FileList, etc.)
└── uv_utils.py            # UV utilities (installation, execution)
```

## Extension Guide

### Adding a New Tool

1. **Create tool file** in `tools/`:

```python
from anyagents.tools.base_tool import CoreBackendTool
from pydantic import BaseModel, Field
from anyagents.outputs.outputs import TextOutputModel

class MyToolInput(BaseModel):
    param: str = Field(description="Parameter description")

class MyTool(CoreBackendTool[MyToolInput, TextOutputModel]):
    name = "my_tool"
    description = "Does something useful"

    def execute(self, inputs: MyToolInput) -> TextOutputModel:
        # Business logic using self.backend
        result = self.backend.execute_command(f"echo {inputs.param}")
        return TextOutputModel(content=result.output)
```

2. **Add to preset** or use with `extra_tool_classes`:
   ```python
   agent = LangChainAgent(
       backend=backend,
       model=model,
       preset=PythonUVPreset(),
       extra_tool_classes=[MyTool],
   )
   ```

3. **Tool automatically works** in all execution environments (local, Docker, E2B) and frameworks

### Adding a New Framework

To integrate a new AI framework:

1. **Create agent class** inheriting from `AgentFactory`:

```python
from anyagents.agents.base import AgentFactory
from typing import TypeVar

TModel = TypeVar("TModel")  # Your framework's model type
TNativeTool = TypeVar("TNativeTool")  # Your framework's tool type

class MyFrameworkAgent(AgentFactory[TModel, TNativeTool]):
    def _convert_tool(self, tool: CoreBackendTool) -> TNativeTool:
        """Convert CoreBackendTool to framework-specific tool"""
        # Implement conversion logic
        pass

    def _run_agent(self, task: str) -> str:
        """Run the framework-specific agent logic"""
        # Implement agent execution
        pass
```

2. **See references**:
   - `agents/langchain_agent.py` for LangChain example
   - `agents/smolagents_agent.py` for smolagents example
   - `agents/pydantic_ai_agent.py` for Pydantic-AI example

**Pattern**: AgentFactory handles common logic (preset, tool conversion), subclasses implement framework-specific behavior.

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
- [tools/README.md](tools/README.md) - Core tools implementation details
- [outputs/README.md](outputs/README.md) - Output models documentation
- [../docs/api-refactoring.md](../docs/api-refactoring.md) - Preset/AgentFactory architecture
