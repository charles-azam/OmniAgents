"""
Minimalist pydantic_ai agent implementation.

This module provides a simple interface to create and run a pydantic_ai Agent
with manually defined tools, working across any execution backend.
"""
import os
from pydantic_ai import Agent, Tool
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.huggingface import HuggingFaceModel
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
from prompttodraft.profiles.base_profile import ProjectProfile
import logfire


def get_pydantic_ai_model_example(model_name: str = "openai/gpt-oss-120b:cerebras") -> OpenAIChatModel:
    if "gpt-5" in model_name:
        return OpenAIChatModel(model_name=model_name)
    elif "gpt-oss-120b" in model_name:
        hf_client = AsyncOpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=os.getenv("HF_TOKEN"),
        )
        hf_provider = OpenAIProvider(openai_client=hf_client)
        return OpenAIChatModel(model_name=model_name, provider=hf_provider)
    else:
        raise ValueError(f"Invalid model name: {model_name}")




def create_pydantic_ai_tools(backend: ExecutionBackend, profile: ProjectProfile) -> list[Tool]:
    """
    Create pydantic_ai tools using the core tools' conversion methods.

    Args:
        backend: The execution backend instance.
        profile: The project profile.

    Returns:
        List of pydantic_ai Tool objects.
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
    tools = [tool_class(backend=backend).to_pydantic_ai_tool() for tool_class in tool_classes]
    
    # Profile tools
    profile_tools = profile.get_tools(backend=backend)
    tools.extend([tool.to_pydantic_ai_tool() for tool in profile_tools])
    
    return tools


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
        model: OpenAIChatModel = get_pydantic_ai_model_example(),
        additional_tools: list | None = None,
        profile: ProjectProfile | None = None,
    ) -> None:
        """
        Initialize the pydantic_ai agent.

        Args:
            backend: Execution backend (LocalBackend, DockerBackend, or E2BBackend)
            model: Pydantic AI model
            additional_tools: Optional additional pydantic_ai tools to add
            profile: Project profile (defaults to PythonUVProfile)
        """
        from prompttodraft.profiles.python_uv_profile import PythonUVProfile
        
        logfire.configure(console=logfire.ConsoleOptions(verbose=True, colors="auto"))
        logfire.instrument_pydantic_ai(
        )
        self.backend = backend
        self.model = model
        self.profile = profile or PythonUVProfile()

        # Create core tools
        self.tools = create_pydantic_ai_tools(backend=backend, profile=self.profile)

        # Add any additional tools
        if additional_tools:
            self.tools.extend(additional_tools)

        # Generate system prompt with current project context
        self.backend.start()
        system_prompt = get_system_prompt(backend=self.backend, model_id="pydantic_ai")
        
        # Add profile instructions
        profile_instructions = self.profile.get_system_prompt_additions()
        if profile_instructions:
            system_prompt += f"\n\n{profile_instructions}"

        # Initialize the pydantic_ai Agent
        self.agent = Agent[str](
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
            self.backend.clean(cleanup_state_manager=True)
            
            # Initialize project
            self.profile.initialize(backend=self.backend)
            
            # Regenerate system prompt with updated project context
            system_prompt = get_system_prompt(backend=self.backend, model_id="pydantic_ai")
            
            # Add profile instructions
            profile_instructions = self.profile.get_system_prompt_additions()
            if profile_instructions:
                system_prompt += f"\n\n{profile_instructions}"
                
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

