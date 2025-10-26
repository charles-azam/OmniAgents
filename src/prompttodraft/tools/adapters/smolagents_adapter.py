"""
Smolagents framework adapter.

This module provides adapters to convert core tools into smolagents Tool format.
"""
from smolagents import Tool

from prompttodraft.tools.core.write_file_tool import WriteFileTool
from prompttodraft.tools.core.read_file_tool import ReadFileTool
from prompttodraft.tools.core.list_directory_tool import ListDirectoryTool
from prompttodraft.tools.core.glob_tool import GlobTool
from prompttodraft.tools.core.search_file_content_tool import SearchFileContentTool
from prompttodraft.tools.core.replace_tool import ReplaceTool
from prompttodraft.tools.core.run_shell_command_tool import RunShellCommandTool
from prompttodraft.tools.core.read_many_files_tool import ReadManyFilesTool
from prompttodraft.tools.core.save_memory_tool import SaveMemoryTool


class SmolagentsToolAdapter(Tool):
    """
    Base adapter for converting Core tools to smolagents format.

    This adapter wraps a core tool and exposes it as a smolagents Tool.

    Note: Subclasses must define their own name, description, inputs, and forward() method.
    """

    def __init__(self, core_tool):
        """
        Initialize the adapter with a core tool.

        Args:
            core_tool: A core tool instance
        """
        self.core = core_tool
        super().__init__()


# Specific adapters for each tool type
class SmolagentsWriteFileTool(SmolagentsToolAdapter):
    """Smolagents adapter for WriteFileTool."""

    name = "write_file"
    description = "Writes content to a specified file. If the file exists, it will be overwritten. If the file doesn't exist, it (and any necessary parent directories) will be created."
    inputs = {
        "file_path": {"type": "string", "description": "The absolute path to the file to write to"},
        "content": {"type": "string", "description": "The content to write into the file"},
    }
    output_type = "string"

    def __init__(self, core: WriteFileTool):
        super().__init__(core_tool=core)

    def forward(self, file_path: str, content: str):
        """Create or overwrite a file."""
        return str(self.core.execute(file_path=file_path, content=content))


class SmolagentsReadFileTool(SmolagentsToolAdapter):
    """Smolagents adapter for ReadFileTool."""

    name = "read_file"
    description = "Reads the contents of a file, optionally limiting output with offset and line count."
    inputs = {
        "path": {"type": "string", "description": "The absolute path to the file to read"},
        "offset": {"type": "integer", "description": "Optional line offset to start reading from (0-indexed)", "nullable": True},
        "limit": {"type": "integer", "description": "Optional maximum number of lines to read", "nullable": True},
    }
    output_type = "string"

    def __init__(self, core: ReadFileTool):
        super().__init__(core_tool=core)

    def forward(self, path: str, offset: int | None = None, limit: int | None = None):
        """Read a file with optional offset and limit."""
        return str(self.core.execute(path=path, offset=offset, limit=limit))


class SmolagentsListDirectoryTool(SmolagentsToolAdapter):
    """Smolagents adapter for ListDirectoryTool."""

    name = "list_directory"
    description = "Lists the contents of a directory with optional filtering and gitignore support."
    inputs = {
        "path": {"type": "string", "description": "The absolute path to the directory to list"},
        "ignore": {"type": "array", "description": "Optional list of glob patterns to ignore", "nullable": True},
        "respect_git_ignore": {"type": "boolean", "description": "Whether to respect .gitignore patterns", "nullable": True},
    }
    output_type = "string"

    def __init__(self, core: ListDirectoryTool):
        super().__init__(core_tool=core)

    def forward(self, path: str, ignore: list[str] | None = None, respect_git_ignore: bool = True):
        """List directory contents."""
        return str(self.core.execute(path=path, ignore=ignore, respect_git_ignore=respect_git_ignore))


class SmolagentsGlobTool(SmolagentsToolAdapter):
    """Smolagents adapter for GlobTool."""

    name = "glob"
    description = "Finds files matching a glob pattern, returning absolute paths sorted by modification time."
    inputs = {
        "pattern": {"type": "string", "description": "The glob pattern to match (e.g., '**/*.py', 'docs/*.md')"},
        "path": {"type": "string", "description": "Optional directory to search within", "nullable": True},
        "case_sensitive": {"type": "boolean", "description": "Whether the search should be case-sensitive", "nullable": True},
        "respect_git_ignore": {"type": "boolean", "description": "Whether to respect .gitignore patterns", "nullable": True},
    }
    output_type = "string"

    def __init__(self, core: GlobTool):
        super().__init__(core_tool=core)

    def forward(self, pattern: str, path: str | None = None, case_sensitive: bool = False, respect_git_ignore: bool = True):
        """Find files matching a glob pattern."""
        return str(self.core.execute(pattern=pattern, path=path, case_sensitive=case_sensitive, respect_git_ignore=respect_git_ignore))


class SmolagentsSearchFileContentTool(SmolagentsToolAdapter):
    """Smolagents adapter for SearchFileContentTool."""

    name = "search_file_content"
    description = "Searches for a pattern in file contents using grep/git grep."
    inputs = {
        "pattern": {"type": "string", "description": "The search pattern (regex supported)"},
        "path": {"type": "string", "description": "Optional directory to search in", "nullable": True},
        "include": {"type": "string", "description": "Optional glob pattern to filter files (e.g., '*.py')", "nullable": True},
    }
    output_type = "string"

    def __init__(self, core: SearchFileContentTool):
        super().__init__(core_tool=core)

    def forward(self, pattern: str, path: str | None = None, include: str | None = None):
        """Search for a pattern in file contents."""
        return str(self.core.execute(pattern=pattern, path=path, include=include))


class SmolagentsReplaceTool(SmolagentsToolAdapter):
    """Smolagents adapter for ReplaceTool."""

    name = "replace"
    description = "Replaces exact text matches in a file with new text, with safety checks."
    inputs = {
        "file_path": {"type": "string", "description": "The absolute path to the file to modify"},
        "old_string": {"type": "string", "description": "The exact text to replace"},
        "new_string": {"type": "string", "description": "The new text to insert"},
        "expected_replacements": {"type": "integer", "description": "Optional expected number of replacements for validation", "nullable": True},
    }
    output_type = "string"

    def __init__(self, core: ReplaceTool):
        super().__init__(core_tool=core)

    def forward(self, file_path: str, old_string: str, new_string: str, expected_replacements: int | None = None):
        """Replace text in a file."""
        return str(self.core.execute(file_path=file_path, old_string=old_string, new_string=new_string, expected_replacements=expected_replacements))


class SmolagentsRunShellCommandTool(SmolagentsToolAdapter):
    """Smolagents adapter for RunShellCommandTool."""

    name = "run_shell_command"
    description = "Executes a shell command in the specified directory."
    inputs = {
        "command": {"type": "string", "description": "The shell command to execute"},
        "directory": {"type": "string", "description": "Optional directory to run the command in", "nullable": True},
        "description": {"type": "string", "description": "Optional description of what the command does", "nullable": True},
    }
    output_type = "string"

    def __init__(self, core: RunShellCommandTool):
        super().__init__(core_tool=core)

    def forward(self, command: str, directory: str | None = None, description: str | None = None):
        """Execute a shell command."""
        return str(self.core.execute(command=command, directory=directory, description=description))


class SmolagentsReadManyFilesTool(SmolagentsToolAdapter):
    """Smolagents adapter for ReadManyFilesTool."""

    name = "read_many_files"
    description = "Reads multiple files at once, with filtering and exclusion support."
    inputs = {
        "paths": {"type": "array", "description": "List of file paths or glob patterns to read"},
        "include": {"type": "array", "description": "Optional additional glob patterns to include", "nullable": True},
        "exclude": {"type": "array", "description": "Optional glob patterns to exclude", "nullable": True},
        "useDefaultExcludes": {"type": "boolean", "description": "Whether to use default exclusions (node_modules, etc.)", "nullable": True},
        "respect_git_ignore": {"type": "boolean", "description": "Whether to respect .gitignore patterns", "nullable": True},
    }
    output_type = "string"

    def __init__(self, core: ReadManyFilesTool):
        super().__init__(core_tool=core)

    def forward(self, paths: list[str], include: list[str] | None = None, exclude: list[str] | None = None, useDefaultExcludes: bool = True, respect_git_ignore: bool = True):
        """Read multiple files at once."""
        return str(self.core.execute(paths=paths, include=include, exclude=exclude, useDefaultExcludes=useDefaultExcludes, respect_git_ignore=respect_git_ignore))


class SmolagentsSaveMemoryTool(SmolagentsToolAdapter):
    """Smolagents adapter for SaveMemoryTool."""

    name = "save_memory"
    description = "Saves a fact or preference to the memory file (.gemini/GEMINI.md)."
    inputs = {
        "fact": {"type": "string", "description": "The fact or preference to remember"},
    }
    output_type = "string"

    def __init__(self, core: SaveMemoryTool):
        super().__init__(core_tool=core)

    def forward(self, fact: str):
        """Save a fact to memory."""
        return str(self.core.execute(fact=fact))
