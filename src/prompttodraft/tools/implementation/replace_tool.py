"""
Replace tool implementation.

This tool replaces text within a file with precise, targeted changes.
"""
from pathlib import Path

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend, FileType
from prompttodraft.tools.outputs.models import (
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class ReplaceTool:
    """
    Framework-agnostic text replacement tool (edit functionality).

    Replaces text within a file. By default, replaces a single occurrence,
    but can replace multiple occurrences when expected_replacements is specified.
    """

    metadata = ToolMetadata(
        name="replace",
        description="Replaces text within a file. By default, replaces a single occurrence, but can replace multiple occurrences when expected_replacements is specified. This tool is designed for precise, targeted changes and requires significant context around the old_string to ensure it modifies the correct location. CRITICAL: Include at least 3 lines of context before and after the target text, matching whitespace and indentation precisely.",
        inputs={
            "file_path": {
                "type": "string",
                "description": "The absolute path to the file to modify (e.g., '/home/user/project/file.txt'). Relative paths are not supported.",
                "nullable": False,
            },
            "old_string": {
                "type": "string",
                "description": "The exact literal text to replace. This string must uniquely identify the single instance to change. It should include at least 3 lines of context before and after the target text, matching whitespace and indentation precisely. If old_string is empty, the tool attempts to create a new file at file_path with new_string as content.",
                "nullable": False,
            },
            "new_string": {
                "type": "string",
                "description": "The exact literal text to replace old_string with.",
                "nullable": False,
            },
            "expected_replacements": {
                "type": "number",
                "description": "Number of replacements expected. Defaults to 1 if not specified. Use when you want to replace multiple occurrences.",
                "nullable": True,
            },
        },
        output_type="string",
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize ReplaceTool with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    def execute(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        expected_replacements: int = 1,
    ) -> ToolOutputModel:
        """
        Execute the replace tool.

        Args:
            file_path: The absolute path to the file to modify
            old_string: The exact literal text to replace
            new_string: The exact literal text to replace old_string with
            expected_replacements: The number of occurrences to replace

        Returns:
            TextOutputModel with success message or ErrorOutputModel on failure
        """
        # Handle empty old_string (create new file)
        if not old_string:
            file_exists = self.backend.file_exists(path=file_path)
            if file_exists is not None:
                return ErrorOutputModel(
                    error=f"Cannot create new file: {file_path} already exists",
                    error_type="FileExistsError",
                )

            self.backend.write_file(file_path=file_path, content=new_string)
            return TextOutputModel(
                content=f"Created new file: {file_path} with provided content.",
            )

        # Check if file exists
        file_type = self.backend.file_exists(path=file_path)
        if file_type is None:
            return ErrorOutputModel(
                error=f"File does not exist: {file_path}",
                error_type="FileNotFoundError",
            )

        if file_type != FileType.FILE:
            return ErrorOutputModel(
                error=f"Path is not a file: {file_path}",
                error_type="NotAFileError",
            )

        # Read current content
        content = self.backend.read_file(file_path=file_path)

        # Count occurrences
        occurrences = content.count(old_string)

        # Validate occurrences
        if occurrences == 0:
            return ErrorOutputModel(
                error=f"Failed to edit, 0 occurrences found. The old_string was not found in the file.",
                error_type="NoMatchError",
            )

        if occurrences != expected_replacements:
            if occurrences > expected_replacements:
                return ErrorOutputModel(
                    error=f"Failed to edit, expected {expected_replacements} occurrences but found {occurrences}. The old_string matches multiple locations in the file. Please provide more context in old_string to make it unique (include at least 3 lines of surrounding context before and after).",
                    error_type="AmbiguousMatchError",
                )
            else:
                return ErrorOutputModel(
                    error=f"Failed to edit, expected {expected_replacements} occurrences but found {occurrences}.",
                    error_type="AmbiguousMatchError",
                )

        # Perform replacement
        new_content = content.replace(old_string, new_string, expected_replacements)

        # Write modified content
        self.backend.write_file(file_path=file_path, content=new_content)

        return TextOutputModel(
            content=f"Successfully modified file: {file_path} ({expected_replacements} replacements).",
        )
