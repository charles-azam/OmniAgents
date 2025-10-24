"""
Docker execution backend.

This module implements the ExecutionBackend for Docker container execution.
"""
import shutil
from pathlib import Path

import docker
from docker.models.containers import Container

from prompttodraft.tools.backends.execution_backend import (
    ExecutionBackend,
    BackendStatus,
    FileType,
    FileInfo,
    CommandResult,
)
from prompttodraft.common import DATA_PATH

DEFAULT_TIMEOUT = 120  # 2 minutes in seconds
DOCKER_IMAGE = "ghcr.io/astral-sh/uv:debian"
CONTAINER_WORKSPACE = "/workspace"


class DockerBackend(ExecutionBackend):
    """Docker execution backend."""

    def __init__(self, project_id: str):
        self._project_id = project_id
        self._status = BackendStatus.UNINITIALIZED
        self._container: Container | None = None
        self._client = docker.from_env()

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def _project_path(self) -> Path:
        return DATA_PATH / self._project_id

    @property
    def _container_name(self) -> str:
        return f"prompttodraft-{self._project_id}"

    def init(self) -> None:
        # Create project directory if it doesn't exist
        self._project_path.mkdir(parents=True, exist_ok=True)

        # Check if container already exists
        try:
            self._container = self._client.containers.get(self._container_name)
            # Container exists, reload and start if needed
            self._container.reload()
            if self._container.status != "running":
                self._container.start()
            self._status = BackendStatus.RUNNING
            return
        except docker.errors.NotFound:
            pass  # Container doesn't exist, create it

        # Pull image if not present
        try:
            self._client.images.get(DOCKER_IMAGE)
        except docker.errors.ImageNotFound:
            self._client.images.pull(DOCKER_IMAGE)

        # Create and start container with volume mount
        self._container = self._client.containers.run(
            image=DOCKER_IMAGE,
            name=self._container_name,
            command="sleep infinity",  # Keep container running
            volumes={str(self._project_path): {"bind": CONTAINER_WORKSPACE, "mode": "rw"}},
            working_dir=CONTAINER_WORKSPACE,
            detach=True,
            remove=False,
        )

        self._status = BackendStatus.RUNNING
        # Load existing files from bucket if any
        self.load_from_bucket()

    def resume(self) -> None:
        if self._container is None:
            # Try to find existing container
            try:
                self._container = self._client.containers.get(self._container_name)
            except docker.errors.NotFound:
                raise RuntimeError("Container not found - call init() first")

        # Reload container state and start only if not running
        self._container.reload()
        if self._container.status != "running":
            self._container.start()

        self._status = BackendStatus.RUNNING
        # Load latest state from bucket
        self.load_from_bucket()

    def pause(self) -> None:
        # Sync current state to bucket before pausing
        self.sync_to_bucket()
        if self._container:
            self._container.stop()
        self._status = BackendStatus.PAUSED

    def shutdown(self) -> None:
        # Sync current state to bucket before shutdown
        self.sync_to_bucket()
        if self._container:
            self._container.stop()
            self._container.remove()
            self._container = None
        self._status = BackendStatus.STOPPED

    def get_status(self) -> BackendStatus:
        return self._status

    def execute_command(self, command: str, timeout: int | None = None) -> CommandResult:
        if self._container is None:
            raise RuntimeError("Container not initialized - call init() first")

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
        return str(self._project_path)

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
            files.append(FileInfo(name=item.name, path=str(item), type=file_type))

            if recursive and file_type == FileType.DIRECTORY:
                files.extend(self.list_directory(path=item, recursive=True))

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
        return [str(p) for p in sorted(search_path.glob(pattern)) if p.is_file()]
