"""
Docker execution backend.

This module implements the ExecutionBackend for Docker container execution.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

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
from prompttodraft.initializers.base import ProjectInitializer
from prompttodraft.common import DOCKER_BACKEND_PATH

DEFAULT_TIMEOUT = 120  # 2 minutes in seconds
CONTAINER_WORKSPACE = "/workspace"


class DockerBackend(ExecutionBackend):
    """Docker execution backend."""

    def __init__(
        self,
        project_id: str,
        state_manager: StateManager,
        initializer: ProjectInitializer
    ):
        super().__init__(state_manager=state_manager, initializer=initializer)
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
            # Run initialization if needed
            self._run_initialization()
            return

        # No container exists, create new one
        # Get Docker configuration from initializer
        docker_image = self.initializer.get_docker_image()
        docker_env_vars = self.initializer.get_docker_env_vars()

        # Replace placeholder values in environment variables
        resolved_env_vars = {
            key: value.replace("/workspace", CONTAINER_WORKSPACE)
            for key, value in docker_env_vars.items()
        }

        # Pull image if not present
        try:
            self._client.images.get(docker_image)
        except docker.errors.ImageNotFound:
            self._client.images.pull(docker_image)

        # On Linux, run container as host user to avoid permission issues
        # On macOS/Windows, Docker Desktop handles user mapping automatically
        container_kwargs = {
            "image": docker_image,
            "name": self._container_name,
            "command": "sleep infinity",  # Keep container running
            "volumes": {str(self._project_path): {"bind": CONTAINER_WORKSPACE, "mode": "rw"}},
            "working_dir": CONTAINER_WORKSPACE,
            "detach": True,
            "remove": False,
            "environment": resolved_env_vars,
        }

        # Only set user on Linux to match host user (avoids root-owned files)
        if os.name == "posix" and hasattr(os, "getuid"):
            container_kwargs["user"] = f"{os.getuid()}:{os.getgid()}"

        # Create and start container with volume mount
        self._container = self._client.containers.run(**container_kwargs)

        self._status = BackendStatus.RUNNING
        # Load existing files from state manager if any
        self.state_manager.load_latest(backend=self)
        # Run initialization if needed
        self._run_initialization()

    def shutdown(self) -> None:
        # Sync current state via state manager before shutdown
        if self._container is None:
            # Already shut down, nothing to do
            return

        self.state_manager.save_snapshot(backend=self, message="Shutdown snapshot")
        self._container.stop()
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

    def get_working_directory(self) -> str:
        """Get the working directory path for commands (container path)."""
        return CONTAINER_WORKSPACE

    def _get_host_working_directory(self) -> Path:
        """Get the host filesystem path where files are actually stored."""
        return self._project_path

    def convert_to_path(self, path: str | Path) -> Path:
        """
        Convert container path to host path for file operations.

        Container paths (e.g., /workspace/file.py) are mapped to host paths
        (e.g., /Users/.../data/project_id/file.py) where the volume is mounted.
        """
        path_obj = Path(path)

        # If path is absolute and starts with container workspace, convert to host path
        if path_obj.is_absolute() and path_obj.is_relative_to(CONTAINER_WORKSPACE):
            # Remove /workspace prefix and append to host project path
            relative_path = path_obj.relative_to(CONTAINER_WORKSPACE)
            return self._project_path / relative_path
        elif path_obj.is_absolute():
            # Absolute path outside workspace - just use it
            return path_obj
        else:
            # Relative path - make it relative to host project path
            return self._project_path / path_obj

    def _convert_to_container_path(self, host_path: Path) -> str:
        """
        Convert host path to container path.

        This is the reverse operation of convert_to_path().
        Host paths (e.g., /Users/.../data/project_id/file.py) are mapped back to
        container paths (e.g., /workspace/file.py).
        """
        if host_path.is_relative_to(self._project_path):
            relative_path = host_path.relative_to(self._project_path)
            return str(Path(CONTAINER_WORKSPACE) / relative_path)
        # If not under project path, return as-is
        return str(host_path)

    def read_file(self, file_path: str | Path) -> str:
        return self.convert_to_path(file_path).read_text()

    def write_file(self, file_path: str | Path, content: str) -> None:
        p = self.convert_to_path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)

    def delete_file(self, path: str | Path) -> None:
        self.convert_to_path(path).unlink()

    def delete_directory(self, path: str | Path) -> None:
        shutil.rmtree(self.convert_to_path(path))

    def create_directory(self, path: str | Path, parents: bool = False) -> None:
        self.convert_to_path(path).mkdir(parents=parents, exist_ok=True)

    def copy_file(self, src: str | Path, dst: str | Path) -> None:
        dst_path = self.convert_to_path(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.convert_to_path(src), dst_path)

    def move_file(self, src: str | Path, dst: str | Path) -> None:
        dst_path = self.convert_to_path(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(self.convert_to_path(src), dst_path)

    def list_directory(self, path: str | Path, recursive: bool = False) -> list[FileInfo]:
        p = self.convert_to_path(path)
        files = []

        for item in sorted(p.iterdir()):
            file_type = (
                FileType.SYMLINK if item.is_symlink()
                else FileType.FILE if item.is_file()
                else FileType.DIRECTORY if item.is_dir()
                else FileType.OTHER
            )
            # Convert host path back to container path for consistency with get_working_directory()
            container_path = self._convert_to_container_path(host_path=item)
            files.append(FileInfo(name=item.name, path=container_path, type=file_type))

            if recursive and file_type == FileType.DIRECTORY:
                # Use container path for recursive call to maintain consistency
                files.extend(self.list_directory(path=container_path, recursive=True))

        return files

    def file_exists(self, path: str | Path) -> FileType | None:
        p = self.convert_to_path(path)
        if not p.exists():
            return None
        if p.is_symlink():
            return FileType.SYMLINK
        if p.is_file():
            return FileType.FILE
        if p.is_dir():
            return FileType.DIRECTORY
        return FileType.OTHER

    def glob_files(self, pattern: str, path: str | Path | None = None) -> list[str]:
        search_path = self.convert_to_path(path) if path else self._project_path
        # Convert host paths back to container paths for consistency
        return [self._convert_to_container_path(host_path=p) for p in sorted(search_path.glob(pattern)) if p.is_file()]
