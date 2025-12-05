"""
Abstract base class for framework-specific coding agents.
"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from anyagents.backends.execution_backend import ExecutionBackend
from anyagents.presets.base import Preset
from anyagents.presets.generic import GenericPreset
from anyagents.tools.base_tool import CoreBackendTool

from anyagents.tools.write_file_tool import WriteFileTool
from anyagents.tools.read_file_tool import ReadFileTool
from anyagents.tools.list_directory_tool import ListDirectoryTool
from anyagents.tools.glob_tool import GlobTool
from anyagents.tools.search_file_content_tool import SearchFileContentTool
from anyagents.tools.replace_tool import ReplaceTool
from anyagents.tools.run_shell_command_tool import RunShellCommandTool
from anyagents.tools.read_many_files_tool import ReadManyFilesTool
from anyagents.tools.save_memory_tool import SaveMemoryTool


CORE_TOOLS: tuple[type[CoreBackendTool], ...] = (
    WriteFileTool,
    ReadFileTool,
    ListDirectoryTool,
    GlobTool,
    SearchFileContentTool,
    ReplaceTool,
    RunShellCommandTool,
    ReadManyFilesTool,
    SaveMemoryTool,
)


TModel = TypeVar("TModel")
TNativeTool = TypeVar("TNativeTool")


class AgentFactory(ABC, Generic[TModel, TNativeTool]):
    """
    Abstract base class for framework-specific coding agents.

    This class provides the common infrastructure for building coding agents
    that work with different AI frameworks (LangChain, smolagents, Pydantic-AI).

    Subclasses must implement:
        - _convert_tool(): Convert CoreBackendTool to native framework tool
        - _run_agent(): Execute the agent with the given task

    Args:
        backend: Execution environment (LocalBackend, DockerBackend, E2BBackend)
        model: Framework-specific model instance
        preset: Development environment preset (default: GenericPreset)
        extra_tool_classes: Additional CoreBackendTool classes to include
        native_tools: Framework-native tools to add directly (no conversion)

    Example:
        class LangChainAgent(AgentFactory[BaseChatModel, LangChainTool]):
            def _convert_tool(self, tool: CoreBackendTool) -> LangChainTool:
                return tool.to_langchain_tool()

            def _run_agent(self, task: str) -> str:
                # LangChain-specific agent execution
                ...

    Usage:
        agent = LangChainAgent(
            backend=LocalBackend(project_id="my-app", state_manager=NoOpStateManager()),
            model=ChatOpenAI(),
            preset=PythonUVPreset(),
            extra_tool_classes=[MyCustomTool],
            native_tools=[DuckDuckGoSearchRun()],
        )
        result = agent.run("Create a FastAPI app")
    """

    def __init__(
        self,
        backend: ExecutionBackend,
        model: TModel,
        preset: Preset | None = None,
        extra_tool_classes: list[type[CoreBackendTool]] | None = None,
        native_tools: list[TNativeTool] | None = None,
    ) -> None:
        self.backend = backend
        self.model = model
        self.preset = preset or GenericPreset()
        self._extra_tool_classes = extra_tool_classes or []
        self._native_tools = native_tools or []

        self.tools: list[TNativeTool] = self._build_tools()

    def _get_all_tool_classes(self) -> list[type[CoreBackendTool]]:
        """Collect all CoreBackendTool classes: core + preset + extra."""
        classes: list[type[CoreBackendTool]] = list(CORE_TOOLS)
        classes.extend(self.preset.tool_classes)
        classes.extend(self._extra_tool_classes)
        return classes

    def _build_tools(self) -> list[TNativeTool]:
        """Build final tool list: converted CoreBackendTools + native tools."""
        tools: list[TNativeTool] = []

        for tool_class in self._get_all_tool_classes():
            instance = tool_class(backend=self.backend)
            tools.append(self._convert_tool(tool=instance))

        tools.extend(self._native_tools)

        return tools

    @abstractmethod
    def _convert_tool(self, tool: CoreBackendTool) -> TNativeTool:
        """
        Convert a CoreBackendTool instance to native framework format.

        Args:
            tool: CoreBackendTool instance (already bound to backend)

        Returns:
            Native framework tool
        """
        ...

    @abstractmethod
    def _run_agent(self, task: str) -> str:
        """
        Execute the agent on the task.

        Framework-specific implementation that creates and runs the agent.

        Args:
            task: The task to perform

        Returns:
            Agent's response as string
        """
        ...

    def run(self, task: str, reset_history: bool = True) -> str:
        """
        Run the agent on a task.

        Args:
            task: The task to perform
            reset_history: Whether to reset state before running

        Returns:
            Agent's response as string
        """
        self.backend.start()

        if reset_history:
            self.backend.clean(cleanup_state_manager=True)

        if not self.preset.is_initialized(backend=self.backend):
            self.preset.initialize_project(backend=self.backend)

        result = self._run_agent(task=task)

        self.backend.shutdown()

        return result
