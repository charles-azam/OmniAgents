"""
Minimalist LangChain agent implementation.

This module provides a simple interface to create and run a LangChain agent
with manually defined tools, working across any execution backend.
"""
import os
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.tools import tool

from prompttodraft.agent.backends.execution_backend import ExecutionBackend
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

from langsmith import traceable


def create_model(provider: str, model_id: str):
    """
    Create a LangChain model from provider and model_id.

    Args:
        provider: Provider name (openai, huggingface, xai).
        model_id: Model identifier.

    Returns:
        Configured LangChain model.
    """
    if provider == "openai":
        return ChatOpenAI(
            model=model_id,
            temperature=0,
        )
    elif provider == "huggingface":
        from langchain_huggingface import ChatHuggingFace
        from langchain_huggingface import HuggingFaceEndpoint

        llm = HuggingFaceEndpoint(
            repo_id=model_id,
            task="text-generation",
            temperature=0,
        )
        return ChatHuggingFace(llm=llm)
    elif provider == "xai":
        from langchain_xai import ChatXAI

        return ChatXAI(
            model=model_id,
            temperature=0,
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def create_langchain_tools(backend: ExecutionBackend) -> list:
    """
    Create manually defined LangChain tools using the core tools.

    Args:
        backend: The execution backend instance.

    Returns:
        List of LangChain tool objects.
    """
    # Initialize all core tools
    write_file_core = WriteFileTool(backend=backend)
    read_file_core = ReadFileTool(backend=backend)
    list_directory_core = ListDirectoryTool(backend=backend)
    glob_core = GlobTool(backend=backend)
    search_file_content_core = SearchFileContentTool(backend=backend)
    replace_core = ReplaceTool(backend=backend)
    run_shell_command_core = RunShellCommandTool(backend=backend)
    read_many_files_core = ReadManyFilesTool(backend=backend)
    save_memory_core = SaveMemoryTool(backend=backend)
    uv_core = UVTool(backend=backend)

    @tool(description=write_file_core.metadata.description)
    def write_file(file_path: str, content: str) -> str:
        result = write_file_core.execute(file_path=file_path, content=content)
        return str(result)

    @tool(description=read_file_core.metadata.description)
    def read_file(path: str, offset: int | None = None, limit: int | None = None) -> str:
        result = read_file_core.execute(path=path, offset=offset, limit=limit)
        return str(result)

    @tool(description=list_directory_core.metadata.description)
    def list_directory(path: str, ignore: list[str] | None = None, respect_git_ignore: bool = True) -> str:
        result = list_directory_core.execute(path=path, ignore=ignore, respect_git_ignore=respect_git_ignore)
        return str(result)

    @tool(description=glob_core.metadata.description)
    def glob(pattern: str, path: str | None = None, case_sensitive: bool = False, respect_git_ignore: bool = True) -> str:
        result = glob_core.execute(pattern=pattern, path=path, case_sensitive=case_sensitive, respect_git_ignore=respect_git_ignore)
        return str(result)

    @tool(description=search_file_content_core.metadata.description)
    def search_file_content(pattern: str, path: str | None = None, include: str | None = None) -> str:
        result = search_file_content_core.execute(pattern=pattern, path=path, include=include)
        return str(result)

    @tool(description=replace_core.metadata.description)
    def replace(file_path: str, old_string: str, new_string: str, expected_replacements: int = 1) -> str:
        result = replace_core.execute(file_path=file_path, old_string=old_string, new_string=new_string, expected_replacements=expected_replacements)
        return str(result)

    @tool(description=run_shell_command_core.metadata.description)
    def run_shell_command(command: str, description: str | None = None, directory: str | None = None) -> str:
        result = run_shell_command_core.execute(command=command, description=description, directory=directory)
        return str(result)

    @tool(description=read_many_files_core.metadata.description)
    def read_many_files(
        paths: list[str],
        exclude: list[str] | None = None,
        include: list[str] | None = None,
        recursive: bool = True,
        useDefaultExcludes: bool = True,
        respect_git_ignore: bool = True,
    ) -> str:
        result = read_many_files_core.execute(
            paths=paths,
            exclude=exclude,
            include=include,
            recursive=recursive,
            useDefaultExcludes=useDefaultExcludes,
            respect_git_ignore=respect_git_ignore,
        )
        return str(result)

    @tool(description=save_memory_core.metadata.description)
    def save_memory(fact: str) -> str:
        result = save_memory_core.execute(fact=fact)
        return str(result)

    @tool(description=uv_core.metadata.description)
    def uv(command: str, description: str | None = None) -> str:
        result = uv_core.execute(command=command, description=description)
        return str(result)

    return [
        write_file,
        read_file,
        list_directory,
        glob,
        search_file_content,
        replace,
        run_shell_command,
        read_many_files,
        save_memory,
        uv,
    ]


class LangChainAgent:
    """
    A minimalist LangChain-based coding agent.

    This agent combines:
    - Any execution backend (Local, Docker, E2B)
    - Core tools with manually defined LangChain wrappers
    - Dynamic system prompt with project context
    - LangGraph's ReAct agent implementation
    """

    def __init__(
        self,
        backend: ExecutionBackend,
        model_id: str = "gpt-5-mini",
        provider: str = "openai",
        additional_tools: list | None = None,
    ) -> None:
        """
        Initialize the LangChain agent.

        Args:
            backend: Execution backend (LocalBackend, DockerBackend, or E2BBackend)
            model_id: Model identifier
            provider: Provider name (openai, huggingface, xai)
            additional_tools: Optional additional LangChain tools to add
        """
        self.backend = backend
        self.model_id = model_id
        self.provider = provider

        # Create core tools manually
        self.tools = create_langchain_tools(backend=backend)

        # Add any additional tools
        if additional_tools:
            self.tools.extend(additional_tools)

        # Initialize the LangChain model
        self.model = create_model(provider=provider, model_id=model_id)

    @traceable
    def run(self, task: str, reset_history: bool = True) -> str:
        """
        Run the agent on a task.

        Args:
            task: The task or question to run
            reset_history: Whether to reset conversation history before running

        Returns:
            The agent's final answer as a string
        """
        # Start backend
        self.backend.start()

        # Cleanup if requested
        if reset_history:
            self.backend.cleanup()

        # Generate system prompt with current project context

        # Create agent executor with system prompt
        agent_executor = create_agent(
            model=self.model,
            tools=self.tools,
        )

        # Run the agent
        result = agent_executor.invoke(
            input={"messages": [("user", task)]}
        )

        # Shutdown backend
        self.backend.shutdown()

        # Extract the final message from the result
        if "messages" in result:
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                return last_message.content
            return str(last_message)

        return str(result)
