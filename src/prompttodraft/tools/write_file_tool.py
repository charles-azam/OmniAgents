"""
Write file tool implementation.

This tool writes content to a specified file, creating it if it doesn't exist.
"""
from pydantic import BaseModel, Field

from prompttodraft.tools.base_tool import CoreTool


class WriteFileTool(CoreTool):
    """
    Framework-agnostic file writing tool.

    Writes content to a specified file. If the file exists, it will be overwritten.
    If the file doesn't exist, it (and any necessary parent directories) will be created.
    """

    name = "write_file"
    description = "Writes content to a specified file. If the file exists, it will be overwritten. If the file doesn't exist, it (and any necessary parent directories) will be created."

    class InputModel(BaseModel):
        file_path: str = Field(description="The absolute path to the file to write to")
        content: str = Field(description="The content to write into the file")

    class OutputModel(BaseModel):
        success: bool = Field(description="Whether the file was written successfully")
        file_path: str = Field(description="The path to the file that was written")
        message: str = Field(description="Human-readable success message")
        is_new_file: bool = Field(description="Whether a new file was created (true) or an existing file was overwritten (false)")

    def execute(self, inputs: InputModel) -> OutputModel:
        # Check if file already exists
        file_exists = self.backend.file_exists(path=inputs.file_path)
        is_new_file = file_exists is None

        # Write the file (backend handles directory creation)
        self.backend.write_file(file_path=inputs.file_path, content=inputs.content)

        # Return structured output
        if is_new_file:
            message = f"Successfully created and wrote to new file: {inputs.file_path}"
        else:
            message = f"Successfully overwrote file: {inputs.file_path}"

        return self.OutputModel(
            success=True,
            file_path=inputs.file_path,
            message=message,
            is_new_file=is_new_file,
        )
