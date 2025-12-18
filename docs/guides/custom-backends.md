# Creating Custom Backends

This guide shows how to create your own execution backend for environments not covered by the built-in backends.

## When to Create a Custom Backend

Create a custom backend when you need to:

- Use a different cloud sandbox provider (Modal, Fly.io, AWS Lambda)
- Execute code on remote servers via SSH
- Run in Kubernetes pods
- Use specialized hardware (GPU clusters)

## Backend Interface

All backends must implement `ExecutionBackend`:

```python
from abc import ABC, abstractmethod
from omniagents.backends.execution_backend import (
    ExecutionBackend,
    CommandResult,
    FileInfo,
    FileType,
    BackendStatus
)
from omniagents.backends.state_manager import StateManager
from pathlib import Path

class MyBackend(ExecutionBackend):
    def __init__(self, project_id: str, state_manager: StateManager):
        super().__init__(state_manager=state_manager)
        self._project_id = project_id
        self._status = BackendStatus.UNINITIALIZED

    @property
    def project_id(self) -> str:
        return self._project_id

    # Implement all abstract methods...
```

## Example: SSH Backend

A backend that executes commands on a remote server via SSH.

```python
from omniagents.backends.execution_backend import (
    ExecutionBackend,
    CommandResult,
    FileInfo,
    FileType,
    BackendStatus
)
from omniagents.backends.state_manager import StateManager
from pathlib import Path
import subprocess

class SSHBackend(ExecutionBackend):
    def __init__(
        self,
        project_id: str,
        state_manager: StateManager,
        host: str,
        user: str,
        key_path: str,
    ):
        super().__init__(state_manager=state_manager)
        self._project_id = project_id
        self._host = host
        self._user = user
        self._key_path = key_path
        self._status = BackendStatus.UNINITIALIZED
        self._working_dir = f"/home/{user}/workspaces/{project_id}"

    @property
    def project_id(self) -> str:
        return self._project_id

    def _ssh_command(self, cmd: str) -> tuple[str, int]:
        """Execute command via SSH."""
        full_cmd = [
            "ssh",
            "-i", self._key_path,
            "-o", "StrictHostKeyChecking=no",
            f"{self._user}@{self._host}",
            f"cd {self._working_dir} && {cmd}"
        ]
        result = subprocess.run(full_cmd, capture_output=True, text=True)
        return result.stdout + result.stderr, result.returncode

    def start(self) -> None:
        # Create workspace directory
        self._ssh_command(f"mkdir -p {self._working_dir}")

        # Load state
        self.state_manager.load_latest(backend=self)

        self._status = BackendStatus.RUNNING

    def shutdown(self) -> None:
        # Save state
        self.state_manager.save_snapshot(backend=self, message="Shutdown")

        self._status = BackendStatus.STOPPED

    def get_status(self) -> BackendStatus:
        return self._status

    def execute_command(
        self,
        command: str,
        timeout: int | None = None
    ) -> CommandResult:
        output, exit_code = self._ssh_command(command)
        return CommandResult(output=output, exit_code=exit_code)

    def get_working_directory(self) -> str:
        return self._working_dir

    def read_file(self, file_path: str | Path) -> str:
        path = self._resolve_path(file_path)
        output, _ = self._ssh_command(f"cat {path}")
        return output

    def write_file(self, file_path: str | Path, content: str) -> None:
        path = self._resolve_path(file_path)
        # Create parent directory
        self._ssh_command(f"mkdir -p $(dirname {path})")
        # Write via heredoc
        self._ssh_command(f"cat > {path} << 'OMNIAGENTS_EOF'\n{content}\nOMNIAGENTS_EOF")

    def delete_file(self, path: str | Path) -> None:
        resolved = self._resolve_path(path)
        self._ssh_command(f"rm -f {resolved}")

    def copy_file(self, src: str | Path, dst: str | Path) -> None:
        src_path = self._resolve_path(src)
        dst_path = self._resolve_path(dst)
        self._ssh_command(f"cp {src_path} {dst_path}")

    def move_file(self, src: str | Path, dst: str | Path) -> None:
        src_path = self._resolve_path(src)
        dst_path = self._resolve_path(dst)
        self._ssh_command(f"mv {src_path} {dst_path}")

    def file_exists(self, path: str | Path) -> FileType | None:
        resolved = self._resolve_path(path)
        output, exit_code = self._ssh_command(f"stat -c %F {resolved} 2>/dev/null")
        if exit_code != 0:
            return None
        file_type = output.strip()
        if "regular" in file_type:
            return FileType.FILE
        elif "directory" in file_type:
            return FileType.DIRECTORY
        elif "symbolic" in file_type:
            return FileType.SYMLINK
        return FileType.OTHER

    def list_directory(
        self,
        path: str | Path,
        recursive: bool = False
    ) -> list[FileInfo]:
        resolved = self._resolve_path(path)
        if recursive:
            output, _ = self._ssh_command(f"find {resolved} -type f -o -type d")
        else:
            output, _ = self._ssh_command(f"ls -1 {resolved}")

        items = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            name = Path(line).name
            file_type = self.file_exists(line) or FileType.FILE
            items.append(FileInfo(name=name, path=line, type=file_type))
        return items

    def create_directory(self, path: str | Path, parents: bool = False) -> None:
        resolved = self._resolve_path(path)
        flag = "-p" if parents else ""
        self._ssh_command(f"mkdir {flag} {resolved}")

    def delete_directory(self, path: str | Path) -> None:
        resolved = self._resolve_path(path)
        self._ssh_command(f"rm -rf {resolved}")

    def glob_files(
        self,
        pattern: str,
        path: str | Path | None = None
    ) -> list[str]:
        base = self._resolve_path(path) if path else self._working_dir
        output, _ = self._ssh_command(f"find {base} -name '{pattern}'")
        return [line for line in output.strip().split("\n") if line]

    def _resolve_path(self, path: str | Path) -> str:
        """Convert relative paths to absolute."""
        path = Path(path)
        if path.is_absolute():
            return str(path)
        return str(Path(self._working_dir) / path)
```

## Using Your Custom Backend

```python
from omniagents.agents.langchain_agent import LangChainAgent
from omniagents.backends.state_manager import NoOpStateManager

backend = SSHBackend(
    project_id="my-project",
    state_manager=NoOpStateManager(),
    host="dev-server.example.com",
    user="ubuntu",
    key_path="/path/to/ssh/key",
)
backend.start()

agent = LangChainAgent(
    backend=backend,
    model=model,
    preset=preset,
)

result = agent.run("Create a Python web server")

backend.shutdown()
```

## Example: Fly.io Backend

```python
import subprocess
import json

class FlyBackend(ExecutionBackend):
    def __init__(
        self,
        project_id: str,
        state_manager: StateManager,
        app_name: str,
    ):
        super().__init__(state_manager=state_manager)
        self._project_id = project_id
        self._app_name = app_name
        self._machine_id: str | None = None

    def start(self) -> None:
        # Create a Fly machine
        result = subprocess.run(
            ["fly", "machine", "run", "python:3.13-slim",
             "--app", self._app_name,
             "--name", self._project_id,
             "--json"],
            capture_output=True, text=True
        )
        machine = json.loads(result.stdout)
        self._machine_id = machine["id"]

        # Load state
        self.state_manager.load_latest(backend=self)
        self._status = BackendStatus.RUNNING

    def shutdown(self) -> None:
        self.state_manager.save_snapshot(backend=self, message="Shutdown")

        # Destroy the machine
        subprocess.run(
            ["fly", "machine", "destroy", self._machine_id,
             "--app", self._app_name, "--force"],
            capture_output=True
        )
        self._status = BackendStatus.STOPPED

    def execute_command(self, command: str, timeout: int | None = None) -> CommandResult:
        result = subprocess.run(
            ["fly", "ssh", "console", "--app", self._app_name,
             "-C", command],
            capture_output=True, text=True,
            timeout=timeout
        )
        return CommandResult(
            output=result.stdout + result.stderr,
            exit_code=result.returncode
        )

    # ... implement remaining methods
```

## Best Practices

### 1. Handle State Manager Integration

Always call state manager methods in `start()` and `shutdown()`:

```python
def start(self) -> None:
    # Setup environment first
    self._create_workspace()

    # Then load state
    self.state_manager.load_latest(backend=self)

def shutdown(self) -> None:
    # Save state first
    self.state_manager.save_snapshot(backend=self, message="Shutdown")

    # Then cleanup
    self._destroy_workspace()
```

### 2. Resolve Paths Consistently

Always resolve relative paths to absolute:

```python
def _resolve_path(self, path: str | Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return Path(self._working_dir) / path
```

### 3. Handle Timeouts

Respect timeout parameters:

```python
def execute_command(self, command: str, timeout: int | None = None) -> CommandResult:
    timeout = timeout or 120  # Default 2 minutes
    # Pass timeout to subprocess or API
```

### 4. Test with All State Managers

Ensure your backend works with all state managers:

```python
@pytest.mark.parametrize("state_manager", [
    NoOpStateManager(),
    GitStateManager(),
    GCSStateManager(),
])
def test_backend_with_state_managers(state_manager):
    backend = MyBackend(project_id="test", state_manager=state_manager)
    # Test lifecycle
```
