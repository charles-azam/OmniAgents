"""
Pydantic AI framework adapter.

This module provides a factory function to automatically convert CoreTools
into pydantic_ai Tool format.
"""
import inspect
from typing import Any

from pydantic_ai import RunContext, Tool, ToolDefinition

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


def create_pydantic_ai_tool(core_tool: CoreTool) -> Tool:
    """
    Create a pydantic_ai Tool from a CoreTool instance.

    This factory function creates a Tool with a prepare function that
    sets up the proper descriptions from the CoreTool metadata.

    Args:
        core_tool: A CoreTool instance to wrap

    Returns:
        A pydantic_ai Tool instance

    Example:
        >>> from prompttodraft.agent.backends.local_backend import LocalBackend
        >>> from prompttodraft.agent.core.write_file_tool import WriteFileTool
        >>>
        >>> backend = LocalBackend(project_id="my-project")
        >>> backend.start()
        >>>
        >>> write_tool = WriteFileTool(backend=backend)
        >>> pydantic_tool = create_pydantic_ai_tool(core_tool=write_tool)
        >>>
        >>> # Now use pydantic_tool with pydantic_ai Agent
    """
    if not isinstance(core_tool, CoreTool):
        raise TypeError(f"Expected CoreTool instance, got {type(core_tool)}")

    metadata = core_tool.metadata

    # Get the signature of the execute method to create a wrapper with the same signature
    execute_sig = inspect.signature(core_tool.execute)
    params = list(execute_sig.parameters.values())[1:]  # Skip 'self'

    # Create a wrapper function that calls execute and converts result to string
    def create_wrapper() -> Any:
        """Factory to create the wrapper function with proper signature."""
        def tool_function(**kwargs: Any) -> str:
            """Dynamically generated tool function."""
            result = core_tool.execute(**kwargs)
            return str(result)

        # Update the wrapper's signature to match execute (without self)
        tool_function.__signature__ = inspect.Signature(parameters=params)  # type: ignore
        tool_function.__name__ = metadata.name

        return tool_function

    tool_function = create_wrapper()

    # Create prepare function to set up descriptions from metadata
    async def prepare_tool(
        _ctx: RunContext, tool_def: ToolDefinition
    ) -> ToolDefinition:
        """Set up tool definition from CoreTool metadata."""
        # Set the main description
        tool_def.description = metadata.description

        # Set parameter descriptions from metadata.inputs
        if tool_def.parameters_json_schema and 'properties' in tool_def.parameters_json_schema:
            for param_name, param_info in metadata.inputs.items():
                if param_name in tool_def.parameters_json_schema['properties']:
                    if 'description' in param_info:
                        tool_def.parameters_json_schema['properties'][param_name]['description'] = param_info['description']

        return tool_def

    # Create and return the Tool with takes_ctx=False since execute doesn't need RunContext
    return Tool(
        function=tool_function,
        takes_ctx=False,
        prepare=prepare_tool,
    )


def create_pydantic_ai_tools(backend: ExecutionBackend) -> list[Tool]:
    """
    Create pydantic_ai Tool instances for all available core tools.

    This is a convenience function that instantiates all 10 core tools
    with the provided backend and wraps them as pydantic_ai Tools.

    Args:
        backend: The execution backend to use for all tools

    Returns:
        List of pydantic_ai Tool instances for all core tools

    Example:
        >>> from pydantic_ai import Agent
        >>> from prompttodraft.agent.backends.local_backend import LocalBackend
        >>>
        >>> backend = LocalBackend(project_id="my-project")
        >>> backend.start()
        >>>
        >>> tools = create_pydantic_ai_tools(backend=backend)
        >>> agent = Agent(model="openai/gpt-4", tools=tools)
        >>> # All 10 tools are now available to the agent
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

    # Convert all core tools to pydantic_ai tools
    return [create_pydantic_ai_tool(core_tool=tool) for tool in core_tools]
