# API Refactoring: Preset and AgentFactory Architecture

## Problem Statement

The original codebase had Python/UV hardcoded in multiple places, making it difficult to:
1. Create agents for other programming languages (Node.js, Rust, etc.)
2. Use different Python toolchains (pip instead of UV)
3. Customize Docker images per project
4. Understand the relationship between backends, tools, and initialization

### Hardcoded Python/UV Locations (Before)

| Location | Issue |
|----------|-------|
| `docker_backend.py` | `DOCKER_IMAGE = "ghcr.io/astral-sh/uv:debian"` hardcoded |
| `docker_backend.py` | UV-specific environment variables hardcoded |
| `execution_backend.py` | `execute_uv()` method in base class |
| `utils.py` | `initialize_project()` was Python/UV specific |
| `langchain_agent.py` | `UVTool` hardcoded in tool list |

## Solution: Two New Abstractions

### 1. Preset

A `Preset` defines the development environment: **tools** and **project initialization**.

```
src/anyagent/presets/
├── base.py       # Preset ABC + InitResult dataclass
├── python.py     # PythonUVPreset, PythonPipPreset
├── generic.py    # GenericPreset (no special tools)
```

```python
class Preset(ABC):
    name: str                                    # e.g., "python-uv"
    docker_image: str | None                     # Suggested Docker image
    tool_classes: tuple[type[CoreBackendTool], ...]  # Language-specific tools

    def initialize_project(backend) -> InitResult  # Setup logic
    def is_initialized(backend) -> bool            # Check if setup needed
```

**Concrete Presets:**
- `PythonUVPreset` - UV package manager + UVTool
- `PythonPipPreset` - pip + venv
- `GenericPreset` - No special tools (just shell access)

### 2. AgentFactory

An abstract base class that all framework-specific agents inherit from.

```python
class AgentFactory(ABC, Generic[TModel, TNativeTool]):
    def __init__(
        self,
        backend: ExecutionBackend,
        model: TModel,
        preset: Preset | None = None,
        extra_tool_classes: list[type[CoreBackendTool]] | None = None,
        native_tools: list[TNativeTool] | None = None,
    )

    @abstractmethod
    def _convert_tool(tool: CoreBackendTool) -> TNativeTool

    @abstractmethod
    def _run_agent(task: str) -> str

    def run(task: str, reset_history: bool = True) -> str  # Common logic
```

**Framework Implementations:**
- `LangChainAgent(AgentFactory[BaseChatModel, LangChainTool])`
- `SmolagentsAgent(AgentFactory[OpenAIModel, SmolagentsTool])`
- `PydanticAIAgent(AgentFactory[OpenAIChatModel, PydanticAITool])`

## Changes Made

### New Files Created

| File | Purpose |
|------|---------|
| `presets/base.py` | `Preset` ABC and `InitResult` dataclass |
| `presets/python.py` | `PythonUVPreset`, `PythonPipPreset` |
| `presets/generic.py` | `GenericPreset` |
| `agents/base.py` | `AgentFactory` ABC and `CORE_TOOLS` tuple |

### Files Modified

| File | Changes |
|------|---------|
| `agents/langchain_agent.py` | Now inherits from `AgentFactory` |
| `agents/smolagent_agent.py` | Now inherits from `AgentFactory`, renamed to `SmolagentsAgent` |
| `agents/pydantic_ai_agent.py` | Now inherits from `AgentFactory` |
| `backends/docker_backend.py` | Added `image` and `environment` parameters |
| `backends/execution_backend.py` | Removed `execute_uv()` method |
| `tools/uv_tool.py` | Now handles UV installation internally |
| `utils.py` | Removed `initialize_project()` (moved to `PythonUVPreset`) |

## New API Usage

### Basic Usage

```python
from anyagent.agents.langchain_agent import LangChainAgent
from anyagent.backends.local_backend import LocalBackend
from anyagent.backends.state_manager import NoOpStateManager
from anyagent.presets.python import PythonUVPreset

backend = LocalBackend(project_id="my-app", state_manager=NoOpStateManager())

agent = LangChainAgent(
    backend=backend,
    model=my_model,
    preset=PythonUVPreset(),
)

agent.run("Create a FastAPI server")
```

### Docker with Preset's Suggested Image

```python
from anyagent.backends.docker_backend import DockerBackend
from anyagent.presets.python import PythonUVPreset

preset = PythonUVPreset()

backend = DockerBackend(
    project_id="my-app",
    state_manager=state_manager,
    image=preset.docker_image,  # "ghcr.io/astral-sh/uv:debian"
)

agent = LangChainAgent(backend=backend, model=model, preset=preset)
```

### Custom Docker Image

```python
from anyagent.presets.generic import GenericPreset

backend = DockerBackend(
    project_id="my-rust-app",
    state_manager=state_manager,
    image="rust:1.75",  # Custom image
)

agent = LangChainAgent(
    backend=backend,
    model=model,
    preset=GenericPreset(),  # No language-specific tools
)
```

### Adding Custom Tools

```python
# Add custom CoreBackendTool classes
agent = LangChainAgent(
    backend=backend,
    model=model,
    preset=PythonUVPreset(),
    extra_tool_classes=[MyCustomTool, AnotherTool],
)

# Add native LangChain tools directly
from langchain_community.tools import DuckDuckGoSearchRun

agent = LangChainAgent(
    backend=backend,
    model=model,
    preset=PythonUVPreset(),
    native_tools=[DuckDuckGoSearchRun()],
)
```

### Using Just Backend + Preset (No Agent)

```python
from anyagent.presets.python import PythonUVPreset

backend = DockerBackend(...)
preset = PythonUVPreset()

backend.start()

# Initialize project using preset
if not preset.is_initialized(backend=backend):
    result = preset.initialize_project(backend=backend)
    print(result.message)

# Use backend directly
backend.write_file(path, content)
backend.execute_command("uv run script.py")

backend.shutdown()
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           User's Code                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LangChainAgent         SmolagentsAgent        PydanticAIAgent              │
│       │                      │                      │                       │
│       └──────────────────────┼──────────────────────┘                       │
│                              │                                              │
│                              ▼                                              │
│                      ┌─────────────────┐                                    │
│                      │  AgentFactory   │  ← Abstract base class             │
│                      │                 │    Handles common logic            │
│                      └─────────────────┘                                    │
│                              │                                              │
│              ┌───────────────┼───────────────┐                              │
│              ▼               ▼               ▼                              │
│      ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│      │   Backend   │  │   Preset    │  │   Native    │                      │
│      │ Local/Docker│  │ Python/Node │  │   Tools     │                      │
│      │    /E2B     │  │  /Generic   │  │ (optional)  │                      │
│      └─────────────┘  └─────────────┘  └─────────────┘                      │
│              │               │                                              │
│              ▼               ▼                                              │
│      ┌─────────────┐  ┌─────────────┐                                       │
│      │StateManager │  │CoreBackend  │                                       │
│      │None/Git/GCS │  │   Tool      │                                       │
│      └─────────────┘  └─────────────┘                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## How to Add a New Language/Runtime

1. Create a new preset in `presets/`:

```python
# presets/node.py
from anyagent.presets.base import Preset, InitResult

class NodeNPMPreset(Preset):
    name = "node-npm"
    docker_image = "node:22-slim"
    tool_classes = (NPMTool,)  # Create NPMTool if needed

    def is_initialized(self, backend):
        package_json = backend.get_working_directory() / "package.json"
        return backend.file_exists(path=package_json) is not None

    def initialize_project(self, backend):
        result = backend.execute_command(command="npm init -y")
        return InitResult(
            success=result.exit_code == 0,
            message=result.output,
            first_run=True,
        )
```

2. Optionally create language-specific tools in `tools/`

3. Use it:

```python
agent = LangChainAgent(
    backend=DockerBackend(..., image="node:22-slim"),
    model=model,
    preset=NodeNPMPreset(),
)
```

## Tests Updated

- `tests/test_agents/test_agent_e2e.py` - Updated `SmolAgentAgent` → `SmolagentsAgent`
- `tests/test_utils.py` - Now tests `PythonUVPreset.initialize_project()`
- `tests/test_backend/test_backend.py` - Replaced `execute_uv()` with `execute_command()`
- `tests/test_tools/test_tools.py` - Uses `PythonUVPreset` for initialization
