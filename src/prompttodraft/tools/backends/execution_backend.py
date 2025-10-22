"""
Abstract execution backend interface.

This module defines the interface for execution backends (local, docker, e2b).
All backends must implement these primitive operations.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class BackendStatus(Enum):
    """Status of the execution backend."""
    UNINITIALIZED = "uninitialized"
    RUNNING = "running"
    PAUSED = "paused"
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

    @abstractmethod
    def init(self) -> None:
        """
        Initialize the backend environment from scratch.

        This creates a new execution environment with:
        - Base project structure and files
        - UV package manager initialization
        - Bucket folder for persistence
        - Initial sync to bucket
        """
        pass

    @abstractmethod
    def resume(self) -> None:
        """Resume the backend after it has been paused."""
        pass

    @abstractmethod
    def pause(self) -> None:
        """
        Pause the backend and sync state to bucket.

        This should:
        - Stop any running processes
        - Sync all modified files to bucket
        - Keep container/environment for quick resume
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        Shutdown the backend completely and flush all state to bucket.

        This should:
        - Stop all processes
        - Sync all files to bucket
        - Destroy the execution environment (container/sandbox)
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

    @abstractmethod
    def sync_to_bucket(self) -> None:
        """
        Incrementally sync changed files to bucket.

        This should only upload files that have been modified since
        the last sync to optimize performance.
        """
        pass

    @abstractmethod
    def load_from_bucket(self, person_id: str, task_id: str) -> None:
        """
        Load previously saved state from bucket.

        This restores a paused/stopped backend from bucket storage:
        - Downloads all files from person_id/task_id/ path
        - Restores working directory state
        - Prepares environment for execution

        Args:
            person_id: Identifier for the user
            task_id: Identifier for the specific task
        """
        pass

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
