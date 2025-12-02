"""
Minimalist smolagents agent implementation.

This module provides a simple interface to create and run a smolagents CodeAgent
with manually defined tools, working across any execution backend.
"""
import os
from smolagents import ToolCallingAgent, OpenAIModel, InferenceClientModel

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

# MODEL EXAMPLES
GPT_5_MINI_OPENAI_SMOLAGENTS = OpenAIModel(model_id="gpt-5-mini")
GPT_OSS_120B_HF_SMOLAGENTS = InferenceClientModel(model_id="openai/gpt-oss-120b", provider="cerebras")


def create_smolagents_tools(backend: ExecutionBackend) -> list:
    """
    Create smolagents tools using the core tools' conversion methods.

    Args:
        backend: The execution backend instance.

    Returns:
        List of smolagents tool instances.
    """
    tool_classes = [
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

    return [tool_class(backend=backend).to_smolagents_tool() for tool_class in tool_classes]


class SmolAgentAgent:
    """
    A minimalist smolagents-based coding agent.

    This agent combines:
    - Any execution backend (Local, Docker, E2B)
    - Core tools with manually defined smolagents wrappers
    - Dynamic system prompt with project context
    """

    def __init__(
        self,
        backend: ExecutionBackend,
        model: OpenAIModel | InferenceClientModel = GPT_OSS_120B_HF_SMOLAGENTS,
        additional_tools: list | None = None,
        max_steps: int = 30,
    ) -> None:
        """
        Initialize the smolagent agent.

        Args:
            backend: Execution backend (LocalBackend, DockerBackend, or E2BBackend)
            model: Smolagents model
            additional_tools: Optional additional smolagents tools to add
            max_steps: Maximum number of agent steps
        """
        self.backend = backend
        self.model = model

        # Create core tools using conversion methods
        self.tools = create_smolagents_tools(backend=backend)

        # Add any additional tools
        if additional_tools:
            self.tools.extend(additional_tools)

        # Initialize the smolagents agent
        self.agent = ToolCallingAgent(
            tools=self.tools,
            model=self.model,
            max_steps=max_steps,
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
            self.backend.clean_state_manager()

        # Run the agent
        result = self.agent.run(task=task)

        self.backend.shutdown()

        return result
