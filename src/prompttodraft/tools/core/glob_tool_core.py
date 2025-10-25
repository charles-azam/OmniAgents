"""
glob tool - Framework-agnostic file pattern matching tool.

Implements the Gemini CLI FindFiles tool specification.
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


class GlobToolCore:
    """
    glob tool for finding files by pattern.

    Implements the Gemini CLI FindFiles specification.
    """

    metadata = ToolMetadata(
        name="glob",
        description="""glob finds files matching specific glob patterns (e.g., `src/**/*.ts`,
`*.md`), returning absolute paths sorted by modification time (newest first).

- **Tool name:** `glob`
- **Display name:** FindFiles
- **Parameters:**
  - `pattern` (string, required): The glob pattern to match against (e.g.,
    `"*.py"`, `"src/**/*.js"`).
  - `path` (string, optional): The absolute path to the directory to search
    within. If omitted, searches the tool's root directory.
  - `case_sensitive` (boolean, optional): Whether the search should be
    case-sensitive. Defaults to `false`.
  - `respect_git_ignore` (boolean, optional): Whether to respect .gitignore
    patterns when finding files. Defaults to `true`.
  - `respect_gemini_ignore` (boolean, optional): Whether to respect .geminiignore
    patterns when finding files. Defaults to `true`.
- **Behavior:**
  - Searches for files matching the glob pattern within the specified directory.
  - Returns a list of absolute paths, sorted with the most recently modified
    files first.
  - Ignores common nuisance directories like `node_modules` and `.git` by
    default.
- **Output (`llmContent`):** A message like:
  `Found 5 file(s) matching "*.ts" within src, sorted by modification time (newest first):\nsrc/file1.ts\nsrc/subdir/file2.ts...`
- **Confirmation:** No.""",
        inputs={
            "pattern": {
                "type": "string",
                "description": "The glob pattern to match against (e.g., \"*.py\", \"src/**/*.js\")"
            },
            "path": {
                "type": "string",
                "description": "The absolute path to the directory to search within. If omitted, searches the tool's root directory.",
                "nullable": True
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether the search should be case-sensitive. Defaults to false.",
                "nullable": True
            },
            "respect_git_ignore": {
                "type": "boolean",
                "description": "Whether to respect .gitignore patterns when finding files. Defaults to true.",
                "nullable": True
            },
            "respect_gemini_ignore": {
                "type": "boolean",
                "description": "Whether to respect .geminiignore patterns when finding files. Defaults to true.",
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
        path: str | None = None,
        case_sensitive: bool = False,
        respect_git_ignore: bool = True,
        respect_gemini_ignore: bool = True
    ) -> ToolOutputModel:
        """
        Find files matching the given glob pattern.

        Args:
            pattern: The glob pattern to match files against
            path: The directory to search in (defaults to working directory)
            case_sensitive: Whether search should be case-sensitive
            respect_git_ignore: Whether to respect .gitignore patterns
            respect_gemini_ignore: Whether to respect .geminiignore patterns

        Returns:
            A TextOutputModel or ErrorOutputModel
        """
        # Determine search path
        if path is None:
            search_path = self.backend.get_working_directory()
        elif not Path(path).is_absolute():
            search_path = str(Path(self.backend.get_working_directory()) / path)
        else:
            search_path = path

        # Verify path exists and is directory
        file_type = self.backend.file_exists(path=search_path)
        if file_type is None:
            return ErrorOutputModel(
                error=f"Path '{search_path}' does not exist",
                error_type="FileNotFoundError"
            )
        if file_type != FileType.DIRECTORY:
            return ErrorOutputModel(
                error=f"Path '{search_path}' is not a directory",
                error_type="ValueError"
            )

        # Find matching files via backend
        try:
            matching_files = self.backend.glob_files(
                pattern=pattern,
                path=search_path
            )
        except Exception as e:
            return ErrorOutputModel(
                error=f"Error finding files: {str(e)}",
                error_type="IOError"
            )

        # Filter by case sensitivity
        if not case_sensitive:
            # For case-insensitive matching, filter using fnmatch
            pattern_lower = pattern.lower()
            filtered_files = []
            for file_path in matching_files:
                # Get relative path for matching
                rel_path = Path(file_path).relative_to(search_path)
                if fnmatch.fnmatch(str(rel_path).lower(), pattern_lower):
                    filtered_files.append(file_path)
            matching_files = filtered_files

        # Filter out common nuisance directories and files
        matching_files = [
            f for f in matching_files
            if not self._is_nuisance_path(path=f)
        ]

        # Apply gitignore filtering
        if respect_git_ignore:
            matching_files = self._filter_git_ignored(
                files=matching_files,
                search_path=search_path
            )

        # If no files found
        if not matching_files:
            return TextOutputModel(
                content=f'Found 0 file(s) matching "{pattern}" within {search_path}'
            )

        # Sort by modification time (newest first)
        sorted_files = self._sort_by_modification_time(files=matching_files)

        # Format output
        file_count = len(sorted_files)
        output_lines = [
            f'Found {file_count} file(s) matching "{pattern}" within {search_path}, sorted by modification time (newest first):'
        ]
        output_lines.extend(sorted_files)

        return TextOutputModel(content="\n".join(output_lines))

    def _is_nuisance_path(self, path: str) -> bool:
        """
        Check if a path contains common nuisance directories.

        Args:
            path: File path to check

        Returns:
            True if path contains nuisance directories
        """
        nuisance_dirs = {
            'node_modules', '.git', '__pycache__', '.venv', 'venv',
            '.pytest_cache', '.mypy_cache', '.tox', 'dist', 'build',
            '.eggs', '*.egg-info'
        }

        path_parts = Path(path).parts
        return any(part in nuisance_dirs for part in path_parts)

    def _filter_git_ignored(self, files: list[str], search_path: str) -> list[str]:
        """
        Filter out files that are git-ignored.

        Args:
            files: List of file paths to filter
            search_path: Base search directory

        Returns:
            Filtered list of files
        """
        try:
            # Check if we're in a git repository
            result = self.backend.execute_command(
                command=f"cd '{search_path}' && git rev-parse --git-dir",
                timeout=5000
            )
            if result.exit_code != 0:
                return files  # Not a git repo, return all files

            # Check each file against git check-ignore
            filtered_files = []
            for file_path in files:
                # Get relative path for git check-ignore
                try:
                    rel_path = Path(file_path).relative_to(search_path)
                except ValueError:
                    # File not under search_path, keep it
                    filtered_files.append(file_path)
                    continue

                result = self.backend.execute_command(
                    command=f"cd '{search_path}' && git check-ignore '{rel_path}'",
                    timeout=5000
                )
                # Exit code 0 means the file is ignored, so skip it
                if result.exit_code != 0:
                    filtered_files.append(file_path)

            return filtered_files

        except Exception:
            return files  # On error, return all files

    def _sort_by_modification_time(self, files: list[str]) -> list[str]:
        """
        Sort files by modification time (newest first).

        Args:
            files: List of file paths

        Returns:
            Sorted list of file paths
        """
        # Get modification times for all files
        file_times = []
        for file_path in files:
            try:
                # Use stat command to get modification time
                result = self.backend.execute_command(
                    command=f"stat -f %m '{file_path}' 2>/dev/null || stat -c %Y '{file_path}' 2>/dev/null",
                    timeout=5000
                )
                if result.exit_code == 0:
                    mtime = int(result.output.strip())
                    file_times.append((file_path, mtime))
                else:
                    # If stat fails, add with time 0
                    file_times.append((file_path, 0))
            except Exception:
                file_times.append((file_path, 0))

        # Sort by modification time (newest first)
        file_times.sort(key=lambda x: x[1], reverse=True)

        return [file_path for file_path, _ in file_times]
