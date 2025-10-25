"""
read_file tool - Framework-agnostic file reading tool.

Implements the Gemini CLI ReadFile tool specification.
"""
from pathlib import Path
import mimetypes
import base64

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend, FileType
from prompttodraft.tools.outputs.models import (
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


# Supported image formats for base64 encoding
IMAGE_FORMATS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp'}
PDF_FORMAT = '.pdf'


class ReadFileToolCore:
    """
    read_file tool for reading file contents.

    Implements the Gemini CLI ReadFile specification.
    """

    metadata = ToolMetadata(
        name="read_file",
        description="""read_file reads and returns the content of a specified file. This tool handles
text, images (PNG, JPG, GIF, WEBP, SVG, BMP), and PDF files. For text files, it
can read specific line ranges. Other binary file types are generally skipped.

- **Tool name:** `read_file`
- **Display name:** ReadFile
- **Parameters:**
  - `absolute_path` (string, required): The absolute path to the file to read.
  - `offset` (number, optional): For text files, the 0-based line number to
    start reading from. Requires `limit` to be set.
  - `limit` (number, optional): For text files, the maximum number of lines to
    read. If omitted, reads a default maximum (e.g., 2000 lines) or the entire
    file if feasible.
- **Behavior:**
  - For text files: Returns the content. If `offset` and `limit` are used,
    returns only that slice of lines. Indicates if content was truncated due to
    line limits or line length limits.
  - For image and PDF files: Returns the file content as a base64-encoded data
    structure suitable for model consumption.
  - For other binary files: Attempts to identify and skip them, returning a
    message indicating it's a generic binary file.
- **Output:** (`llmContent`):
  - For text files: The file content, potentially prefixed with a truncation
    message.
  - For image/PDF files: An object containing `inlineData` with `mimeType` and
    base64 `data`.
  - For other binary files: A message like
    `Cannot display content of binary file: /path/to/data.bin`.
- **Confirmation:** No.""",
        inputs={
            "absolute_path": {
                "type": "string",
                "description": "The absolute path to the file to read (e.g., '/home/user/project/file.txt'). Relative paths are not supported."
            },
            "offset": {
                "type": "number",
                "description": "For text files, the 0-based line number to start reading from. Requires limit to be set.",
                "nullable": True
            },
            "limit": {
                "type": "number",
                "description": "For text files, the maximum number of lines to read. If omitted, reads a default maximum (2000 lines).",
                "nullable": True
            }
        },
        output_type="string"
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize ReadFileToolCore with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    def execute(
        self,
        absolute_path: str,
        offset: int | None = None,
        limit: int | None = None
    ) -> ToolOutputModel:
        """
        Read a file with validation and formatting.

        Args:
            absolute_path: The absolute path to the file to read
            offset: The line number to start reading from (0-indexed)
            limit: The maximum number of lines to read

        Returns:
            A ToolOutputModel (TextOutput or ErrorOutput)
        """
        # Ensure path is absolute
        path = absolute_path
        if not Path(path).is_absolute():
            path = str(Path(self.backend.get_working_directory()) / path)

        # Check if file exists
        file_type = self.backend.file_exists(path=path)
        if file_type is None:
            return ErrorOutputModel(
                error=f"File '{path}' does not exist",
                error_type="FileNotFoundError"
            )
        if file_type != FileType.FILE:
            return ErrorOutputModel(
                error=f"Path '{path}' is not a file",
                error_type="ValueError"
            )

        # Get file extension and mime type
        file_path_obj = Path(path)
        extension = file_path_obj.suffix.lower()
        mime_type, _ = mimetypes.guess_type(path)

        # Handle image files - return base64 encoded
        if extension in IMAGE_FORMATS:
            return self._handle_image_file(path=path, mime_type=mime_type)

        # Handle PDF files - return base64 encoded
        if extension == PDF_FORMAT:
            return self._handle_pdf_file(path=path)

        # Read file content as text
        try:
            content = self.backend.read_file(file_path=path)
        except Exception as e:
            return ErrorOutputModel(
                error=f"Error reading file: {str(e)}",
                error_type="IOError"
            )

        # Check if it's a binary file (contains null bytes)
        if '\0' in content:
            return TextOutputModel(
                content=f"Cannot display content of binary file: {path}"
            )

        # Apply offset and limit for text files
        lines = content.split('\n')
        total_lines = len(lines)

        # Set defaults
        if offset is None:
            offset = 0
        if limit is None:
            limit = 2000

        # Validate offset
        if offset < 0:
            return ErrorOutputModel(
                error="Offset must be non-negative",
                error_type="ValueError"
            )
        if offset >= total_lines:
            return ErrorOutputModel(
                error=f"Offset {offset} exceeds file length ({total_lines} lines)",
                error_type="ValueError"
            )

        # Slice lines
        end_line = min(offset + limit, total_lines)
        selected_lines = lines[offset:end_line]

        # Truncate long lines (2000 char limit)
        truncated_lines = []
        line_truncated = False
        for line in selected_lines:
            if len(line) > 2000:
                truncated_lines.append(line[:2000] + "...")
                line_truncated = True
            else:
                truncated_lines.append(line)

        result_content = '\n'.join(truncated_lines)

        # Add truncation message if needed
        truncation_msg = []
        if end_line < total_lines or offset > 0:
            truncation_msg.append(
                f"[File content truncated: showing lines {offset + 1}-{end_line} of {total_lines} total lines]"
            )
        if line_truncated:
            truncation_msg.append(
                "[Some lines were truncated at 2000 characters]"
            )

        if truncation_msg:
            result_content = '\n'.join(truncation_msg) + '\n\n' + result_content

        return TextOutputModel(content=result_content)

    def _handle_image_file(self, path: str, mime_type: str | None) -> ToolOutputModel:
        """
        Handle image file by returning base64 encoded data.

        Args:
            path: Path to the image file
            mime_type: MIME type of the image

        Returns:
            TextOutputModel with base64 encoded image data
        """
        try:
            # Read file as binary using execute_command
            result = self.backend.execute_command(
                command=f"base64 '{path}'",
                timeout=30000
            )
            if result.exit_code != 0:
                return ErrorOutputModel(
                    error=f"Error reading image file: {result.output}",
                    error_type="IOError"
                )

            # Clean up base64 output (remove newlines)
            base64_data = result.output.replace('\n', '').replace('\r', '')

            # Determine mime type
            if mime_type is None:
                extension = Path(path).suffix.lower()
                mime_type_map = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp',
                    '.svg': 'image/svg+xml',
                    '.bmp': 'image/bmp'
                }
                mime_type = mime_type_map.get(extension, 'image/jpeg')

            # Return in Gemini inlineData format
            inline_data = {
                "inlineData": {
                    "mimeType": mime_type,
                    "data": base64_data
                }
            }
            return TextOutputModel(content=str(inline_data))

        except Exception as e:
            return ErrorOutputModel(
                error=f"Error processing image file: {str(e)}",
                error_type="IOError"
            )

    def _handle_pdf_file(self, path: str) -> ToolOutputModel:
        """
        Handle PDF file by returning base64 encoded data.

        Args:
            path: Path to the PDF file

        Returns:
            TextOutputModel with base64 encoded PDF data
        """
        try:
            # Read file as binary using execute_command
            result = self.backend.execute_command(
                command=f"base64 '{path}'",
                timeout=60000
            )
            if result.exit_code != 0:
                return ErrorOutputModel(
                    error=f"Error reading PDF file: {result.output}",
                    error_type="IOError"
                )

            # Clean up base64 output (remove newlines)
            base64_data = result.output.replace('\n', '').replace('\r', '')

            # Return in Gemini inlineData format
            inline_data = {
                "inlineData": {
                    "mimeType": "application/pdf",
                    "data": base64_data
                }
            }
            return TextOutputModel(content=str(inline_data))

        except Exception as e:
            return ErrorOutputModel(
                error=f"Error processing PDF file: {str(e)}",
                error_type="IOError"
            )
