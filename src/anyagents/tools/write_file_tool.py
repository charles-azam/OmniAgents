"""
Write file tool implementation.

This tool writes content to a specified file, creating it if it doesn't exist.
"""
from pydantic import BaseModel, Field

from anyagents.tools.base_tool import CoreBackendTool
from anyagents.backends.execution_backend import ExecutionBackend
from anyagents.outputs.outputs import (
    TextOutputModel,
    ToolOutputModel,
)


class WriteFileInput(BaseModel):
    """Input model for WriteFileTool."""
    file_path: str = Field(description="The path to the file to write to, relative to the working directory (e.g., 'hello.py' or 'src/main.py')")
    content: str = Field(description="The content to write into the file")


class WriteFileTool(CoreBackendTool[WriteFileInput, TextOutputModel]):
    """
    Framework-agnostic file writing tool.

    Writes content to a specified file. If the file exists, it will be overwritten.
    If the file doesn't exist, it (and any necessary parent directories) will be created.
    """

    name = "write_file"
    description = "Writes content to a specified file. If the file exists, it will be overwritten. If the file doesn't exist, it (and any necessary parent directories) will be created."

    def execute(self, inputs: WriteFileInput) -> TextOutputModel:
        """
        Execute the write_file tool.

        Args:
            inputs: Validated input model with file_path and content

        Returns:
            TextOutputModel with success message
        """
        # Convert str path to Path object
        path_obj = self.backend.convert_to_path(path=inputs.file_path)

        # Check if file already exists
        file_exists = self.backend.file_exists(path=path_obj)
        is_new_file = file_exists is None

        # Write the file (backend handles directory creation)
        self.backend.write_file(file_path=path_obj, content=inputs.content)

        # Return success message
        if is_new_file:
            return TextOutputModel(
                content=f"Successfully created and wrote to new file: {inputs.file_path}",
            )
        else:
            return TextOutputModel(
                content=f"Successfully overwrote file: {inputs.file_path}",
            )
