# Backends API Reference

## ExecutionBackend (Abstract Base)

All backends inherit from `ExecutionBackend` and implement these methods.

### Constructor

```python
ExecutionBackend(state_manager: StateManager)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `state_manager` | `StateManager` | Handles workspace persistence |

### Properties

```python
@property
def project_id(self) -> str:
    """Unique identifier for this project/workspace."""

@property
def status(self) -> BackendStatus:
    """Current status: UNINITIALIZED, RUNNING, or STOPPED."""
```

### Lifecycle Methods

```python
def start(self) -> None:
    """
    Start the execution environment.
    - Creates environment (container, sandbox, etc.)
    - Calls state_manager.load_latest() to restore files
    """

def shutdown(self) -> None:
    """
    Shutdown the execution environment.
    - Calls state_manager.save_snapshot() to persist files
    - Destroys environment
    """

def get_status(self) -> BackendStatus:
    """Get current backend status."""
```

### Command Execution

```python
def execute_command(
    self,
    command: str,
    timeout: int | None = None
) -> CommandResult:
    """
    Execute a bash command.

    Args:
        command: Shell command to execute
        timeout: Max execution time in seconds (default: 120)

    Returns:
        CommandResult with output (stdout+stderr) and exit_code
    """
```

### File Operations

```python
def read_file(self, file_path: str | Path) -> str:
    """Read file contents as string."""

def write_file(self, file_path: str | Path, content: str) -> None:
    """Write content to file. Creates parent directories."""

def delete_file(self, path: str | Path) -> None:
    """Delete a file."""

def copy_file(self, src: str | Path, dst: str | Path) -> None:
    """Copy file from src to dst."""

def move_file(self, src: str | Path, dst: str | Path) -> None:
    """Move file from src to dst."""

def file_exists(self, path: str | Path) -> FileType | None:
    """
    Check if path exists.

    Returns:
        FileType.FILE, FileType.DIRECTORY, FileType.SYMLINK,
        FileType.OTHER, or None if doesn't exist
    """
```

### Directory Operations

```python
def get_working_directory(self) -> str:
    """Get the workspace root directory path."""

def list_directory(
    self,
    path: str | Path,
    recursive: bool = False
) -> list[FileInfo]:
    """
    List directory contents.

    Returns:
        List of FileInfo(name, path, type)
    """

def create_directory(
    self,
    path: str | Path,
    parents: bool = False
) -> None:
    """Create directory. If parents=True, creates parent dirs."""

def delete_directory(self, path: str | Path) -> None:
    """Delete directory and contents."""

def glob_files(
    self,
    pattern: str,
    path: str | Path | None = None
) -> list[str]:
    """Find files matching glob pattern."""
```

---

## LocalBackend

Executes code directly on the host machine.

```python
from omniagents.backends.local_backend import LocalBackend
from omniagents.backends.state_manager import NoOpStateManager

backend = LocalBackend(
    project_id="my-project",
    state_manager=NoOpStateManager()
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_id` | `str` | Required | Unique project identifier |
| `state_manager` | `StateManager` | Required | State persistence handler |

**Working directory**: `data/{project_id}/`

**Command execution**: Uses `subprocess` with `/bin/bash`

---

## DockerBackend

Executes code in an isolated Docker container.

```python
from omniagents.backends.docker_backend import DockerBackend
from omniagents.backends.state_manager import GitStateManager

backend = DockerBackend(
    project_id="my-project",
    state_manager=GitStateManager(),
    image="ghcr.io/astral-sh/uv:debian",
    environment={"MY_VAR": "value"},
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_id` | `str` | Required | Unique project identifier |
| `state_manager` | `StateManager` | Required | State persistence handler |
| `image` | `str` | `"ghcr.io/astral-sh/uv:debian"` | Docker image to use |
| `environment` | `dict[str, str]` | `{}` | Environment variables |

**Working directory**: `/workspace` (mounted from `data/{project_id}/`)

**Container lifecycle**:

- `start()`: Creates and starts container
- `shutdown()`: Stops and removes container

---

## E2BBackend

Executes code in E2B cloud sandboxes.

```python
from omniagents.backends.e2b_backend import E2BBackend
from omniagents.backends.state_manager import GCSStateManager
import os

os.environ["E2B_API_KEY"] = "your-api-key"

backend = E2BBackend(
    project_id="my-project",
    state_manager=GCSStateManager(),
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_id` | `str` | Required | Unique project identifier |
| `state_manager` | `StateManager` | Required | State persistence handler |

**Working directory**: `/tmp/workspace` (in sandbox)

**Sandbox lifetime**: 1 hour default timeout

---

## Data Classes

### BackendStatus

```python
class BackendStatus(Enum):
    UNINITIALIZED = "uninitialized"
    RUNNING = "running"
    STOPPED = "stopped"
```

### FileType

```python
class FileType(Enum):
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    OTHER = "other"
```

### FileInfo

```python
@dataclass
class FileInfo:
    name: str      # Filename
    path: str      # Full path
    type: FileType # File, directory, etc.
```

### CommandResult

```python
@dataclass
class CommandResult:
    output: str    # Combined stdout + stderr
    exit_code: int # 0 for success
```

---

## StateManager Interface

```python
class StateManager(ABC):
    @abstractmethod
    def save_snapshot(
        self,
        backend: ExecutionBackend,
        message: str = ""
    ) -> str:
        """Save workspace state. Returns snapshot ID."""

    @abstractmethod
    def load_latest(
        self,
        backend: ExecutionBackend
    ) -> bool:
        """Load latest snapshot. Returns True if found."""

    @abstractmethod
    def list_snapshots(
        self,
        project_id: str
    ) -> list[SnapshotInfo]:
        """List all snapshots for project."""

    @abstractmethod
    def cleanup(
        self,
        project_id: str
    ) -> None:
        """Delete all snapshots for project."""
```

### Implementations

- `NoOpStateManager` - No persistence
- `GitStateManager` - GitHub branches
- `GCSStateManager` - Google Cloud Storage

See [State Management](../concepts/state-management.md) for details.
