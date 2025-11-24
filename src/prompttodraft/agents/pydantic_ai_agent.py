"""
Minimalist pydantic_ai agent implementation.

This module provides a simple interface to create and run a pydantic_ai Agent
with automatically generated tools, working across any execution backend.
"""
import os
from dataclasses import dataclass
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from openai import AsyncOpenAI
import logfire

from prompttodraft.backends.execution_backend import ExecutionBackend
from prompttodraft.prompts.system_prompt import get_system_prompt
from prompttodraft.adapters import generate_pydantic_ai_tools


logfire.configure(console=logfire.ConsoleOptions(verbose=True, colors="auto"))
logfire.instrument_pydantic_ai()


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


class PydanticAIAgent:
    """
    A minimalist pydantic_ai-based coding agent.

    This agent combines:
    - Any execution backend (Local, Docker, E2B)
    - Core tools with auto-generated pydantic_ai wrappers
    - Dynamic system prompt with project context
    """

    def __init__(
        self,
        backend: ExecutionBackend,
        model_id: str = "gpt-4o-mini",
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

        # Auto-generate tools from core tools
        self.tools = generate_pydantic_ai_tools(
            deps_type=AgentDependencies,
            backend_attr="backend",
        )

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
