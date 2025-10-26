"""
Tool factory for creating framework-specific tools.

This module provides factory methods to create tools for different frameworks
(smolagents, openai, etc.) and execution environments (local, docker, e2b).
"""
from typing import Literal

from smolagents import Tool

from prompttodraft.tools.backends.execution_backend import ExecutionBackend
from prompttodraft.tools.backends.local_backend import LocalBackend
from prompttodraft.tools.backends.docker_backend import DockerBackend
from prompttodraft.tools.backends.e2b_backend import E2BBackend

from prompttodraft.tools.core.write_file_tool import WriteFileTool
from prompttodraft.tools.core.read_file_tool import ReadFileTool
from prompttodraft.tools.core.list_directory_tool import ListDirectoryTool
from prompttodraft.tools.core.glob_tool import GlobTool
from prompttodraft.tools.core.search_file_content_tool import SearchFileContentTool
from prompttodraft.tools.core.replace_tool import ReplaceTool
from prompttodraft.tools.core.run_shell_command_tool import RunShellCommandTool
from prompttodraft.tools.core.read_many_files_tool import ReadManyFilesTool
from prompttodraft.tools.core.save_memory_tool import SaveMemoryTool

from prompttodraft.tools.adapters.smolagents_adapter import (
    SmolagentsWriteFileTool,
    SmolagentsReadFileTool,
    SmolagentsListDirectoryTool,
    SmolagentsGlobTool,
    SmolagentsSearchFileContentTool,
    SmolagentsReplaceTool,
    SmolagentsRunShellCommandTool,
    SmolagentsReadManyFilesTool,
    SmolagentsSaveMemoryTool,
)


class ToolFactory:
    """Factory for creating framework-specific tools."""

    @staticmethod
    def create_smolagents_tools(backend: ExecutionBackend) -> list[Tool]:
        """
        Create smolagents-compatible tools for the given backend.

        Args:
            backend: An ExecutionBackend instance (LocalBackend, DockerBackend, or E2BBackend)

        Returns:
            List of smolagents Tool instances
        """
        # Create core tool instances with the backend
        write_file_tool = WriteFileTool(backend=backend)
        read_file_tool = ReadFileTool(backend=backend)
        list_directory_tool = ListDirectoryTool(backend=backend)
        glob_tool = GlobTool(backend=backend)
        search_file_content_tool = SearchFileContentTool(backend=backend)
        replace_tool = ReplaceTool(backend=backend)
        run_shell_command_tool = RunShellCommandTool(backend=backend)
        read_many_files_tool = ReadManyFilesTool(backend=backend)
        save_memory_tool = SaveMemoryTool(backend=backend)

        # Wrap each core tool with smolagents adapter
        return [
            SmolagentsWriteFileTool(core=write_file_tool),
            SmolagentsReadFileTool(core=read_file_tool),
            SmolagentsListDirectoryTool(core=list_directory_tool),
            SmolagentsGlobTool(core=glob_tool),
            SmolagentsSearchFileContentTool(core=search_file_content_tool),
            SmolagentsReplaceTool(core=replace_tool),
            SmolagentsRunShellCommandTool(core=run_shell_command_tool),
            SmolagentsReadManyFilesTool(core=read_many_files_tool),
            SmolagentsSaveMemoryTool(core=save_memory_tool),
        ]

    @staticmethod
    def create_backend(
        environment: Literal["local", "docker", "e2b"] = "local",
        project_id: str | None = None,
    ) -> ExecutionBackend:
        """
        Create an ExecutionBackend instance for the given environment.

        Args:
            environment: The execution environment ("local", "docker", or "e2b")
            project_id: Optional project ID (required for docker and e2b backends)

        Returns:
            ExecutionBackend instance

        Raises:
            ValueError: If unknown environment or missing project_id
        """
        match environment:
            case "local":
                return LocalBackend(project_id=project_id or "local")
            case "docker":
                if project_id is None:
                    raise ValueError("project_id is required for docker backend")
                return DockerBackend(project_id=project_id)
            case "e2b":
                if project_id is None:
                    raise ValueError("project_id is required for e2b backend")
                return E2BBackend(project_id=project_id)
            case _:
                raise ValueError(f"Unknown environment: {environment}")
