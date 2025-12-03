"""
Minimalist LangChain agent implementation.

This module provides a simple interface to create and run a LangChain agent
with manually defined tools, working across any execution backend.
"""
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel

from prompttodraft.backends.execution_backend import ExecutionBackend
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
from prompttodraft.tools.base_tool import CoreBackendTool
from langsmith import traceable
import os

def get_langchain_model_example(model_name: str = "openai/gpt-oss-120b:cerebras") -> ChatOpenAI:
    if "gpt-5" in model_name:
        return ChatOpenAI(model=model_name)
    elif "gpt-oss-120b" in model_name:
        return ChatOpenAI(base_url="https://router.huggingface.co/v1", api_key=os.environ["HF_TOKEN"], model=model_name)
    else:
        raise ValueError(f"Invalid model name: {model_name}")




def create_langchain_tools(backend: ExecutionBackend) -> list:
    """
    Create LangChain tools using the core tools' conversion methods.

    Args:
        backend: The execution backend instance.

    Returns:
        List of LangChain tool objects.
    """
    tool_classes: list[type[CoreBackendTool]] = [
        WriteFileTool,
        ReadFileTool,
        ListDirectoryTool,
        GlobTool,
        SearchFileContentTool,
        ReplaceTool,
        RunShellCommandTool,
        ReadManyFilesTool,
        SaveMemoryTool,
        UVTool,
    ]

    return [tool_class(backend=backend).to_langchain_tool() for tool_class in tool_classes]


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
        model: BaseChatModel = get_langchain_model_example(),
        additional_tools: list | None = None,
    ) -> None:
        """
        Initialize the LangChain agent.

        Args:
            backend: Execution backend (LocalBackend, DockerBackend, or E2BBackend)
            model: LangChain model
            additional_tools: Optional additional LangChain tools to add
        """
        self.backend = backend
        self.model = model

        # Create core tools manually
        self.tools = create_langchain_tools(backend=backend)

        # Add any additional tools
        if additional_tools:
            self.tools.extend(additional_tools)

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
            self.backend.clean(cleanup_state_manager=True)

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
