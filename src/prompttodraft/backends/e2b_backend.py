"""
E2B execution backend.

This module implements the ExecutionBackend for E2B sandbox execution.
"""
from __future__ import annotations

from pathlib import Path

from e2b_code_interpreter import Sandbox
from e2b.sandbox.filesystem.filesystem import FileType as E2BFileType
from e2b.sandbox.commands.command_handle import CommandExitException
from e2b.exceptions import NotFoundException

from prompttodraft.backends.execution_backend import (
    ExecutionBackend,
    BackendStatus,
    FileType,
    FileInfo,
    CommandResult,
)
from prompttodraft.backends.state_manager import StateManager
from prompttodraft.initializers.base import ProjectInitializer
from prompttodraft.common import GCP_DATA_PATH

DEFAULT_TIMEOUT = 120  # 2 minutes in seconds
SANDBOX_TIMEOUT = 3600  # 1 hour for sandbox lifetime
SANDBOX_WORKING_DIR = "/tmp/workspace"  # Working directory inside E2B sandbox


class E2BBackend(ExecutionBackend):
    """E2B execution backend."""

    def __init__(
        self,
        project_id: str,
        state_manager: StateManager,
        initializer: ProjectInitializer
    ):
        super().__init__(state_manager=state_manager, initializer=initializer)
        self._project_id = project_id
        self._status = BackendStatus.UNINITIALIZED
        self._sandbox: Sandbox | None = None

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def _project_path(self) -> Path:
        # E2B files only exist in remote sandbox, this path is only for GCP staging
        return GCP_DATA_PATH / self._project_id

    def start(self) -> None:
        # Create project directory if it doesn't exist
        self._project_path.mkdir(parents=True, exist_ok=True)

        # Always create new sandbox (ephemeral approach)
        self._sandbox = Sandbox.create(
            timeout=SANDBOX_TIMEOUT,
            metadata={"project_id": self._project_id}
        )

        # Create working directory in sandbox
        self._sandbox.files.make_dir(path=SANDBOX_WORKING_DIR)

        self._status = BackendStatus.RUNNING

        # Load existing files from state manager if any
        self.state_manager.load_latest(backend=self)
        # Run initialization if needed
        self._run_initialization()

    def shutdown(self) -> None:
        # Sync files via state manager and kill sandbox
        if self._sandbox is None:
            # Already shut down, nothing to do
            return

        # Sync before killing sandbox
        self.state_manager.save_snapshot(backend=self, message="Shutdown snapshot")

        self._sandbox.kill()
        self._sandbox = None
        self._status = BackendStatus.STOPPED

    def get_status(self) -> BackendStatus:
        return self._status

    def execute_command(self, command: str, timeout: int | None = None) -> CommandResult:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        try:
            result = self._sandbox.commands.run(
                cmd=command,
                cwd=SANDBOX_WORKING_DIR,
                timeout=timeout or DEFAULT_TIMEOUT
            )
            return CommandResult(
                output=result.stdout + result.stderr if result.stderr else result.stdout,
                exit_code=result.exit_code
            )
        except CommandExitException as e:
            return CommandResult(
                output=e.stdout + e.stderr if e.stderr else e.stdout,
                exit_code=e.exit_code
            )

    def get_working_directory(self) -> str:
        return SANDBOX_WORKING_DIR

    def _normalize_path(self, path: str | Path) -> str:
        """
        Normalize a path to an absolute path within the sandbox.
        Converts relative paths to absolute paths based on working directory.
        """
        path_obj = Path(path)
        # If path is already absolute, return as-is
        if path_obj.is_absolute():
            return str(path_obj)
        # If path is relative, make it absolute relative to working directory
        return str(Path(SANDBOX_WORKING_DIR) / path_obj)

    def read_file(self, file_path: str | Path) -> str:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        sandbox_path = self._normalize_path(path=file_path)
        try:
            return self._sandbox.files.read(path=sandbox_path)
        except NotFoundException as e:
            raise FileNotFoundError(str(e)) from e

    def write_file(self, file_path: str | Path, content: str) -> None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        sandbox_path = self._normalize_path(path=file_path)
        # Create parent directory if needed
        parent = str(Path(sandbox_path).parent)
        if parent != "/" and parent != ".":
            try:
                self._sandbox.files.make_dir(path=parent)
            except:
                pass  # Directory might already exist

        self._sandbox.files.write(path=sandbox_path, data=content)

    def delete_file(self, path: str | Path) -> None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        sandbox_path = self._normalize_path(path=path)
        # Check if file exists first, since E2B's remove() doesn't raise exception for non-existent files
        if not self._sandbox.files.exists(path=sandbox_path):
            raise FileNotFoundError(f"File not found: {path}")

        self._sandbox.files.remove(path=sandbox_path)

    def delete_directory(self, path: str | Path) -> None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        sandbox_path = self._normalize_path(path=path)
        # E2B remove works for both files and directories
        self._sandbox.files.remove(path=sandbox_path)

    def create_directory(self, path: str | Path, parents: bool = False) -> None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        sandbox_path = self._normalize_path(path=path)
        self._sandbox.files.make_dir(path=sandbox_path)

    def copy_file(self, src: str | Path, dst: str | Path) -> None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        src_path = self._normalize_path(path=src)
        dst_path = self._normalize_path(path=dst)
        # E2B doesn't have built-in copy, use command
        result = self._sandbox.commands.run(cmd=f"cp {src_path} {dst_path}", cwd=SANDBOX_WORKING_DIR)
        if result.exit_code != 0:
            raise RuntimeError(f"Copy failed: {result.stderr}")

    def move_file(self, src: str | Path, dst: str | Path) -> None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        src_path = self._normalize_path(path=src)
        dst_path = self._normalize_path(path=dst)
        self._sandbox.files.rename(old_path=src_path, new_path=dst_path)

    def list_directory(self, path: str | Path, recursive: bool = False) -> list[FileInfo]:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        sandbox_path = self._normalize_path(path=path)
        files = []
        entries = self._sandbox.files.list(path=sandbox_path)

        for entry in sorted(entries, key=lambda x: x.name):
            file_type = FileType.DIRECTORY if entry.type == E2BFileType.DIR else FileType.FILE
            entry_path = str(Path(sandbox_path) / entry.name)
            files.append(FileInfo(
                name=entry.name,
                path=entry_path,
                type=file_type
            ))

            if recursive and file_type == FileType.DIRECTORY:
                try:
                    subdir_files = self.list_directory(
                        path=entry_path,
                        recursive=True
                    )
                    files.extend(subdir_files)
                except:
                    pass  # Skip inaccessible directories

        return files

    def file_exists(self, path: str | Path) -> FileType | None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        sandbox_path = self._normalize_path(path=path)
        if not self._sandbox.files.exists(path=sandbox_path):
            return None

        info = self._sandbox.files.get_info(path=sandbox_path)
        return FileType.DIRECTORY if info.type == E2BFileType.DIR else FileType.FILE

    def glob_files(self, pattern: str, path: str | Path | None = None) -> list[str]:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        # Use find command for glob since E2B doesn't have native glob
        search_path = self._normalize_path(path=path) if path else SANDBOX_WORKING_DIR

        # Convert glob pattern to find command
        # Handle ** recursive glob patterns
        if pattern.startswith("**/"):
            # **/*.py -> find all .py files recursively
            file_pattern = pattern[3:]  # Remove **/
            result = self._sandbox.commands.run(
                cmd=f"find {search_path} -type f -name '{file_pattern}'",
                cwd=SANDBOX_WORKING_DIR
            )
        elif "**/" in pattern:
            # Complex pattern with ** in middle - not common, treat as literal
            result = self._sandbox.commands.run(
                cmd=f"find {search_path} -type f -name '{pattern}'",
                cwd=SANDBOX_WORKING_DIR
            )
        else:
            # Simple pattern like *.py -> only search in the directory itself
            result = self._sandbox.commands.run(
                cmd=f"find {search_path} -maxdepth 1 -type f -name '{pattern}'",
                cwd=SANDBOX_WORKING_DIR
            )

        if result.exit_code != 0:
            return []

        files = [f.strip() for f in result.stdout.split("\n") if f.strip()]
        return sorted(files)
