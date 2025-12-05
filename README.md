# AnyAgent

A multi-backend execution framework for AI coding agents. Run the same tools across local, Docker, or E2B environments with any AI framework (smolagents, Pydantic-AI, LangChain).

## Core Design Principle

**Write once, run anywhere**: Code tools once, execute in any environment (local/Docker/E2B), integrate with any framework (smolagents/Pydantic-AI/LangChain).

## Architecture

AnyAgent uses a **3-layer architecture**:

```
┌─────────────────────────────────────────┐
│    Layer 3: Framework Integration       │
│  smolagents, Pydantic-AI, LangChain     │
│  - Manual tool wrappers per framework   │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│    Layer 2: Core Tools                  │
│  10 Gemini CLI-inspired coding tools    │
│  - Framework-agnostic business logic    │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│    Layer 1: Execution Backends          │
│  Local, Docker, E2B                     │
│  - Primitive operations only            │
└─────────────────────────────────────────┘
```

**Benefits:**
- **Mix and Match**: Any backend + any framework + any storage
- **Write Once, Use Everywhere**: Tool logic works in all environments
- **Independent Testing**: Mock any layer for isolated testing

## Features

- **Multi-Backend Support**: Run code locally, in Docker containers, or E2B sandboxes
- **Unified API**: Same tool interface across all backends
- **Framework Agnostic**: Works with smolagents, Pydantic-AI, LangChain
- **10 Gemini CLI Tools**: list_directory, read_file, write_file, glob, search, replace, run_shell_command, read_many_files, save_memory, uv
- **State Persistence**: Automatic sync to GitHub or Google Cloud Storage
- **Comprehensive Testing**: E2E tests for all backends

## Quick Start

### Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### Basic Usage

```python
from anyagent.backends.local_backend import LocalBackend
from anyagent.backends.state_manager import GitStateManager

# Create backend with Git storage
backend = LocalBackend(project_id="my-project", state_manager=GitStateManager())
backend.start()

# Write a file
backend.write_file(file_path="hello.py", content="print('Hello, World!')")

# Execute a command
result = backend.execute_command(command="python hello.py")
print(result.output)  # "Hello, World!"

# Shutdown (saves state to Git)
backend.shutdown()
```

### Using with AI Agents

```python
from anyagent.agents.smolagents_agent import SmolagentsAgent
from anyagent.backends.local_backend import LocalBackend
from anyagent.backends.state_manager import GitStateManager
from anyagent.presets.python import PythonUVPreset

# Create backend
backend = LocalBackend(project_id="my-project", state_manager=GitStateManager())
backend.start()

# Create agent with Python/UV preset
from smolagents import HfApiModel
model = HfApiModel(model_id="Qwen/Qwen2.5-Coder-32B-Instruct")

agent = SmolagentsAgent(
    backend=backend,
    model=model,
    preset=PythonUVPreset(),
)

# Run task
result = agent.run("Create a FastAPI server with a /hello endpoint")
```

## Backend Options

| Backend | Environment | Isolation | Best For |
|---------|-------------|-----------|----------|
| **LocalBackend** | Host machine | None | Development, testing |
| **DockerBackend** | Docker container | Container-level | Isolated testing |
| **E2BBackend** | Cloud sandbox | Full sandbox | Production, scaling |

### Docker Backend

```python
from anyagent.backends.docker_backend import DockerBackend

backend = DockerBackend(project_id="my-project", state_manager=GitStateManager())
backend.start()  # Creates container
# ... use backend ...
backend.shutdown()  # Stops container
```

### E2B Backend

```python
from anyagent.backends.e2b_backend import E2BBackend

backend = E2BBackend(project_id="my-project", state_manager=GitStateManager())
backend.start()  # Creates sandbox
# ... use backend ...
backend.shutdown()  # Destroys sandbox
```

## State Persistence

### Git Storage (Default)

```python
from anyagent.backends.state_manager import GitStateManager

backend = LocalBackend(project_id="my-project", state_manager=GitStateManager())
```

- Requires: `gh` CLI installed and authenticated
- State saved to GitHub branches (e.g., `state/my-project`)
- Free, version controlled, easy to inspect

### Google Cloud Storage

```python
from anyagent.backends.state_manager import GCSStateManager

backend = LocalBackend(project_id="my-project", state_manager=GCSStateManager())
```

- Requires: GCP credentials configured
- State saved to GCS bucket with timestamps
- Enterprise-grade, handles large files

### No Persistence

```python
from anyagent.backends.state_manager import NoOpStateManager

backend = LocalBackend(project_id="my-project", state_manager=NoOpStateManager())
```

## Configuration

### GitHub Storage

Set up GitHub personal access token with `repo` scope:

```bash
export ANYAGENT_GITHUB_API_KEY="ghp_your_token_here"
export ANYAGENT_GITHUB_STATE_REPO="your-org/your-repo"  # Optional
```

### Google Cloud Storage

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/gcp-credentials.json"
export BUCKET_ANYAGENT="your-bucket-name"
```

### E2B API Key

```bash
export E2B_API_KEY="e2b_your_api_key_here"
```

## Running Tests

```bash
# Run all tests
uv run python -m pytest tests/test_backend.py tests/test_tools.py -v

# Run specific backend tests
uv run python -m pytest tests/test_backend.py::test_local_backend_e2e -v
uv run python -m pytest tests/test_backend.py::test_docker_backend_e2e -v
uv run python -m pytest tests/test_backend.py::test_e2b_backend_e2e -v
```

## Documentation

- **[Tools Guide](src/anyagent/README.md)** - Tool catalog, framework integration, extension guide
- **[Backends API Reference](src/anyagent/backends/README.md)** - Backend interface details, state management
- **[Tools API](src/anyagent/tools/README.md)** - Tool implementation patterns
- **[Preset Architecture](docs/api-refactoring.md)** - Preset/AgentFactory design and usage

## CI/CD

The project uses GitHub Actions for continuous testing. See [Setup Secrets Guide](.github/SETUP_SECRETS.md) for configuring the CI/CD pipeline.

## Contributing

Contributions are welcome! Please ensure all tests pass before submitting a PR.

## License

See LICENSE file for details.
