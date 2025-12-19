# Omniagents

A multi-backend execution framework for AI coding agents. Write tools once, run them anywhere.

## Install

```bash
uv add git+https://github.com/charles-azam/omniagents.git
```

## What is Omniagents?

Omniagents provides a unified interface for building AI coding agents that work across multiple execution environments (Local, Docker, E2B) and AI frameworks (smolagents, Pydantic-AI, LangChain).

```python
from omniagents.agents.langchain_agent import LangChainAgent
from omniagents.backends.docker_backend import DockerBackend
from omniagents.backends.state_manager import GitStateManager
from omniagents.presets.python import PythonUVPreset
from langchain_openai import ChatOpenAI

# Create isolated Docker environment with Git-based state persistence
backend = DockerBackend(
    project_id="my-project",
    state_manager=GitStateManager()
)
backend.start()

# Create agent with Python/UV preset
agent = LangChainAgent(
    backend=backend,
    model=ChatOpenAI(model="gpt-4"),
    preset=PythonUVPreset(),
)

# Run coding task
result = agent.run("Create a FastAPI server with a /hello endpoint")
backend.shutdown()  # Saves state to Git
```

## Features

| Feature | Description |
|---------|-------------|
| **10 Coding Tools** | File operations, shell commands, search, replace |
| **3 Execution Backends** | Local, Docker, E2B cloud sandboxes |
| **3 AI Frameworks** | smolagents, Pydantic-AI, LangChain |
| **State Persistence** | Git or GCS - restore sessions across runs |
| **Presets** | Python/UV, Python/pip, Generic |

## Installation

```bash
# Using uv (recommended)
uv add omniagents

# Using pip
pip install omniagents
```

## Quick Start

```python
from omniagents.backends.local_backend import LocalBackend
from omniagents.backends.state_manager import NoOpStateManager
from omniagents.tools.write_file_tool import WriteFileTool
from omniagents.tools.run_shell_command_tool import RunShellCommandTool

# Create backend
backend = LocalBackend(project_id="demo", state_manager=NoOpStateManager())
backend.start()

# Use tools directly
write_tool = WriteFileTool(backend=backend)
write_tool.execute(absolute_path="hello.py", content="print('Hello!')")

shell_tool = RunShellCommandTool(backend=backend)
result = shell_tool.execute(command="python hello.py")
print(result.content)  # "Hello!"

backend.shutdown()
```

## Architecture

```
┌─────────────────────────────────────────┐
│    Layer 3: Framework Integration       │
│  smolagents, Pydantic-AI, LangChain     │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│    Layer 2: Core Tools                  │
│  10 Gemini CLI-inspired coding tools    │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│    Layer 1: Execution Backends          │
│  Local, Docker, E2B                     │
└─────────────────────────────────────────┘
```

## Documentation

Full documentation is available at [docs/](docs/index.md) or build locally:

```bash
# Install docs dependencies
uv sync --extra docs

# Serve documentation locally
uv run mkdocs serve
```

### Quick Links

- [Installation](docs/getting-started/installation.md)
- [Quick Start](docs/getting-started/quickstart.md)
- [Architecture](docs/concepts/architecture.md)
- [Backends](docs/concepts/backends.md)
- [Tools Reference](docs/api/tools.md)

## Backend Options

| Backend | Environment | Isolation | Best For |
|---------|-------------|-----------|----------|
| `LocalBackend` | Host machine | None | Development |
| `DockerBackend` | Docker container | Container | Testing |
| `E2BBackend` | Cloud sandbox | Full | Production |

## State Persistence

| Manager | Storage | Best For |
|---------|---------|----------|
| `NoOpStateManager` | None | Testing |
| `GitStateManager` | GitHub branches | Version control |
| `GCSStateManager` | Google Cloud Storage | Enterprise |

## Running Tests

```bash
# All tests
uv run pytest tests/ -v

# Skip E2B tests (require API key)
uv run pytest tests/ -v -m "not e2b"

# Skip LLM tests (require API keys)
uv run pytest tests/ -v -m "not llm"
```

## Contributing

Contributions are welcome! Please ensure all tests pass before submitting a PR.

## License

MIT License - see LICENSE file for details.
