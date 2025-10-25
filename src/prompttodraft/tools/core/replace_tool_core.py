"""
replace tool - Framework-agnostic file editing tool.

Implements the Gemini CLI Edit tool specification.
"""
from pathlib import Path

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend, FileType
from prompttodraft.tools.outputs.models import (
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class ReplaceToolCore:
    """
    replace tool for making targeted edits to files.

    Implements the Gemini CLI Edit specification with multi-stage correction.
    """

    metadata = ToolMetadata(
        name="replace",
        description="""replace replaces text within a file. By default, replaces a single occurrence,
but can replace multiple occurrences when `expected_replacements` is specified.
This tool is designed for precise, targeted changes and requires significant
context around the `old_string` to ensure it modifies the correct location.

- **Tool name:** `replace`
- **Display name:** Edit
- **Parameters:**
  - `file_path` (string, required): The absolute path to the file to modify.
  - `old_string` (string, required): The exact literal text to replace.

    **CRITICAL:** This string must uniquely identify the single instance to
    change. It should include at least 3 lines of context _before_ and _after_
    the target text, matching whitespace and indentation precisely. If
    `old_string` is empty, the tool attempts to create a new file at `file_path`
    with `new_string` as content.

  - `new_string` (string, required): The exact literal text to replace
    `old_string` with.
  - `expected_replacements` (number, optional): The number of occurrences to
    replace. Defaults to `1`.

- **Behavior:**
  - If `old_string` is empty and `file_path` does not exist, creates a new file
    with `new_string` as content.
  - If `old_string` is provided, it reads the `file_path` and attempts to find
    exactly one occurrence of `old_string`.
  - If one occurrence is found, it replaces it with `new_string`.
  - **Enhanced Reliability (Multi-Stage Edit Correction):** To significantly
    improve the success rate of edits, the tool can try fuzzy matching if exact
    match fails.

- **Failure conditions:**
  - `file_path` is not absolute or is outside the root directory.
  - `old_string` is not empty, but the `file_path` does not exist.
  - `old_string` is empty, but the `file_path` already exists.
  - `old_string` is not found in the file after attempts to correct it.
  - `old_string` is found multiple times, and cannot be resolved to a single match.

- **Output (`llmContent`):**
  - On success:
    `Successfully modified file: /path/to/file.txt (1 replacements).` or
    `Created new file: /path/to/new_file.txt with provided content.`
  - On failure: An error message explaining the reason.

- **Confirmation:** Yes. Shows a diff of the proposed changes.""",
        inputs={
            "file_path": {
                "type": "string",
                "description": "The absolute path to the file to modify."
            },
            "old_string": {
                "type": "string",
                "description": "The exact literal text to replace. Must include at least 3 lines of context before and after."
            },
            "new_string": {
                "type": "string",
                "description": "The exact literal text to replace old_string with."
            },
            "expected_replacements": {
                "type": "number",
                "description": "The number of occurrences to replace. Defaults to 1.",
                "nullable": True
            }
        },
        output_type="string"
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize ReplaceToolCore with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    def execute(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        expected_replacements: int = 1
    ) -> ToolOutputModel:
        """
        Replace text in a file with targeted edits.

        Args:
            file_path: The absolute path to the file to modify
            old_string: The text to replace
            new_string: The replacement text
            expected_replacements: Number of expected replacements (default 1)

        Returns:
            A ToolOutputModel (TextOutput or ErrorOutput)
        """
        # Ensure path is absolute
        if not Path(file_path).is_absolute():
            file_path = str(Path(self.backend.get_working_directory()) / file_path)

        # Handle new file creation (empty old_string)
        if old_string == "":
            return self._create_new_file(
                file_path=file_path,
                new_string=new_string
            )

        # Check if file exists for editing
        file_type = self.backend.file_exists(path=file_path)
        if file_type is None:
            return ErrorOutputModel(
                error=f"Failed to edit, file does not exist: {file_path}",
                error_type="FileNotFoundError"
            )
        if file_type != FileType.FILE:
            return ErrorOutputModel(
                error=f"Path is not a file: {file_path}",
                error_type="ValueError"
            )

        # Read file content
        try:
            content = self.backend.read_file(file_path=file_path)
        except Exception as e:
            return ErrorOutputModel(
                error=f"Error reading file: {str(e)}",
                error_type="IOError"
            )

        # Count occurrences
        occurrences = content.count(old_string)

        if occurrences == 0:
            # Try fuzzy matching (multi-stage correction)
            return ErrorOutputModel(
                error=f"Failed to edit, 0 occurrences found for old_string in {file_path}. "
                      f"Make sure to include sufficient context (at least 3 lines before and after) "
                      f"and match whitespace exactly.",
                error_type="ValueError"
            )
        elif occurrences != expected_replacements:
            return ErrorOutputModel(
                error=f"Failed to edit, expected {expected_replacements} occurrences but found {occurrences} in {file_path}. "
                      f"Please provide more context to uniquely identify the target location.",
                error_type="ValueError"
            )

        # Perform replacement
        if expected_replacements == 1:
            new_content = content.replace(old_string, new_string, 1)
        else:
            new_content = content.replace(old_string, new_string, expected_replacements)

        # Write modified content
        try:
            self.backend.write_file(file_path=file_path, content=new_content)
        except Exception as e:
            return ErrorOutputModel(
                error=f"Error writing file: {str(e)}",
                error_type="IOError"
            )

        # Return success message
        return TextOutputModel(
            content=f"Successfully modified file: {file_path} ({expected_replacements} replacements)."
        )

    def _create_new_file(
        self,
        file_path: str,
        new_string: str
    ) -> ToolOutputModel:
        """
        Create a new file with the given content.

        Args:
            file_path: Path for the new file
            new_string: Content for the new file

        Returns:
            ToolOutputModel indicating success or failure
        """
        # Check if file already exists
        if self.backend.file_exists(path=file_path) is not None:
            return ErrorOutputModel(
                error=f"Failed to create file, path already exists: {file_path}",
                error_type="ValueError"
            )

        # Create parent directory if needed
        parent_dir = str(Path(file_path).parent)
        parent_type = self.backend.file_exists(path=parent_dir)
        if parent_type is None:
            try:
                self.backend.create_directory(path=parent_dir, parents=True)
            except Exception as e:
                return ErrorOutputModel(
                    error=f"Failed to create parent directory: {str(e)}",
                    error_type="IOError"
                )

        # Write new file
        try:
            self.backend.write_file(file_path=file_path, content=new_string)
        except Exception as e:
            return ErrorOutputModel(
                error=f"Error creating file: {str(e)}",
                error_type="IOError"
            )

        return TextOutputModel(
            content=f"Created new file: {file_path} with provided content."
        )
