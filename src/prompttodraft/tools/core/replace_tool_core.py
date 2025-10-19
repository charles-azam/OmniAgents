"""
ReplaceToolCore - Framework-agnostic file writing/replacement tool.

Extracted from smolcc/tools/replace_tool.py with business logic separated from execution.
"""
import os

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend
from prompttodraft.tools.outputs.models import (
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)

MAX_LINES = 16000


class ReplaceToolCore:
    """
    Framework-agnostic file writing/replacement tool.

    Extracted from smolcc/tools/replace_tool.py:17-90
    """

    # Metadata (from replace_tool.py:22-31)
    metadata = ToolMetadata(
        name="Replace",
        description="""Writes data to a file on the local filesystem, replacing any existing file with the same name.

Before invoking this tool:

1. First inspect the current file with the **ReadFile** tool so you fully understand its contents and context.

2. Directory check (relevant only when creating a brand-new file):
   • Use the **LS** tool to confirm the parent directory already exists and is indeed the intended destination.""",
        inputs={
            "file_path": {
                "type": "string",
                "description": "The absolute path to the file to write (must be absolute, not relative)"
            },
            "content": {
                "type": "string",
                "description": "The content to write to the file"
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
        content: str
    ) -> ToolOutputModel:
        """
        Write content to a file, creating or overwriting it (from replace_tool.py:40-86).

        Args:
            file_path: The absolute path to the file to write
            content: The content to write to the file

        Returns:
            A ToolOutputModel (TextOutput or ErrorOutput)
        """
        # Make sure path is absolute
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)

        # Check if parent directory exists
        parent_dir = os.path.dirname(file_path)
        if not self.backend.file_exists(path=parent_dir):
            return ErrorOutputModel(
                error=f"Parent directory '{parent_dir}' does not exist",
                error_type="FileNotFoundError"
            )

        # Check file permissions if the file already exists
        if self.backend.file_exists(path=file_path):
            if not self.backend.is_file(path=file_path):
                return ErrorOutputModel(
                    error=f"Path '{file_path}' exists but is not a file",
                    error_type="ValueError"
                )

        # Write the content to the file
        try:
            file_existed = self.backend.file_exists(path=file_path)
            self.backend.write_file(file_path=file_path, content=content)

            # Return success message
            if not file_existed:
                return TextOutputModel(content=f"File created successfully at: {file_path}")
            else:
                # Add cat -n style line numbering for updates
                preview_lines = content.splitlines()[:MAX_LINES]
                numbered_lines = [f"{i+1:6d}\t{line}" for i, line in enumerate(preview_lines)]
                numbered_preview = "\n".join(numbered_lines)

                return TextOutputModel(
                    content=f"The file {file_path} has been updated. Here's the result of running `cat -n` on a snippet of the edited file:\n{numbered_preview}"
                )

        except Exception as e:
            return ErrorOutputModel(error=f"Error writing to file '{file_path}': {str(e)}", error_type="IOError")
