"""
Glob tool implementation.

This tool finds files matching specific glob patterns.
"""
from pathlib import Path

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend
from prompttodraft.tools.outputs.models import (
    FileInfo,
    FileListOutputModel,
    ToolOutputModel,
)


class GlobTool:
    """
    Framework-agnostic glob file finding tool.

    Finds files matching specific glob patterns (e.g., src/**/*.ts, *.md),
    returning absolute paths sorted by modification time (newest first).
    """

    metadata = ToolMetadata(
        name="glob",
        description="Efficiently finds files matching specific glob patterns (e.g., '**/*.py', 'docs/*.md'), returning absolute paths sorted by modification time (newest first). Ideal for quickly locating files based on their name or path structure, especially in large codebases.",
        inputs={
            "pattern": {
                "type": "string",
                "description": "The glob pattern to match against (e.g., '**/*.py', 'docs/*.md').",
                "nullable": False,
            },
            "path": {
                "type": "string",
                "description": "Optional: The absolute path to the directory to search within. If omitted, searches the root directory.",
                "nullable": True,
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Optional: Whether the search should be case-sensitive. Defaults to false.",
                "nullable": True,
            },
            "respect_git_ignore": {
                "type": "boolean",
                "description": "Optional: Whether to respect .gitignore patterns when finding files. Only available in git repositories. Defaults to true.",
                "nullable": True,
            },
        },
        output_type="string",
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize GlobTool with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    def execute(
        self,
        pattern: str,
        path: str | None = None,
        case_sensitive: bool = False,
        respect_git_ignore: bool = True,
    ) -> ToolOutputModel:
        """
        Execute the glob tool.

        Args:
            pattern: The glob pattern to match against
            path: Optional directory to search within
            case_sensitive: Whether the search should be case-sensitive (not currently implemented)
            respect_git_ignore: Whether to respect .gitignore patterns (not currently implemented)

        Returns:
            FileListOutputModel with matching files

        Note:
            case_sensitive and respect_git_ignore parameters are accepted for API compatibility
            but not currently implemented in this backend-based approach.
        """
        # Get matched file paths
        matched_paths = self.backend.glob_files(pattern=pattern, path=path)

        # Get file modification times
        file_infos = []
        for file_path in matched_paths:
            # Get file modification time using stat command
            result = self.backend.execute_command(
                command=f'stat -f "%m" "{file_path}" 2>/dev/null || stat -c "%Y" "{file_path}" 2>/dev/null',
                timeout=5000,
            )

            mtime = 0
            if result.exit_code == 0 and result.output:
                mtime = int(result.output.strip())

            file_infos.append(
                FileInfo(
                    name=Path(file_path).name,
                    path=file_path,
                    is_dir=False,
                    size="",
                    modified=mtime,
                )
            )

        # Sort by modification time (newest first)
        file_infos.sort(key=lambda x: x.modified or 0, reverse=True)

        search_path = path if path else self.backend.get_working_directory()

        return FileListOutputModel(
            files=file_infos,
            path=search_path,
            total_count=len(file_infos),
        )
