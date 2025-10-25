"""
search_file_content tool - Framework-agnostic content search tool.

Implements the Gemini CLI SearchText tool specification.
"""
from pathlib import Path
import re

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend, FileType
from prompttodraft.tools.outputs.models import (
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class SearchFileContentToolCore:
    """
    search_file_content tool for searching regex patterns in files.

    Implements the Gemini CLI SearchText specification.
    """

    metadata = ToolMetadata(
        name="search_file_content",
        description="""search_file_content searches for a regular expression pattern within the
content of files in a specified directory. Can filter files by a glob pattern.
Returns the lines containing matches, along with their file paths and line
numbers.

- **Tool name:** `search_file_content`
- **Display name:** SearchText
- **Parameters:**
  - `pattern` (string, required): The regular expression (regex) to search for
    (e.g., `"function\\s+myFunction"`).
  - `path` (string, optional): The absolute path to the directory to search
    within. Defaults to the current working directory.
  - `include` (string, optional): A glob pattern to filter which files are
    searched (e.g., `"*.js"`, `"src/**/*.{ts,tsx}"`). If omitted, searches most
    files (respecting common ignores).
- **Behavior:**
  - Uses `git grep` if available in a Git repository for speed; otherwise, falls
    back to system `grep` or a JavaScript-based search.
  - Returns a list of matching lines, each prefixed with its file path (relative
    to the search directory) and line number.
- **Output (`llmContent`):** A formatted string of matches.
- **Confirmation:** No.""",
        inputs={
            "pattern": {
                "type": "string",
                "description": "The regular expression (regex) to search for (e.g., \"function\\s+myFunction\")"
            },
            "path": {
                "type": "string",
                "description": "The absolute path to the directory to search within. Defaults to the current working directory.",
                "nullable": True
            },
            "include": {
                "type": "string",
                "description": "A glob pattern to filter which files are searched (e.g., \"*.js\", \"src/**/*.{ts,tsx}\")",
                "nullable": True
            }
        },
        output_type="string"
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize SearchFileContentToolCore with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    def execute(
        self,
        pattern: str,
        path: str | None = None,
        include: str | None = None
    ) -> ToolOutputModel:
        """
        Search for files containing content that matches the regex pattern.

        Args:
            pattern: The regular expression pattern to search for
            include: File pattern to include in the search (e.g. "*.js")
            path: The directory to search in (defaults to current working directory)

        Returns:
            A ToolOutputModel (TextOutput or ErrorOutput)
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

        # Validate regex pattern
        try:
            re.compile(pattern)
        except re.error as e:
            return ErrorOutputModel(
                error=f"Invalid regular expression pattern: {str(e)}",
                error_type="ValueError"
            )

        # Try to use git grep first (fastest if in a git repo)
        result = self._try_git_grep(
            pattern=pattern,
            search_path=search_path,
            include=include
        )

        if result is not None:
            return result

        # Fallback to system grep
        result = self._try_system_grep(
            pattern=pattern,
            search_path=search_path,
            include=include
        )

        return result

    def _try_git_grep(
        self,
        pattern: str,
        search_path: str,
        include: str | None
    ) -> ToolOutputModel | None:
        """
        Try to search using git grep.

        Args:
            pattern: Regex pattern to search for
            search_path: Directory to search in
            include: Optional file pattern filter

        Returns:
            ToolOutputModel if successful, None if git grep not available
        """
        try:
            # Check if we're in a git repository
            check_result = self.backend.execute_command(
                command=f"cd '{search_path}' && git rev-parse --git-dir",
                timeout=5000
            )
            if check_result.exit_code != 0:
                return None  # Not a git repo

            # Build git grep command
            cmd_parts = [f"cd '{search_path}' && git grep -n -E"]

            # Add pattern (escape single quotes in pattern)
            escaped_pattern = pattern.replace("'", "'\\''")
            cmd_parts.append(f"'{escaped_pattern}'")

            # Add file pattern filter if provided
            if include:
                cmd_parts.append(f"-- '{include}'")

            command = " ".join(cmd_parts)

            # Execute git grep
            result = self.backend.execute_command(
                command=command,
                timeout=30000
            )

            # Exit code 1 means no matches found, not an error
            if result.exit_code == 1:
                return TextOutputModel(
                    content=f'Found 0 matches for pattern "{pattern}" in path "{search_path}" (filter: "{include or "*"}")'
                )
            elif result.exit_code != 0:
                return None  # Other error, try fallback

            # Parse and format output
            return self._format_grep_output(
                output=result.output,
                pattern=pattern,
                search_path=search_path,
                include=include
            )

        except Exception:
            return None  # Fallback to system grep

    def _try_system_grep(
        self,
        pattern: str,
        search_path: str,
        include: str | None
    ) -> ToolOutputModel:
        """
        Search using system grep command.

        Args:
            pattern: Regex pattern to search for
            search_path: Directory to search in
            include: Optional file pattern filter

        Returns:
            ToolOutputModel with search results
        """
        try:
            # Build grep command
            cmd_parts = ["grep -r -n -E"]

            # Add pattern (escape single quotes)
            escaped_pattern = pattern.replace("'", "'\\''")
            cmd_parts.append(f"'{escaped_pattern}'")

            # Add file pattern filter if provided
            if include:
                cmd_parts.append(f"--include='{include}'")

            # Exclude common directories
            exclude_dirs = [
                ".git", "node_modules", "__pycache__", ".venv",
                "venv", ".pytest_cache", "dist", "build"
            ]
            for exclude_dir in exclude_dirs:
                cmd_parts.append(f"--exclude-dir='{exclude_dir}'")

            # Add search path
            cmd_parts.append(f"'{search_path}'")

            command = " ".join(cmd_parts)

            # Execute grep
            result = self.backend.execute_command(
                command=command,
                timeout=30000
            )

            # Exit code 1 means no matches found
            if result.exit_code == 1:
                return TextOutputModel(
                    content=f'Found 0 matches for pattern "{pattern}" in path "{search_path}" (filter: "{include or "*"}")'
                )
            elif result.exit_code != 0:
                return ErrorOutputModel(
                    error=f"Grep command failed: {result.output}",
                    error_type="CommandError"
                )

            # Parse and format output
            return self._format_grep_output(
                output=result.output,
                pattern=pattern,
                search_path=search_path,
                include=include
            )

        except Exception as e:
            return ErrorOutputModel(
                error=f"Error searching files: {str(e)}",
                error_type="IOError"
            )

    def _format_grep_output(
        self,
        output: str,
        pattern: str,
        search_path: str,
        include: str | None
    ) -> ToolOutputModel:
        """
        Format grep output into a readable format.

        Args:
            output: Raw grep output
            pattern: Search pattern
            search_path: Base search directory
            include: File filter pattern

        Returns:
            Formatted TextOutputModel
        """
        lines = output.strip().split('\n')
        match_count = len(lines)

        if match_count == 0:
            return TextOutputModel(
                content=f'Found 0 matches for pattern "{pattern}" in path "{search_path}" (filter: "{include or "*"}")'
            )

        # Group matches by file
        file_matches = {}
        for line in lines:
            if not line.strip():
                continue

            # Parse line: filepath:linenumber:content
            parts = line.split(':', 2)
            if len(parts) >= 3:
                file_path = parts[0]
                line_number = parts[1]
                content = parts[2]

                if file_path not in file_matches:
                    file_matches[file_path] = []
                file_matches[file_path].append((line_number, content))

        # Format output
        output_lines = [
            f'Found {match_count} matches for pattern "{pattern}" in path "{search_path}" (filter: "{include or "*"}"):'
        ]
        output_lines.append("---")

        for file_path, matches in file_matches.items():
            output_lines.append(f"File: {file_path}")
            for line_number, content in matches:
                output_lines.append(f"L{line_number}: {content}")
            output_lines.append("---")

        return TextOutputModel(content="\n".join(output_lines))
