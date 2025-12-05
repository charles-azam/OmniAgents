"""
Search file content tool implementation.

This tool searches for a regular expression pattern within file contents.
"""
from pydantic import BaseModel, Field

from anyagents.tools.base_tool import CoreBackendTool
from anyagents.outputs.outputs import (
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class SearchFileContentInput(BaseModel):
    """Input model for SearchFileContentTool."""
    pattern: str = Field(description="The regular expression (regex) to search for in file contents (e.g., 'function\\s+myFunction').")
    path: str | None = Field(default=None, description="Optional: The path to the directory to search within, relative to the working directory. Defaults to the working directory.")
    include: str | None = Field(default=None, description="Optional: File pattern to include in the search (e.g., '*.js', '*.{ts,tsx}'). If omitted, searches most files.")


class SearchFileContentTool(CoreBackendTool[SearchFileContentInput, ToolOutputModel]):
    """
    Framework-agnostic file content search tool (grep functionality).

    Searches for a regular expression pattern within the content of files
    in a specified directory. Can filter files by a glob pattern.
    """

    name = "search_file_content"
    description = "Searches for a regular expression pattern within the content of files in a specified directory. Uses git grep if available in a Git repository for speed; otherwise, falls back to system grep. Can filter files by a glob pattern. Returns the lines containing matches, along with their file paths and line numbers."

    def execute(self, inputs: SearchFileContentInput) -> ToolOutputModel:
        """
        Execute the search_file_content tool.

        Args:
            inputs: Validated input model with pattern, path, and include

        Returns:
            TextOutputModel with search results or ErrorOutputModel on failure
        """
        search_path = inputs.path if inputs.path else str(self.backend.get_working_directory())

        # Build grep command
        # Try git grep first if in a git repo, otherwise use regular grep
        grep_cmd_parts = []

        # Check if we're in a git repository
        git_check = self.backend.execute_command(
            command=f'cd "{search_path}" && git rev-parse --git-dir 2>/dev/null',
            timeout=5000,
        )

        if git_check.exit_code == 0:
            # Use git grep with --untracked to also search untracked files
            grep_cmd_parts.append(f'cd "{search_path}" && git grep --untracked -n "{inputs.pattern}"')
            if inputs.include:
                # Add file pattern as pathspec (git grep uses pathspec, not --glob)
                grep_cmd_parts.append(f'-- "{inputs.include}"')
        else:
            # Use regular grep
            grep_cmd_parts.append(f'grep -rn "{inputs.pattern}" "{search_path}"')
            if inputs.include:
                # Add file pattern using --include
                grep_cmd_parts.append(f'--include="{inputs.include}"')

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
                content=f'Found 0 matches for pattern "{inputs.pattern}" in path "{search_path}"'
                + (f' (filter: "{inputs.include}")' if inputs.include else ""),
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
            f'Found {total_matches} matches for pattern "{inputs.pattern}" in path "{search_path}"'
            + (f' (filter: "{inputs.include}")' if inputs.include else "") + ":",
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
