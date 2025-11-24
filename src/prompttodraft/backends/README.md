# Execution Backends API Reference

Execution backends provide primitive operations (execute commands, read/write files, etc.) across different execution environments.

## Backend Comparison

| Feature | LocalBackend | DockerBackend | E2BBackend |
|---------|-------------|---------------|------------|
| **Environment** | Host machine | Docker container | Cloud sandbox |
| **Isolation** | None | Container | Full sandbox |
| **Startup time** | Instant | ~2-5s | ~5-10s |
| **State persistence** | Git/GCS/DVC/None | Git/GCS/DVC/None | Git/GCS/DVC/None |
| **Dependencies** | None | Docker daemon | E2B API key |
| **Best for** | Development | Isolated testing | Production |

## Quick Examples

### LocalBackend

```python
from prompttodraft.backends.local_backend import LocalBackend
from prompttodraft.backends.state_manager import GitStateManager

backend = LocalBackend(project_id="my-project", state_manager=GitStateManager())
backend.start()
result = backend.execute_command("echo 'Hello'")
backend.shutdown()
```

### DockerBackend

```python
from prompttodraft.backends.docker_backend import DockerBackend

backend = DockerBackend(project_id="my-project", state_manager=GitStateManager())
backend.start()  # Creates/starts container
result = backend.execute_command("npm install")
backend.shutdown()  # Stops and removes container
```

### E2BBackend

```python
from prompttodraft.backends.e2b_backend import E2BBackend

backend = E2BBackend(project_id="my-project", state_manager=GitStateManager())
backend.start()  # Creates sandbox
result = backend.execute_command("python script.py")
backend.shutdown()  # Destroys sandbox
```

## ExecutionBackend Interface

All backends implement this interface:

### Lifecycle Management

```python
def start() -> None:
    """Create/start environment and load state"""

def shutdown() -> None:
    """Save state and destroy environment"""

def get_status() -> BackendStatus:
    """Get current status (UNINITIALIZED, RUNNING, STOPPED)"""
```

### Command Execution

```python
def execute_command(command: str, timeout: int | None = None) -> CommandResult:
    """Execute bash command, return output + exit code"""

def execute_uv(uv_command: str, timeout: int | None = None) -> CommandResult:
    """Execute uv command (installs uv if needed)"""
```

Returns: `CommandResult(output: str, exit_code: int)` with merged stdout/stderr.

### File Operations

```python
def read_file(file_path: str | Path) -> str
def write_file(file_path: str | Path, content: str) -> None
def delete_file(path: str | Path) -> None
def copy_file(src: str | Path, dst: str | Path) -> None
def move_file(src: str | Path, dst: str | Path) -> None
def file_exists(path: str | Path) -> FileType | None
```

### Directory Operations

```python
def get_working_directory() -> str
def list_directory(path: str | Path, recursive: bool = False) -> list[FileInfo]
def create_directory(path: str | Path, parents: bool = False) -> None
def delete_directory(path: str | Path) -> None
def glob_files(pattern: str, path: str | Path | None = None) -> list[str]
```

## State Persistence

Backends delegate state management to `StateManager` implementations.

### StateManager Interface

Backends don't handle persistence directly:

```python
class StateManager(ABC):
    def save_snapshot(backend, message) -> str  # Save current state
    def load_latest(backend) -> bool            # Load latest state
    def cleanup(project_id) -> None             # Delete all state
    def list_snapshots(project_id) -> list      # List all snapshots
```

### Implementations

#### Git Storage (Default)

```python
from prompttodraft.backends.state_manager import GitStateManager

backend = LocalBackend(project_id="my-project", state_manager=GitStateManager())
```

- Uses GitHub branches for state (e.g., `state/my-project`)
- Each project gets its own branch
- Automatic commit and push on shutdown
- Free, version controlled, easy to inspect

#### GCS Storage

```python
from prompttodraft.backends.state_manager import GCSStateManager

backend = LocalBackend(project_id="my-project", state_manager=GCSStateManager())
```

- Uses Google Cloud Storage buckets
- Timestamped snapshots (e.g., `project_id/20250108_143022_123456/`)
- Enterprise-grade, handles large files
- Requires GCP credentials

#### DVC Storage (Git + GCS for Large Files)

```python
from prompttodraft.backends.state_manager import DVCStateManager

backend = LocalBackend(project_id="my-project", state_manager=DVCStateManager())
```

- Uses DVC (Data Version Control) + Git with GCS backend
- Small files and code go to Git (version controlled)
- Large files (CAD, media, data) go to GCS via DVC
- Best of both worlds: version control + large file support
- Requires both GitHub token and GCS bucket
- Configurable patterns for which files use DVC (default: `*.step`, `*.stl`, `*.png`, `*.csv`, etc.)

**Environment variables:**
- `PROMPTTODRAFT_GITHUB_STATE_REPO`: GitHub repo (default: `charlesazam/prompttodraft-states`)
- `PROMPTTODRAFT_GITHUB_API_KEY`: GitHub token
- `BUCKET_PROMPT_TO_DRAFT`: GCS bucket for DVC cache

**Custom patterns:**
```python
# Only track specific large files with DVC
dvc_manager = DVCStateManager(dvc_patterns=["*.step", "*.stl", "data/*.parquet"])
backend = LocalBackend(project_id="my-project", state_manager=dvc_manager)
```

#### No Persistence

```python
from prompttodraft.backends.state_manager import NoOpStateManager

backend = LocalBackend(project_id="my-project", state_manager=NoOpStateManager())
```

- No state persistence
- For testing and ephemeral workloads

## Data Classes

```python
class BackendStatus(Enum):
    UNINITIALIZED = "uninitialized"
    RUNNING = "running"
    STOPPED = "stopped"

class FileType(Enum):
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    OTHER = "other"

@dataclass
class FileInfo:
    name: str
    path: str
    type: FileType

@dataclass
class CommandResult:
    output: str
    exit_code: int
```

## Path Handling

All backends normalize paths using `convert_to_path()`:

```python
def convert_to_path(self, path: str | Path) -> Path:
    """Convert relative paths to absolute based on working_directory"""
    path = Path(path)
    if path.is_absolute() and path.is_relative_to(working_dir):
        return path
    else:
        return working_dir / path
```

## Backend Details

### LocalBackend
- Working directory: `{DATA_PATH}/{project_id}/`
- Command execution: `subprocess` with `/bin/bash`
- File operations: Python's `pathlib` and `shutil`

### DockerBackend
- Image: `ghcr.io/astral-sh/uv:debian`
- Working directory: `/workspace` (mounted to local)
- Command execution: `container.exec_run()` with `/bin/bash`
- File operations: Volume-mounted, uses local filesystem

### E2BBackend
- Sandbox: Ephemeral E2B cloud sandbox
- Working directory: `/tmp/workspace` (in sandbox)
- Command execution: `sandbox.commands.run()` with bash
- File operations: E2B filesystem API with local sync

## Creating a Custom Backend

To add a new execution environment:

1. **Implement ExecutionBackend interface**:

```python
from prompttodraft.backends.execution_backend import ExecutionBackend, CommandResult
from prompttodraft.backends.state_manager import StateManager

class MyBackend(ExecutionBackend):
    def __init__(self, project_id: str, state_manager: StateManager):
        super().__init__(state_manager=state_manager)
        self._project_id = project_id

    @property
    def project_id(self) -> str:
        return self._project_id

    def start(self) -> None:
        # Create environment
        # Load from state manager
        self.state_manager.load_latest(backend=self)

    def shutdown(self) -> None:
        # Save to state manager
        self.state_manager.save_snapshot(backend=self, message="Shutdown")
        # Destroy environment

    def execute_command(self, command: str, timeout: int | None = None) -> CommandResult:
        # Execute in your environment
        pass

    def get_working_directory(self) -> str:
        # Return working directory path
        pass

    # ... implement all other ExecutionBackend methods
```

2. **All core tools work automatically** with your new backend

3. **Use with any framework**:

```python
from prompttodraft.smolagent_agent import SmolAgentAgent

backend = MyBackend(project_id="test", state_manager=GitStateManager())
backend.start()

agent = SmolAgentAgent(backend=backend, provider="huggingface", model_id="...")
```

## See Also

- [execution_backend.py](execution_backend.py) - ExecutionBackend abstract interface
- [state_manager.py](state_manager.py) - StateManager implementations
