# PromptToDraft

[![Test All Backends](https://github.com/charles-azam/prompttodraft/actions/workflows/test.yml/badge.svg)](https://github.com/charles-azam/prompttodraft/actions/workflows/test.yml)

A multi-backend execution framework supporting local, Docker, and E2B sandbox environments.

## Features

- **Multi-Backend Support**: Run code in local, Docker containers, or E2B sandboxes
- **Unified API**: Same interface across all backends
- **File Operations**: Read, write, copy, move, and manage files
- **Command Execution**: Execute shell commands with timeout support
- **State Persistence**: Automatic sync to/from cloud storage
- **Comprehensive Testing**: E2E tests for all backends

## Backend Implementations

### 1. Local Backend
- Executes directly on the local filesystem
- Best for development and testing
- No additional setup required

### 2. Docker Backend
- Isolated execution in Docker containers
- File operations via volume mounts
- Automatic container lifecycle management
- Container reuse for efficiency

### 3. E2B Backend
- Secure sandboxed execution via E2B
- True isolation with ephemeral environments
- Cloud-native architecture

## Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

## Usage

```python
from prompttodraft.agent.backends.local_backend import LocalBackend
from prompttodraft.agent.backends.docker_backend import DockerBackend
from prompttodraft.agent.backends.e2b_backend import E2BBackend
from prompttodraft.agent.backends.state_manager import StorageType

# Choose your backend with storage option
backend = LocalBackend(project_id="my-project", storage=StorageType.GIT)
# backend = DockerBackend(project_id="my-project", storage=StorageType.GIT)
# backend = E2BBackend(project_id="my-project", storage=StorageType.GIT)

# Start the backend (loads state if it exists)
backend.start()

# Write a file
backend.write_file(file_path="hello.py", content="print('Hello, World!')")

# Execute a command
result = backend.execute_command(command="python hello.py")
print(result.output)  # "Hello, World!"

# Shutdown (saves state)
backend.shutdown()
```

### Storage Backends

**GitHub Storage (default):**
```python
from prompttodraft.agent.backends.state_manager import StorageType

backend = LocalBackend(project_id="my-project", storage=StorageType.GIT)
```
- Requires: `gh` CLI installed and authenticated
- State saved to: GitHub branches (e.g., `state/my-project`)
- Benefits: Free, version controlled, easy to inspect

**GCS Storage:**
```python
backend = LocalBackend(project_id="my-project", storage=StorageType.GCS)
```
- Requires: GCP credentials configured
- State saved to: GCS bucket with timestamps
- Benefits: Enterprise-grade, already set up in many orgs

**No Storage:**
```python
backend = LocalBackend(project_id="my-project", storage=StorageType.NONE)
```
- No state persistence
- Best for: Testing, ephemeral workloads

## Running Tests

```bash
# Run all tests
uv run python -m pytest tests/test_backend.py tests/test_tools.py -v

# Run specific backend tests
uv run python -m pytest tests/test_backend.py::test_local_backend_e2e -v
uv run python -m pytest tests/test_backend.py::test_docker_backend_e2e -v
uv run python -m pytest tests/test_backend.py::test_e2b_backend_e2e -v
```

## Configuration

### GitHub State Storage (Default)

Set up a GitHub personal access token with `repo` scope:

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token" and select `repo` scope
3. Copy the token and set it as an environment variable:

```bash
export PROMPTTODRAFT_GITHUB_API_KEY="ghp_your_token_here"
```

Configure the state repository (optional):

```bash
# Default: charlesazam/prompttodraft-states
export PROMPTTODRAFT_GITHUB_STATE_REPO="your-org/your-repo"
```

The token is used for:
- Pushing/pulling state to GitHub branches
- Listing commit history
- Deleting state branches during cleanup

### Google Cloud Storage

Set up credentials for GCS state persistence:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/gcp-credentials.json"
export BUCKET_PROMPT_TO_DRAFT="your-bucket-name"
```

### E2B API Key

For E2B backend:

```bash
export E2B_API_KEY="e2b_your_api_key_here"
```

## CI/CD

The project uses GitHub Actions for continuous testing. See [Setup Secrets Guide](.github/SETUP_SECRETS.md) for configuring the CI/CD pipeline.

## Architecture

All backends implement the `ExecutionBackend` abstract interface:

- **File Operations**: `read_file`, `write_file`, `delete_file`, `copy_file`, `move_file`
- **Directory Operations**: `create_directory`, `delete_directory`, `list_directory`
- **Search**: `glob_files`, `file_exists`
- **Execution**: `execute_command`
- **State Management**: `sync_to_bucket`, `load_from_bucket`
- **Lifecycle**: `start`, `shutdown`, `get_status`

## Contributing

Contributions are welcome! Please ensure all tests pass before submitting a PR.

## License

See LICENSE file for details.

