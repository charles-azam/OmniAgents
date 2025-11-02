"""
Search file content tool implementation.

This tool searches for a regular expression pattern within file contents.
"""
from pathlib import Path

from prompttodraft.agent.core.base_tool import CoreTool
from prompttodraft.agent.core.metadata import ToolMetadata
from prompttodraft.agent.backends.execution_backend import ExecutionBackend
from prompttodraft.agent.outputs.models import (
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class SearchFileContentTool(CoreTool):
    """
    Framework-agnostic file content search tool (grep functionality).

    Searches for a regular expression pattern within the content of files
    in a specified directory. Can filter files by a glob pattern.
    """

    metadata = ToolMetadata(
        name="search_file_content",
        description="Searches for a regular expression pattern within the content of files in a specified directory. Uses git grep if available in a Git repository for speed; otherwise, falls back to system grep. Can filter files by a glob pattern. Returns the lines containing matches, along with their file paths and line numbers.",
        inputs={
            "pattern": {
                "type": "string",
                "description": "The regular expression (regex) to search for in file contents (e.g., 'function\\s+myFunction').",
                "nullable": False,
            },
            "path": {
                "type": "string",
                "description": "Optional: The absolute path to the directory to search within. Defaults to the current working directory.",
                "nullable": True,
            },
            "include": {
                "type": "string",
                "description": "Optional: File pattern to include in the search (e.g., '*.js', '*.{ts,tsx}'). If omitted, searches most files.",
                "nullable": True,
            },
        },
        output_type="string",
    )

    def execute(
        self,
        pattern: str,
        path: str | None = None,
        include: str | None = None,
    ) -> ToolOutputModel:
        """
        Execute the search_file_content tool.

        Args:
            pattern: The regular expression to search for
            path: Optional directory to search within
            include: Optional glob pattern to filter files

        Returns:
            TextOutputModel with search results or ErrorOutputModel on failure
        """
        search_path = path if path else self.backend.get_working_directory()

        # Build grep command
        # Try git grep first if in a git repo, otherwise use regular grep
        grep_cmd_parts = []

        # Check if we're in a git repository
        git_check = self.backend.execute_command(
            command=f'cd "{search_path}" && git rev-parse --git-dir 2>/dev/null',
            timeout=5000,
        )

        if git_check.exit_code == 0:
            # Use git grep
            grep_cmd_parts.append(f'cd "{search_path}" && git grep -n "{pattern}"')
            if include:
                # Add file pattern as pathspec (git grep uses pathspec, not --glob)
                grep_cmd_parts.append(f'-- "{include}"')
        else:
            # Use regular grep
            grep_cmd_parts.append(f'grep -rn "{pattern}" "{search_path}"')
            if include:
                # Add file pattern using --include
                grep_cmd_parts.append(f'--include="{include}"')

        grep_cmd = " ".join(grep_cmd_parts)

        # Execute grep command
        result = self.backend.execute_command(
            command=grep_cmd,
            timeout=30000,
        )

        # grep returns exit code 1 when no matches found
        if result.exit_code != 0 and result.exit_code != 1:
            return ErrorOutputModel(
                error=f"Search failed: {result.output}",
                error_type="SearchError",
            )

        if not result.output or result.exit_code == 1:
            return TextOutputModel(
                content=f'Found 0 matches for pattern "{pattern}" in path "{search_path}"'
                + (f' (filter: "{include}")' if include else ""),
            )

        # Parse grep output and format it
        lines = result.output.strip().split("\n")
        matches_by_file = {}

        for line in lines:
            # Parse grep output: file:line:content or file-line-content
            parts = line.split(":", 2)
            if len(parts) >= 3:
                file_path = parts[0]
                line_num = parts[1]
                content = parts[2]

                if file_path not in matches_by_file:
                    matches_by_file[file_path] = []

                matches_by_file[file_path].append((line_num, content))

        # Format output
        total_matches = sum(len(matches) for matches in matches_by_file.values())
        output_lines = [
            f'Found {total_matches} matches for pattern "{pattern}" in path "{search_path}"'
            + (f' (filter: "{include}")' if include else "") + ":",
        ]

        for file_path, matches in matches_by_file.items():
            output_lines.append("---")
            # Make path relative to search path
            rel_path = file_path
            if file_path.startswith(search_path):
                rel_path = file_path[len(search_path):].lstrip("/")

            output_lines.append(f"File: {rel_path}")
            for line_num, content in matches:
                output_lines.append(f"L{line_num}: {content}")

        output_lines.append("---")

        return TextOutputModel(content="\n".join(output_lines))
