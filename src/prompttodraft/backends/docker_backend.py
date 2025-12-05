"""
Docker execution backend.

This module implements the ExecutionBackend for Docker container execution.
"""
import os
import shutil
from pathlib import Path

from beartype import beartype
import docker
from docker.models.containers import Container

from prompttodraft.backends.execution_backend import (
    ExecutionBackend,
    BackendStatus,
    FileType,
    FileInfo,
    CommandResult,
)
from prompttodraft.backends.state_manager import StateManager
from prompttodraft.common import DOCKER_BACKEND_PATH

DEFAULT_TIMEOUT = 120  # 2 minutes in seconds
DOCKER_IMAGE = "ghcr.io/astral-sh/uv:debian"
CONTAINER_WORKSPACE = "/workspace"


@beartype
class DockerBackend(ExecutionBackend):
    """Docker execution backend."""

    def __init__(self, project_id: str, state_manager: StateManager):
        super().__init__(state_manager=state_manager)
        self._project_id = project_id
        self._status = BackendStatus.UNINITIALIZED
        self._container: Container | None = None
        self._client = docker.from_env()

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def _project_path(self) -> Path:
        return DOCKER_BACKEND_PATH / self._project_id

    @property
    def _container_name(self) -> str:
        return f"prompttodraft-{self._project_id}"

    def start(self) -> None:
        # Create project directory if it doesn't exist
        self._project_path.mkdir(parents=True, exist_ok=True)

        # Check if container already exists (for restart after shutdown)
        if self._container is None:
            try:
                self._container = self._client.containers.get(self._container_name)
            except docker.errors.NotFound:
                pass  # Container doesn't exist, will create below

        # If we have a container reference, try to start it
        if self._container is not None:
            self._container.reload()
            if self._container.status != "running":
                self._container.start()
            self._status = BackendStatus.RUNNING
            # Load latest state from state manager
            self.state_manager.load_latest(backend=self)
            return

        # No container exists, create new one
        # Pull image if not present
        try:
            self._client.images.get(DOCKER_IMAGE)
        except docker.errors.ImageNotFound:
            self._client.images.pull(DOCKER_IMAGE)

        # On Linux, run container as host user to avoid permission issues
        # On macOS/Windows, Docker Desktop handles user mapping automatically
        container_kwargs = {
            "image": DOCKER_IMAGE,
            "name": self._container_name,
            "command": "sleep infinity",  # Keep container running
            "volumes": {str(self._project_path): {"bind": CONTAINER_WORKSPACE, "mode": "rw"}},
            "working_dir": CONTAINER_WORKSPACE,
            "detach": True,
            "remove": False,
            "environment": {
                "HOME": CONTAINER_WORKSPACE,
                "UV_CACHE_DIR": f"{CONTAINER_WORKSPACE}/.cache/uv",
                "UV_TOOL_DIR": f"{CONTAINER_WORKSPACE}/.local/bin",
                "UV_PYTHON_INSTALL_DIR": f"{CONTAINER_WORKSPACE}/.local/share/uv/python",
            },
        }

        # Only set user on Linux to match host user (avoids root-owned files)
        if os.name == "posix" and hasattr(os, "getuid"):
            container_kwargs["user"] = f"{os.getuid()}:{os.getgid()}"

        # Create and start container with volume mount
        self._container = self._client.containers.run(**container_kwargs)

        self._status = BackendStatus.RUNNING
        # Load existing files from state manager if any
        self.state_manager.load_latest(backend=self)

    def shutdown(self) -> None:
        # Sync current state via state manager before shutdown
        if self._container is None:
            # Already shut down, nothing to do
            return

        self.state_manager.save_snapshot(backend=self, message="Shutdown snapshot")
        self._container.stop(timeout=0)
        self._container.remove()
        self._container = None
        self._status = BackendStatus.STOPPED

    def get_status(self) -> BackendStatus:
        return self._status

    def execute_command(self, command: str, timeout: int | None = None) -> CommandResult:
        if self._container is None:
            raise RuntimeError("Container not initialized - call start() first")

        exit_code, output = self._container.exec_run(
            cmd=["/bin/bash", "-c", command],
            workdir=CONTAINER_WORKSPACE,
            demux=False,  # Merge stdout and stderr
        )

        # Convert bytes to string if needed
        if isinstance(output, bytes):
            output = output.decode("utf-8")

        return CommandResult(output=output.rstrip("\n") if output else "", exit_code=exit_code)

    def get_working_directory(self) -> Path:
        """Get the working directory as seen by the LLM (/workspace)."""
        return Path(CONTAINER_WORKSPACE)

    def _to_system_path(self, virtual_path: Path) -> Path:
        """Convert LLM path (/workspace/...) to host path."""
        if virtual_path.is_absolute():
            if not str(virtual_path).startswith(CONTAINER_WORKSPACE):
                raise ValueError(f"Path {virtual_path} is outside workspace {CONTAINER_WORKSPACE}")
            rel_path = virtual_path.relative_to(CONTAINER_WORKSPACE)
            return self._project_path / rel_path
        return self._project_path / virtual_path

    def _to_virtual_path(self, system_path: str | Path) -> Path:
        """Convert host path to container path."""
        host_path = Path(system_path)
        if host_path.is_relative_to(self._project_path):
            relative_path = host_path.relative_to(self._project_path)
            return Path(CONTAINER_WORKSPACE) / relative_path
        return host_path

    def _determine_file_type(self, system_path: Path) -> FileType | None:
        """
        Determine the type of a filesystem entry on the host.

        Args:
            system_path: Path object on the host filesystem

        Returns:
            FileType if the path exists, None otherwise
        """
        if not system_path.exists():
            return None
        if system_path.is_symlink():
            return FileType.SYMLINK
        if system_path.is_file():
            return FileType.FILE
        if system_path.is_dir():
            return FileType.DIRECTORY
        return FileType.OTHER

    def read_file(self, file_path: Path) -> str:
        host_path = self._to_system_path(file_path)
        return host_path.read_text()

    def write_file(self, file_path: Path, content: str) -> None:
        host_path = self._to_system_path(file_path)
        host_path.parent.mkdir(parents=True, exist_ok=True)
        host_path.write_text(content)

    def delete_file(self, path: Path) -> None:
        host_path = self._to_system_path(path)
        host_path.unlink()

    def delete_directory(self, path: Path) -> None:
        host_path = self._to_system_path(path)
        shutil.rmtree(host_path)

    def create_directory(self, path: Path, parents: bool = False) -> None:
        host_path = self._to_system_path(path)
        host_path.mkdir(parents=parents, exist_ok=True)

    def copy_file(self, src: Path, dst: Path) -> None:
        host_src = self._to_system_path(src)
        host_dst = self._to_system_path(dst)
        host_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(host_src, host_dst)

    def move_file(self, src: Path, dst: Path) -> None:
        host_src = self._to_system_path(src)
        host_dst = self._to_system_path(dst)
        host_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(host_src, host_dst)

    def list_directory(self, path: Path, recursive: bool = False) -> list[FileInfo]:
        files = []
        host_path = self._to_system_path(path)

        if not host_path.exists():
            raise FileNotFoundError(f"Directory {path} does not exist")

        for item in sorted(host_path.iterdir()):
            file_type = (
                FileType.SYMLINK if item.is_symlink()
                else FileType.FILE if item.is_file()
                else FileType.DIRECTORY if item.is_dir()
                else FileType.OTHER
            )
            virtual_path = self._to_virtual_path(item)
            files.append(FileInfo(name=item.name, path=virtual_path, type=file_type))

            if recursive and file_type == FileType.DIRECTORY:
                files.extend(self.list_directory(path=virtual_path, recursive=True))

        return files

    def file_exists(self, path: Path) -> FileType | None:
        host_path = self._to_system_path(path)
        return self._determine_file_type(system_path=host_path)

    def glob_files(self, pattern: str, path: Path | None = None) -> list[str]:
        search_path = self._to_system_path(path) if path else self._project_path
        return [str(self._to_virtual_path(p)) for p in sorted(search_path.glob(pattern)) if p.is_file()]
