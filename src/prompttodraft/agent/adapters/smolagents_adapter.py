"""
Smolagents framework adapter.

This module provides a factory function to automatically convert CoreTools
into smolagents Tool format.
"""
from smolagents import Tool

from prompttodraft.agent.core.base_tool import CoreTool
from prompttodraft.agent.backends.execution_backend import ExecutionBackend

# Import all core tools
from prompttodraft.agent.core.write_file_tool import WriteFileTool
from prompttodraft.agent.core.read_file_tool import ReadFileTool
from prompttodraft.agent.core.list_directory_tool import ListDirectoryTool
from prompttodraft.agent.core.glob_tool import GlobTool
from prompttodraft.agent.core.search_file_content_tool import SearchFileContentTool
from prompttodraft.agent.core.replace_tool import ReplaceTool
from prompttodraft.agent.core.run_shell_command_tool import RunShellCommandTool
from prompttodraft.agent.core.read_many_files_tool import ReadManyFilesTool
from prompttodraft.agent.core.save_memory_tool import SaveMemoryTool
from prompttodraft.agent.core.uv_tool import UVTool


def create_smolagents_tool(core_tool: CoreTool) -> Tool:
    """
    Automatically create a smolagents Tool from any CoreTool instance.

    This factory function dynamically generates a smolagents Tool class
    that wraps the core tool, using the core tool's metadata for all
    smolagents attributes.

    Args:
        core_tool: A CoreTool instance to wrap

    Returns:
        A smolagents Tool instance

    Example:
        >>> from prompttodraft.agent.backends.local_backend import LocalBackend
        >>> from prompttodraft.agent.core.write_file_tool import WriteFileTool
        >>>
        >>> backend = LocalBackend(project_id="my-project")
        >>> backend.start()
        >>>
        >>> write_tool = WriteFileTool(backend=backend)
        >>> smolagents_tool = create_smolagents_tool(core_tool=write_tool)
        >>>
        >>> # Now use smolagents_tool with smolagents framework
    """
    if not isinstance(core_tool, CoreTool):
        raise TypeError(f"Expected CoreTool instance, got {type(core_tool)}")

    metadata = core_tool.metadata

    class DynamicSmolagentsTool(Tool):
        """Dynamically generated smolagents tool wrapper."""

        name = metadata.name
        description = metadata.description
        inputs = metadata.inputs
        output_type = metadata.output_type
        skip_forward_signature_validation = True  # Allow generic **kwargs signature

        def __init__(self):
            self._core = core_tool
            super().__init__()

        def forward(self, **kwargs):
            """Forward all arguments to the core tool's execute method."""
            result = self._core.execute(**kwargs)
            return str(result)

    return DynamicSmolagentsTool()


def create_smolagents_tools(backend: ExecutionBackend) -> list[Tool]:
    """
    Create smolagents Tool instances for all available core tools.

    This is a convenience function that instantiates all 10 core tools
    with the provided backend and wraps them as smolagents Tools.

    Args:
        backend: The execution backend to use for all tools

    Returns:
        List of smolagents Tool instances for all core tools

    Example:
        >>> from prompttodraft.agent.backends.local_backend import LocalBackend
        >>>
        >>> backend = LocalBackend(project_id="my-project")
        >>> backend.start()
        >>>
        >>> tools = create_smolagents_tools(backend=backend)
        >>> # tools is a list of 10 smolagents Tool instances
        >>> # Use them with smolagents framework
    """
    # Instantiate all core tools with the backend
    core_tools = [
        WriteFileTool(backend=backend),
        ReadFileTool(backend=backend),
        ListDirectoryTool(backend=backend),
        GlobTool(backend=backend),
        SearchFileContentTool(backend=backend),
        ReplaceTool(backend=backend),
        RunShellCommandTool(backend=backend),
        ReadManyFilesTool(backend=backend),
        SaveMemoryTool(backend=backend),
        UVTool(backend=backend),
    ]

    # Convert all core tools to smolagents tools
    return [create_smolagents_tool(core_tool=tool) for tool in core_tools]
