"""
Write file tool implementation.

This tool writes content to a specified file, creating it if it doesn't exist.
"""
from pathlib import Path

from prompttodraft.agent.tools.base_tool import CoreTool
from prompttodraft.agent.tools.metadata import ToolMetadata
from prompttodraft.agent.backends.execution_backend import ExecutionBackend, FileType
from prompttodraft.agent.outputs.models import (
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class WriteFileTool(CoreTool):
    """
    Framework-agnostic file writing tool.

    Writes content to a specified file. If the file exists, it will be overwritten.
    If the file doesn't exist, it (and any necessary parent directories) will be created.
    """

    metadata = ToolMetadata(
        name="write_file",
        description="Writes content to a specified file. If the file exists, it will be overwritten. If the file doesn't exist, it (and any necessary parent directories) will be created.",
        inputs={
            "file_path": {
                "type": "string",
                "description": "The absolute path to the file to write to",
                "nullable": False,
            },
            "content": {
                "type": "string",
                "description": "The content to write into the file",
                "nullable": False,
            },
        },
        output_type="string",
    )

    def execute(
        self,
        file_path: str,
        content: str,
    ) -> ToolOutputModel:
        """
        Execute the write_file tool.

        Args:
            file_path: The absolute path to the file to write to
            content: The content to write into the file

        Returns:
            TextOutputModel with success message or ErrorOutputModel on failure
        """
        # Check if file already exists
        file_exists = self.backend.file_exists(path=file_path)
        is_new_file = file_exists is None

        # Write the file (backend handles directory creation)
        self.backend.write_file(file_path=file_path, content=content)

        # Return success message
        if is_new_file:
            return TextOutputModel(
                content=f"Successfully created and wrote to new file: {file_path}",
            )
        else:
            return TextOutputModel(
                content=f"Successfully overwrote file: {file_path}",
            )
