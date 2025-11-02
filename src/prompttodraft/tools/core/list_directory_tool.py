"""
List directory tool implementation.

This tool lists the names of files and subdirectories within a specified directory path.
"""
from pathlib import Path
from fnmatch import fnmatch

from prompttodraft.tools.core.base_tool import CoreTool
from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend, FileType
from prompttodraft.tools.outputs.models import (
    FileInfo,
    FileListOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class ListDirectoryTool(CoreTool):
    """
    Framework-agnostic directory listing tool.

    Lists the names of files and subdirectories directly within a specified directory path.
    Can optionally ignore entries matching provided glob patterns.
    """

    metadata = ToolMetadata(
        name="list_directory",
        description="Lists the names of files and subdirectories directly within a specified directory path. Can optionally ignore entries matching provided glob patterns. Returns entries sorted with directories first, then alphabetically.",
        inputs={
            "path": {
                "type": "string",
                "description": "The absolute path to the directory to list (must be absolute, not relative).",
                "nullable": False,
            },
            "ignore": {
                "type": "array",
                "description": "Optional: List of glob patterns to ignore (e.g., ['*.log', '.git']).",
                "items": {"type": "string"},
                "nullable": True,
            },
            "respect_git_ignore": {
                "type": "boolean",
                "description": "Optional: Whether to respect .gitignore patterns when listing files. Only available in git repositories. Defaults to true.",
                "nullable": True,
            },
        },
        output_type="string",
    )

    def _is_git_repository(self) -> bool:
        """
        Check if the working directory is a git repository.

        Returns:
            True if in a git repository, False otherwise
        """
        try:
            result = self.backend.execute_command(
                command="git rev-parse --is-inside-work-tree",
                timeout=2000  # 2 seconds
            )
            return result.exit_code == 0 and result.output.strip() == "true"
        except Exception:
            return False

    def _should_ignore_by_git(self, entry_path: str) -> bool:
        """
        Check if a file should be ignored according to .gitignore.

        Args:
            entry_path: Absolute path to the entry to check

        Returns:
            True if the entry should be ignored, False otherwise
        """
        try:
            # git check-ignore returns exit code 0 if the path is ignored
            # Use -q flag for quiet mode (no output, just exit code)
            result = self.backend.execute_command(
                command=f"git check-ignore -q '{entry_path}'",
                timeout=2000  # 2 seconds
            )
            return result.exit_code == 0
        except Exception:
            return False

    def execute(
        self,
        path: str,
        ignore: list[str] | None = None,
        respect_git_ignore: bool = True,
    ) -> ToolOutputModel:
        """
        Execute the list_directory tool.

        Args:
            path: The absolute path to the directory to list
            ignore: Optional list of glob patterns to exclude
            respect_git_ignore: Whether to respect .gitignore patterns

        Returns:
            FileListOutputModel with directory contents or ErrorOutputModel on failure
        """
        # Check if directory exists
        file_type = self.backend.file_exists(path=path)
        if file_type is None:
            return ErrorOutputModel(
                error=f"Directory does not exist: {path}",
                error_type="DirectoryNotFoundError",
            )

        if file_type != FileType.DIRECTORY:
            return ErrorOutputModel(
                error=f"Path is not a directory: {path}",
                error_type="NotADirectoryError",
            )

        # Check if we should respect gitignore
        use_gitignore = respect_git_ignore and self._is_git_repository()

        # List directory contents
        entries = self.backend.list_directory(path=path, recursive=False)

        # Apply gitignore filtering if enabled
        if use_gitignore:
            filtered_entries = []
            for entry in entries:
                if not self._should_ignore_by_git(entry.path):
                    filtered_entries.append(entry)
            entries = filtered_entries

        # Apply ignore patterns if provided
        if ignore:
            filtered_entries = []
            for entry in entries:
                should_ignore = False
                for pattern in ignore:
                    if fnmatch(entry.name, pattern):
                        should_ignore = True
                        break
                if not should_ignore:
                    filtered_entries.append(entry)
            entries = filtered_entries

        # Convert to FileInfo output format
        file_infos = []
        for entry in entries:
            file_infos.append(
                FileInfo(
                    name=entry.name,
                    path=entry.path,
                    is_dir=entry.type == FileType.DIRECTORY,
                    size="",
                )
            )

        # Sort entries: directories first, then alphabetically
        file_infos.sort(key=lambda x: (not x.is_dir, x.name))

        return FileListOutputModel(
            files=file_infos,
            path=path,
            total_count=len(file_infos),
        )
