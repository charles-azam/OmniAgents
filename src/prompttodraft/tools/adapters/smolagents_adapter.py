"""
Smolagents framework adapter.

This module provides adapters to convert core tools into smolagents Tool format.
"""
from smolagents import Tool

from prompttodraft.tools.core.bash_tool_core import BashToolCore
from prompttodraft.tools.core.view_tool_core import ViewToolCore
from prompttodraft.tools.core.edit_tool_core import EditToolCore
from prompttodraft.tools.core.replace_tool_core import ReplaceToolCore
from prompttodraft.tools.core.glob_tool_core import GlobToolCore
from prompttodraft.tools.core.grep_tool_core import GrepToolCore
from prompttodraft.tools.core.ls_tool_core import LSToolCore
from prompttodraft.tools.core.user_input_tool_core import UserInputToolCore


class SmolagentsToolAdapter(Tool):
    """
    Base adapter for converting Core tools to smolagents format.

    This adapter wraps a core tool and exposes it as a smolagents Tool.

    Note: Subclasses must define their own forward() method with the correct signature
    to match smolagents validation requirements.
    """

    def __init__(self, core_tool):
        """
        Initialize the adapter with a core tool.

        Args:
            core_tool: A core tool instance (e.g., BashToolCore, ViewToolCore)
        """
        super().__init__()
        self.core = core_tool

        # Copy metadata from core tool to smolagents format
        self.name = core_tool.metadata.name
        self.description = core_tool.metadata.description
        self.inputs = core_tool.metadata.inputs
        self.output_type = core_tool.metadata.output_type


# Specific adapters for each tool type
class SmolagentsBashTool(SmolagentsToolAdapter):
    """Smolagents adapter for BashToolCore."""

    def __init__(self, core: BashToolCore):
        super().__init__(core_tool=core)

    def forward(self, command: str, timeout: int | None = None):
        """Execute bash command."""
        return str(self.core.execute(command=command, timeout=timeout))


class SmolagentsViewTool(SmolagentsToolAdapter):
    """Smolagents adapter for ViewToolCore."""

    def __init__(self, core: ViewToolCore):
        super().__init__(core_tool=core)

    def forward(self, file_path: str, offset: int | None = None, limit: int | None = None):
        """Read a file."""
        return str(self.core.execute(file_path=file_path, offset=offset, limit=limit))


class SmolagentsEditTool(SmolagentsToolAdapter):
    """Smolagents adapter for EditToolCore."""

    def __init__(self, core: EditToolCore):
        super().__init__(core_tool=core)

    def forward(self, file_path: str, old_string: str, new_string: str):
        """Edit a file."""
        return str(self.core.execute(file_path=file_path, old_string=old_string, new_string=new_string))


class SmolagentsReplaceTool(SmolagentsToolAdapter):
    """Smolagents adapter for ReplaceToolCore."""

    def __init__(self, core: ReplaceToolCore):
        super().__init__(core_tool=core)

    def forward(self, file_path: str, content: str):
        """Replace file contents."""
        return str(self.core.execute(file_path=file_path, content=content))


class SmolagentsGlobTool(SmolagentsToolAdapter):
    """Smolagents adapter for GlobToolCore."""

    def __init__(self, core: GlobToolCore):
        super().__init__(core_tool=core)

    def forward(self, pattern: str, path: str | None = None):
        """Find files matching pattern."""
        return str(self.core.execute(pattern=pattern, path=path))


class SmolagentsGrepTool(SmolagentsToolAdapter):
    """Smolagents adapter for GrepToolCore."""

    def __init__(self, core: GrepToolCore):
        super().__init__(core_tool=core)

    def forward(self, pattern: str, include: str | None = None, path: str | None = None):
        """Search file contents."""
        return str(self.core.execute(pattern=pattern, include=include, path=path))


class SmolagentsLSTool(SmolagentsToolAdapter):
    """Smolagents adapter for LSToolCore."""

    def __init__(self, core: LSToolCore):
        super().__init__(core_tool=core)

    def forward(self, path: str, ignore: list[str] | None = None):
        """List directory contents."""
        return str(self.core.execute(path=path, ignore=ignore))


class SmolagentsUserInputTool(SmolagentsToolAdapter):
    """Smolagents adapter for UserInputToolCore."""

    def __init__(self, core: UserInputToolCore):
        super().__init__(core_tool=core)

    def forward(self, question: str):
        """Ask user for input."""
        return str(self.core.execute(question=question))
