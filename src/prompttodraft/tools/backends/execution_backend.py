"""
Abstract execution backend interface.

This module defines the interface for execution backends (local, docker, e2b).
All backends must implement these primitive operations.
"""
from abc import ABC, abstractmethod


class ExecutionBackend(ABC):
    """Abstract base class for execution backends."""

    @abstractmethod
    def execute_command(
        self,
        command: str,
        timeout: int | None = None
    ) -> tuple[str, bool]:
        """
        Execute a bash command.

        Args:
            command: The bash command to execute
            timeout: Optional timeout in milliseconds

        Returns:
            Tuple of (command output, is_error)
        """
        pass

    @abstractmethod
    def read_file(
        self,
        file_path: str,
        offset: int = 0,
        limit: int | None = None
    ) -> str:
        """
        Read a file from the filesystem.

        Args:
            file_path: Absolute path to the file
            offset: Line number to start reading from (0-indexed)
            limit: Maximum number of lines to read

        Returns:
            File contents with line numbers
        """
        pass

    @abstractmethod
    def write_file(
        self,
        file_path: str,
        content: str
    ) -> None:
        """
        Write content to a file.

        Args:
            file_path: Absolute path to the file
            content: Content to write

        Raises:
            IOError: If file cannot be written
        """
        pass

    @abstractmethod
    def list_directory(
        self,
        path: str
    ) -> list[dict[str, str | int | bool]]:
        """
        List contents of a directory.

        Args:
            path: Absolute path to the directory

        Returns:
            List of file info dictionaries with keys:
            - name: str
            - path: str
            - is_dir: bool
            - size: int
            - modified: int (Unix timestamp)
            - modified_date: str (formatted date)
        """
        pass

    @abstractmethod
    def file_exists(
        self,
        path: str
    ) -> bool:
        """
        Check if a file or directory exists.

        Args:
            path: Absolute path to check

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    def is_file(
        self,
        path: str
    ) -> bool:
        """
        Check if a path is a file (not a directory).

        Args:
            path: Absolute path to check

        Returns:
            True if path is a file, False otherwise
        """
        pass

    @abstractmethod
    def is_directory(
        self,
        path: str
    ) -> bool:
        """
        Check if a path is a directory.

        Args:
            path: Absolute path to check

        Returns:
            True if path is a directory, False otherwise
        """
        pass

    @abstractmethod
    def glob_files(
        self,
        pattern: str,
        path: str | None = None
    ) -> list[str]:
        """
        Find files matching a glob pattern.

        Args:
            pattern: Glob pattern (e.g., "**/*.py")
            path: Base directory to search (defaults to current working directory)

        Returns:
            List of matching file paths
        """
        pass

    @abstractmethod
    def search_files(
        self,
        pattern: str,
        include: str | None = None,
        path: str | None = None
    ) -> list[dict[str, str | int | list]]:
        """
        Search file contents using regex.

        Args:
            pattern: Regular expression pattern
            include: File pattern to include (e.g., "*.py")
            path: Base directory to search

        Returns:
            List of match info dictionaries with keys:
            - path: str
            - language: str
            - matches: list[dict] (with line_number, context, match_text, etc.)
            - modified: int
        """
        pass

    @abstractmethod
    def get_file_stats(
        self,
        path: str
    ) -> dict[str, str | int]:
        """
        Get file statistics.

        Args:
            path: Absolute path to the file

        Returns:
            Dictionary with file stats (size, modified time, etc.)
        """
        pass
