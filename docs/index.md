# Omniagents

A multi-backend execution framework for AI coding agents. Write tools once, run them anywhere.

## What is Omniagents?

Omniagents provides a unified interface for building AI coding agents that work across:

- **Multiple execution environments**: Local, Docker, or E2B cloud sandboxes
- **Multiple AI frameworks**: smolagents, Pydantic-AI, LangChain
- **Multiple state backends**: Git, Google Cloud Storage, or no persistence

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

## Core Features

| Feature | Description |
|---------|-------------|
| **10 Coding Tools** | File operations, shell commands, search, replace - everything an AI needs to code |
| **3 Execution Backends** | Local, Docker, E2B - same tools work everywhere |
| **3 AI Frameworks** | smolagents, Pydantic-AI, LangChain - use your preferred framework |
| **State Persistence** | Git or GCS - restore user sessions across runs |
| **Presets** | Python/UV, Python/pip, Generic - quick setup for any project type |

## Architecture

Omniagents uses a clean 3-layer architecture:

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

**Benefits:**

- **Write once, use everywhere**: Same tool code works in all environments
- **Mix and match**: Any backend + any framework + any storage
- **Easy testing**: Mock any layer for isolated testing

## Quick Links

- [Installation](getting-started/installation.md) - Get started in 5 minutes
- [Quick Start](getting-started/quickstart.md) - Your first agent
- [Architecture](concepts/architecture.md) - Understand the design
- [Tools Reference](api/tools.md) - All 10 coding tools

## Installation

```bash
# Using uv (recommended)
uv add omniagents

# Using pip
pip install omniagents
```

## License

MIT License - see LICENSE file for details.
