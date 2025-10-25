"""
list_directory tool - Framework-agnostic directory listing tool.

Implements the Gemini CLI ReadFolder tool specification.
"""
from pathlib import Path
import fnmatch

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend, FileType
from prompttodraft.tools.outputs.models import (
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class ListDirectoryToolCore:
    """
    list_directory tool for listing directory contents.

    Implements the Gemini CLI ReadFolder specification.
    """

    metadata = ToolMetadata(
        name="list_directory",
        description="""list_directory lists the names of files and subdirectories directly within a
specified directory path. It can optionally ignore entries matching provided
glob patterns.

- **Tool name:** `list_directory`
- **Display name:** ReadFolder
- **Parameters:**
  - `path` (string, required): The absolute path to the directory to list.
  - `ignore` (array of strings, optional): A list of glob patterns to exclude
    from the listing (e.g., `["*.log", ".git"]`).
  - `respect_git_ignore` (boolean, optional): Whether to respect `.gitignore`
    patterns when listing files. Defaults to `true`.
- **Behavior:**
  - Returns a list of file and directory names.
  - Indicates whether each entry is a directory.
  - Sorts entries with directories first, then alphabetically.
- **Output (`llmContent`):** A string like:
  `Directory listing for /path/to/your/folder:\\n[DIR] subfolder1\\nfile1.txt\\nfile2.png`
- **Confirmation:** No.""",
        inputs={
            "path": {
                "type": "string",
                "description": "The absolute path to the directory to list."
            },
            "ignore": {
                "type": "array",
                "description": "A list of glob patterns to exclude from the listing (e.g., [\"*.log\", \".git\"])",
                "items": {"type": "string"},
                "nullable": True
            },
            "respect_git_ignore": {
                "type": "boolean",
                "description": "Whether to respect .gitignore patterns when listing files. Defaults to true.",
                "nullable": True
            }
        },
        output_type="string"
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize ListDirectoryToolCore with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    def execute(
        self,
        path: str,
        ignore: list[str] | None = None,
        respect_git_ignore: bool = True
    ) -> ToolOutputModel:
        """
        List files and directories in the given path.

        Args:
            path: The absolute path to the directory to list
            ignore: Optional list of glob patterns to ignore
            respect_git_ignore: Whether to respect .gitignore patterns

        Returns:
            A TextOutputModel or ErrorOutputModel
        """
        # Ensure path is absolute
        if not Path(path).is_absolute():
            path = str(Path(self.backend.get_working_directory()) / path)

        # Check if path exists and is a directory
        file_type = self.backend.file_exists(path=path)
        if file_type is None:
            return ErrorOutputModel(
                error=f"Path '{path}' does not exist",
                error_type="FileNotFoundError"
            )
        if file_type != FileType.DIRECTORY:
            return ErrorOutputModel(
                error=f"Path '{path}' is not a directory",
                error_type="ValueError"
            )

        # Get directory listing from backend
        try:
            file_infos = self.backend.list_directory(path=path, recursive=False)
        except Exception as e:
            return ErrorOutputModel(
                error=f"Error listing directory: {str(e)}",
                error_type="IOError"
            )

        # Get git-ignored files if respect_git_ignore is True
        git_ignored = set()
        if respect_git_ignore:
            git_ignored = self._get_git_ignored_files(path=path)

        # Filter and sort entries
        filtered_entries = []
        for file_info in file_infos:
            # Check if should be ignored
            if self._should_ignore(
                file_info=file_info,
                ignore_patterns=ignore or [],
                git_ignored=git_ignored
            ):
                continue

            filtered_entries.append(file_info)

        # Sort: directories first, then alphabetically by name
        sorted_entries = sorted(
            filtered_entries,
            key=lambda x: (x.type != FileType.DIRECTORY, x.name.lower())
        )

        # Format output
        output_lines = [f"Directory listing for {path}:"]
        for entry in sorted_entries:
            if entry.type == FileType.DIRECTORY:
                output_lines.append(f"[DIR] {entry.name}")
            else:
                output_lines.append(entry.name)

        return TextOutputModel(content="\n".join(output_lines))

    def _get_git_ignored_files(self, path: str) -> set[str]:
        """
        Get set of filenames that are ignored by git.

        Args:
            path: Directory path to check

        Returns:
            Set of filenames that are git-ignored
        """
        try:
            # Check if we're in a git repository
            result = self.backend.execute_command(
                command=f"cd '{path}' && git rev-parse --git-dir",
                timeout=5000
            )
            if result.exit_code != 0:
                return set()  # Not a git repo

            # Get list of all files
            file_infos = self.backend.list_directory(path=path, recursive=False)
            filenames = [info.name for info in file_infos]

            # Check each file against git check-ignore
            git_ignored = set()
            for filename in filenames:
                result = self.backend.execute_command(
                    command=f"cd '{path}' && git check-ignore '{filename}'",
                    timeout=5000
                )
                # Exit code 0 means the file is ignored
                if result.exit_code == 0:
                    git_ignored.add(filename)

            return git_ignored
        except Exception:
            return set()  # If anything fails, return empty set

    def _should_ignore(
        self,
        file_info,
        ignore_patterns: list[str],
        git_ignored: set[str]
    ) -> bool:
        """
        Check if a file should be ignored.

        Args:
            file_info: FileInfo object
            ignore_patterns: List of glob patterns to ignore
            git_ignored: Set of git-ignored filenames

        Returns:
            True if the file should be ignored
        """
        filename = file_info.name

        # Check git ignore
        if filename in git_ignored:
            return True

        # Check ignore patterns
        for pattern in ignore_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True

        return False
