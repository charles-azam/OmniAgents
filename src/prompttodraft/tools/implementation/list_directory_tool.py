"""
List directory tool implementation.

This tool lists the names of files and subdirectories within a specified directory path.
"""
from pathlib import Path
from fnmatch import fnmatch

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend, FileType
from prompttodraft.tools.outputs.models import (
    FileInfo,
    FileListOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class ListDirectoryTool:
    """
    Framework-agnostic directory listing tool.

    Lists the names of files and subdirectories directly within a specified directory path.
    Can optionally ignore entries matching provided glob patterns.
    """

    metadata = ToolMetadata(
        name="list_directory",
        description="Lists the names of files and subdirectories directly within a specified directory path. Can optionally ignore entries matching provided glob patterns and respect .gitignore patterns.",
        inputs={
            "path": {
                "type": "string",
                "description": "The absolute path to the directory to list",
                "nullable": False,
            },
            "ignore": {
                "type": "array",
                "description": "A list of glob patterns to exclude from the listing (e.g., ['*.log', '.git'])",
                "items": {"type": "string"},
                "nullable": True,
            },
            "respect_git_ignore": {
                "type": "boolean",
                "description": "Whether to respect .gitignore patterns when listing files. Defaults to true",
                "nullable": True,
            },
        },
        output_type="string",
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize ListDirectoryTool with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

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

        # List directory contents
        entries = self.backend.list_directory(path=path, recursive=False)

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
