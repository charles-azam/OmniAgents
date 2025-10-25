"""
read_many_files tool - Framework-agnostic multi-file reading tool.

Implements the Gemini CLI Multi File Read tool specification.
"""
from pathlib import Path
import fnmatch

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend, FileType
from prompttodraft.tools.outputs.models import (
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


# Supported media formats for base64 encoding
IMAGE_FORMATS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp'}
PDF_FORMAT = '.pdf'
AUDIO_FORMATS = {'.mp3', '.wav'}
VIDEO_FORMATS = {'.mp4', '.mov'}

DEFAULT_EXCLUDES = [
    'node_modules/**', '.git/**', '__pycache__/**', '.venv/**', 'venv/**',
    '.pytest_cache/**', '.mypy_cache/**', '.tox/**', 'dist/**', 'build/**',
    '.eggs/**', '*.egg-info/**', '*.pyc', '*.so', '*.dylib', '*.dll'
]


class ReadManyFilesToolCore:
    """
    read_many_files tool for reading multiple files.

    Implements the Gemini CLI Multi File Read specification.
    """

    metadata = ToolMetadata(
        name="read_many_files",
        description="""Use `read_many_files` to read content from multiple files specified by paths or
glob patterns. The behavior of this tool depends on the provided files:

- For text files, this tool concatenates their content into a single string.
- For image (e.g., PNG, JPEG), PDF, audio (MP3, WAV), and video (MP4, MOV)
  files, it reads and returns them as base64-encoded data, provided they are
  explicitly requested by name or extension.

`read_many_files` can be used to perform tasks such as getting an overview of a
codebase, finding where specific functionality is implemented, reviewing
documentation, or gathering context from multiple configuration files.

**Note:** `read_many_files` looks for files following the provided paths or glob
patterns. A directory path such as `"/docs"` will return an empty result; the
tool requires a pattern such as `"/docs/*"` or `"/docs/*.md"` to identify the
relevant files.

### Arguments

`read_many_files` takes the following arguments:

- `paths` (list[string], required): An array of glob patterns or paths relative
  to the tool's target directory (e.g., `["src/**/*.ts"]`,
  `["README.md", "docs/*", "assets/logo.png"]`).
- `exclude` (list[string], optional): Glob patterns for files/directories to
  exclude (e.g., `["**/*.log", "temp/"]`). These are added to default excludes
  if `useDefaultExcludes` is true.
- `include` (list[string], optional): Additional glob patterns to include. These
  are merged with `paths` (e.g., `["*.test.ts"]`).
- `recursive` (boolean, optional): Whether to search recursively. Defaults to `true`.
- `useDefaultExcludes` (boolean, optional): Whether to apply default exclusion
  patterns (e.g., `node_modules`, `.git`). Defaults to `true`.
- `file_filtering_options` (object, optional): Whether to respect ignore
  patterns from .gitignore or .geminiignore.
  - `respect_git_ignore` (boolean, optional): Whether to respect `.gitignore`
    patterns. Defaults to `true`.
  - `respect_gemini_ignore` (boolean, optional): Whether to respect
    `.geminiignore` patterns. Defaults to `true`.""",
        inputs={
            "paths": {
                "type": "array",
                "description": "An array of glob patterns or paths (e.g., [\"src/**/*.ts\"], [\"README.md\"])",
                "items": {"type": "string"}
            },
            "exclude": {
                "type": "array",
                "description": "Glob patterns for files/directories to exclude (e.g., [\"**/*.log\"])",
                "items": {"type": "string"},
                "nullable": True
            },
            "include": {
                "type": "array",
                "description": "Additional glob patterns to include (e.g., [\"*.test.ts\"])",
                "items": {"type": "string"},
                "nullable": True
            },
            "recursive": {
                "type": "boolean",
                "description": "Whether to search recursively. Defaults to true.",
                "nullable": True
            },
            "useDefaultExcludes": {
                "type": "boolean",
                "description": "Whether to apply default exclusion patterns. Defaults to true.",
                "nullable": True
            },
            "file_filtering_options": {
                "type": "object",
                "description": "Optional: Whether to respect ignore patterns from .gitignore or .geminiignore",
                "properties": {
                    "respect_git_ignore": {
                        "type": "boolean",
                        "description": "Optional: Whether to respect .gitignore patterns. Defaults to true."
                    },
                    "respect_gemini_ignore": {
                        "type": "boolean",
                        "description": "Optional: Whether to respect .geminiignore patterns. Defaults to true."
                    }
                },
                "nullable": True
            }
        },
        output_type="string"
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize ReadManyFilesToolCore with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    def execute(
        self,
        paths: list[str],
        exclude: list[str] | None = None,
        include: list[str] | None = None,
        recursive: bool = True,
        useDefaultExcludes: bool = True,
        file_filtering_options: dict[str, bool] | None = None
    ) -> ToolOutputModel:
        """
        Read multiple files matching the given patterns.

        Args:
            paths: List of glob patterns or file paths
            exclude: Optional list of patterns to exclude
            include: Optional list of additional patterns to include
            recursive: Whether to search recursively
            useDefaultExcludes: Whether to apply default excludes
            file_filtering_options: Optional dict with respect_git_ignore and respect_gemini_ignore

        Returns:
            A ToolOutputModel with concatenated file contents
        """
        # Extract filtering options with defaults
        respect_git_ignore = True
        respect_gemini_ignore = True
        if file_filtering_options:
            respect_git_ignore = file_filtering_options.get('respect_git_ignore', True)
            respect_gemini_ignore = file_filtering_options.get('respect_gemini_ignore', True)
        # Merge paths and include patterns
        all_patterns = list(paths)
        if include:
            all_patterns.extend(include)

        # Build exclude patterns
        exclude_patterns = []
        if useDefaultExcludes:
            exclude_patterns.extend(DEFAULT_EXCLUDES)
        if exclude:
            exclude_patterns.extend(exclude)

        # Find matching files
        working_dir = self.backend.get_working_directory()
        matching_files = []

        for pattern in all_patterns:
            # Handle absolute paths and relative patterns
            if Path(pattern).is_absolute():
                search_path = str(Path(pattern).parent)
                pattern_name = Path(pattern).name
            else:
                search_path = working_dir
                pattern_name = pattern

            # Use backend glob_files
            try:
                found_files = self.backend.glob_files(
                    pattern=pattern_name,
                    path=search_path
                )
                matching_files.extend(found_files)
            except Exception:
                # Pattern didn't match any files, continue
                continue

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for f in matching_files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)

        # Apply exclude patterns
        filtered_files = []
        for file_path in unique_files:
            if self._should_exclude(
                file_path=file_path,
                exclude_patterns=exclude_patterns,
                working_dir=working_dir
            ):
                continue
            filtered_files.append(file_path)

        # Apply gitignore filtering
        if respect_git_ignore:
            filtered_files = self._filter_git_ignored(
                files=filtered_files,
                working_dir=working_dir
            )

        # If no files found
        if not filtered_files:
            return TextOutputModel(
                content="No files found matching the specified patterns."
            )

        # Read and concatenate file contents
        contents = []
        for file_path in filtered_files:
            content = self._read_file_content(file_path=file_path)
            if content:
                # Add separator
                relative_path = Path(file_path).relative_to(working_dir)
                contents.append(f"--- {relative_path} ---")
                contents.append(content)

        # Add end marker
        contents.append("--- End of content ---")

        return TextOutputModel(content="\n".join(contents))

    def _should_exclude(
        self,
        file_path: str,
        exclude_patterns: list[str],
        working_dir: str
    ) -> bool:
        """
        Check if file should be excluded based on patterns.

        Args:
            file_path: File path to check
            exclude_patterns: List of exclude patterns
            working_dir: Working directory for relative paths

        Returns:
            True if file should be excluded
        """
        try:
            relative_path = str(Path(file_path).relative_to(working_dir))
        except ValueError:
            relative_path = file_path

        for pattern in exclude_patterns:
            if fnmatch.fnmatch(relative_path, pattern):
                return True
            # Also check filename alone
            if fnmatch.fnmatch(Path(file_path).name, pattern):
                return True

        return False

    def _filter_git_ignored(
        self,
        files: list[str],
        working_dir: str
    ) -> list[str]:
        """
        Filter out files that are git-ignored.

        Args:
            files: List of file paths
            working_dir: Working directory

        Returns:
            Filtered list of files
        """
        try:
            # Check if we're in a git repository
            result = self.backend.execute_command(
                command=f"cd '{working_dir}' && git rev-parse --git-dir",
                timeout=5000
            )
            if result.exit_code != 0:
                return files  # Not a git repo

            # Check each file
            filtered_files = []
            for file_path in files:
                try:
                    rel_path = Path(file_path).relative_to(working_dir)
                except ValueError:
                    filtered_files.append(file_path)
                    continue

                result = self.backend.execute_command(
                    command=f"cd '{working_dir}' && git check-ignore '{rel_path}'",
                    timeout=5000
                )
                # Exit code 0 means ignored, so skip it
                if result.exit_code != 0:
                    filtered_files.append(file_path)

            return filtered_files

        except Exception:
            return files

    def _read_file_content(self, file_path: str) -> str | None:
        """
        Read file content, handling text, images, PDFs, etc.

        Args:
            file_path: Path to the file

        Returns:
            File content as string, or None if binary/unreadable
        """
        extension = Path(file_path).suffix.lower()

        # Handle images, PDFs, audio, video with base64
        if extension in IMAGE_FORMATS or extension == PDF_FORMAT or \
           extension in AUDIO_FORMATS or extension in VIDEO_FORMATS:
            return self._read_as_base64(file_path=file_path, extension=extension)

        # Read as text
        try:
            content = self.backend.read_file(file_path=file_path)

            # Check for binary file (null bytes)
            if '\0' in content:
                return f"[Binary file skipped: {Path(file_path).name}]"

            return content

        except Exception:
            return f"[Error reading file: {Path(file_path).name}]"

    def _read_as_base64(self, file_path: str, extension: str) -> str:
        """
        Read file as base64 encoded data.

        Args:
            file_path: Path to the file
            extension: File extension

        Returns:
            Base64 encoded string with mime type
        """
        try:
            # Use base64 command
            result = self.backend.execute_command(
                command=f"base64 '{file_path}'",
                timeout=60000
            )
            if result.exit_code != 0:
                return f"[Error encoding file: {Path(file_path).name}]"

            # Clean up base64 output
            base64_data = result.output.replace('\n', '').replace('\r', '')

            # Determine mime type
            mime_type_map = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.svg': 'image/svg+xml',
                '.bmp': 'image/bmp',
                '.pdf': 'application/pdf',
                '.mp3': 'audio/mpeg',
                '.wav': 'audio/wav',
                '.mp4': 'video/mp4',
                '.mov': 'video/quicktime'
            }
            mime_type = mime_type_map.get(extension, 'application/octet-stream')

            # Return in inline data format
            return str({
                "inlineData": {
                    "mimeType": mime_type,
                    "data": base64_data
                }
            })

        except Exception:
            return f"[Error encoding file: {Path(file_path).name}]"
