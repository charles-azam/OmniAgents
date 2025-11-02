"""
Read many files tool implementation.

This tool reads content from multiple files specified by paths or glob patterns.
"""
from pathlib import Path

from prompttodraft.agent.core.base_tool import CoreTool
from prompttodraft.agent.core.metadata import ToolMetadata
from prompttodraft.agent.backends.execution_backend import ExecutionBackend, FileType
from prompttodraft.agent.outputs.models import (
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class ReadManyFilesTool(CoreTool):
    """
    Framework-agnostic multi-file reading tool.

    Reads content from multiple files specified by paths or glob patterns.
    For text files, concatenates their content. For image/PDF files,
    returns them as base64-encoded data.
    """

    # Supported media extensions
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
    PDF_EXTENSIONS = {".pdf"}
    AUDIO_EXTENSIONS = {".mp3", ".wav"}
    VIDEO_EXTENSIONS = {".mp4", ".mov"}
    MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS | AUDIO_EXTENSIONS | VIDEO_EXTENSIONS

    # Default exclude patterns
    DEFAULT_EXCLUDES = [
        "node_modules/**",
        ".git/**",
        ".venv/**",
        "__pycache__/**",
        "*.pyc",
        ".DS_Store",
    ]

    metadata = ToolMetadata(
        name="read_many_files",
        description="Reads content from multiple files specified by paths or glob patterns. The behavior depends on the provided files: for text files, concatenates their content into a single string; for image (PNG, JPEG), PDF, audio (MP3, WAV), and video (MP4, MOV) files, reads and returns them as base64-encoded data if explicitly requested by name or extension. Can be used to get an overview of a codebase, find where specific functionality is implemented, review documentation, or gather context from multiple configuration files.",
        inputs={
            "paths": {
                "type": "array",
                "description": "An array of glob patterns or paths relative to the tool's target directory (e.g., ['src/**/*.ts'], ['README.md', 'docs/*', 'assets/logo.png']). Note: A directory path such as '/docs' will return an empty result; use a pattern such as '/docs/*' or '/docs/*.md'.",
                "items": {"type": "string"},
                "nullable": False,
            },
            "exclude": {
                "type": "array",
                "description": "Optional: Glob patterns for files/directories to exclude (e.g., ['**/*.log', 'temp/']). These are added to default excludes if useDefaultExcludes is true.",
                "items": {"type": "string"},
                "nullable": True,
            },
            "include": {
                "type": "array",
                "description": "Optional: Additional glob patterns to include. These are merged with paths (e.g., ['*.test.ts'] to specifically add test files if they were broadly excluded, or ['images/*.jpg'] to include specific image types).",
                "items": {"type": "string"},
                "nullable": True,
            },
            "recursive": {
                "type": "boolean",
                "description": "Optional: Whether to search recursively. This is primarily controlled by ** in glob patterns. Defaults to true.",
                "nullable": True,
            },
            "useDefaultExcludes": {
                "type": "boolean",
                "description": "Optional: Whether to apply a list of default exclusion patterns (e.g., node_modules, .git, non-image/PDF binary files). Defaults to true.",
                "nullable": True,
            },
            "respect_git_ignore": {
                "type": "boolean",
                "description": "Optional: Whether to respect .gitignore patterns when finding files. Defaults to true.",
                "nullable": True,
            },
        },
        output_type="string",
    )

    def _is_media_file(self, file_path: str) -> bool:
        """
        Check if file is a media file.

        Args:
            file_path: Path to the file

        Returns:
            True if file is a media file
        """
        extension = Path(file_path).suffix.lower()
        return extension in self.MEDIA_EXTENSIONS

    def _is_binary_file(self, content: str) -> bool:
        """
        Check if content appears to be binary.

        Args:
            content: File content to check

        Returns:
            True if content appears to be binary
        """
        return "\x00" in content[:8192]

    def _is_git_repository(self) -> bool:
        """
        Check if the working directory is a git repository.

        Returns:
            True if in a git repository, False otherwise
        """
        try:
            result = self.backend.execute_command(
                command="git rev-parse --is-inside-work-tree",
                timeout=2000  # 2 seconds
            )
            return result.exit_code == 0 and result.output.strip() == "true"
        except Exception:
            return False

    def _should_ignore_by_git(self, file_path: str) -> bool:
        """
        Check if a file should be ignored according to .gitignore.

        Args:
            file_path: Absolute path to the file to check

        Returns:
            True if the file should be ignored, False otherwise
        """
        try:
            # git check-ignore returns exit code 0 if the path is ignored
            result = self.backend.execute_command(
                command=f"git check-ignore -q '{file_path}'",
                timeout=2000  # 2 seconds
            )
            return result.exit_code == 0
        except Exception:
            return False

    def _should_exclude(self, file_path: str, exclude_patterns: list[str]) -> bool:
        """
        Check if file should be excluded based on patterns.

        Args:
            file_path: Path to check
            exclude_patterns: List of glob patterns to exclude

        Returns:
            True if file should be excluded
        """
        from fnmatch import fnmatch

        path_str = str(file_path)
        for pattern in exclude_patterns:
            if fnmatch(path_str, pattern) or fnmatch(Path(path_str).name, pattern):
                return True
        return False

    def execute(
        self,
        paths: list[str],
        exclude: list[str] | None = None,
        include: list[str] | None = None,
        recursive: bool = True,
        useDefaultExcludes: bool = True,
        respect_git_ignore: bool = True,
    ) -> ToolOutputModel:
        """
        Execute the read_many_files tool.

        Args:
            paths: Array of glob patterns or paths
            exclude: Optional glob patterns to exclude
            include: Optional additional glob patterns to include
            recursive: Whether to search recursively
            useDefaultExcludes: Whether to apply default exclusion patterns
            respect_git_ignore: Whether to respect .gitignore patterns

        Returns:
            TextOutputModel with concatenated file contents or ErrorOutputModel on failure
        """
        # Combine paths and include patterns
        all_patterns = list(paths)
        if include:
            all_patterns.extend(include)

        # Build exclude patterns
        exclude_patterns = []
        if useDefaultExcludes:
            exclude_patterns.extend(self.DEFAULT_EXCLUDES)
        if exclude:
            exclude_patterns.extend(exclude)

        # Collect all matching files
        all_files = []
        working_dir = self.backend.get_working_directory()

        for pattern in all_patterns:
            # Use glob to find matching files
            matched_files = self.backend.glob_files(pattern=pattern, path=working_dir)
            all_files.extend(matched_files)

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for f in all_files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)

        # Apply exclude patterns
        filtered_files = [
            f for f in unique_files if not self._should_exclude(file_path=f, exclude_patterns=exclude_patterns)
        ]

        # Apply gitignore filtering if requested
        if respect_git_ignore and self._is_git_repository():
            filtered_files = [
                f for f in filtered_files if not self._should_ignore_by_git(file_path=f)
            ]

        if not filtered_files:
            return TextOutputModel(content="No files matched the specified patterns.")

        # Read and concatenate file contents
        output_parts = []

        for file_path in filtered_files:
            # Check if file exists and is a file
            file_type = self.backend.file_exists(path=file_path)
            if file_type != FileType.FILE:
                continue

            # Add separator with file path
            output_parts.append(f"--- {file_path} ---")

            # Check if it's a media file
            if self._is_media_file(file_path=file_path):
                # Read as base64
                result = self.backend.execute_command(
                    command=f'base64 "{file_path}"',
                    timeout=30000,
                )

                if result.exit_code == 0:
                    mime_type = self._get_mime_type(file_path=file_path)
                    output_parts.append(f"[Media File: {Path(file_path).name}]")
                    output_parts.append(f"MIME Type: {mime_type}")
                    output_parts.append(f"Base64 Data: {result.output.strip()}")
                else:
                    output_parts.append(f"[Error reading media file: {file_path}]")
            else:
                # Read as text
                content = self.backend.read_file(file_path=file_path)

                # Check if binary
                if self._is_binary_file(content=content):
                    output_parts.append(f"[Skipped binary file: {file_path}]")
                else:
                    output_parts.append(content)

            output_parts.append("")  # Empty line after each file

        output_parts.append("--- End of content ---")

        return TextOutputModel(content="\n".join(output_parts))

    def _get_mime_type(self, file_path: str) -> str:
        """
        Get MIME type for a file.

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
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
        }
        return mime_types.get(extension, "application/octet-stream")
