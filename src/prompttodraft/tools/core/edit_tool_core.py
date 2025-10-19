"""
EditToolCore - Framework-agnostic file editing tool.

Extracted from smolcc/tools/edit_tool.py with business logic separated from execution.
"""
import os

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend
from prompttodraft.tools.outputs.models import (
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class EditToolCore:
    """
    Framework-agnostic file editing tool.

    Extracted from smolcc/tools/edit_tool.py:20-299
    """

    # Metadata (from edit_tool.py:26-99)
    metadata = ToolMetadata(
        name="Edit",
        description="""This utility is designed for making in-place edits to files.
If your goal is to move or rename a file, you should normally reach for the
Bash tool and the `mv` command.  When you need to replace an entire file's
contents, the Write tool is more appropriate.

Before you run this utility:

1. Examine the file with the View tool so you fully understand its context.
2. When creating a brand-new file, confirm the directory path is correct:
   • Use the LS tool to be sure the parent folder exists and is the intended
     location.

Supplying an edit requires three fields:

1. **file_path** – An *absolute* path (starts with "/") to the file you want to
   change.
2. **old_string** – The exact text to be replaced.  It *must* appear exactly
   once in the file and include every space, tab, and line break exactly as
   written.
3. **new_string** – The replacement text that will take the place of
   `old_string`.

The tool swaps **one** occurrence of `old_string` with `new_string` in the
specified file.

CRITICAL RULES FOR USING THIS TOOL
==================================

1. **UNIQUENESS** – `old_string` must single-handedly identify the correct
   spot.  To achieve that:
   • Provide at least 3–5 lines of context **before** the edit location.
   • Provide at least 3–5 lines of context **after** the edit location.
   • Preserve all whitespace, indentation, and surrounding code exactly as it
     appears in the file.

2. **SINGLE INSTANCE** – The utility edits only one occurrence at a time.
   • Make separate calls for each additional change.
   • Each call's `old_string` must uniquely flag its own spot with ample
     context.

3. **VERIFICATION** – Prior to calling the tool:
   • Count how many times the target text occurs in the file.
   • If it appears more than once, gather enough surrounding text so the
     `old_string` isolates exactly one instance.
   • Plan separate calls for every additional instance.

**Failure to follow these rules will cause errors:**

• The edit fails if `old_string` matches multiple places.
• The edit fails if `old_string` does not match the file *exactly* (including
  whitespace).
• Insufficient context can lead to changing the wrong code.

GENERAL EDITING GUIDELINES
--------------------------

• Ensure the resulting file is valid, idiomatic code.
• Never leave the file in a broken state.
• Always provide absolute paths (begin with "/").

### Creating a new file

• Use a fresh `file_path` (include new directories if needed).
• Set `old_string` to an empty string.
• Put the complete contents of the new file in `new_string`.""",
        inputs={
            "file_path": {
                "type": "string",
                "description": "The absolute path to the file to modify"
            },
            "old_string": {
                "type": "string",
                "description": "The text to replace"
            },
            "new_string": {
                "type": "string",
                "description": "The text to replace it with"
            }
        },
        output_type="string"
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize EditToolCore with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    def execute(
        self,
        file_path: str,
        old_string: str,
        new_string: str
    ) -> ToolOutputModel:
        """
        Edit a file by replacing old_string with new_string (from edit_tool.py:102-201).

        Args:
            file_path: The absolute path to the file to modify
            old_string: The text to replace
            new_string: The text to replace it with

        Returns:
            A ToolOutputModel (TextOutput or ErrorOutput)
        """
        # Make sure path is absolute
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)

        # Check if we're creating a new file
        is_new_file = not self.backend.file_exists(path=file_path) and old_string == ""

        # If creating a new file, ensure parent directory exists
        if is_new_file:
            parent_dir = os.path.dirname(file_path)
            if not self.backend.file_exists(path=parent_dir):
                # Try to create the directory
                try:
                    os.makedirs(parent_dir, exist_ok=True)
                except Exception as e:
                    return ErrorOutputModel(
                        error=f"Could not create parent directory '{parent_dir}': {str(e)}",
                        error_type="IOError"
                    )

            # Create the new file
            try:
                self.backend.write_file(file_path=file_path, content=new_string)

                # For new files, return formatted snippet
                numbered_content = self._add_line_numbers(content=new_string, start_line=1)
                return TextOutputModel(
                    content=f"The file {file_path} has been updated. Here's the result of running `cat -n` on a snippet of the edited file:\n{numbered_content}"
                )
            except Exception as e:
                return ErrorOutputModel(error=f"Error creating file '{file_path}': {str(e)}", error_type="IOError")

        # For existing files, check if file exists
        if not self.backend.file_exists(path=file_path):
            return ErrorOutputModel(error=f"File '{file_path}' does not exist", error_type="FileNotFoundError")

        if not self.backend.is_file(path=file_path):
            return ErrorOutputModel(error=f"Path '{file_path}' is not a file", error_type="ValueError")

        # Read the file content
        try:
            file_content_with_numbers = self.backend.read_file(file_path=file_path, offset=0, limit=None)
            # Remove line numbers that were added by read_file
            lines_with_numbers = file_content_with_numbers.split('\n')
            lines = []
            for line in lines_with_numbers:
                # Skip truncation messages but keep empty lines
                if line.startswith('(Result truncated'):
                    continue
                # Remove line number prefix (format: "     1\t")
                if '\t' in line:
                    # Split by tab and take everything after the first tab
                    parts = line.split('\t', 1)
                    if len(parts) > 1:
                        lines.append(parts[1])
                    else:
                        # Line with tab but no content after - keep empty
                        lines.append('')
                else:
                    # No tab means it's an empty line from line numbering
                    # Only keep it if the line is truly empty
                    if not line.strip():
                        lines.append('')
            file_content = '\n'.join(lines)

        except Exception as e:
            return ErrorOutputModel(error=f"Error reading file '{file_path}': {str(e)}", error_type="IOError")

        # Special handling for empty old_string
        if old_string == "":
            # Append to an existing file
            new_content = file_content + new_string
            try:
                self.backend.write_file(file_path=file_path, content=new_content)
                snippet = self._get_snippet(new_content=new_content, old_string="", new_string=new_string)
                return self._format_result(file_path=file_path, snippet=snippet)
            except Exception as e:
                return ErrorOutputModel(error=f"Error writing to file '{file_path}': {str(e)}", error_type="IOError")

        # For non-empty old_string, check if it's in the file
        if old_string not in file_content:
            return ErrorOutputModel(
                error="The specified text was not found in the file",
                error_type="ValueError"
            )

        # Count occurrences
        occurrences = file_content.count(old_string)
        if occurrences > 1:
            return ErrorOutputModel(
                error=f"The specified text appears {occurrences} times in the file. Please provide more context to uniquely identify which instance to replace.",
                error_type="ValueError"
            )

        # Replace the text
        new_content = file_content.replace(old_string, new_string, 1)

        # Write the changed content back to the file
        try:
            self.backend.write_file(file_path=file_path, content=new_content)
        except Exception as e:
            return ErrorOutputModel(error=f"Error writing to file '{file_path}': {str(e)}", error_type="IOError")

        # Get a snippet of the modified file
        snippet = self._get_snippet(new_content=new_content, old_string=old_string, new_string=new_string)

        # Return success message with snippet
        return self._format_result(file_path=file_path, snippet=snippet)

    def _get_snippet(self, new_content: str, old_string: str, new_string: str) -> str:
        """
        Get a snippet of the modified file around the edit point (from edit_tool.py:203-259).

        Args:
            new_content: The content of the modified file
            old_string: The string that was replaced
            new_string: The string that replaced it

        Returns:
            A snippet of the modified file as a string with line numbers
        """
        # Number of context lines before/after the change
        n_lines_snippet = 4

        # For new files or if old_string is empty
        if old_string == "":
            # Just return the first few lines of the new content
            new_lines = new_content.split('\n')
            max_lines = min(len(new_lines), n_lines_snippet * 2)
            return '\n'.join(new_lines[:max_lines])

        # Find the position of the new string in the content
        lines = new_content.split('\n')

        # If file is short enough, return the whole thing
        if len(lines) <= n_lines_snippet * 2:
            return new_content

        # Try to find where the edit happened
        try:
            # First, try to find where the new_string appears
            new_string_parts = new_string.split('\n')
            first_line_of_new = new_string_parts[0] if new_string_parts else ""

            # Find this line in the content
            line_index = -1
            for i, line in enumerate(lines):
                if first_line_of_new in line:
                    line_index = i
                    break

            # If we found it, create a window around it
            if line_index >= 0:
                start_line = max(0, line_index - n_lines_snippet)
                end_line = min(len(lines), line_index + len(new_string_parts) + n_lines_snippet)
                return '\n'.join(lines[start_line:end_line])

            # If we couldn't find it, just return a reasonable chunk from the start
            return '\n'.join(lines[:n_lines_snippet * 2])

        except Exception:
            # Fallback to just showing the first few lines
            return '\n'.join(lines[:n_lines_snippet * 2])

    def _format_result(self, file_path: str, snippet: str) -> TextOutputModel:
        """
        Format the result message with the edited file details (from edit_tool.py:261-275).

        Args:
            file_path: The path to the file that was modified
            snippet: A snippet of the modified file

        Returns:
            A formatted TextOutputModel
        """
        # Add line numbers to the snippet
        numbered_snippet = self._add_line_numbers(content=snippet, start_line=1)

        return TextOutputModel(
            content=f"The file {file_path} has been updated. Here's the result of running `cat -n` on a snippet of the edited file:\n{numbered_snippet}"
        )

    def _add_line_numbers(self, content: str, start_line: int = 1) -> str:
        """
        Add line numbers to content (from edit_tool.py:277-295).

        Args:
            content: The content to add line numbers to
            start_line: The line number to start from

        Returns:
            Content with line numbers
        """
        lines = content.split('\n')
        result = []

        for i, line in enumerate(lines):
            line_number = start_line + i
            result.append(f"{line_number:6d}\t{line}")

        return '\n'.join(result)
