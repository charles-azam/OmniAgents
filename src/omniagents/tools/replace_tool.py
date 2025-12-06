"""
Replace tool implementation.

This tool replaces text within a file with precise, targeted changes.
"""
from pydantic import BaseModel, Field

from omniagents.tools.base_tool import CoreBackendTool
from omniagents.backends.execution_backend import FileType
from omniagents.outputs.outputs import (
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class ReplaceInput(BaseModel):
    """Input model for ReplaceTool."""
    file_path: str = Field(description="The path to the file to modify, relative to the working directory (e.g., 'hello.py' or 'src/main.py')")
    old_string: str = Field(description="The exact literal text to replace. This string must uniquely identify the single instance to change. It should include at least 3 lines of context before and after the target text, matching whitespace and indentation precisely. If old_string is empty, the tool attempts to create a new file at file_path with new_string as content.")
    new_string: str = Field(description="The exact literal text to replace old_string with.")
    expected_replacements: int = Field(default=1, description="Number of replacements expected. Defaults to 1 if not specified. Use when you want to replace multiple occurrences.")


class ReplaceTool(CoreBackendTool[ReplaceInput, ToolOutputModel]):
    """
    Framework-agnostic text replacement tool (edit functionality).

    Replaces text within a file. By default, replaces a single occurrence,
    but can replace multiple occurrences when expected_replacements is specified.
    """

    name = "replace"
    description = "Replaces text within a file. By default, replaces a single occurrence, but can replace multiple occurrences when expected_replacements is specified. This tool is designed for precise, targeted changes and requires significant context around the old_string to ensure it modifies the correct location. CRITICAL: Include at least 3 lines of context before and after the target text, matching whitespace and indentation precisely."

    def execute(self, inputs: ReplaceInput) -> ToolOutputModel:
        """
        Execute the replace tool.

        Args:
            inputs: Validated input model with file_path, old_string, new_string, and expected_replacements

        Returns:
            TextOutputModel with success message or ErrorOutputModel on failure
        """
        # Convert str path to Path object
        path_obj = self.backend.convert_to_path(path=inputs.file_path)

        # Handle empty old_string (create new file)
        if not inputs.old_string:
            file_exists = self.backend.file_exists(path=path_obj)
            if file_exists is not None:
                return ErrorOutputModel(
                    error=f"Cannot create new file: {inputs.file_path} already exists",
                    error_type="FileExistsError",
                )

            self.backend.write_file(file_path=path_obj, content=inputs.new_string)
            return TextOutputModel(
                content=f"Created new file: {inputs.file_path} with provided content.",
            )

        # Check if file exists
        file_type = self.backend.file_exists(path=path_obj)
        if file_type is None:
            return ErrorOutputModel(
                error=f"File does not exist: {inputs.file_path}",
                error_type="FileNotFoundError",
            )

        if file_type != FileType.FILE:
            return ErrorOutputModel(
                error=f"Path is not a file: {inputs.file_path}",
                error_type="NotAFileError",
            )

        # Read current content
        content = self.backend.read_file(file_path=path_obj)

        # Count occurrences
        occurrences = content.count(inputs.old_string)

        # Validate occurrences
        if occurrences == 0:
            return ErrorOutputModel(
                error=f"Failed to edit, 0 occurrences found. The old_string was not found in the file.",
                error_type="NoMatchError",
            )

        if occurrences != inputs.expected_replacements:
            if occurrences > inputs.expected_replacements:
                return ErrorOutputModel(
                    error=f"Failed to edit, expected {inputs.expected_replacements} occurrences but found {occurrences}. The old_string matches multiple locations in the file. Please provide more context in old_string to make it unique (include at least 3 lines of surrounding context before and after).",
                    error_type="AmbiguousMatchError",
                )
            else:
                return ErrorOutputModel(
                    error=f"Failed to edit, expected {inputs.expected_replacements} occurrences but found {occurrences}.",
                    error_type="AmbiguousMatchError",
                )

        # Perform replacement
        new_content = content.replace(inputs.old_string, inputs.new_string, inputs.expected_replacements)

        # Write modified content
        self.backend.write_file(file_path=path_obj, content=new_content)

        return TextOutputModel(
            content=f"Successfully modified file: {inputs.file_path} ({inputs.expected_replacements} replacements).",
        )
