"""
List directory tool implementation.

This tool lists the names of files and subdirectories within a specified directory path.
"""
from fnmatch import fnmatch
from pydantic import BaseModel, Field

from prompttodraft.tools.base_tool import CoreTool
from prompttodraft.backends.execution_backend import FileType


class ListDirectoryTool(CoreTool):
    """
    Framework-agnostic directory listing tool.

    Lists the names of files and subdirectories directly within a specified directory path.
    Can optionally ignore entries matching provided glob patterns.
    """

    name = "list_directory"
    description = "Lists the names of files and subdirectories directly within a specified directory path. Can optionally ignore entries matching provided glob patterns. Returns entries sorted with directories first, then alphabetically."

    class InputModel(BaseModel):
        path: str = Field(description="The absolute path to the directory to list (must be absolute, not relative).")
        ignore: list[str] | None = Field(default=None, description="Optional: List of glob patterns to ignore (e.g., ['*.log', '.git']).")
        respect_git_ignore: bool = Field(default=True, description="Optional: Whether to respect .gitignore patterns when listing files. Only available in git repositories. Defaults to true.")

    class FileInfo(BaseModel):
        name: str = Field(description="Name of the file or directory")
        path: str = Field(description="Absolute path to the file or directory")
        is_dir: bool = Field(description="Whether this is a directory")
        size: str = Field(description="Size of the file (empty for directories)")

    class OutputModel(BaseModel):
        success: bool = Field(description="Whether the directory listing was successful")
        message: str = Field(description="Human-readable summary message")
        path: str = Field(description="The directory path that was listed")
        files: list[FileInfo] = Field(default_factory=list, description="List of files and directories found")
        total_count: int = Field(description="Total number of entries found")
        error: str | None = Field(default=None, description="Error message if operation failed")

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

    def execute(self, inputs: InputModel) -> OutputModel:
        """
        Execute the list_directory tool.

        Args:
            inputs: Validated input model with path, ignore, and respect_git_ignore

        Returns:
            OutputModel with directory contents or error details
        """
        # Check if directory exists
        file_type = self.backend.file_exists(path=inputs.path)
        if file_type is None:
            return self.OutputModel(
                success=False,
                message=f"Directory does not exist: {inputs.path}",
                path=inputs.path,
                files=[],
                total_count=0,
                error=f"Directory does not exist: {inputs.path}",
            )

        if file_type != FileType.DIRECTORY:
            return self.OutputModel(
                success=False,
                message=f"Path is not a directory: {inputs.path}",
                path=inputs.path,
                files=[],
                total_count=0,
                error=f"Path is not a directory: {inputs.path}",
            )

        # Check if we should respect gitignore
        use_gitignore = inputs.respect_git_ignore and self._is_git_repository()

        # List directory contents
        entries = self.backend.list_directory(path=inputs.path, recursive=False)

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

        # Convert to FileInfo output format
        file_infos = []
        for entry in entries:
            file_infos.append(
                self.FileInfo(
                    name=entry.name,
                    path=entry.path,
                    is_dir=entry.type == FileType.DIRECTORY,
                    size="",
                )
            )

        # Sort entries: directories first, then alphabetically
        file_infos.sort(key=lambda x: (not x.is_dir, x.name))

        return self.OutputModel(
            success=True,
            message=f"Successfully listed {len(file_infos)} entries in directory: {inputs.path}",
            path=inputs.path,
            files=file_infos,
            total_count=len(file_infos),
        )
