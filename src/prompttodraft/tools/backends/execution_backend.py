"""
Abstract execution backend interface.

This module defines the interface for execution backends (local, docker, e2b).
All backends must implement these primitive operations.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from datetime import datetime, timezone

from prompttodraft.common import GCP_DATA_PATH
from prompttodraft import storage_utils


class BackendStatus(Enum):
    """Status of the execution backend."""
    UNINITIALIZED = "uninitialized"
    RUNNING = "running"
    STOPPED = "stopped"


class FileType(Enum):
    """Type of filesystem entry."""
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    OTHER = "other"


@dataclass
class FileInfo:
    """Information about a file or directory."""
    name: str
    path: str
    type: FileType


@dataclass
class CommandResult:
    """Result of command execution."""
    output: str
    exit_code: int


class ExecutionBackend(ABC):
    """Abstract base class for execution backends."""

    @abstractmethod
    def __init__(self, project_id: str) -> None:
        """
        Create a backend instance for a specific project.

        Args:
            project_id: Identifier for the project
        """
        pass

    @property
    @abstractmethod
    def project_id(self) -> str:
        """Get the project ID for this backend instance."""
        pass

    @abstractmethod
    def start(self) -> None:
        """
        Start or restart the backend environment.

        This creates or reconnects to an execution environment:
        - Creates project directory/container/sandbox if needed
        - Loads files from bucket if available
        - Sets status to RUNNING

        Can be called after initialization or after shutdown to restart.
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        Shutdown the backend completely and flush all state to bucket.

        This should:
        - Sync all files to bucket
        - Stop all processes
        - Destroy the execution environment (container/sandbox)
        - Set status to STOPPED
        """
        pass

    @abstractmethod
    def get_status(self) -> BackendStatus:
        """
        Get the current status of the backend.

        Returns:
            Current backend status
        """
        pass

    # === State Management ===

    def _should_sync_file(self, file_path: str) -> bool:
        """
        Check if a file should be synced to bucket based on gitignore-like rules.

        Args:
            file_path: Relative file path from working directory

        Returns:
            True if file should be synced, False otherwise
        """
        path = Path(file_path)

        # Skip any file under a directory that starts with "."
        for part in path.parts:
            if part.startswith("."):
                return False

        # Ignore specific patterns
        ignore_patterns = [
            "__pycache__", "node_modules"
        ]

        for part in path.parts:
            if part in ignore_patterns or part.endswith(".pyc"):
                return False

        # Include only specific extensions
        allowed_extensions = {".py", ".txt", ".md", ".json", ".yaml", ".yml", ".toml"}
        allowed_filenames = {"pyproject.toml"}

        if path.name in allowed_filenames:
            return True

        return path.suffix in allowed_extensions

    def sync_to_bucket(self) -> None:
        """
        Sync all relevant files from working directory to bucket with timestamp.

        Files are saved under project_id/timestamp/ to create immutable snapshots.
        This prevents deleted files from being restored on reload.

        Only syncs files matching allowed extensions (.py, .txt, .md, .json, .yaml, .toml)
        and excludes common ignore patterns (.venv/, __pycache__/, etc.).
        """
        working_dir = Path(self.get_working_directory())

        # Create timestamp snapshot
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        project_data_path = GCP_DATA_PATH / self.project_id / timestamp

        # List all files recursively
        files = self.list_directory(path=working_dir, recursive=True)

        for file_info in files:
            if file_info.type != FileType.FILE:
                continue

            # Get relative path from working directory
            file_path = Path(file_info.path)
            relative_path = file_path.relative_to(working_dir)

            # Check if file should be synced
            if not self._should_sync_file(str(relative_path)):
                continue

            # Read file content
            content = self.read_file(file_path=file_path)

            # Write to bucket with timestamp (storage_utils expects path relative to GCP_DATA_PATH)
            bucket_path = project_data_path / relative_path
            storage_utils.write_to_storage(file_path=bucket_path, content=content)

    def load_from_bucket(self) -> None:
        """
        Load all files from the latest snapshot in bucket into the working directory.

        Finds the most recent timestamp snapshot under project_id/ and loads all files
        from that snapshot. This ensures deleted files are not restored.
        """
        working_dir = Path(self.get_working_directory())
        bucket = storage_utils.get_bucket()

        # Find all timestamp directories for this project
        prefix = f"{self.project_id}/"
        timestamps = set()

        for blob in bucket.list_blobs(prefix=prefix):
            # Extract timestamp from blob path: project_id/timestamp/file/path
            blob_path = Path(blob.name)
            parts = blob_path.parts

            if len(parts) >= 2 and parts[0] == self.project_id:
                timestamps.add(parts[1])

        if not timestamps:
            # No snapshots exist yet
            return

        # Get the latest timestamp (lexicographically sorted due to timestamp format)
        latest_timestamp = max(timestamps)

        # Load files from latest snapshot
        snapshot_prefix = f"{self.project_id}/{latest_timestamp}/"
        project_data_path = GCP_DATA_PATH / self.project_id / latest_timestamp

        for blob in bucket.list_blobs(prefix=snapshot_prefix):
            # Get relative path from snapshot directory
            blob_path = Path(blob.name)
            # Remove project_id/timestamp/ prefix to get file relative path
            relative_path = blob_path.relative_to(self.project_id).relative_to(latest_timestamp)

            # Check if file should be loaded (same filters as sync)
            if not self._should_sync_file(str(relative_path)):
                continue

            # Read from bucket
            bucket_file_path = project_data_path / relative_path
            content = storage_utils.read_from_storage(file_path=bucket_file_path)

            # Write to working directory
            dest_path = working_dir / relative_path
            self.write_file(file_path=dest_path, content=content)

    # === Command Execution ===

    @abstractmethod
    def execute_command(
        self,
        command: str,
        timeout: int | None = None
    ) -> CommandResult:
        """
        Execute a bash command synchronously.

        Args:
            command: The bash command to execute
            timeout: Optional timeout in milliseconds

        Returns:
            CommandResult with output (stdout+stderr merged) and exit_code
        """
        pass

    def execute_uv(
        self,
        uv_command: str,
        timeout: int | None = None
    ) -> CommandResult:
        """
        Execute a uv command, ensuring uv is installed first.

        Args:
            uv_command: The uv command to execute (e.g., "run script.py", "add requests", "sync")
            timeout: Optional timeout in milliseconds

        Returns:
            CommandResult with output (stdout+stderr merged) and exit_code
        """
        # Check if uv is installed
        uv_check = self.execute_command(
            command='export PATH="$HOME/.local/bin:$PATH" && command -v uv',
            timeout=10000,
        )

        if uv_check.exit_code != 0:
            # Install uv
            install_command = "curl -LsSf https://astral.sh/uv/install.sh | sh"
            install_result = self.execute_command(
                command=install_command,
                timeout=120000,
            )

            if install_result.exit_code != 0:
                return CommandResult(
                    output=f"Failed to install uv: {install_result.output}",
                    exit_code=install_result.exit_code,
                )

        # Execute the uv command with PATH set
        full_command = f'export PATH="$HOME/.local/bin:$PATH" && uv {uv_command}'
        return self.execute_command(command=full_command, timeout=timeout)

    # === Working Directory ===

    @abstractmethod
    def get_working_directory(self) -> str:
        """
        Get the current working directory.

        Returns:
            Absolute path to current working directory
        """
        pass
    
    def convert_to_path(self, path: str | Path) -> Path:
        """
        Convert a string path to a Path object.
        """
        path = Path(path)
        working_dir = self.get_working_directory()
        if path.is_relative_to(working_dir):
            return path
        else:
            return working_dir / path

    # === File Operations ===

    @abstractmethod
    def read_file(self, file_path: str | Path) -> str:
        """Read a file from the filesystem."""
        pass

    @abstractmethod
    def write_file(self, file_path: str | Path, content: str) -> None:
        """Write content to a file, creating it if it doesn't exist."""
        pass

    @abstractmethod
    def delete_file(self, path: str | Path) -> None:
        """Delete a file."""
        pass

    @abstractmethod
    def delete_directory(self, path: str | Path) -> None:
        """Delete a directory recursively."""
        pass

    @abstractmethod
    def create_directory(self, path: str | Path, parents: bool = False) -> None:
        """Create a directory."""
        pass

    @abstractmethod
    def copy_file(self, src: str | Path, dst: str | Path) -> None:
        """Copy a file from src to dst."""
        pass

    @abstractmethod
    def move_file(self, src: str | Path, dst: str | Path) -> None:
        """Move/rename a file from src to dst."""
        pass

    @abstractmethod
    def list_directory(self, path: str | Path, recursive: bool = False) -> list[FileInfo]:
        """List contents of a directory."""
        pass

    @abstractmethod
    def file_exists(self, path: str | Path) -> FileType | None:
        """Check if a file or directory exists and return its type."""
        pass

    @abstractmethod
    def glob_files(self, pattern: str, path: str | Path | None = None) -> list[str]:
        """Find files matching a glob pattern."""
        pass
