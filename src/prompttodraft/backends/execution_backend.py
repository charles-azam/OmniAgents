"""
Abstract execution backend interface.

This module defines the interface for execution backends (local, docker, e2b).
All backends must implement these primitive operations.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from prompttodraft.backends.state_manager import StateManager

if TYPE_CHECKING:
    from prompttodraft.initializers.base import ProjectInitializer


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

    @property
    def is_dir(self) -> bool:
        """Check if this is a directory."""
        return self.type == FileType.DIRECTORY


@dataclass
class CommandResult:
    """Result of command execution."""
    output: str
    exit_code: int


class ExecutionBackend(ABC):
    """Abstract base class for execution backends."""

    def __init__(
        self,
        state_manager: StateManager,
        initializer: ProjectInitializer
    ) -> None:
        """
        Create a backend instance with a state manager and initializer.

        Args:
            state_manager: StateManager instance for state persistence
                - GitStateManager(): Use GitHub branches
                - GCSStateManager(): Use Google Cloud Storage buckets
                - NoOpStateManager(): No state persistence
            initializer: ProjectInitializer instance for project setup
                - PythonInitializer(): Initialize Python projects with uv
                - TypeScriptInitializer(): Initialize TypeScript projects with npm
                - NoOpInitializer(): Skip initialization
        """
        self.state_manager = state_manager
        self.initializer = initializer

    @property
    @abstractmethod
    def project_id(self) -> str:
        """Get the project ID for this backend instance."""
        pass

    def _run_initialization(self) -> None:
        """
        Run project initialization if not already initialized.

        This method should be called by backend implementations at the end of their start() method.
        """
        if not self.initializer.is_initialized():
            self.initializer.initialize()

    @abstractmethod
    def start(self) -> None:
        """
        Start or restart the backend environment.

        This creates or reconnects to an execution environment:
        - Creates project directory/container/sandbox if needed
        - Loads files from bucket if available
        - Sets status to RUNNING
        - Runs initialization if not already initialized

        Can be called after initialization or after shutdown to restart.

        Implementations should call self._run_initialization() at the end.
        """
        pass
    
    def cleanup(self) -> None:
        """
        Cleanup the backend environment.
        """
        self.state_manager.cleanup(project_id=self.project_id)

    def clean(self) -> None:
        """
        Remove all files from working directory and save a clean snapshot.

        This creates a clean state while preserving the project's storage location:
        - For Git: Removes all files and creates a commit called "clean"
        - For GCS: Removes all files and saves a snapshot

        Unlike cleanup(), this does not destroy the branch or bucket prefix.

        After removing all files, creates an empty README.md to ensure the snapshot
        is trackable (especially important for GCS storage which discovers snapshots
        by looking at blob paths).
        """
        # Get working directory
        working_dir = Path(self.get_working_directory())

        # List all files and directories (non-recursive at root level)
        items = self.list_directory(path=working_dir, recursive=False)

        # Delete all items except .git directory (needed for Git storage)
        for item in items:
            if item.name == '.git':
                continue

            if item.is_dir:
                self.delete_directory(path=item.path)
            else:
                self.delete_file(path=item.path)

        # Create empty README.md to ensure snapshot is trackable
        # This is especially important for GCS storage which discovers snapshots
        # by looking at blob paths - without at least one file, the snapshot
        # timestamp won't be discoverable
        self.write_file(file_path=working_dir / "README.md", content="")

        # Save the clean state
        self.state_manager.save_snapshot(backend=self, message="clean")


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
