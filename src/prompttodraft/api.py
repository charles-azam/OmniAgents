"""
High-level API for creating agents in PromptToDraft.
"""
from typing import Any, Literal

from prompttodraft.agents.langchain_agent import LangChainAgent, get_langchain_model_example
from prompttodraft.agents.pydantic_ai_agent import PydanticAIAgent, get_pydantic_ai_model_example
from prompttodraft.agents.smolagent_agent import SmolAgentAgent, get_smolagents_model_example
from prompttodraft.backends.docker_backend import DockerBackend
from prompttodraft.backends.execution_backend import ExecutionBackend
from prompttodraft.backends.local_backend import LocalBackend
from prompttodraft.backends.state_manager import NoOpStateManager, StateManager
from prompttodraft.profiles.base_profile import ProjectProfile
from prompttodraft.profiles.empty_profile import EmptyProfile
from prompttodraft.profiles.python_uv_profile import PythonUVProfile


class AgentFactory:
    """
    Factory for creating agents with various configurations.
    """

    @staticmethod
    def create_agent(
        framework: Literal["langchain", "smolagents", "pydantic_ai"] = "langchain",
        backend_type: Literal["local", "docker"] = "local",
        language: Literal["python-uv", "empty"] = "python-uv",
        model_name: str | None = None,
        project_id: str = "default-project",
        state_manager: StateManager | None = None,
    ) -> Any:
        """
        Create a configured agent.

        Args:
            framework: The agent framework to use.
            backend_type: The execution backend type.
            language: The project language/profile.
            model_name: Optional model name override.
            project_id: Project ID for the backend.
            state_manager: Optional state manager (defaults to NoOp).

        Returns:
            An instantiated agent.
        """
        # 1. Create State Manager
        if state_manager is None:
            state_manager = NoOpStateManager()

        # 2. Create Backend
        backend: ExecutionBackend
        if backend_type == "local":
            backend = LocalBackend(project_id=project_id, state_manager=state_manager)
        elif backend_type == "docker":
            backend = DockerBackend(project_id=project_id, state_manager=state_manager)
        else:
            raise ValueError(f"Unknown backend type: {backend_type}")

        # 3. Create Profile
        profile: ProjectProfile
        if language == "python-uv":
            profile = PythonUVProfile()
        elif language == "empty":
            profile = EmptyProfile()
        else:
            raise ValueError(f"Unknown language profile: {language}")

        # 4. Create Agent
        if framework == "langchain":
            model = get_langchain_model_example(model_name) if model_name else get_langchain_model_example()
            return LangChainAgent(backend=backend, model=model, profile=profile)
        elif framework == "smolagents":
            model = get_smolagents_model_example(model_name) if model_name else get_smolagents_model_example()
            return SmolAgentAgent(backend=backend, model=model, profile=profile)
        elif framework == "pydantic_ai":
            model = get_pydantic_ai_model_example(model_name) if model_name else get_pydantic_ai_model_example()
            return PydanticAIAgent(backend=backend, model=model, profile=profile)
        else:
            raise ValueError(f"Unknown framework: {framework}")
