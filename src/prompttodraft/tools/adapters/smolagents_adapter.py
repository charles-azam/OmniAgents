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

    def forward(self, **kwargs):
        """
        Execute the core tool and return the result.

        Args:
            **kwargs: Tool parameters

        Returns:
            String representation of the output (for smolagents compatibility)
        """
        # Execute the core tool
        output_model = self.core.execute(**kwargs)

        # For smolagents, return string representation
        # The output model's __str__ method provides a good default
        return str(output_model)


# Specific adapters for each tool type
class SmolagentsBashTool(SmolagentsToolAdapter):
    """Smolagents adapter for BashToolCore."""

    def __init__(self, core: BashToolCore):
        super().__init__(core_tool=core)


class SmolagentsViewTool(SmolagentsToolAdapter):
    """Smolagents adapter for ViewToolCore."""

    def __init__(self, core: ViewToolCore):
        super().__init__(core_tool=core)


class SmolagentsEditTool(SmolagentsToolAdapter):
    """Smolagents adapter for EditToolCore."""

    def __init__(self, core: EditToolCore):
        super().__init__(core_tool=core)


class SmolagentsReplaceTool(SmolagentsToolAdapter):
    """Smolagents adapter for ReplaceToolCore."""

    def __init__(self, core: ReplaceToolCore):
        super().__init__(core_tool=core)


class SmolagentsGlobTool(SmolagentsToolAdapter):
    """Smolagents adapter for GlobToolCore."""

    def __init__(self, core: GlobToolCore):
        super().__init__(core_tool=core)


class SmolagentsGrepTool(SmolagentsToolAdapter):
    """Smolagents adapter for GrepToolCore."""

    def __init__(self, core: GrepToolCore):
        super().__init__(core_tool=core)


class SmolagentsLSTool(SmolagentsToolAdapter):
    """Smolagents adapter for LSToolCore."""

    def __init__(self, core: LSToolCore):
        super().__init__(core_tool=core)


class SmolagentsUserInputTool(SmolagentsToolAdapter):
    """Smolagents adapter for UserInputToolCore."""

    def __init__(self, core: UserInputToolCore):
        super().__init__(core_tool=core)
