"""
Replace tool implementation.

This tool replaces text within a file with precise, targeted changes.
"""
from pydantic import BaseModel, Field

from prompttodraft.tools.base_tool import CoreTool
from prompttodraft.backends.execution_backend import FileType


class ReplaceTool(CoreTool):
    """
    Framework-agnostic text replacement tool (edit functionality).

    Replaces text within a file. By default, replaces a single occurrence,
    but can replace multiple occurrences when expected_replacements is specified.
    """

    name = "replace"
    description = "Replaces text within a file. By default, replaces a single occurrence, but can replace multiple occurrences when expected_replacements is specified. This tool is designed for precise, targeted changes and requires significant context around the old_string to ensure it modifies the correct location. CRITICAL: Include at least 3 lines of context before and after the target text, matching whitespace and indentation precisely."

    class InputModel(BaseModel):
        file_path: str = Field(description="The absolute path to the file to modify (e.g., '/home/user/project/file.txt'). Relative paths are not supported.")
        old_string: str = Field(description="The exact literal text to replace. This string must uniquely identify the single instance to change. It should include at least 3 lines of context before and after the target text, matching whitespace and indentation precisely. If old_string is empty, the tool attempts to create a new file at file_path with new_string as content.")
        new_string: str = Field(description="The exact literal text to replace old_string with.")
        expected_replacements: int = Field(default=1, description="Number of replacements expected. Defaults to 1 if not specified. Use when you want to replace multiple occurrences.")

    class OutputModel(BaseModel):
        success: bool = Field(description="Whether the replacement was successful")
        message: str = Field(description="Human-readable summary of the operation")
        file_path: str = Field(description="The file path that was modified")
        replacements_made: int = Field(description="Number of replacements made")
        is_new_file: bool = Field(default=False, description="Whether a new file was created")
        error: str | None = Field(default=None, description="Error message if operation failed")

    def execute(self, inputs: InputModel) -> OutputModel:
        """
        Execute the replace tool.

        Args:
            inputs: Validated input model with file_path, old_string, new_string, and expected_replacements

        Returns:
            OutputModel with success or error details
        """
        # Handle empty old_string (create new file)
        if not inputs.old_string:
            file_exists = self.backend.file_exists(path=inputs.file_path)
            if file_exists is not None:
                return self.OutputModel(
                    success=False,
                    message=f"Cannot create new file: {inputs.file_path} already exists",
                    file_path=inputs.file_path,
                    replacements_made=0,
                    is_new_file=False,
                    error=f"Cannot create new file: {inputs.file_path} already exists",
                )

            self.backend.write_file(file_path=inputs.file_path, content=inputs.new_string)
            return self.OutputModel(
                success=True,
                message=f"Created new file: {inputs.file_path} with provided content",
                file_path=inputs.file_path,
                replacements_made=0,
                is_new_file=True,
            )

        # Check if file exists
        file_type = self.backend.file_exists(path=inputs.file_path)
        if file_type is None:
            return self.OutputModel(
                success=False,
                message=f"File does not exist: {inputs.file_path}",
                file_path=inputs.file_path,
                replacements_made=0,
                error=f"File does not exist: {inputs.file_path}",
            )

        if file_type != FileType.FILE:
            return self.OutputModel(
                success=False,
                message=f"Path is not a file: {inputs.file_path}",
                file_path=inputs.file_path,
                replacements_made=0,
                error=f"Path is not a file: {inputs.file_path}",
            )

        # Read current content
        content = self.backend.read_file(file_path=inputs.file_path)

        # Count occurrences
        occurrences = content.count(inputs.old_string)

        # Validate occurrences
        if occurrences == 0:
            return self.OutputModel(
                success=False,
                message="Failed to edit: old_string was not found in the file",
                file_path=inputs.file_path,
                replacements_made=0,
                error=f"Failed to edit, 0 occurrences found. The old_string was not found in the file.",
            )

        if occurrences != inputs.expected_replacements:
            if occurrences > inputs.expected_replacements:
                return self.OutputModel(
                    success=False,
                    message=f"Failed to edit: expected {inputs.expected_replacements} occurrences but found {occurrences}",
                    file_path=inputs.file_path,
                    replacements_made=0,
                    error=f"Failed to edit, expected {inputs.expected_replacements} occurrences but found {occurrences}. The old_string matches multiple locations in the file. Please provide more context in old_string to make it unique (include at least 3 lines of surrounding context before and after).",
                )
            else:
                return self.OutputModel(
                    success=False,
                    message=f"Failed to edit: expected {inputs.expected_replacements} occurrences but found {occurrences}",
                    file_path=inputs.file_path,
                    replacements_made=0,
                    error=f"Failed to edit, expected {inputs.expected_replacements} occurrences but found {occurrences}.",
                )

        # Perform replacement
        new_content = content.replace(inputs.old_string, inputs.new_string, inputs.expected_replacements)

        # Write modified content
        self.backend.write_file(file_path=inputs.file_path, content=new_content)

        return self.OutputModel(
            success=True,
            message=f"Successfully modified file: {inputs.file_path} ({inputs.expected_replacements} replacements)",
            file_path=inputs.file_path,
            replacements_made=inputs.expected_replacements,
        )
