"""
List directory tool implementation.

This tool lists the names of files and subdirectories within a specified directory path.
"""
from fnmatch import fnmatch
from pydantic import BaseModel, Field

from anyagent.tools.base_tool import CoreBackendTool
from anyagent.backends.execution_backend import FileType
from anyagent.outputs.outputs import (
    FileInfo,
    FileListOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)
from pathlib import Path

class ListDirectoryInput(BaseModel):
    """Input model for ListDirectoryTool."""
    path: str = Field(description="The path to the directory to list, relative to the working directory (e.g., '.' for root, 'src' for src directory)")
    ignore: list[str] | None = Field(default=None, description="Optional: List of glob patterns to ignore (e.g., ['*.log', '.git']).")
    respect_git_ignore: bool = Field(default=True, description="Optional: Whether to respect .gitignore patterns when listing files. Only available in git repositories. Defaults to true.")


class ListDirectoryTool(CoreBackendTool[ListDirectoryInput, ToolOutputModel]):
    """
    Framework-agnostic directory listing tool.

    Lists the names of files and subdirectories directly within a specified directory path.
    Can optionally ignore entries matching provided glob patterns.
    """

    name = "list_directory"
    description = "Lists the names of files and subdirectories directly within a specified directory path. Can optionally ignore entries matching provided glob patterns. Returns entries sorted with directories first, then alphabetically."

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

    def _should_ignore_by_git(self, entry_path: Path) -> bool:
        """
        Check if a file should be ignored according to .gitignore.

        Args:
            entry_path: Path object to the entry to check

        Returns:
            True if the entry should be ignored, False otherwise
        """
        try:
            # git check-ignore returns exit code 0 if the path is ignored
            # Use -q flag for quiet mode (no output, just exit code)
            result = self.backend.execute_command(
                command=f"git check-ignore -q '{str(entry_path)}'",
                timeout=2000  # 2 seconds
            )
            return result.exit_code == 0
        except Exception:
            return False

    def execute(self, inputs: ListDirectoryInput) -> ToolOutputModel:
        """
        Execute the list_directory tool.

        Args:
            inputs: Validated input model with path, ignore, and respect_git_ignore

        Returns:
            FileListOutputModel with directory contents or ErrorOutputModel on failure
        """
        # Convert str path to Path object
        path_obj = self.backend.convert_to_path(path=inputs.path)

        # Check if directory exists
        file_type = self.backend.file_exists(path=path_obj)
        if file_type is None:
            return ErrorOutputModel(
                error=f"Directory does not exist: {inputs.path}",
                error_type="DirectoryNotFoundError",
            )

        if file_type != FileType.DIRECTORY:
            return ErrorOutputModel(
                error=f"Path is not a directory: {inputs.path}",
                error_type="NotADirectoryError",
            )

        # Check if we should respect gitignore
        use_gitignore = inputs.respect_git_ignore and self._is_git_repository()

        # List directory contents
        entries = self.backend.list_directory(path=path_obj, recursive=False)

        # Apply gitignore filtering if enabled
        if use_gitignore:
            filtered_entries = []
            for entry in entries:
                if not self._should_ignore_by_git(entry.path):
                    filtered_entries.append(entry)
            entries = filtered_entries

        # Apply ignore patterns if provided
        if inputs.ignore:
            filtered_entries = []
            for entry in entries:
                should_ignore = False
                for pattern in inputs.ignore:
                    if fnmatch(entry.name, pattern):
                        should_ignore = True
                        break
                if not should_ignore:
                    filtered_entries.append(entry)
            entries = filtered_entries

        # Convert to FileInfo output format (from outputs module)
        from anyagent.outputs.outputs import FileInfo as OutputFileInfo

        file_infos = []
        for entry in entries:
            file_infos.append(
                OutputFileInfo(
                    name=entry.name,
                    path=str(entry.path),  # Convert Path to str for output
                    is_dir=entry.type == FileType.DIRECTORY,
                    size="",
                )
            )

        # Sort entries: directories first, then alphabetically
        file_infos.sort(key=lambda x: (not x.is_dir, x.name))

        return FileListOutputModel(
            files=file_infos,
            path=inputs.path,
            total_count=len(file_infos),
        )
