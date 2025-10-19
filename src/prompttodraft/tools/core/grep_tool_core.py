"""
GrepToolCore - Framework-agnostic content search tool.

Extracted from smolcc/tools/grep_tool.py with business logic separated from execution.
"""
import os
import re
import time

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend
from prompttodraft.tools.outputs.models import (
    FileInfo,
    FileListOutputModel,
    CodeOutputModel,
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class GrepToolCore:
    """
    Framework-agnostic content search tool.

    Extracted from smolcc/tools/grep_tool.py:20-466
    """

    # Metadata (from grep_tool.py:26-42)
    metadata = ToolMetadata(
        name="GrepTool",
        description="""
- Blazingly fast content-search utility that scales gracefully to codebases of any size
- Looks inside files using standard regular-expression queries
- Accepts full regex syntax (e.g., "log.*Error", "function\\s+\\w+", and similar patterns)
- Narrow the scan with the **include** parameter to match file globs such as "*.js" or "*.{ts,tsx}"
- Emits the list of matching file paths ordered by most-recent modification time
- Reach for this tool whenever you need to locate files whose contents match specific patterns
- For exploratory hunts that might demand several passes of globbing and grepping, switch to the Agent tool instead""",
        inputs={
            "pattern": {
                "type": "string",
                "description": "The regular expression pattern to search for in file contents"
            },
            "include": {
                "type": "string",
                "description": 'File pattern to include in the search (e.g. "*.js", "*.{ts,tsx}")',
                "nullable": True
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
        Initialize GrepToolCore with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    def execute(
        self,
        pattern: str,
        include: str | None = None,
        path: str | None = None
    ) -> ToolOutputModel:
        """
        Search for files containing content that matches the regex pattern (from grep_tool.py:44-110).

        Args:
            pattern: The regular expression pattern to search for in file contents
            include: File pattern to include in the search (e.g. "*.js", "*.{ts,tsx}")
            path: The directory to search in (defaults to current working directory)

        Returns:
            A ToolOutputModel (FileListOutput, CodeOutput, or TextOutput)
        """
        start_time = time.time()
        search_path = path or os.getcwd()

        # Make sure search_path is absolute
        search_path = os.path.abspath(search_path)

        # Compile the regex pattern
        try:
            re.compile(pattern)
        except re.error as e:
            return ErrorOutputModel(error=f"Invalid regular expression pattern: {str(e)}", error_type="ValueError")

        # Search for pattern in files via backend
        file_matches = self.backend.search_files(pattern=pattern, include=include, path=search_path)

        # Check if we found any matches
        if not file_matches:
            all_files_count = len(self.backend.glob_files(pattern=include or "**/*", path=search_path))
            return TextOutputModel(content=f"No matches found for pattern '{pattern}' in {all_files_count} files")

        # Calculate total match count
        match_count = sum(len(f['matches']) for f in file_matches)

        # Truncate to max 10 files for display
        truncated = len(file_matches) > 10
        displayed_files = file_matches[:10]

        duration_ms = int((time.time() - start_time) * 1000)

        # Format results for display
        return self._format_results(
            pattern=pattern,
            file_matches=displayed_files,
            total_files=len(file_matches),
            truncated=truncated,
            duration_ms=duration_ms,
            search_path=search_path,
            match_count=match_count
        )

    def _format_results(
        self,
        pattern: str,
        file_matches: list[dict[str, str | int | list]],
        total_files: int,
        truncated: bool,
        duration_ms: int,
        search_path: str,
        match_count: int
    ) -> ToolOutputModel:
        """
        Format search results for rich display (from grep_tool.py:252-339).

        Args:
            pattern: The search pattern
            file_matches: List of file match information
            total_files: Total number of matching files
            truncated: Whether results were truncated
            duration_ms: Search duration in milliseconds
            search_path: Path that was searched
            match_count: Total number of matches

        Returns:
            A ToolOutputModel for display
        """
        # Create a summary with statistics
        summary = f"Found {match_count} matches in {total_files} files"
        if truncated:
            summary += f" (showing first 10 files)"
        summary += f" for pattern '{pattern}' in {search_path}"
        summary += f" ({duration_ms}ms)"

        # Check if we should show all matches as a table
        if total_files <= 5:
            # For small result sets, we'll show all matches with context
            result = f"{summary}\n\n"

            for file_info in file_matches:
                file_path = file_info['path']

                result += f"File: {file_path}\n"

                for match in file_info['matches'][:5]:  # Limit to 5 matches per file
                    line_number = match['line_number']
                    context_lines = match['context']
                    match_line_index = match['match_line_index']

                    # Format context with line numbers and highlighting
                    context_with_numbers = ""
                    for i, line in enumerate(context_lines):
                        line_num = line_number - match_line_index + i

                        # Highlight the match line
                        if i == match_line_index:
                            # Add markers for the match
                            match_start, match_end = match['match_span']
                            highlighted_line = line[:match_start] + "§" + line[match_start:match_end] + "§" + line[match_end:]
                            context_with_numbers += f"{line_num:4d} | {highlighted_line}\n"
                        else:
                            context_with_numbers += f"{line_num:4d} | {line}\n"

                    result += context_with_numbers + "\n"

                # If we have more matches than shown
                if len(file_info['matches']) > 5:
                    result += f"... and {len(file_info['matches']) - 5} more matches in this file\n\n"

            # Return as CodeOutput
            return CodeOutputModel(content=result, language="text", line_numbers=False)
        else:
            # For larger result sets, just return a file list
            file_list = []
            for file_info in file_matches:
                match_count_file = len(file_info['matches'])
                first_line = file_info['matches'][0]['line_number'] if match_count_file > 0 else 0

                file_list.append(
                    FileInfo(
                        name=os.path.basename(file_info['path']),
                        path=file_info['path'],
                        is_dir=False,
                        size=match_count_file,  # Use match count as "size" for display
                        modified=file_info['modified'],
                        modified_date=""
                    )
                )

            # Return as FileListOutputModel
            return FileListOutputModel(
                files=file_list,
                path=f"Search results for '{pattern}' in {search_path} ({duration_ms}ms)",
                total_count=len(file_list),
                truncated=truncated
            )
