"""
Local execution backend.

This module implements the ExecutionBackend for local execution.
"""
import subprocess
import shutil
from pathlib import Path

from beartype import beartype

from prompttodraft.backends.execution_backend import (
    ExecutionBackend,
    BackendStatus,
    FileType,
    FileInfo,
    CommandResult,
)
from prompttodraft.backends.state_manager import StateManager
from prompttodraft.common import LOCAL_BACKEND_PATH

DEFAULT_TIMEOUT = 120  # 2 minutes in seconds


@beartype
class LocalBackend(ExecutionBackend):
    """Local execution backend."""

    def __init__(self, project_id: str, state_manager: StateManager):
        super().__init__(state_manager=state_manager)
        self._project_id = project_id
        self._status = BackendStatus.UNINITIALIZED

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
        self.load_latest_snapshot()

    def shutdown(self) -> None:
        # Sync current state via state manager before shutdown
        self.save_snapshot(message="Shutdown snapshot")
        self._status = BackendStatus.STOPPED

    def get_status(self) -> BackendStatus:
        return self._status

    def execute_command(self, command: str, timeout: int | None = None) -> CommandResult:
        translated_command = self._replace_virtual_paths_in_command(command)

        proc = subprocess.Popen(
            ["/bin/bash", "-c", translated_command],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=self._project_path
        )
        try:
            output, _ = proc.communicate(timeout=timeout or DEFAULT_TIMEOUT)
            if output:
                output = self._replace_system_paths_in_output(output)
            return CommandResult(output=output, exit_code=proc.returncode)
        except subprocess.TimeoutExpired:
            proc.kill()
            output, _ = proc.communicate()
            if output:
                output = self._replace_system_paths_in_output(output)
            return CommandResult(output=f"Timeout\n{output}", exit_code=124)

    def _replace_virtual_paths_in_command(self, command: str) -> str:
        """Replace virtual paths (/workspace) with system paths in shell commands."""
        return command.replace("/workspace", str(self._project_path))

    def _replace_system_paths_in_output(self, output: str) -> str:
        """Replace system paths with virtual paths (/workspace) in command output."""
        return output.replace(str(self._project_path), "/workspace")

    def get_working_directory(self) -> Path:
        """Get the working directory as seen by the LLM."""
        return Path("/workspace")
    
    def _to_system_path(self, virtual_path: Path) -> Path:
        """Convert virtual path (/workspace/...) to host path."""
        workspace = self.get_working_directory()
        if virtual_path.is_absolute():
            if not str(virtual_path).startswith(str(workspace)):
                raise ValueError(f"Path {virtual_path} is outside workspace {workspace}")
            rel_path = virtual_path.relative_to(workspace)
            return self._project_path / rel_path
        return self._project_path / virtual_path

    def _to_virtual_path(self, system_path: str | Path) -> Path:
        """Convert host path to virtual path."""
        system_path_obj = Path(system_path)
        if system_path_obj.is_relative_to(self._project_path):
            rel = system_path_obj.relative_to(self._project_path)
            return self.get_working_directory() / rel
        return system_path_obj

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
