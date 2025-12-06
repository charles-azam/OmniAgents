"""
Abstract execution backend interface.

This module defines the interface for execution backends (local, docker, e2b).
All backends must implement these primitive operations.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from beartype import beartype

from omniagents.backends.state_manager import StateManager


@beartype
class BackendStatus(Enum):
    """Status of the execution backend."""
    UNINITIALIZED = "uninitialized"
    RUNNING = "running"
    STOPPED = "stopped"


@beartype
class FileType(Enum):
    """Type of filesystem entry."""
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    OTHER = "other"


@beartype
@dataclass
class FileInfo:
    """Information about a file or directory."""
    name: str
    path: Path
    type: FileType

    @property
    def is_dir(self) -> bool:
        """Check if this is a directory."""
        return self.type == FileType.DIRECTORY


@beartype
@dataclass
class CommandResult:
    """Result of command execution."""
    output: str
    exit_code: int


@beartype
class ExecutionBackend(ABC):
    """Abstract base class for execution backends."""

    def __init__(self, state_manager: StateManager) -> None:
        """
        Create a backend instance with a state manager.

        Args:
            state_manager: StateManager instance for state persistence
                - GitStateManager(): Use GitHub branches
                - GCSStateManager(): Use Google Cloud Storage buckets
                - NoOpStateManager(): No state persistence
        """
        self._state_manager = state_manager

    @property
    def state_manager(self) -> StateManager:
        """Get the state manager instance (read-only)."""
        return self._state_manager

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
    
    def save_snapshot(self, message: str = "") -> str:
        """
        Save current state using the configured state manager.

        Args:
            message: Optional message describing this snapshot

        Returns:
            snapshot_id: Identifier for this snapshot (commit SHA, timestamp, etc.)
        """
        return self._state_manager.save_snapshot(backend=self, message=message)

    def load_latest_snapshot(self) -> bool:
        """
        Load latest snapshot into working directory using the configured state manager.

        Returns:
            True if snapshot was loaded, False if no snapshots exist
        """
        return self._state_manager.load_latest(backend=self)

    def list_snapshots(self) -> list[dict[str, str | int]]:
        """
        List all available snapshots with metadata.

        Used only for testing.

        Returns:
            List of snapshot metadata dicts
        """
        return self._state_manager.list_snapshots(project_id=self.project_id)

    def cleanup_state_manager(self) -> None:
        """
        Cleanup the backend environment and state manager.

        This removes all state data from storage (GCS/Git branches/etc).
        """
        self._state_manager.cleanup(project_id=self.project_id)


    def clean(self, cleanup_state_manager: bool = False) -> None:
        """
        Remove all files from working directory and save a clean snapshot.

        This creates a clean state while preserving the project's storage location:
        - For Git: Removes all files and creates a commit called "clean"
        - For GCS: Removes all files and saves a snapshot

        Unlike cleanup(), this does not destroy the branch or bucket prefix.

        After removing all files, creates an empty README.md to ensure the snapshot
        is trackable (especially important for GCS storage which discovers snapshots
        by looking at blob paths).

        Args:
            cleanup_state_manager: Whether to cleanup the state manager as well

        Note:
            For E2BBackend, this requires the backend to be started (sandbox must be running).
            If the backend is not started, only state manager cleanup will be performed.
        """
        # For backends that require initialization (like E2B), gracefully handle uninitialized state
        backend_is_running = self.get_status() == BackendStatus.RUNNING

        if backend_is_running:
            # Get working directory
            working_dir = self.get_working_directory()

            # List all files and directories (non-recursive at root level)
            # Check if working directory exists (may not exist for fresh E2B backend)
            try:
                if self.file_exists(path=working_dir) is not None:
                    items = self.list_directory(path=working_dir, recursive=False)

                    # Delete all items except .git directory (needed for Git storage)
                    for item in items:
                        if item.name == '.git':
                            continue

                        # item.path is already a Path object
                        if item.is_dir:
                            self.delete_directory(path=item.path)
                        else:
                            self.delete_file(path=item.path)

                    # Create empty README.md to ensure snapshot is trackable
                    # This is especially important for GCS storage which discovers snapshots
                    # by looking at blob paths - without at least one file, the snapshot
                    # timestamp won't be discoverable
                    self.write_file(file_path=working_dir / "README.md", content="")
            except RuntimeError:
                # Backend not initialized (e.g., E2B sandbox not created yet)
                # Skip file operations, only do state manager cleanup if requested
                pass

        if cleanup_state_manager:
            self._state_manager.cleanup(project_id=self.project_id)

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
    def get_working_directory(self) -> Path:
        """
        Get the working directory as seen by the LLM (virtual path).

        For DockerBackend, this is /workspace.
        For LocalBackend, this is also /workspace (mapped to a temp dir on host).

        Returns:
            Path object representing the root of the workspace in the LLM's view.
        """
        pass

    # === Internal Path Translation ===

    @abstractmethod
    def _to_system_path(self, virtual_path: Path) -> Path:
        """
        Convert a virtual path (LLM view) to a system path (Host/Container/Sandbox view).

        This is an internal method to standardize path resolution across backends.

        Args:
            virtual_path: Path object in the LLM's view (e.g. /workspace/file.py)

        Returns:
            Path object representing the actual location on the execution system.
        """
        pass

    @abstractmethod
    def _to_virtual_path(self, system_path: str | Path) -> Path:
        """
        Convert a system path (Host/Container/Sandbox view) to a virtual path (LLM view).

        This is an internal method to standardize path resolution across backends.

        Args:
            system_path: Path or string on the execution system

        Returns:
            Path object in the LLM's view (e.g. /workspace/file.py)
        """
        pass

    def convert_to_path(self, path: str) -> Path:
        """
        Convert a string path to a normalized Path object in the LLM's view.

        Enforces that the path is within the working directory.

        Args:
            path: String path from LLM tool call

        Returns:
            Path object relative to working directory (LLM view)

        Raises:
            ValueError: If path attempts to escape the working directory
        """
        path_obj = Path(path)
        working_dir = self.get_working_directory()
        
        # Normalize to resolve '..'
        # Since we are dealing with virtual paths, we can use os.path.normpath
        # But we need to be careful about OS differences if the host is Windows vs Posix
        # Assuming Posix paths for LLM interaction (/workspace/...)
        import posixpath
        
        str_path = str(path_obj)
        if not path_obj.is_absolute():
            # Join with working dir first
            str_path = posixpath.join(str(working_dir), str_path)
            
        # Normalize path (resolve ..)
        normalized_path_str = posixpath.normpath(str_path)
        normalized_path = Path(normalized_path_str)
        
        # Check if it starts with working directory
        if not str(normalized_path).startswith(str(working_dir)):
             raise ValueError(f"Path '{path}' resolves to '{normalized_path}' which is outside the working directory '{working_dir}'")
        
        return normalized_path

    # === File Operations ===

    @abstractmethod
    def read_file(self, file_path: Path) -> str:
        """Read a file from the filesystem.

        Args:
            file_path: Path object to the file to read

        Returns:
            File contents as string
        """
        pass

    @abstractmethod
    def write_file(self, file_path: Path, content: str) -> None:
        """Write content to a file, creating it if it doesn't exist.

        Args:
            file_path: Path object to the file to write
            content: String content to write to the file
        """
        pass

    @abstractmethod
    def delete_file(self, path: Path) -> None:
        """Delete a file.

        Args:
            path: Path object to the file to delete
        """
        pass

    @abstractmethod
    def delete_directory(self, path: Path) -> None:
        """Delete a directory recursively.

        Args:
            path: Path object to the directory to delete
        """
        pass

    @abstractmethod
    def create_directory(self, path: Path, parents: bool = False) -> None:
        """Create a directory.

        Args:
            path: Path object to the directory to create
            parents: Whether to create parent directories
        """
        pass

    @abstractmethod
    def copy_file(self, src: Path, dst: Path) -> None:
        """Copy a file from src to dst.

        Args:
            src: Path object to source file
            dst: Path object to destination file
        """
        pass

    @abstractmethod
    def move_file(self, src: Path, dst: Path) -> None:
        """Move/rename a file from src to dst.

        Args:
            src: Path object to source file
            dst: Path object to destination file
        """
        pass

    @abstractmethod
    def list_directory(self, path: Path, recursive: bool = False) -> list[FileInfo]:
        """List contents of a directory.

        Args:
            path: Path object to the directory to list
            recursive: Whether to list recursively

        Returns:
            List of FileInfo objects
        """
        pass

    @abstractmethod
    def file_exists(self, path: Path) -> FileType | None:
        """Check if a file or directory exists and return its type.

        Args:
            path: Path object to check

        Returns:
            FileType if exists, None otherwise
        """
        pass

    @abstractmethod
    def glob_files(self, pattern: str, path: Path | None = None) -> list[str]:
        """Find files matching a glob pattern.

        Args:
            pattern: Glob pattern string (e.g., '*.py', '**/*.txt')
            path: Optional Path object to search within

        Returns:
            List of file paths as strings
        """
        pass
