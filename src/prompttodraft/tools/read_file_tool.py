"""
Read file tool implementation.

This tool reads and returns the content of a specified file.
Handles text, images (PNG, JPG, GIF, WEBP, SVG, BMP), and PDF files.
"""
from pathlib import Path
from pydantic import BaseModel, Field

from prompttodraft.tools.base_tool import CoreTool
from prompttodraft.backends.execution_backend import FileType


class ReadFileTool(CoreTool):
    """
    Framework-agnostic file reading tool.

    Reads and returns the content of a specified file. Handles text files, images,
    and PDFs. For text files, can read specific line ranges.
    """

    # Supported image and media extensions
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
    PDF_EXTENSIONS = {".pdf"}
    MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS

    name = "read_file"
    description = "Reads and returns the content of a specified file. If the file is large, the content will be truncated. The tool's response will clearly indicate if truncation has occurred. Handles text, images (PNG, JPG, GIF, WEBP, SVG, BMP), and PDF files. For text files, can read specific line ranges using offset and limit."

    class InputModel(BaseModel):
        path: str = Field(description="The absolute path to the file to read (e.g., '/home/user/project/file.txt'). Must be an absolute path.")
        offset: int | None = Field(default=None, description="Optional: For text files, the 0-based line number to start reading from. Requires 'limit' to be set. Use for paginating through large files.")
        limit: int | None = Field(default=None, description="Optional: For text files, maximum number of lines to read. Use with 'offset' to paginate through large files. If omitted, reads the entire file (up to a default limit of 2000 lines).")

    class OutputModel(BaseModel):
        success: bool = Field(description="Whether the file was read successfully")
        file_path: str = Field(description="The path to the file that was read")
        content_type: str = Field(description="Type of content: 'text', 'media', or 'error'")
        message: str = Field(description="Human-readable message about the result")
        # Text file fields
        content: str | None = Field(default=None, description="File content for text files")
        is_truncated: bool = Field(default=False, description="Whether content was truncated")
        total_lines: int | None = Field(default=None, description="Total number of lines in text file")
        # Media file fields
        media_filename: str | None = Field(default=None, description="Filename for media files")
        media_mime_type: str | None = Field(default=None, description="MIME type for media files")
        media_base64: str | None = Field(default=None, description="Base64-encoded media data")
        media_size_bytes: int | None = Field(default=None, description="Size of media file in bytes")
        # Error field
        error: str | None = Field(default=None, description="Error message if read failed")

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

    def execute(self, inputs: InputModel) -> OutputModel:
        """
        Execute the read_file tool.

        Args:
            inputs: Validated input model with path, offset, and limit

        Returns:
            OutputModel with file content or error details
        """
        # Check if file exists
        file_type = self.backend.file_exists(path=inputs.path)
        if file_type is None:
            return self.OutputModel(
                success=False,
                file_path=inputs.path,
                content_type="error",
                message=f"File does not exist: {inputs.path}",
                error=f"File does not exist: {inputs.path}",
            )

        if file_type != FileType.FILE:
            return self.OutputModel(
                success=False,
                file_path=inputs.path,
                content_type="error",
                message=f"Path is not a file: {inputs.path}",
                error=f"Path is not a file: {inputs.path}",
            )

        # Check if this is a media file (image or PDF)
        if self._is_media_file(file_path=inputs.path):
            # Get mime type
            mime_type = self._get_mime_type(file_path=inputs.path)

            # Use execute_command to read binary file and encode to base64
            result = self.backend.execute_command(
                command=f'base64 "{inputs.path}"',
                timeout=30000,
            )

            if result.exit_code != 0:
                return self.OutputModel(
                    success=False,
                    file_path=inputs.path,
                    content_type="error",
                    message=f"Failed to read media file: {result.output}",
                    error=f"Failed to read media file: {result.output}",
                )

            base64_data = result.output.strip()

            # Get file size
            size_result = self.backend.execute_command(
                command=f'wc -c < "{inputs.path}"',
                timeout=5000,
            )
            size_bytes = None
            if size_result.exit_code == 0:
                try:
                    size_bytes = int(size_result.output.strip())
                except ValueError:
                    pass

            filename = Path(inputs.path).name
            return self.OutputModel(
                success=True,
                file_path=inputs.path,
                content_type="media",
                message=f"Successfully read media file: {filename} ({mime_type})",
                media_filename=filename,
                media_mime_type=mime_type,
                media_base64=base64_data,
                media_size_bytes=size_bytes,
            )

        # Read text file
        content = self.backend.read_file(file_path=inputs.path)

        # Check if it's a binary file
        if self._is_binary_file(content=content):
            return self.OutputModel(
                success=True,
                file_path=inputs.path,
                content_type="text",
                message=f"Cannot display content of binary file: {inputs.path}",
                content=f"Cannot display content of binary file: {inputs.path}",
            )

        # Handle line offset and limit for text files
        is_truncated = False
        total_lines_count = None

        if inputs.offset is not None or inputs.limit is not None:
            lines = content.splitlines()
            total_lines_count = len(lines)

            start = inputs.offset if inputs.offset is not None else 0
            end = start + inputs.limit if inputs.limit is not None else len(lines)

            # Validate offset
            if start >= total_lines_count:
                return self.OutputModel(
                    success=False,
                    file_path=inputs.path,
                    content_type="error",
                    message=f"Offset {start} is beyond file length ({total_lines_count} lines)",
                    error=f"Offset {start} is beyond file length ({total_lines_count} lines)",
                )

            selected_lines = lines[start:end]
            content = "\n".join(selected_lines)

            # Add truncation message if content was sliced
            if start > 0 or end < total_lines_count:
                is_truncated = True
                truncation_msg = f"[File content truncated: showing lines {start + 1}-{min(end, total_lines_count)} of {total_lines_count} total lines]\n"
                content = truncation_msg + content
        else:
            # Apply default limit of 2000 lines
            lines = content.splitlines()
            total_lines_count = len(lines)
            if len(lines) > 2000:
                is_truncated = True
                content = "\n".join(lines[:2000])
                content = f"[File content truncated: showing lines 1-2000 of {len(lines)} total lines]\n" + content

        return self.OutputModel(
            success=True,
            file_path=inputs.path,
            content_type="text",
            message=f"Successfully read file: {inputs.path}",
            content=content,
            is_truncated=is_truncated,
            total_lines=total_lines_count,
        )
