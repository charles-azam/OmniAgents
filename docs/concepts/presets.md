# Presets

Presets define development environments: which tools are available and how to initialize a project. They make it easy to work with different languages and toolchains.

## Available Presets

| Preset | Language | Package Manager | Docker Image |
|--------|----------|-----------------|--------------|
| `PythonUVPreset` | Python | UV | `ghcr.io/astral-sh/uv:debian` |
| `PythonPipPreset` | Python | pip + venv | `python:3.13-slim` |
| `GenericPreset` | Any | None | None |

## PythonUVPreset

For Python projects using UV package manager. Recommended for new projects.

```python
from omniagents.presets.python import PythonUVPreset
from omniagents.agents.langchain_agent import LangChainAgent
from omniagents.backends.docker_backend import DockerBackend

preset = PythonUVPreset()

backend = DockerBackend(
    project_id="my-python-app",
    state_manager=state_manager,
    image=preset.docker_image,  # "ghcr.io/astral-sh/uv:debian"
)
backend.start()

agent = LangChainAgent(
    backend=backend,
    model=model,
    preset=preset,  # Adds UVTool, handles initialization
)

result = agent.run("Create a FastAPI application")
```

**Provides:**

- `UVTool` for package management
- Auto-initialization with `uv init` + `uv sync`
- Checks for `pyproject.toml` to detect existing projects

## PythonPipPreset

For Python projects using traditional pip + venv.

```python
from omniagents.presets.python import PythonPipPreset

preset = PythonPipPreset()

backend = DockerBackend(
    project_id="legacy-app",
    state_manager=state_manager,
    image=preset.docker_image,  # "python:3.13-slim"
)

agent = LangChainAgent(
    backend=backend,
    model=model,
    preset=preset,
)
```

**Provides:**

- No special tools (uses shell for pip)
- Auto-initialization with `python -m venv .venv`
- Checks for `.venv` directory to detect existing projects

## GenericPreset

For any language or when you don't need special tooling.

```python
from omniagents.presets.generic import GenericPreset

preset = GenericPreset()

backend = DockerBackend(
    project_id="rust-app",
    state_manager=state_manager,
    image="rust:1.75",  # Custom image
)

agent = LangChainAgent(
    backend=backend,
    model=model,
    preset=preset,  # No special tools, just core tools
)
```

**Provides:**

- No language-specific tools
- No initialization
- Just the 10 core tools

## Preset Interface

All presets implement:

```python
class Preset(ABC):
    name: str                 # e.g., "python-uv"
    docker_image: str | None  # Suggested Docker image
    tool_classes: tuple[type[CoreBackendTool], ...]  # Additional tools

    @abstractmethod
    def is_initialized(self, backend: ExecutionBackend) -> bool:
        """Check if project is already initialized."""

    @abstractmethod
    def initialize_project(self, backend: ExecutionBackend) -> InitResult:
        """Initialize a new project."""
```

## Using Presets Without Agents

Presets work independently of agents:

```python
from omniagents.presets.python import PythonUVPreset
from omniagents.backends.docker_backend import DockerBackend

preset = PythonUVPreset()
backend = DockerBackend(project_id="my-app", ...)
backend.start()

# Check and initialize manually
if not preset.is_initialized(backend):
    result = preset.initialize_project(backend)
    print(f"Initialized: {result.message}")

# Use backend directly
backend.execute_command("uv add requests")
backend.execute_command("uv run python main.py")

backend.shutdown()
```

## Creating Custom Presets

Create presets for other languages:

```python
from omniagents.presets.base import Preset, InitResult
from omniagents.backends.execution_backend import ExecutionBackend

class NodeNPMPreset(Preset):
    name = "node-npm"
    docker_image = "node:22-slim"
    tool_classes = ()  # Add NPMTool if you create one

    def is_initialized(self, backend: ExecutionBackend) -> bool:
        """Check if package.json exists."""
        return backend.file_exists("package.json") is not None

    def initialize_project(self, backend: ExecutionBackend) -> InitResult:
        """Initialize with npm init."""
        result = backend.execute_command("npm init -y")
        return InitResult(
            success=result.exit_code == 0,
            message=result.output,
            first_run=True,
        )
```

Use it:

```python
preset = NodeNPMPreset()

backend = DockerBackend(
    project_id="node-app",
    state_manager=state_manager,
    image=preset.docker_image,
)

agent = LangChainAgent(
    backend=backend,
    model=model,
    preset=preset,
)

result = agent.run("Create an Express.js server")
```

## Preset + Agent Flow

When you call `agent.run()`:

1. **Check initialization**: `preset.is_initialized(backend)`
2. **Initialize if needed**: `preset.initialize_project(backend)`
3. **Collect tools**: Core tools + preset tools + extra tools
4. **Convert tools**: To framework-specific format
5. **Run agent**: Execute the task

```
agent.run("Create a web server")
        │
        ▼
┌───────────────────────────────┐
│ Is project initialized?       │
│ preset.is_initialized()       │
└───────────────┬───────────────┘
                │ No
                ▼
┌───────────────────────────────┐
│ Initialize project            │
│ preset.initialize_project()   │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ Collect all tools             │
│ Core + Preset + Extra         │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ Run framework agent           │
│ _run_agent(task)              │
└───────────────────────────────┘
```
