"""
Read file tool implementation.

This tool reads and returns the content of a specified file.
Handles text, images (PNG, JPG, GIF, WEBP, SVG, BMP), and PDF files.
"""
import base64
from pathlib import Path

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend, FileType
from prompttodraft.tools.outputs.models import (
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class ReadFileTool:
    """
    Framework-agnostic file reading tool.

    Reads and returns the content of a specified file. Handles text files, images,
    and PDFs. For text files, can read specific line ranges.
    """

    # Supported image and media extensions
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
    PDF_EXTENSIONS = {".pdf"}
    MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS

    metadata = ToolMetadata(
        name="read_file",
        description="Reads and returns the content of a specified file. If the file is large, the content will be truncated. The tool's response will clearly indicate if truncation has occurred. Handles text, images (PNG, JPG, GIF, WEBP, SVG, BMP), and PDF files. For text files, can read specific line ranges using offset and limit.",
        inputs={
            "absolute_path": {
                "type": "string",
                "description": "The absolute path to the file to read (e.g., '/home/user/project/file.txt'). Relative paths are not supported. You must provide an absolute path.",
                "nullable": False,
            },
            "offset": {
                "type": "number",
                "description": "Optional: For text files, the 0-based line number to start reading from. Requires 'limit' to be set. Use for paginating through large files.",
                "nullable": True,
            },
            "limit": {
                "type": "number",
                "description": "Optional: For text files, maximum number of lines to read. Use with 'offset' to paginate through large files. If omitted, reads the entire file (up to a default limit of 2000 lines).",
                "nullable": True,
            },
        },
        output_type="string",
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize ReadFileTool with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    def _get_mime_type(self, file_path: str) -> str:
        """
        Get MIME type for a file based on its extension.

        Args:
            file_path: Path to the file

        Returns:
            MIME type string
        """
        extension = Path(file_path).suffix.lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".svg": "image/svg+xml",
            ".bmp": "image/bmp",
            ".pdf": "application/pdf",
        }
        return mime_types.get(extension, "application/octet-stream")

    def _is_media_file(self, file_path: str) -> bool:
        """
        Check if file is a media file (image or PDF).

        Args:
            file_path: Path to the file

        Returns:
            True if file is a media file
        """
        extension = Path(file_path).suffix.lower()
        return extension in self.MEDIA_EXTENSIONS

    def _is_binary_file(self, content: str) -> bool:
        """
        Check if content appears to be binary by looking for null bytes.

        Args:
            content: File content to check

        Returns:
            True if content appears to be binary
        """
        return "\x00" in content[:8192]  # Check first 8KB

    def execute(
        self,
        absolute_path: str,
        offset: int | None = None,
        limit: int | None = None,
    ) -> ToolOutputModel:
        """
        Execute the read_file tool.

        Args:
            absolute_path: The absolute path to the file to read
            offset: For text files, the 0-based line number to start reading from
            limit: For text files, the maximum number of lines to read

        Returns:
            TextOutputModel with file content or ErrorOutputModel on failure
        """
        # Check if file exists
        file_type = self.backend.file_exists(path=absolute_path)
        if file_type is None:
            return ErrorOutputModel(
                error=f"File does not exist: {absolute_path}",
                error_type="FileNotFoundError",
            )

        if file_type != FileType.FILE:
            return ErrorOutputModel(
                error=f"Path is not a file: {absolute_path}",
                error_type="NotAFileError",
            )

        # Check if this is a media file (image or PDF)
        if self._is_media_file(file_path=absolute_path):
            # Read file as binary and encode to base64
            content = self.backend.read_file(file_path=absolute_path)
            # For media files, we need to read as bytes
            # Since backend returns string, we'll need to encode the path and use a command
            mime_type = self._get_mime_type(file_path=absolute_path)

            # Use execute_command to read binary file
            result = self.backend.execute_command(
                command=f'base64 "{absolute_path}"',
                timeout=30000,
            )

            if result.exit_code != 0:
                return ErrorOutputModel(
                    error=f"Failed to read media file: {result.output}",
                    error_type="ReadError",
                )

            base64_data = result.output.strip()

            return TextOutputModel(
                content=f"[Media File: {Path(absolute_path).name}]\nMIME Type: {mime_type}\nBase64 Data: {base64_data}",
                metadata={"mime_type": mime_type, "is_media": True},
            )

        # Read text file
        content = self.backend.read_file(file_path=absolute_path)

        # Check if it's a binary file
        if self._is_binary_file(content=content):
            return TextOutputModel(
                content=f"Cannot display content of binary file: {absolute_path}",
            )

        # Handle line offset and limit for text files
        if offset is not None or limit is not None:
            lines = content.splitlines()
            total_lines = len(lines)

            start = offset if offset is not None else 0
            end = start + limit if limit is not None else len(lines)

            # Validate offset
            if start >= total_lines:
                return ErrorOutputModel(
                    error=f"Offset {start} is beyond file length ({total_lines} lines)",
                    error_type="InvalidOffsetError",
                )

            selected_lines = lines[start:end]
            content = "\n".join(selected_lines)

            # Add truncation message if content was sliced
            if start > 0 or end < total_lines:
                truncation_msg = f"[File content truncated: showing lines {start + 1}-{min(end, total_lines)} of {total_lines} total lines]\n"
                content = truncation_msg + content
        else:
            # Apply default limit of 2000 lines
            lines = content.splitlines()
            if len(lines) > 2000:
                content = "\n".join(lines[:2000])
                content = f"[File content truncated: showing lines 1-2000 of {len(lines)} total lines]\n" + content

        return TextOutputModel(content=content)
