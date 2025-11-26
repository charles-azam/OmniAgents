"""
Search file content tool implementation.

This tool searches for a regular expression pattern within file contents.
"""
from pydantic import BaseModel, Field

from prompttodraft.tools.base_tool import CoreTool


class SearchFileContentTool(CoreTool):
    """
    Framework-agnostic file content search tool (grep functionality).

    Searches for a regular expression pattern within the content of files
    in a specified directory. Can filter files by a glob pattern.
    """

    name = "search_file_content"
    description = "Searches for a regular expression pattern within the content of files in a specified directory. Uses git grep if available in a Git repository for speed; otherwise, falls back to system grep. Can filter files by a glob pattern. Returns the lines containing matches, along with their file paths and line numbers."

    class InputModel(BaseModel):
        pattern: str = Field(description="The regular expression (regex) to search for in file contents (e.g., 'function\\s+myFunction').")
        path: str | None = Field(default=None, description="Optional: The absolute path to the directory to search within. Defaults to the current working directory.")
        include: str | None = Field(default=None, description="Optional: File pattern to include in the search (e.g., '*.js', '*.{ts,tsx}'). If omitted, searches most files.")

    class OutputModel(BaseModel):
        success: bool = Field(description="Whether the search completed successfully")
        message: str = Field(description="Human-readable summary of search results")
        content: str = Field(description="Formatted search results with file paths, line numbers, and matching lines")
        total_matches: int = Field(description="Total number of matches found")
        files_with_matches: int = Field(description="Number of files containing matches")
        pattern: str = Field(description="The search pattern used")
        search_path: str = Field(description="The directory path that was searched")
        error: str | None = Field(default=None, description="Error message if search failed")

    def execute(self, inputs: InputModel) -> OutputModel:
        """
        Execute the search_file_content tool.

        Args:
            inputs: Validated input model with pattern, path, and include

        Returns:
            OutputModel with search results or error details
        """
        search_path = inputs.path if inputs.path else self.backend.get_working_directory()

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
            grep_cmd_parts.append(f'cd "{search_path}" && git grep -n "{inputs.pattern}"')
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
            return self.OutputModel(
                success=False,
                message=f"Search failed: {result.output}",
                content="",
                total_matches=0,
                files_with_matches=0,
                pattern=inputs.pattern,
                search_path=search_path,
                error=f"Search failed: {result.output}",
            )

        if not result.output or result.exit_code == 1:
            content = f'Found 0 matches for pattern "{inputs.pattern}" in path "{search_path}"' + (f' (filter: "{inputs.include}")' if inputs.include else "")
            return self.OutputModel(
                success=True,
                message=f"No matches found for pattern '{inputs.pattern}'",
                content=content,
                total_matches=0,
                files_with_matches=0,
                pattern=inputs.pattern,
                search_path=search_path,
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

        return self.OutputModel(
            success=True,
            message=f"Found {total_matches} matches in {len(matches_by_file)} files for pattern '{inputs.pattern}'",
            content="\n".join(output_lines),
            total_matches=total_matches,
            files_with_matches=len(matches_by_file),
            pattern=inputs.pattern,
            search_path=search_path,
        )
