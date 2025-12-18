# Installation

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Install with uv (Recommended)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add omniagents to your project
uv add omniagents

# Or install globally
uv tool install omniagents
```

## Install with pip

```bash
pip install omniagents
```

## Optional Dependencies

### For Docker Backend

Install Docker Desktop or Docker Engine:

```bash
# macOS
brew install docker

# Ubuntu/Debian
sudo apt-get install docker.io
```

### For E2B Backend

Get an API key from [e2b.dev](https://e2b.dev) and set it:

```bash
export E2B_API_KEY="your-api-key"
```

### For Git State Manager

Install and authenticate the GitHub CLI:

```bash
# Install gh
brew install gh  # macOS
# or: sudo apt install gh  # Ubuntu

# Authenticate
gh auth login
```

### For GCS State Manager

Set up Google Cloud credentials:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
export BUCKET_OMNIAGENTS="your-bucket-name"
```

## Verify Installation

```python
from omniagents.backends.local_backend import LocalBackend
from omniagents.backends.state_manager import NoOpStateManager

backend = LocalBackend(
    project_id="test",
    state_manager=NoOpStateManager()
)
backend.start()
print(f"Working directory: {backend.get_working_directory()}")
backend.shutdown()
```

## Development Installation

To contribute or modify omniagents:

```bash
# Clone the repository
git clone https://github.com/charlesazam/omniagents.git
cd omniagents

# Install dependencies
uv sync

# Run tests
uv run pytest tests/ -v
```
