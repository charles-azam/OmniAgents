"""
GlobToolCore - Framework-agnostic file pattern matching tool.

Extracted from smolcc/tools/glob_tool.py with business logic separated from execution.
"""
import os
import time
from datetime import datetime

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend
from prompttodraft.tools.outputs.models import (
    FileInfo,
    FileListOutputModel,
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class GlobToolCore:
    """
    Framework-agnostic file pattern matching tool.

    Extracted from smolcc/tools/glob_tool.py:19-208
    """

    # Metadata (from glob_tool.py:25-36)
    metadata = ToolMetadata(
        name="GlobTool",
        description="""- Lightning-quick file-pattern matcher that scales to projects of any size
- Understands glob expressions such as "**/*.js" and "src/**/*.ts"
- Returns matching file paths in descending order of last-modified time
- Reach for this tool whenever you need to locate files by name patterns
- For exploratory searches that may involve several rounds of globbing and grepping, use the Agent tool instead""",
        inputs={
            "pattern": {
                "type": "string",
                "description": "The glob pattern to match files against"
            },
            "path": {
                "type": "string",
                "description": "The directory to search in. Defaults to the current working directory.",
                "nullable": True
            }
        },
        output_type="string"
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize GlobToolCore with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    def execute(
        self,
        pattern: str,
        path: str | None = None
    ) -> ToolOutputModel:
        """
        Find files matching the given glob pattern (from glob_tool.py:39-87).

        Args:
            pattern: The glob pattern to match files against (e.g. "**/*.py")
            path: The directory to search in (defaults to current working directory)

        Returns:
            A FileListOutputModel or ErrorOutputModel
        """
        start_time = time.time()
        search_path = path or os.getcwd()

        # Make sure search_path is absolute
        search_path = os.path.abspath(search_path) if not os.path.isabs(search_path) else search_path

        # Verify path exists
        if not self.backend.file_exists(path=search_path):
            return ErrorOutputModel(error=f"Path '{search_path}' does not exist", error_type="FileNotFoundError")
        if not self.backend.is_directory(path=search_path):
            return ErrorOutputModel(error=f"Path '{search_path}' is not a directory", error_type="ValueError")

        # Find matching files via backend
        matching_files = self.backend.glob_files(pattern=pattern, path=search_path)

        # Limit results
        truncated = len(matching_files) > 100
        matching_files = matching_files[:100]

        # If no files found, return a simple message
        if not matching_files:
            return TextOutputModel(content=f"No files found matching pattern '{pattern}' in '{search_path}'")

        # Convert to rich file info format
        file_info_list = self._convert_to_file_info(matching_files=matching_files)

        # Calculate duration in milliseconds
        duration_ms = int((time.time() - start_time) * 1000)

        # Add a note about truncation if needed
        if truncated:
            truncation_note = "(Results limited to 100 files. Consider using a more specific pattern.)"
            file_info_list.append(
                FileInfo(
                    name=truncation_note,
                    path="",
                    is_dir=False,
                    size="",
                    modified=None,
                    modified_date=None
                )
            )

        # Return as FileListOutputModel
        return FileListOutputModel(
            files=file_info_list,
            path=f"{search_path} (pattern: {pattern}, {duration_ms}ms)",
            total_count=len(file_info_list),
            truncated=truncated
        )

    def _convert_to_file_info(self, matching_files: list[str]) -> list[FileInfo]:
        """
        Convert file paths to rich file info objects (from glob_tool.py:158-203).

        Args:
            matching_files: List of file paths

        Returns:
            List of FileInfo objects
        """
        file_info_list = []

        for file_path in matching_files:
            try:
                # Get file stats
                stats = self.backend.get_file_stats(path=file_path)

                # Format size
                size = stats["size"]
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"

                # Format modification time
                modified_date = datetime.fromtimestamp(stats["modified"]).strftime("%Y-%m-%d %H:%M:%S")

                # Create file info
                file_info = FileInfo(
                    name=os.path.basename(file_path),
                    is_dir=False,  # We only match files, not directories
                    size=size,
                    modified=stats["modified"],
                    modified_date=modified_date,
                    path=file_path
                )

                file_info_list.append(file_info)
            except (PermissionError, FileNotFoundError):
                # Skip files we can't access
                continue

        return file_info_list
