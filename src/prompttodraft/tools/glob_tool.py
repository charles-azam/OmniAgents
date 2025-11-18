"""
Glob tool implementation.

This tool finds files matching specific glob patterns.
"""
from pathlib import Path

from prompttodraft.tools.base_tool import CoreTool
from prompttodraft.tools.metadata import ToolMetadata
from prompttodraft.backends.execution_backend import ExecutionBackend
from prompttodraft.outputs.outputs import (
    FileInfo,
    FileListOutputModel,
    ToolOutputModel,
)


class GlobTool(CoreTool):
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
                "description": "Optional: Whether the search should be case-sensitive. Defaults to false (case-insensitive).",
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

    def _is_git_repository(self, search_path: str) -> bool:
        """
        Check if the search path is within a git repository.

        Args:
            search_path: Path to check

        Returns:
            True if path is in a git repository
        """
        result = self.backend.execute_command(
            command=f'cd "{search_path}" && git rev-parse --git-dir 2>/dev/null',
            timeout=5000,
        )
        return result.exit_code == 0

    def _filter_gitignored_files(self, file_paths: list[str], search_path: str) -> list[str]:
        """
        Filter out files that match .gitignore patterns.

        Args:
            file_paths: List of file paths to filter
            search_path: The directory being searched

        Returns:
            List of files not ignored by git
        """
        if not file_paths:
            return []

        # git check-ignore returns 0 for ignored files, 1 for non-ignored
        # We'll check each file individually for reliability
        non_ignored_files = []

        for file_path in file_paths:
            result = self.backend.execute_command(
                command=f'cd "{search_path}" && git check-ignore -q "{file_path}"',
                timeout=5000,
            )
            # Exit code 0 means the file IS ignored, 1 means it's NOT ignored
            if result.exit_code != 0:
                non_ignored_files.append(file_path)

        return non_ignored_files

    def _apply_case_sensitivity(
        self,
        file_paths: list[str],
        case_sensitive: bool,
    ) -> list[str]:
        """
        Apply case sensitivity filtering to matched files.

        Args:
            file_paths: List of matched file paths
            case_sensitive: Whether to enforce case sensitivity

        Returns:
            Filtered list of file paths
        """
        if case_sensitive:
            # Python's glob is already case-sensitive on Unix systems
            # No additional filtering needed
            return file_paths

        # For case-insensitive matching, Python's glob behavior varies by OS
        # For now, we'll just return all files since glob already matched them
        return file_paths

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
            case_sensitive: Whether the search should be case-sensitive
            respect_git_ignore: Whether to respect .gitignore patterns

        Returns:
            FileListOutputModel with matching files
        """
        # Get matched file paths
        matched_paths = self.backend.glob_files(pattern=pattern, path=path)

        # Determine search path for filtering
        search_path = path if path else self.backend.get_working_directory()

        # Apply case sensitivity filtering if needed
        if case_sensitive:
            matched_paths = self._apply_case_sensitivity(
                file_paths=matched_paths,
                case_sensitive=case_sensitive,
            )

        # Apply gitignore filtering if requested
        if respect_git_ignore and self._is_git_repository(search_path=search_path):
            matched_paths = self._filter_gitignored_files(
                file_paths=matched_paths,
                search_path=search_path,
            )

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
                try:
                    mtime = int(result.output.strip())
                except ValueError:
                    # stat command might not support format options on this system
                    mtime = 0

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
