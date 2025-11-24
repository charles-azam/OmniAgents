"""
Local execution backend.

This module implements the ExecutionBackend for local execution.
"""
from __future__ import annotations

import subprocess
import shutil
from pathlib import Path

from prompttodraft.backends.execution_backend import (
    ExecutionBackend,
    BackendStatus,
    FileType,
    FileInfo,
    CommandResult,
)
from prompttodraft.backends.state_manager import StateManager
from prompttodraft.common import LOCAL_BACKEND_PATH
from prompttodraft.initializers.base import ProjectInitializer

DEFAULT_TIMEOUT = 120  # 2 minutes in seconds


class LocalBackend(ExecutionBackend):
    """Local execution backend."""

    def __init__(
        self,
        project_id: str,
        state_manager: StateManager,
        initializer: ProjectInitializer | None = None
    ):
        super().__init__(state_manager=state_manager, initializer=initializer)
        self._project_id = project_id
        self._status = BackendStatus.UNINITIALIZED

        # Handle circular dependency: if no initializer provided, create default PythonInitializer
        if self.initializer is None:
            from prompttodraft.initializers.python_initializer import PythonInitializer
            self.initializer = PythonInitializer(backend=self)

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def _project_path(self) -> Path:
        # Use temp directory to avoid nested project issues with parent repo
        return LOCAL_BACKEND_PATH / self._project_id

    def start(self) -> None:
        self._project_path.mkdir(parents=True, exist_ok=True)
        self._status = BackendStatus.RUNNING
        # Load existing files from state manager if any
        self.state_manager.load_latest(backend=self)

        # Initialize project if not already initialized
        if not self.initializer.is_initialized():
            self.initializer.initialize()

    def shutdown(self) -> None:
        # Sync current state via state manager before shutdown
        self.state_manager.save_snapshot(backend=self, message="Shutdown snapshot")
        self._status = BackendStatus.STOPPED

    def get_status(self) -> BackendStatus:
        return self._status

    def execute_command(self, command: str, timeout: int | None = None) -> CommandResult:
        proc = subprocess.Popen(
            ["/bin/bash", "-c", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=self._project_path
        )
        try:
            output, _ = proc.communicate(timeout=timeout or DEFAULT_TIMEOUT)
            return CommandResult(output=output, exit_code=proc.returncode)
        except subprocess.TimeoutExpired:
            proc.kill()
            output, _ = proc.communicate()
            return CommandResult(output=f"Timeout\n{output}", exit_code=124)

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
