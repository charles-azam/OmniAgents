"""
Minimalist pydantic_ai agent implementation.

This module provides a simple interface to create and run a pydantic_ai Agent
with manually defined tools, working across any execution backend.
"""
import os
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from openai import AsyncOpenAI

from prompttodraft.backends.execution_backend import ExecutionBackend
from prompttodraft.prompts.system_prompt import get_system_prompt
from prompttodraft.tools.write_file_tool import WriteFileTool
from prompttodraft.tools.read_file_tool import ReadFileTool
from prompttodraft.tools.list_directory_tool import ListDirectoryTool
from prompttodraft.tools.glob_tool import GlobTool
from prompttodraft.tools.search_file_content_tool import SearchFileContentTool
from prompttodraft.tools.replace_tool import ReplaceTool
from prompttodraft.tools.run_shell_command_tool import RunShellCommandTool
from prompttodraft.tools.read_many_files_tool import ReadManyFilesTool
from prompttodraft.tools.save_memory_tool import SaveMemoryTool
from prompttodraft.tools.uv_tool import UVTool
import logfire

logfire.configure(console=logfire.ConsoleOptions(verbose=True, colors="auto"))
logfire.instrument_pydantic_ai(

)

@dataclass
class AgentDependencies:
    """Dependencies injected into agent tools via RunContext."""
    backend: ExecutionBackend


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


def create_pydantic_ai_tools() -> list[Tool]:
    """
    Create manually defined pydantic_ai tools using the core tools.

    Tools receive the backend via RunContext[AgentDependencies].

    Returns:
        List of pydantic_ai Tool objects.
    """

    def write_file(ctx: RunContext[AgentDependencies], file_path: str, content: str) -> str:
        write_file_core = WriteFileTool(backend=ctx.deps.backend)
        result = write_file_core.execute(file_path=file_path, content=content)
        return str(result)

    def read_file(ctx: RunContext[AgentDependencies], path: str, offset: int | None = None, limit: int | None = None) -> str:
        read_file_core = ReadFileTool(backend=ctx.deps.backend)
        result = read_file_core.execute(path=path, offset=offset, limit=limit)
        return str(result)

    def list_directory(ctx: RunContext[AgentDependencies], path: str, ignore: list[str] | None = None, respect_git_ignore: bool = True) -> str:
        list_directory_core = ListDirectoryTool(backend=ctx.deps.backend)
        result = list_directory_core.execute(path=path, ignore=ignore, respect_git_ignore=respect_git_ignore)
        return str(result)

    def glob(ctx: RunContext[AgentDependencies], pattern: str, path: str | None = None, case_sensitive: bool = False, respect_git_ignore: bool = True) -> str:
        glob_core = GlobTool(backend=ctx.deps.backend)
        result = glob_core.execute(pattern=pattern, path=path, case_sensitive=case_sensitive, respect_git_ignore=respect_git_ignore)
        return str(result)

    def search_file_content(ctx: RunContext[AgentDependencies], pattern: str, path: str | None = None, include: str | None = None) -> str:
        search_file_content_core = SearchFileContentTool(backend=ctx.deps.backend)
        result = search_file_content_core.execute(pattern=pattern, path=path, include=include)
        return str(result)

    def replace(ctx: RunContext[AgentDependencies], file_path: str, old_string: str, new_string: str, expected_replacements: int | None = None) -> str:
        replace_core = ReplaceTool(backend=ctx.deps.backend)
        result = replace_core.execute(file_path=file_path, old_string=old_string, new_string=new_string, expected_replacements=expected_replacements)
        return str(result)

    def run_shell_command(ctx: RunContext[AgentDependencies], command: str, description: str | None = None, directory: str | None = None) -> str:
        run_shell_command_core = RunShellCommandTool(backend=ctx.deps.backend)
        result = run_shell_command_core.execute(command=command, description=description, directory=directory)
        return str(result)

    def read_many_files(ctx: RunContext[AgentDependencies], paths: list[str], exclude: list[str] | None = None, include: list[str] | None = None, recursive: bool = True, useDefaultExcludes: bool = True, respect_git_ignore: bool = True) -> str:
        read_many_files_core = ReadManyFilesTool(backend=ctx.deps.backend)
        result = read_many_files_core.execute(paths=paths, exclude=exclude, include=include, recursive=recursive, useDefaultExcludes=useDefaultExcludes, respect_git_ignore=respect_git_ignore)
        return str(result)

    def save_memory(ctx: RunContext[AgentDependencies], fact: str) -> str:
        save_memory_core = SaveMemoryTool(backend=ctx.deps.backend)
        result = save_memory_core.execute(fact=fact)
        return str(result)

    def uv(ctx: RunContext[AgentDependencies], command: str, description: str | None = None) -> str:
        uv_core = UVTool(backend=ctx.deps.backend)
        result = uv_core.execute(command=command, description=description)
        return str(result)

    # Create temporary instances to get metadata
    # Note: We create these with a placeholder backend just to access metadata
    # The actual backend will come from RunContext at runtime
    class _MetadataBackend:
        """Minimal backend stub for accessing tool metadata."""
        pass

    metadata_backend = _MetadataBackend()  # type: ignore

    write_file_meta = WriteFileTool(backend=metadata_backend)  # type: ignore
    read_file_meta = ReadFileTool(backend=metadata_backend)  # type: ignore
    list_directory_meta = ListDirectoryTool(backend=metadata_backend)  # type: ignore
    glob_meta = GlobTool(backend=metadata_backend)  # type: ignore
    search_file_content_meta = SearchFileContentTool(backend=metadata_backend)  # type: ignore
    replace_meta = ReplaceTool(backend=metadata_backend)  # type: ignore
    run_shell_command_meta = RunShellCommandTool(backend=metadata_backend)  # type: ignore
    read_many_files_meta = ReadManyFilesTool(backend=metadata_backend)  # type: ignore
    save_memory_meta = SaveMemoryTool(backend=metadata_backend)  # type: ignore
    uv_meta = UVTool(backend=metadata_backend)  # type: ignore

    return [
        Tool(function=write_file, takes_ctx=True, name=write_file_meta.metadata.name, description=write_file_meta.metadata.description),
        Tool(function=read_file, takes_ctx=True, name=read_file_meta.metadata.name, description=read_file_meta.metadata.description),
        Tool(function=list_directory, takes_ctx=True, name=list_directory_meta.metadata.name, description=list_directory_meta.metadata.description),
        Tool(function=glob, takes_ctx=True, name=glob_meta.metadata.name, description=glob_meta.metadata.description),
        Tool(function=search_file_content, takes_ctx=True, name=search_file_content_meta.metadata.name, description=search_file_content_meta.metadata.description),
        Tool(function=replace, takes_ctx=True, name=replace_meta.metadata.name, description=replace_meta.metadata.description),
        Tool(function=run_shell_command, takes_ctx=True, name=run_shell_command_meta.metadata.name, description=run_shell_command_meta.metadata.description),
        Tool(function=read_many_files, takes_ctx=True, name=read_many_files_meta.metadata.name, description=read_many_files_meta.metadata.description),
        Tool(function=save_memory, takes_ctx=True, name=save_memory_meta.metadata.name, description=save_memory_meta.metadata.description),
        Tool(function=uv, takes_ctx=True, name=uv_meta.metadata.name, description=uv_meta.metadata.description),
    ]


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

        # Create core tools with deps support
        self.tools = create_pydantic_ai_tools()

        # Add any additional tools
        if additional_tools:
            self.tools.extend(additional_tools)

        # Create the model
        self.model = create_model(provider=provider, model_id=model_id)

        # Generate system prompt with current project context
        self.backend.start()
        system_prompt = get_system_prompt(backend=self.backend, model_id=self.model_id)

        # Initialize the pydantic_ai Agent with deps_type
        self.agent = Agent[AgentDependencies, str](
            model=self.model,
            deps_type=AgentDependencies,
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
            # Recreate agent with updated system prompt and deps_type
            self.agent = Agent(
                model=self.model,
                deps_type=AgentDependencies,
                system_prompt=system_prompt,
                tools=self.tools,
            )

        # Create dependencies for this run
        deps = AgentDependencies(backend=self.backend)

        # Run the agent with deps
        result = self.agent.run_sync(user_prompt=task, deps=deps)

        self.backend.shutdown()

        return result.output
