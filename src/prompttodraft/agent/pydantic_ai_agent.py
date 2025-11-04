"""
Minimalist pydantic_ai agent implementation.

This module provides a simple interface to create and run a pydantic_ai Agent
with manually defined tools, working across any execution backend.
"""
import os
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from openai import AsyncOpenAI

from prompttodraft.agent.backends.execution_backend import ExecutionBackend
from prompttodraft.agent.system_prompt import get_system_prompt
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


def create_model(provider: str, model_id: str) -> OpenAIChatModel:
    """
    Create a pydantic_ai model from provider and model_id.

    Args:
        provider: Provider name (openai, huggingface, xai).
        model_id: Model identifier.

    Returns:
        Configured pydantic_ai model.
    """
    if provider == "openai":
        return OpenAIChatModel(model_name=model_id)
    elif provider == "huggingface":
        raise NotImplementedError("HuggingFace provider not yet supported in Pydantic AI")
    elif provider == "xai":
        xai_client = AsyncOpenAI(
            base_url="https://api.x.ai/v1",
            api_key=os.getenv("XAI_API_KEY"),
        )
        xai_provider = OpenAIProvider(openai_client=xai_client)
        return OpenAIChatModel(model_name=model_id, provider=xai_provider)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


# Manual pydantic_ai tool definitions
def create_write_file_tool(backend: ExecutionBackend) -> Tool:
    """Create write_file tool."""
    core_tool = WriteFileTool(backend=backend)

    def write_file(file_path: str, content: str) -> str:
        """Write content to a specified file. If the file exists, it will be overwritten."""
        result = core_tool.execute(file_path=file_path, content=content)
        return str(result)

    return Tool(function=write_file, takes_ctx=False)


def create_read_file_tool(backend: ExecutionBackend) -> Tool:
    """Create read_file tool."""
    core_tool = ReadFileTool(backend=backend)

    def read_file(path: str, offset: int | None = None, limit: int | None = None) -> str:
        """Read and return the content of a specified file."""
        result = core_tool.execute(path=path, offset=offset, limit=limit)
        return str(result)

    return Tool(function=read_file, takes_ctx=False)


def create_list_directory_tool(backend: ExecutionBackend) -> Tool:
    """Create list_directory tool."""
    core_tool = ListDirectoryTool(backend=backend)

    def list_directory(path: str, ignore: list[str] | None = None, respect_git_ignore: bool = True) -> str:
        """List the names of files and subdirectories within a specified directory path."""
        result = core_tool.execute(path=path, ignore=ignore, respect_git_ignore=respect_git_ignore)
        return str(result)

    return Tool(function=list_directory, takes_ctx=False)


def create_glob_tool(backend: ExecutionBackend) -> Tool:
    """Create glob tool."""
    core_tool = GlobTool(backend=backend)

    def glob(pattern: str, path: str | None = None, case_sensitive: bool = False, respect_git_ignore: bool = True) -> str:
        """Find files matching specific glob patterns, returning absolute paths sorted by modification time."""
        result = core_tool.execute(pattern=pattern, path=path, case_sensitive=case_sensitive, respect_git_ignore=respect_git_ignore)
        return str(result)

    return Tool(function=glob, takes_ctx=False)


def create_search_file_content_tool(backend: ExecutionBackend) -> Tool:
    """Create search_file_content tool."""
    core_tool = SearchFileContentTool(backend=backend)

    def search_file_content(pattern: str, path: str | None = None, include: str | None = None) -> str:
        """Search for a regular expression pattern within the content of files in a specified directory."""
        result = core_tool.execute(pattern=pattern, path=path, include=include)
        return str(result)

    return Tool(function=search_file_content, takes_ctx=False)


def create_replace_tool(backend: ExecutionBackend) -> Tool:
    """Create replace tool."""
    core_tool = ReplaceTool(backend=backend)

    def replace(file_path: str, old_string: str, new_string: str, expected_replacements: int = 1) -> str:
        """Replace text within a file with precise, targeted changes."""
        result = core_tool.execute(file_path=file_path, old_string=old_string, new_string=new_string, expected_replacements=expected_replacements)
        return str(result)

    return Tool(function=replace, takes_ctx=False)


def create_run_shell_command_tool(backend: ExecutionBackend) -> Tool:
    """Create run_shell_command tool."""
    core_tool = RunShellCommandTool(backend=backend)

    def run_shell_command(command: str, description: str | None = None, directory: str | None = None) -> str:
        """Execute a shell command in the execution environment."""
        result = core_tool.execute(command=command, description=description, directory=directory)
        return str(result)

    return Tool(function=run_shell_command, takes_ctx=False)


def create_read_many_files_tool(backend: ExecutionBackend) -> Tool:
    """Create read_many_files tool."""
    core_tool = ReadManyFilesTool(backend=backend)

    def read_many_files(
        paths: list[str],
        exclude: list[str] | None = None,
        include: list[str] | None = None,
        recursive: bool = True,
        useDefaultExcludes: bool = True,
        respect_git_ignore: bool = True,
    ) -> str:
        """Read content from multiple files specified by paths or glob patterns."""
        result = core_tool.execute(
            paths=paths,
            exclude=exclude,
            include=include,
            recursive=recursive,
            useDefaultExcludes=useDefaultExcludes,
            respect_git_ignore=respect_git_ignore,
        )
        return str(result)

    return Tool(function=read_many_files, takes_ctx=False)


def create_save_memory_tool(backend: ExecutionBackend) -> Tool:
    """Create save_memory tool."""
    core_tool = SaveMemoryTool(backend=backend)

    def save_memory(fact: str) -> str:
        """Save and recall information across sessions."""
        result = core_tool.execute(fact=fact)
        return str(result)

    return Tool(function=save_memory, takes_ctx=False)


def create_uv_tool(backend: ExecutionBackend) -> Tool:
    """Create uv tool."""
    core_tool = UVTool(backend=backend)

    def uv(command: str, description: str | None = None) -> str:
        """Execute uv package manager commands in the execution environment."""
        result = core_tool.execute(command=command, description=description)
        return str(result)

    return Tool(function=uv, takes_ctx=False)


class PydanticAIAgent:
    """
    A minimalist pydantic_ai-based coding agent.

    This agent combines:
    - Any execution backend (Local, Docker, E2B)
    - Core tools with manually defined pydantic_ai wrappers
    - Dynamic system prompt with project context
    """

    def __init__(
        self,
        backend: ExecutionBackend,
        model_id: str = "gpt-5-mini",
        provider: str = "openai",
        additional_tools: list | None = None,
    ) -> None:
        """
        Initialize the pydantic_ai agent.

        Args:
            backend: Execution backend (LocalBackend, DockerBackend, or E2BBackend)
            model_id: Model identifier
            provider: Provider name (openai, xai)
            additional_tools: Optional additional pydantic_ai tools to add
        """
        self.backend = backend
        self.model_id = model_id
        self.provider = provider

        # Create core tools manually
        self.tools = [
            create_write_file_tool(backend=backend),
            create_read_file_tool(backend=backend),
            create_list_directory_tool(backend=backend),
            create_glob_tool(backend=backend),
            create_search_file_content_tool(backend=backend),
            create_replace_tool(backend=backend),
            create_run_shell_command_tool(backend=backend),
            create_read_many_files_tool(backend=backend),
            create_save_memory_tool(backend=backend),
            create_uv_tool(backend=backend),
        ]

        # Add any additional tools
        if additional_tools:
            self.tools.extend(additional_tools)

        # Create the model
        self.model = create_model(provider=provider, model_id=model_id)

        # Generate system prompt with current project context
        self.backend.start()
        system_prompt = get_system_prompt(backend=self.backend, model_id=self.model_id)

        # Initialize the pydantic_ai Agent
        self.agent = Agent(
            model=self.model,
            system_prompt=system_prompt,
            tools=self.tools,
        )

    def run(self, task: str, reset_history: bool = True) -> str:
        """
        Run the agent on a task.

        Args:
            task: The task or question to run
            reset_history: Whether to reset conversation history before running

        Returns:
            The agent's final answer as a string
        """
        self.backend.start()

        if reset_history:
            self.backend.cleanup()
            # Regenerate system prompt with updated project context
            system_prompt = get_system_prompt(backend=self.backend, model_id=self.model_id)
            # Recreate agent with updated system prompt
            self.agent = Agent(
                model=self.model,
                system_prompt=system_prompt,
                tools=self.tools,
            )

        # Run the agent
        result = self.agent.run_sync(user_prompt=task)

        self.backend.shutdown()

        return result.output
