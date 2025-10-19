"""
ViewToolCore - Framework-agnostic file reading tool.

Extracted from smolcc/tools/view_tool.py with business logic separated from execution.
"""
import os
import mimetypes

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend
from prompttodraft.tools.outputs.models import (
    CodeOutputModel,
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)

# File extension to language mapping (from view_tool.py:23-100)
LANGUAGE_MAP = {
    # Python files
    '.py': 'python',
    '.pyx': 'python',
    '.pyw': 'python',
    # JavaScript/TypeScript files
    '.js': 'javascript',
    '.jsx': 'jsx',
    '.ts': 'typescript',
    '.tsx': 'tsx',
    # Web files
    '.html': 'html',
    '.htm': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.sass': 'sass',
    '.less': 'less',
    # Data files
    '.json': 'json',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.toml': 'toml',
    '.xml': 'xml',
    # Shell scripts
    '.sh': 'bash',
    '.bash': 'bash',
    '.zsh': 'bash',
    '.fish': 'fish',
    # C-family languages
    '.c': 'c',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.h': 'c',
    '.hpp': 'cpp',
    '.cs': 'csharp',
    '.java': 'java',
    # Ruby
    '.rb': 'ruby',
    '.erb': 'erb',
    # Go
    '.go': 'go',
    # Rust
    '.rs': 'rust',
    # Swift
    '.swift': 'swift',
    # Markdown
    '.md': 'markdown',
    '.markdown': 'markdown',
    # Structured Config
    '.ini': 'ini',
    '.cfg': 'ini',
    '.conf': 'ini',
    # Other languages
    '.php': 'php',
    '.pl': 'perl',
    '.kotlin': 'kotlin',
    '.kt': 'kotlin',
    '.lua': 'lua',
    '.sql': 'sql',
    '.r': 'r',
    '.dart': 'dart',
    '.scala': 'scala',
    '.elm': 'elm',
    '.clj': 'clojure',
    '.ex': 'elixir',
    '.exs': 'elixir',
    '.hs': 'haskell',
    '.fs': 'fsharp',
    '.fsx': 'fsharp',
    '.lisp': 'lisp',
    '.matlab': 'matlab',
    '.m': 'matlab',
    '.asm': 'asm6502',
    '.bat': 'batch',
    '.ps1': 'powershell',
    '.dockerfile': 'dockerfile',
}


class ViewToolCore:
    """
    Framework-agnostic file reading tool.

    Extracted from smolcc/tools/view_tool.py:103-301
    """

    # Metadata (from view_tool.py:108-115)
    metadata = ToolMetadata(
        name="View",
        description="Retrieves a file's contents from the local filesystem. The **file_path** parameter must be an absolute path (relative paths are not allowed). By default, the tool returns up to 2,000 lines starting at the top of the file. You may optionally specify a line offset and a maximum number of lines—handy for extremely long files—but when feasible, omit these options to load the entire file. Any line longer than 2,000 characters will be truncated. If the target is an image, the tool will render it for you. For Jupyter notebooks (`.ipynb`), use **ReadNotebook** instead.",
        inputs={
            "file_path": {
                "type": "string",
                "description": "The absolute path to the file to read"
            },
            "offset": {
                "type": "number",
                "description": "The line number to start reading from. Only provide if the file is too large to read at once",
                "nullable": True
            },
            "limit": {
                "type": "number",
                "description": "The number of lines to read. Only provide if the file is too large to read at once.",
                "nullable": True
            }
        },
        output_type="string"
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize ViewToolCore with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    def execute(
        self,
        file_path: str,
        offset: int | None = None,
        limit: int | None = None
    ) -> ToolOutputModel:
        """
        Read a file with validation and formatting (from view_tool.py:117-222).

        Args:
            file_path: The absolute path to the file to read
            offset: The line number to start reading from (0-indexed)
            limit: The maximum number of lines to read

        Returns:
            A ToolOutputModel (CodeOutput or TextOutput or ErrorOutput)
        """
        # Make sure path is absolute
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)

        # Check if file exists
        if not self.backend.file_exists(path=file_path):
            return ErrorOutputModel(error=f"File '{file_path}' does not exist", error_type="FileNotFoundError")
        if not self.backend.is_file(path=file_path):
            return ErrorOutputModel(error=f"Path '{file_path}' is not a file", error_type="ValueError")

        # Check if this is an image file
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type.startswith('image/'):
            return TextOutputModel(
                content=f"This is an image file ({mime_type}). Images are supported in certain environments but not in a text-only interface."
            )

        # Handle Jupyter notebook files
        if file_path.lower().endswith('.ipynb'):
            return TextOutputModel(
                content="This is a Jupyter notebook file. Please use the ReadNotebook tool instead to view it properly."
            )

        # Set defaults for offset and limit
        if offset is None:
            offset = 0
        if limit is None:
            limit = 2000

        # Read file via backend
        try:
            result = self.backend.read_file(file_path=file_path, offset=offset, limit=limit)
        except ValueError as e:
            return TextOutputModel(content=str(e))
        except Exception as e:
            return ErrorOutputModel(error=f"Error reading file: {str(e)}", error_type="IOError")

        # Return result as CodeOutput if the file is code, otherwise as TextOutput
        if self._is_code_file(file_path=file_path):
            language = self._get_language_for_file(file_path=file_path)
            return CodeOutputModel(content=result, language=language, line_numbers=False)
        else:
            return TextOutputModel(content=result)

    def _is_code_file(self, file_path: str) -> bool:
        """
        Determine if a file is a code file (from view_tool.py:241-273).

        Args:
            file_path: Path to the file

        Returns:
            True if the file appears to be code, False otherwise
        """
        # Check extension first
        ext = os.path.splitext(file_path)[1].lower()
        if ext in LANGUAGE_MAP:
            return True

        # Check some common code patterns if extension doesn't match
        try:
            # Read first 10 lines from backend
            first_content = self.backend.read_file(file_path=file_path, offset=0, limit=10)

            # Look for patterns that suggest code
            code_indicators = [
                "import ", "from ", "def ", "class ", "function ",
                "var ", "let ", "const ", "#include", "package ",
                "using ", "public class", "pragma", "{", "<html", "<?php"
            ]

            if any(indicator in first_content for indicator in code_indicators):
                return True
        except:
            pass  # If we can't read the file, assume it's not code

        return False

    def _get_language_for_file(self, file_path: str) -> str:
        """
        Get the language for syntax highlighting (from view_tool.py:275-296).

        Args:
            file_path: Path to the file

        Returns:
            Language identifier for syntax highlighting
        """
        ext = os.path.splitext(file_path)[1].lower()

        # Check for special cases first
        if file_path.lower().endswith('dockerfile'):
            return 'dockerfile'

        # Use the extension mapping
        if ext in LANGUAGE_MAP:
            return LANGUAGE_MAP[ext]

        # Default to plain text
        return 'text'
