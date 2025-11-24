"""
Minimalist smolagents agent implementation.

This module provides a simple interface to create and run a smolagents CodeAgent
with automatically generated tools, working across any execution backend.
"""
import os
from smolagents import ToolCallingAgent, OpenAIModel, InferenceClientModel

from prompttodraft.backends.execution_backend import ExecutionBackend
from prompttodraft.adapters import generate_smolagents_tools


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
    - Core tools with auto-generated smolagents wrappers
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
            model_id: Model identifier
            provider: Provider name (openai, huggingface, xai)
            additional_tools: Optional additional smolagents tools to add
            max_steps: Maximum number of agent steps
        """
        self.backend = backend
        self.model_id = model_id

        # Auto-generate tools from core tools
        self.tools = generate_smolagents_tools(backend=backend)

        # Add any additional tools
        if additional_tools:
            self.tools.extend(additional_tools)

        # Initialize the smolagents agent
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

        # Run the agent
        result = self.agent.run(task=task)

        self.backend.shutdown()

        return result
