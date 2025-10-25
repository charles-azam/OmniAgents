"""
write_file tool - Framework-agnostic file writing tool.

Implements the Gemini CLI WriteFile tool specification.
"""
from pathlib import Path

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend, FileType
from prompttodraft.tools.outputs.models import (
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class WriteFileToolCore:
    """
    write_file tool for writing content to files.

    Implements the Gemini CLI WriteFile specification.
    """

    metadata = ToolMetadata(
        name="write_file",
        description="""write_file writes content to a specified file. If the file exists, it will be
overwritten. If the file doesn't exist, it (and any necessary parent
directories) will be created.

- **Tool name:** `write_file`
- **Display name:** WriteFile
- **Parameters:**
  - `file_path` (string, required): The absolute path to the file to write to.
  - `content` (string, required): The content to write into the file.
- **Behavior:**
  - Writes the provided `content` to the `file_path`.
  - Creates parent directories if they don't exist.
- **Output (`llmContent`):** A success message, e.g.,
  `Successfully overwrote file: /path/to/your/file.txt` or
  `Successfully created and wrote to new file: /path/to/new/file.txt`.
- **Confirmation:** Yes. Shows a diff of changes and asks for user approval
  before writing.""",
        inputs={
            "file_path": {
                "type": "string",
                "description": "The absolute path to the file to write to."
            },
            "content": {
                "type": "string",
                "description": "The content to write into the file."
            }
        },
        output_type="string"
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize WriteFileToolCore with an execution backend.

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
        Write content to a file.

        Args:
            file_path: The absolute path to the file to write to
            content: The content to write into the file

        Returns:
            A ToolOutputModel (TextOutput or ErrorOutput)
        """
        # Ensure path is absolute
        if not Path(file_path).is_absolute():
            file_path = str(Path(self.backend.get_working_directory()) / file_path)

        # Check if file already exists
        file_type = self.backend.file_exists(path=file_path)
        file_existed = file_type is not None

        if file_existed and file_type != FileType.FILE:
            return ErrorOutputModel(
                error=f"Path exists but is not a file: {file_path}",
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

        # Write file
        try:
            self.backend.write_file(file_path=file_path, content=content)
        except Exception as e:
            return ErrorOutputModel(
                error=f"Error writing file: {str(e)}",
                error_type="IOError"
            )

        # Return success message
        if file_existed:
            return TextOutputModel(
                content=f"Successfully overwrote file: {file_path}"
            )
        else:
            return TextOutputModel(
                content=f"Successfully created and wrote to new file: {file_path}"
            )
