"""
E2B execution backend.

This module implements the ExecutionBackend for E2B sandbox execution.
"""
from pathlib import Path

from beartype import beartype
from e2b_code_interpreter import Sandbox
from e2b.sandbox.filesystem.filesystem import FileType as E2BFileType
from e2b.sandbox.commands.command_handle import CommandExitException
from e2b.exceptions import NotFoundException

from anyagent.backends.execution_backend import (
    ExecutionBackend,
    BackendStatus,
    FileType,
    FileInfo,
    CommandResult,
)
from anyagent.backends.state_manager import StateManager
from anyagent.common import GCP_DATA_PATH

DEFAULT_TIMEOUT = 120  # 2 minutes in seconds
SANDBOX_TIMEOUT = 3600  # 1 hour for sandbox lifetime
SANDBOX_WORKING_DIR = "/workspace"  # Working directory inside E2B sandbox


@beartype
class E2BBackend(ExecutionBackend):
    """E2B execution backend."""

    def __init__(self, project_id: str, state_manager: StateManager):
        super().__init__(state_manager=state_manager)
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
        self.load_latest_snapshot()

    def shutdown(self) -> None:
        # Sync files via state manager and kill sandbox
        if self._sandbox is None:
            # Already shut down, nothing to do
            return

        # Sync before killing sandbox
        self.save_snapshot(message="Shutdown snapshot")

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

    def get_working_directory(self) -> Path:
        """Get the working directory as seen by the LLM (/workspace)."""
        return Path(SANDBOX_WORKING_DIR)

    def _to_system_path(self, virtual_path: Path) -> Path:
        """Convert virtual path to sandbox path."""
        if not virtual_path.is_absolute():
            virtual_path = Path(SANDBOX_WORKING_DIR) / virtual_path

        if not str(virtual_path).startswith(SANDBOX_WORKING_DIR):
            raise ValueError(f"Path {virtual_path} is outside workspace {SANDBOX_WORKING_DIR}")

        return virtual_path

    def _to_virtual_path(self, system_path: str | Path) -> Path:
        """Convert sandbox path to virtual path."""
        return Path(system_path)

    def read_file(self, file_path: Path) -> str:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        sandbox_path = self._to_system_path(file_path)
        try:
            return self._sandbox.files.read(path=str(sandbox_path))
        except NotFoundException as e:
            raise FileNotFoundError(str(e)) from e

    def write_file(self, file_path: Path, content: str) -> None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        sandbox_path = self._to_system_path(file_path)
        parent = str(sandbox_path.parent)
        if parent != "/" and parent != ".":
            try:
                self._sandbox.files.make_dir(path=parent)
            except:
                pass

        self._sandbox.files.write(path=str(sandbox_path), data=content)

    def delete_file(self, path: Path) -> None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        sandbox_path = self._to_system_path(path)
        if not self._sandbox.files.exists(path=str(sandbox_path)):
            raise FileNotFoundError(f"File not found: {path}")

        self._sandbox.files.remove(path=str(sandbox_path))

    def delete_directory(self, path: Path) -> None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        sandbox_path = self._to_system_path(path)
        self._sandbox.files.remove(path=str(sandbox_path))

    def create_directory(self, path: Path, parents: bool = False) -> None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        sandbox_path = self._to_system_path(path)
        self._sandbox.files.make_dir(path=str(sandbox_path))

    def copy_file(self, src: Path, dst: Path) -> None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        src_path = self._to_system_path(src)
        dst_path = self._to_system_path(dst)
        result = self._sandbox.commands.run(cmd=f"cp {src_path} {dst_path}", cwd=SANDBOX_WORKING_DIR)
        if result.exit_code != 0:
            raise RuntimeError(f"Copy failed: {result.stderr}")

    def move_file(self, src: Path, dst: Path) -> None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        src_path = self._to_system_path(src)
        dst_path = self._to_system_path(dst)
        self._sandbox.files.rename(old_path=str(src_path), new_path=str(dst_path))

    def list_directory(self, path: Path, recursive: bool = False) -> list[FileInfo]:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        sandbox_path = self._to_system_path(path)
        files = []

        # Try to list directory - if it fails, directory doesn't exist
        try:
            entries = self._sandbox.files.list(path=str(sandbox_path))
        except Exception:
            raise FileNotFoundError(f"Directory {path} does not exist")

        if not entries:
            return []

        for entry in sorted(entries, key=lambda x: x.name):
            file_type = FileType.DIRECTORY if entry.type == E2BFileType.DIR else FileType.FILE
            entry_path = sandbox_path / entry.name
            virtual_path = self._to_virtual_path(entry_path)

            files.append(FileInfo(name=entry.name, path=virtual_path, type=file_type))

            if recursive and file_type == FileType.DIRECTORY:
                try:
                    files.extend(self.list_directory(path=virtual_path, recursive=True))
                except:
                    pass

        return files

    def file_exists(self, path: Path) -> FileType | None:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        sandbox_path = self._to_system_path(path)
        if not self._sandbox.files.exists(path=str(sandbox_path)):
            return None

        info = self._sandbox.files.get_info(path=str(sandbox_path))
        return FileType.DIRECTORY if info.type == E2BFileType.DIR else FileType.FILE

    def glob_files(self, pattern: str, path: Path | None = None) -> list[str]:
        if self._sandbox is None:
            raise RuntimeError("Sandbox not initialized - call start() first")

        search_path = str(self._to_system_path(path)) if path else SANDBOX_WORKING_DIR

        if pattern.startswith("**/"):
            file_pattern = pattern[3:]
            result = self._sandbox.commands.run(
                cmd=f"find {search_path} -type f -name '{file_pattern}'",
                cwd=SANDBOX_WORKING_DIR
            )
        elif "**/" in pattern:
            result = self._sandbox.commands.run(
                cmd=f"find {search_path} -type f -name '{pattern}'",
                cwd=SANDBOX_WORKING_DIR
            )
        else:
            result = self._sandbox.commands.run(
                cmd=f"find {search_path} -maxdepth 1 -type f -name '{pattern}'",
                cwd=SANDBOX_WORKING_DIR
            )

        if result.exit_code != 0:
            return []

        files = [f.strip() for f in result.stdout.split("\n") if f.strip()]
        return sorted([str(self._to_virtual_path(f)) for f in files])
