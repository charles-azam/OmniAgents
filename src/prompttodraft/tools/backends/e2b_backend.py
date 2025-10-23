"""
E2B execution backend.

This module implements the ExecutionBackend for E2B sandbox execution.
"""
from pathlib import Path

from e2b_code_interpreter import Sandbox
from e2b.sandbox.filesystem.filesystem import FileType as E2BFileType
from e2b.sandbox.commands.command_handle import CommandExitException

from prompttodraft.tools.backends.execution_backend import (
    ExecutionBackend,
    BackendStatus,
    FileType,
    FileInfo,
    CommandResult,
)
from prompttodraft.common import DATA_PATH

DEFAULT_TIMEOUT = 120  # 2 minutes in seconds
SANDBOX_TIMEOUT = 3600  # 1 hour for sandbox lifetime
SANDBOX_WORKING_DIR = "/tmp/workspace"  # Working directory inside E2B sandbox


class E2BBackend(ExecutionBackend):
    """E2B execution backend."""

    def __init__(self, project_id: str):
        self._project_id = project_id
        self._status = BackendStatus.UNINITIALIZED
        self._sandbox: Sandbox | None = None
        self._sandbox_id: str | None = None

    @property
    def _project_path(self) -> Path:
        return DATA_PATH / self._project_id

    @property
    def _sandbox_id_file(self) -> Path:
        """File to store sandbox ID for persistence."""
        return self._project_path / ".e2b_sandbox_id"

    @staticmethod
    def convert_to_path(path: str | Path) -> Path:
        """Convert string or Path to Path object."""
        return Path(path) if isinstance(path, str) else path

    def _save_sandbox_id(self) -> None:
        """Save sandbox ID to local file for persistence."""
        if self._sandbox_id:
            self._project_path.mkdir(parents=True, exist_ok=True)
            self._sandbox_id_file.write_text(self._sandbox_id)

    def _load_sandbox_id(self) -> str | None:
        """Load sandbox ID from local file."""
        if self._sandbox_id_file.exists():
            return self._sandbox_id_file.read_text().strip()
        return None

    def init(self) -> None:
        # Create project directory if it doesn't exist
        self._project_path.mkdir(parents=True, exist_ok=True)

        # Check if we have a saved sandbox ID
        saved_id = self._load_sandbox_id()
        if saved_id:
            # Try to reconnect to existing sandbox
            try:
                self._sandbox = Sandbox.connect(sandbox_id=saved_id)
                self._sandbox_id = saved_id
                self._status = BackendStatus.RUNNING
                return
            except Exception:
                # Sandbox no longer exists, create new one
                pass

        # Create new sandbox with metadata
        self._sandbox = Sandbox.create(
            timeout=SANDBOX_TIMEOUT,
            metadata={"project_id": self._project_id}
        )
        self._sandbox_id = self._sandbox.sandbox_id
        self._save_sandbox_id()

        # Create working directory in sandbox
        self._sandbox.files.make_dir(path=SANDBOX_WORKING_DIR)

        self._status = BackendStatus.RUNNING

    def resume(self) -> None:
        if self._sandbox is None:
            # Try to load sandbox ID and reconnect
            saved_id = self._load_sandbox_id()
            if saved_id:
                self._sandbox = Sandbox.connect(sandbox_id=saved_id)
                self._sandbox_id = saved_id
            else:
                raise RuntimeError("Sandbox not found - call init() first")

        self._status = BackendStatus.RUNNING

    def pause(self) -> None:
        # E2B sandboxes stay alive, just mark as paused
        self._status = BackendStatus.PAUSED

    def shutdown(self) -> None:
        # Don't kill sandbox immediately - let it timeout naturally
        # This allows files to persist for verification
        # The sandbox will auto-cleanup after SANDBOX_TIMEOUT
        self._status = BackendStatus.STOPPED

    def get_status(self) -> BackendStatus:
        return self._status

    def sync_to_bucket(self) -> None:
        pass  # No-op for e2b backend

    def load_from_bucket(self, person_id: str, task_id: str) -> None:
        pass  # No-op for e2b backend

    def execute_command(self, command: str, timeout: int | None = None) -> CommandResult:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call init() first")

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

    def read_file(self, file_path: str | Path) -> str:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call init() first")

        # E2B uses absolute paths inside the sandbox
        sandbox_path = str(file_path)
        return self._sandbox.files.read(path=sandbox_path)

    def write_file(self, file_path: str | Path, content: str) -> None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call init() first")

        sandbox_path = str(file_path)
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
            raise RuntimeError("Sandbox not initialized - call init() first")

        self._sandbox.files.remove(path=str(path))

    def delete_directory(self, path: str | Path) -> None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call init() first")

        # E2B remove works for both files and directories
        self._sandbox.files.remove(path=str(path))

    def create_directory(self, path: str | Path, parents: bool = False) -> None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call init() first")

        self._sandbox.files.make_dir(path=str(path))

    def copy_file(self, src: str | Path, dst: str | Path) -> None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call init() first")

        # E2B doesn't have built-in copy, use command
        result = self._sandbox.commands.run(cmd=f"cp {src} {dst}", cwd=SANDBOX_WORKING_DIR)
        if result.exit_code != 0:
            raise RuntimeError(f"Copy failed: {result.stderr}")

    def move_file(self, src: str | Path, dst: str | Path) -> None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call init() first")

        self._sandbox.files.rename(old_path=str(src), new_path=str(dst))

    def list_directory(self, path: str | Path, recursive: bool = False) -> list[FileInfo]:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call init() first")

        files = []
        entries = self._sandbox.files.list(path=str(path))

        for entry in sorted(entries, key=lambda x: x.name):
            file_type = FileType.DIRECTORY if entry.type == E2BFileType.DIR else FileType.FILE
            files.append(FileInfo(
                name=entry.name,
                path=str(Path(path) / entry.name),
                type=file_type
            ))

            if recursive and file_type == FileType.DIRECTORY:
                try:
                    subdir_files = self.list_directory(
                        path=str(Path(path) / entry.name),
                        recursive=True
                    )
                    files.extend(subdir_files)
                except:
                    pass  # Skip inaccessible directories

        return files

    def file_exists(self, path: str | Path) -> FileType | None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call init() first")

        if not self._sandbox.files.exists(path=str(path)):
            return None

        info = self._sandbox.files.get_info(path=str(path))
        return FileType.DIRECTORY if info.type == E2BFileType.DIR else FileType.FILE

    def glob_files(self, pattern: str, path: str | Path | None = None) -> list[str]:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call init() first")

        # Use find command for glob since E2B doesn't have native glob
        search_path = str(path) if path else SANDBOX_WORKING_DIR
        result = self._sandbox.commands.run(
            cmd=f"find {search_path} -name '{pattern}' -type f",
            cwd=SANDBOX_WORKING_DIR
        )

        if result.exit_code != 0:
            return []

        files = [f.strip() for f in result.stdout.split("\n") if f.strip()]
        return sorted(files)
