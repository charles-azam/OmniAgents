"""
LSToolCore - Framework-agnostic directory listing tool.

Extracted from smolcc/tools/ls_tool.py with business logic separated from execution.
"""
import os
import fnmatch

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend
from prompttodraft.tools.outputs.models import (
    FileInfo,
    FileListOutputModel,
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class LSToolCore:
    """
    Framework-agnostic directory listing tool.

    Extracted from smolcc/tools/ls_tool.py:21-149
    """

    # Metadata (from ls_tool.py:26-31)
    metadata = ToolMetadata(
        name="LS",
        description="Displays a directory's contents—files and sub-directories—at the location specified by **path**. The **path** argument must be an absolute path (it cannot be relative). You may optionally supply an **ignore** parameter: an array of glob patterns that should be skipped. If you already know the directories you want to scan, the Glob and Grep tools are generally the better choice.",
        inputs={
            "path": {
                "type": "string",
                "description": "The absolute path to the directory to list (must be absolute, not relative)"
            },
            "ignore": {
                "type": "array",
                "description": "List of glob patterns to ignore",
                "items": {"type": "string"},
                "nullable": True
            }
        },
        output_type="string"
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize LSToolCore with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    def execute(
        self,
        path: str,
        ignore: list[str] | None = None
    ) -> ToolOutputModel:
        """
        List files and directories in the given path (from ls_tool.py:34-59).

        Args:
            path: The absolute path to the directory to list
            ignore: Optional list of glob patterns to ignore

        Returns:
            A FileListOutputModel or ErrorOutputModel
        """
        # Ensure path is absolute
        if not os.path.isabs(path):
            path = os.path.abspath(path)

        # Check if path exists and is a directory
        if not self.backend.file_exists(path=path):
            return ErrorOutputModel(error=f"Path '{path}' does not exist", error_type="FileNotFoundError")
        if not self.backend.is_directory(path=path):
            return ErrorOutputModel(error=f"Path '{path}' is not a directory", error_type="ValueError")

        # Get file information for the directory via backend
        file_info_raw = self.backend.list_directory(path=path)

        # Filter files based on ignore patterns
        file_info_filtered = []
        for info in file_info_raw:
            if not self._should_skip(path=info["path"], ignore_patterns=ignore or []):
                # Convert to FileInfo objects
                file_info_filtered.append(
                    FileInfo(
                        name=info["name"],
                        path=info["path"],
                        is_dir=info["is_dir"],
                        size=info["size"],
                        modified=info["modified"],
                        modified_date=info["modified_date"]
                    )
                )

        # Return as FileListOutputModel
        return FileListOutputModel(
            files=file_info_filtered,
            path=path,
            total_count=len(file_info_filtered),
            truncated=False
        )

    def _should_skip(self, path: str, ignore_patterns: list[str]) -> bool:
        """
        Determines if a path should be skipped (from ls_tool.py:119-144).

        Args:
            path: Path to check
            ignore_patterns: List of glob patterns to ignore

        Returns:
            True if the path should be skipped, False otherwise
        """
        basename = os.path.basename(path.rstrip(os.path.sep))

        # Skip hidden files and directories
        if basename.startswith('.') and basename != '.':
            return True

        # Skip __pycache__ directories
        if basename == '__pycache__' or '__pycache__/' in path.replace(os.path.sep, '/'):
            return True

        # Skip paths matching ignore patterns
        if any(fnmatch.fnmatch(path, pattern) for pattern in ignore_patterns):
            return True

        return False
