# PromptToDraft

A multi-backend execution framework for AI coding agents. Run the same tools across local, Docker, or E2B environments with any AI framework (smolagents, Pydantic-AI, LangChain).

## Core Design Principle

**Write once, run anywhere**: Code tools once, execute in any environment (local/Docker/E2B), integrate with any framework (smolagents/Pydantic-AI/LangChain).

## Architecture

PromptToDraft uses a **3-layer architecture**:

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
from prompttodraft.backends.local_backend import LocalBackend
from prompttodraft.backends.state_manager import GitStateManager

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
from prompttodraft.smolagent_agent import SmolAgentAgent
from prompttodraft.backends.local_backend import LocalBackend
from prompttodraft.backends.state_manager import GitStateManager

# Create backend
backend = LocalBackend(project_id="my-project", state_manager=GitStateManager())
backend.start()

# Create agent
agent = SmolAgentAgent(
    backend=backend,
    provider="huggingface",
    model_id="Qwen/Qwen2.5-Coder-32B-Instruct"
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
from prompttodraft.backends.docker_backend import DockerBackend

backend = DockerBackend(project_id="my-project", state_manager=GitStateManager())
backend.start()  # Creates container
# ... use backend ...
backend.shutdown()  # Stops container
```

### E2B Backend

```python
from prompttodraft.backends.e2b_backend import E2BBackend

backend = E2BBackend(project_id="my-project", state_manager=GitStateManager())
backend.start()  # Creates sandbox
# ... use backend ...
backend.shutdown()  # Destroys sandbox
```

## State Persistence

### Git Storage (Default)

```python
from prompttodraft.backends.state_manager import GitStateManager

backend = LocalBackend(project_id="my-project", state_manager=GitStateManager())
```

- Requires: `gh` CLI installed and authenticated
- State saved to GitHub branches (e.g., `state/my-project`)
- Free, version controlled, easy to inspect

### Google Cloud Storage

```python
from prompttodraft.backends.state_manager import GCSStateManager

backend = LocalBackend(project_id="my-project", state_manager=GCSStateManager())
```

- Requires: GCP credentials configured
- State saved to GCS bucket with timestamps
- Enterprise-grade, handles large files

### No Persistence

```python
from prompttodraft.backends.state_manager import NoOpStateManager

backend = LocalBackend(project_id="my-project", state_manager=NoOpStateManager())
```

## Configuration

### GitHub Storage

Set up GitHub personal access token with `repo` scope:

```bash
export PROMPTTODRAFT_GITHUB_API_KEY="ghp_your_token_here"
export PROMPTTODRAFT_GITHUB_STATE_REPO="your-org/your-repo"  # Optional
```

### Google Cloud Storage

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/gcp-credentials.json"
export BUCKET_PROMPT_TO_DRAFT="your-bucket-name"
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

## Code Coverage

```bash
# Run tests with coverage report
uv run python -m pytest --cov=src/prompttodraft --cov-report=term-missing --cov-report=html

# View HTML coverage report
open htmlcov/index.html

# Run tests with coverage and fail if below threshold (e.g., 80%)
uv run python -m pytest --cov=src/prompttodraft --cov-report=term-missing --cov-fail-under=80
```

Coverage configuration is defined in `pyproject.toml` under `[tool.coverage.*]` sections.

## Documentation

- **[Agent Tools Guide](src/prompttodraft/agent/README.md)** - Tool catalog, framework integration, extension guide
- **[Backends API Reference](src/prompttodraft/agent/backends/README.md)** - Backend interface details, state management
- **[Core Tools API](src/prompttodraft/agent/core/README.md)** - Tool implementation patterns
- **[Benchmark Suite](src/prompttodraft/benchmark/tasks/README.md)** - Comparing AI frameworks

## CI/CD

The project uses GitHub Actions for continuous testing. See [Setup Secrets Guide](.github/SETUP_SECRETS.md) for configuring the CI/CD pipeline.

## Contributing

Contributions are welcome! Please ensure all tests pass before submitting a PR.

## License

See LICENSE file for details.
