"""
Fly.io execution backend.

This module implements the ExecutionBackend for Fly.io Machines execution.
Uses flyctl CLI for SSH/SFTP operations and REST API for machine lifecycle.
"""
import os
import subprocess
import tempfile
from pathlib import Path

import httpx
from beartype import beartype

from omniagents.backends.execution_backend import (
    ExecutionBackend,
    BackendStatus,
    FileType,
    FileInfo,
    CommandResult,
)
from omniagents.backends.state_manager import StateManager
from omniagents.common import GCP_DATA_PATH

DEFAULT_TIMEOUT = 120  # 2 minutes in seconds
MACHINE_TIMEOUT = 3600  # 1 hour for machine lifetime
FLY_WORKING_DIR = "/workspace"  # Working directory inside Fly machine
FLY_API_BASE = "https://api.machines.dev/v1"


@beartype
class FlyBackend(ExecutionBackend):
    """Fly.io execution backend using flyctl CLI and REST API."""

    def __init__(
        self,
        project_id: str,
        state_manager: StateManager,
        app_name: str,
        api_token: str | None = None,
        region: str = "iad",
        image: str = "ubuntu:22.04",
        cpu_kind: str = "shared",
        cpus: int = 1,
        memory_mb: int = 256,
    ):
        """
        Create a Fly.io backend instance.

        Args:
            project_id: Unique identifier for this backend instance
            state_manager: StateManager instance for state persistence
            app_name: Fly.io app name (must exist, create with `fly apps create`)
            api_token: Fly.io API token (defaults to FLY_API_TOKEN env var)
            region: Fly.io region code (default: iad - Ashburn, Virginia)
            image: Docker image to use (default: ubuntu:22.04)
            cpu_kind: CPU type - "shared" or "performance" (default: shared)
            cpus: Number of CPUs (default: 1)
            memory_mb: Memory in MB (default: 256)
        """
        super().__init__(state_manager=state_manager)
        self._project_id = project_id
        self._app_name = app_name
        self._api_token = api_token or os.environ.get("FLY_API_TOKEN")
        self._region = region
        self._image = image
        self._cpu_kind = cpu_kind
        self._cpus = cpus
        self._memory_mb = memory_mb
        self._status = BackendStatus.UNINITIALIZED
        self._machine_id: str | None = None

        if not self._api_token:
            raise ValueError("FLY_API_TOKEN environment variable or api_token parameter required")

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def machine_id(self) -> str | None:
        """Get the current machine ID if running."""
        return self._machine_id

    @property
    def _project_path(self) -> Path:
        # Local path for GCP staging (same pattern as E2B)
        return GCP_DATA_PATH / self._project_id

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for Fly.io API requests."""
        return {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }

    def _create_machine(self) -> str:
        """
        Create a new Fly.io machine.

        Returns:
            Machine ID
        """
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{FLY_API_BASE}/apps/{self._app_name}/machines",
                headers=self._get_headers(),
                json={
                    "name": f"omniagents-{self._project_id}",
                    "region": self._region,
                    "config": {
                        "image": self._image,
                        "auto_destroy": False,
                        "guest": {
                            "cpu_kind": self._cpu_kind,
                            "cpus": self._cpus,
                            "memory_mb": self._memory_mb,
                        },
                        "env": {
                            "PROJECT_ID": self._project_id,
                        },
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["id"]

    def _wait_for_machine_state(self, target_state: str, timeout: int = 60) -> None:
        """
        Wait for machine to reach a target state.

        Args:
            target_state: State to wait for (e.g., "started", "stopped")
            timeout: Maximum time to wait in seconds
        """
        import time

        start_time = time.time()
        while time.time() - start_time < timeout:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{FLY_API_BASE}/apps/{self._app_name}/machines/{self._machine_id}",
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                data = response.json()
                if data["state"] == target_state:
                    return
            time.sleep(1)

        raise TimeoutError(f"Machine did not reach state '{target_state}' within {timeout} seconds")

    def _destroy_machine(self) -> None:
        """Destroy the current Fly.io machine."""
        if self._machine_id is None:
            return

        with httpx.Client(timeout=60.0) as client:
            response = client.delete(
                f"{FLY_API_BASE}/apps/{self._app_name}/machines/{self._machine_id}",
                headers=self._get_headers(),
                params={"force": "true"},
            )
            # 404 is fine - machine may already be destroyed
            if response.status_code != 404:
                response.raise_for_status()

    def _run_flyctl(
        self,
        args: list[str],
        timeout: int | None = None,
        input_data: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """
        Run a flyctl command.

        Args:
            args: Command arguments (without 'flyctl' prefix)
            timeout: Command timeout in seconds
            input_data: Optional stdin input

        Returns:
            CompletedProcess result
        """
        cmd = ["flyctl"] + args + ["--app", self._app_name]
        if self._machine_id:
            cmd.extend(["--machine", self._machine_id])

        env = os.environ.copy()
        env["FLY_API_TOKEN"] = self._api_token

        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout or DEFAULT_TIMEOUT,
            input=input_data,
            env=env,
        )

    def start(self) -> None:
        # Create project directory if it doesn't exist
        self._project_path.mkdir(parents=True, exist_ok=True)

        # Create new machine
        self._machine_id = self._create_machine()

        # Wait for machine to be started
        self._wait_for_machine_state(target_state="started", timeout=120)

        # Create working directory in machine
        self._run_flyctl(
            args=["ssh", "console", "--command", f"mkdir -p {FLY_WORKING_DIR}"],
            timeout=30,
        )

        self._status = BackendStatus.RUNNING

        # Load existing files from state manager if any
        self.load_latest_snapshot()

    def shutdown(self) -> None:
        if self._machine_id is None:
            return

        # Sync before destroying machine
        self.save_snapshot(message="Shutdown snapshot")

        self._destroy_machine()
        self._machine_id = None
        self._status = BackendStatus.STOPPED

    def get_status(self) -> BackendStatus:
        return self._status

    def execute_command(self, command: str, timeout: int | None = None) -> CommandResult:
        if self._machine_id is None:
            raise RuntimeError("Machine not initialized - call start() first")

        result = self._run_flyctl(
            args=["ssh", "console", "--command", f"cd {FLY_WORKING_DIR} && {command}"],
            timeout=timeout or DEFAULT_TIMEOUT,
        )

        output = result.stdout
        if result.stderr:
            output = output + result.stderr if output else result.stderr

        return CommandResult(
            output=output,
            exit_code=result.returncode,
        )

    def get_working_directory(self) -> Path:
        """Get the working directory as seen by the LLM (/workspace)."""
        return Path(FLY_WORKING_DIR)

    def _to_system_path(self, virtual_path: Path) -> Path:
        """Convert virtual path to machine path."""
        if not virtual_path.is_absolute():
            virtual_path = Path(FLY_WORKING_DIR) / virtual_path

        if not str(virtual_path).startswith(FLY_WORKING_DIR):
            raise ValueError(f"Path {virtual_path} is outside workspace {FLY_WORKING_DIR}")

        return virtual_path

    def _to_virtual_path(self, system_path: str | Path) -> Path:
        """Convert machine path to virtual path."""
        return Path(system_path)

    def read_file(self, file_path: Path) -> str:
        if self._machine_id is None:
            raise RuntimeError("Machine not initialized - call start() first")

        machine_path = self._to_system_path(file_path)

        # Use cat via SSH to read file content
        result = self._run_flyctl(
            args=["ssh", "console", "--command", f"cat {machine_path}"],
            timeout=30,
        )

        if result.returncode != 0:
            if "No such file" in result.stderr or "cannot open" in result.stderr.lower():
                raise FileNotFoundError(f"File not found: {file_path}")
            raise RuntimeError(f"Failed to read file: {result.stderr}")

        return result.stdout

    def write_file(self, file_path: Path, content: str) -> None:
        if self._machine_id is None:
            raise RuntimeError("Machine not initialized - call start() first")

        machine_path = self._to_system_path(file_path)

        # Create parent directory if needed
        parent = str(machine_path.parent)
        if parent != "/" and parent != ".":
            self._run_flyctl(
                args=["ssh", "console", "--command", f"mkdir -p {parent}"],
                timeout=30,
            )

        # Write content to temp file and upload via SFTP
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tmp") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        result = self._run_flyctl(
            args=["ssh", "sftp", "put", tmp_path, str(machine_path)],
            timeout=60,
        )

        # Clean up temp file
        os.unlink(tmp_path)

        if result.returncode != 0:
            raise RuntimeError(f"Failed to write file: {result.stderr}")

    def delete_file(self, path: Path) -> None:
        if self._machine_id is None:
            raise RuntimeError("Machine not initialized - call start() first")

        machine_path = self._to_system_path(path)

        # Check if file exists first
        check_result = self._run_flyctl(
            args=["ssh", "console", "--command", f"test -f {machine_path} && echo exists"],
            timeout=30,
        )
        if "exists" not in check_result.stdout:
            raise FileNotFoundError(f"File not found: {path}")

        result = self._run_flyctl(
            args=["ssh", "console", "--command", f"rm {machine_path}"],
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to delete file: {result.stderr}")

    def delete_directory(self, path: Path) -> None:
        if self._machine_id is None:
            raise RuntimeError("Machine not initialized - call start() first")

        machine_path = self._to_system_path(path)

        result = self._run_flyctl(
            args=["ssh", "console", "--command", f"rm -rf {machine_path}"],
            timeout=60,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to delete directory: {result.stderr}")

    def create_directory(self, path: Path, parents: bool = False) -> None:
        if self._machine_id is None:
            raise RuntimeError("Machine not initialized - call start() first")

        machine_path = self._to_system_path(path)
        flag = "-p" if parents else ""

        result = self._run_flyctl(
            args=["ssh", "console", "--command", f"mkdir {flag} {machine_path}"],
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to create directory: {result.stderr}")

    def copy_file(self, src: Path, dst: Path) -> None:
        if self._machine_id is None:
            raise RuntimeError("Machine not initialized - call start() first")

        src_path = self._to_system_path(src)
        dst_path = self._to_system_path(dst)

        result = self._run_flyctl(
            args=["ssh", "console", "--command", f"cp {src_path} {dst_path}"],
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to copy file: {result.stderr}")

    def move_file(self, src: Path, dst: Path) -> None:
        if self._machine_id is None:
            raise RuntimeError("Machine not initialized - call start() first")

        src_path = self._to_system_path(src)
        dst_path = self._to_system_path(dst)

        result = self._run_flyctl(
            args=["ssh", "console", "--command", f"mv {src_path} {dst_path}"],
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to move file: {result.stderr}")

    def list_directory(self, path: Path, recursive: bool = False) -> list[FileInfo]:
        if self._machine_id is None:
            raise RuntimeError("Machine not initialized - call start() first")

        machine_path = self._to_system_path(path)

        # Check if directory exists
        check_result = self._run_flyctl(
            args=["ssh", "console", "--command", f"test -d {machine_path} && echo exists"],
            timeout=30,
        )
        if "exists" not in check_result.stdout:
            raise FileNotFoundError(f"Directory {path} does not exist")

        # Use ls -la to get detailed listing
        result = self._run_flyctl(
            args=["ssh", "console", "--command", f"ls -la {machine_path}"],
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to list directory: {result.stderr}")

        files: list[FileInfo] = []
        for line in result.stdout.strip().split("\n"):
            # Skip header line and . / .. entries
            if line.startswith("total") or not line.strip():
                continue

            parts = line.split()
            if len(parts) < 9:
                continue

            name = parts[-1]
            if name in (".", ".."):
                continue

            # Determine file type from first character of permissions
            perms = parts[0]
            if perms.startswith("d"):
                file_type = FileType.DIRECTORY
            elif perms.startswith("l"):
                file_type = FileType.SYMLINK
            else:
                file_type = FileType.FILE

            entry_path = machine_path / name
            virtual_path = self._to_virtual_path(entry_path)

            files.append(FileInfo(name=name, path=virtual_path, type=file_type))

            # Recursive listing
            if recursive and file_type == FileType.DIRECTORY:
                try:
                    files.extend(self.list_directory(path=virtual_path, recursive=True))
                except Exception:
                    pass

        return sorted(files, key=lambda f: f.name)

    def file_exists(self, path: Path) -> FileType | None:
        if self._machine_id is None:
            raise RuntimeError("Machine not initialized - call start() first")

        machine_path = self._to_system_path(path)

        # Check if path exists and determine type
        result = self._run_flyctl(
            args=[
                "ssh",
                "console",
                "--command",
                f"if [ -d {machine_path} ]; then echo DIR; elif [ -f {machine_path} ]; then echo FILE; elif [ -L {machine_path} ]; then echo LINK; else echo NONE; fi",
            ],
            timeout=30,
        )

        output = result.stdout.strip()
        if output == "DIR":
            return FileType.DIRECTORY
        elif output == "FILE":
            return FileType.FILE
        elif output == "LINK":
            return FileType.SYMLINK
        return None

    def glob_files(self, pattern: str, path: Path | None = None) -> list[str]:
        if self._machine_id is None:
            raise RuntimeError("Machine not initialized - call start() first")

        search_path = str(self._to_system_path(path)) if path else FLY_WORKING_DIR

        if pattern.startswith("**/"):
            file_pattern = pattern[3:]
            cmd = f"find {search_path} -type f -name '{file_pattern}'"
        elif "**/" in pattern:
            cmd = f"find {search_path} -type f -name '{pattern}'"
        else:
            cmd = f"find {search_path} -maxdepth 1 -type f -name '{pattern}'"

        result = self._run_flyctl(
            args=["ssh", "console", "--command", cmd],
            timeout=60,
        )

        if result.returncode != 0:
            return []

        files = [f.strip() for f in result.stdout.split("\n") if f.strip()]
        return sorted([str(self._to_virtual_path(f)) for f in files])
