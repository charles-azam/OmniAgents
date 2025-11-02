"""
Minimalist smolagents agent implementation.

This module provides a simple interface to create and run a smolagents CodeAgent
with the core tools, working across any execution backend.
"""
from smolagents import CodeAgent, ApiModel, ToolCallingAgent, OpenAIModel, InferenceClientModel
import os

from prompttodraft.agent.adapters.smolagents_adapter import create_smolagents_tools
from prompttodraft.agent.backends.execution_backend import ExecutionBackend
from prompttodraft.agent.system_prompt import get_system_prompt

def create_model(provider: str, model_id: str):
    """
    Create a smolagents model from provider and model_id.

    Args:
        provider: Provider name (openai, huggingface, xai).
        model_id: Model identifier.

    Returns:
        Configured smolagents model.
    """
    if provider == "openai":
        return OpenAIModel(model_id=model_id)
    elif provider == "huggingface":
        return InferenceClientModel(model_id=model_id)
    elif provider == "xai":
        return OpenAIModel(
            model_id=model_id,
            api_key=os.getenv("XAI_API_KEY"),
            api_base="https://api.x.ai/v1"
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")




class SmolAgentAgent:
    """
    A minimalist smolagents-based coding agent.

    This agent combines:
    - Any execution backend (Local, Docker, E2B)
    - Core Gemini CLI tools via smolagents adapter
    - Dynamic system prompt with project context
    """

    def __init__(
        self,
        backend: ExecutionBackend,
        model_id: str = "openai/gpt-oss-120b",
        provider: str = "huggingface",
        additional_tools: list | None = None,
        max_steps: int = 30,
    ) -> None:
        """
        Initialize the smolagent agent.

        Args:
            backend: Execution backend (LocalBackend, DockerBackend, or E2BBackend)
            model_id: HuggingFace model identifier
            additional_tools: Optional additional smolagents tools to add
        """
        self.backend = backend
        self.model_id = model_id

        # Create core tools from backend
        self.tools = create_smolagents_tools(backend=backend)

        # Add any additional tools
        if additional_tools:
            self.tools.extend(additional_tools)

        # Initialize the smolagents CodeAgent
        self.model = create_model(provider=provider, model_id=model_id)
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
            self.backend.cleanup()
        # Generate system prompt with current project context
        system_prompt = get_system_prompt(backend=self.backend, model_id=self.model_id)

        # Combine system prompt with task
        full_prompt = f"{system_prompt}\n\n{task}"

        # Reset history if requested
        if reset_history:
            self.agent.logs = []

        # Run the agent
        result = self.agent.run(task=full_prompt)

        self.backend.shutdown()

        return result.output

