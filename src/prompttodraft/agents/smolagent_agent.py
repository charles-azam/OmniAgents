"""
Minimalist smolagents agent implementation.

This module provides a simple interface to create and run a smolagents CodeAgent
with manually defined tools, working across any execution backend.
"""
from smolagents import ToolCallingAgent, OpenAIModel, InferenceClientModel

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
from prompttodraft.profiles.base_profile import ProjectProfile

def get_smolagents_model_example(model_name: str = "openai/gpt-oss-120b") -> OpenAIModel:
    if "gpt-5" in model_name:
        return OpenAIModel(model_id=model_name)
    elif "gpt-oss-120b" in model_name:
        return InferenceClientModel(model_id=model_name, provider="cerebras")
    else:
        raise ValueError(f"Invalid model name: {model_name}")



def create_smolagents_tools(backend: ExecutionBackend, profile: ProjectProfile) -> list:
    """
    Create smolagents tools using the core tools' conversion methods.

    Args:
        backend: The execution backend instance.
        profile: The project profile.

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
    ]

    # Base tools
    tools = [tool_class(backend=backend).to_smolagents_tool() for tool_class in tool_classes]
    
    # Profile tools
    profile_tools = profile.get_tools(backend=backend)
    tools.extend([tool.to_smolagents_tool() for tool in profile_tools])
    
    return tools


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
        model: OpenAIModel | InferenceClientModel = get_smolagents_model_example(),
        additional_tools: list | None = None,
        max_steps: int = 30,
        profile: ProjectProfile | None = None,
    ) -> None:
        """
        Initialize the smolagent agent.

        Args:
            backend: Execution backend (LocalBackend, DockerBackend, or E2BBackend)
            model: Smolagents model
            additional_tools: Optional additional smolagents tools to add
            max_steps: Maximum number of agent steps
            profile: Project profile (defaults to PythonUVProfile)
        """
        from prompttodraft.profiles.python_uv_profile import PythonUVProfile
        
        self.backend = backend
        self.model = model
        self.max_steps = max_steps
        self.profile = profile or PythonUVProfile()

        # Create core tools using conversion methods
        self.tools = create_smolagents_tools(backend=backend, profile=self.profile)

        # Add any additional tools
        if additional_tools:
            self.tools.extend(additional_tools)

        # Agent will be initialized in run() with the system prompt
        self.agent: ToolCallingAgent | None = None

    def _create_agent_with_context(self) -> None:
        """Create the agent with instructions containing working directory context."""
        # Generate instructions with current project context
        # Using instructions parameter instead of system_prompt to avoid Jinja2 conflicts
        instructions = get_system_prompt(backend=self.backend, model_id="smolagents")
        
        # Add profile instructions
        profile_instructions = self.profile.get_system_prompt_additions()
        if profile_instructions:
            instructions += f"\n\n{profile_instructions}"

        self.agent = ToolCallingAgent(
            tools=self.tools,
            model=self.model,
            max_steps=self.max_steps,
            instructions=instructions,
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
            self.backend.clean(cleanup_state_manager=True)
            
        # Initialize project
        self.profile.initialize(backend=self.backend)

        # Create/recreate agent with current working directory context
        self._create_agent_with_context()

        # Run the agent
        result = self.agent.run(task=task)

        self.backend.shutdown()

        return result

