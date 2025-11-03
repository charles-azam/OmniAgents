"""
Minimalist LangChain agent implementation.

This module provides a simple interface to create and run a LangChain agent
with the core tools, working across any execution backend.
"""
import os
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from prompttodraft.agent.adapters.langchain_adapter import create_langchain_tools
from prompttodraft.agent.backends.execution_backend import ExecutionBackend
from prompttodraft.agent.system_prompt import get_system_prompt


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


class LangChainAgent:
    """
    A minimalist LangChain-based coding agent.

    This agent combines:
    - Any execution backend (Local, Docker, E2B)
    - Core tools via LangChain adapter
    - Dynamic system prompt with project context
    - LangGraph's ReAct agent implementation
    """

    def __init__(
        self,
        backend: ExecutionBackend,
        model_id: str = "gpt-4o-mini",
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

        # Create core tools from backend
        self.tools = create_langchain_tools(backend=backend)

        # Add any additional tools
        if additional_tools:
            self.tools.extend(additional_tools)

        # Initialize the LangChain model
        self.model = create_model(provider=provider, model_id=model_id)

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
