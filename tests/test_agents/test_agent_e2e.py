"""
End-to-end tests for all agent implementations.

This module tests LangChain, Pydantic AI, and SmolAgents agents
with a common task to verify they all work correctly.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

from prompttodraft.agents.langchain_agent import (
    LangChainAgent,
    GPT_OSS_120B_HF_LANGCHAIN,
    GPT_5_MINI_OPENAI_LANGCHAIN,
)
from prompttodraft.agents.pydantic_ai_agent import (
    PydanticAIAgent,
    GPT_OSS_120B_HF_PYDANTIC_AI,
    GPT_5_MINI_OPENAI_PYDANTIC_AI,
)
from prompttodraft.agents.smolagent_agent import (
    SmolAgentAgent,
    GPT_OSS_120B_HF_SMOLAGENTS,
    GPT_5_MINI_OPENAI_SMOLAGENTS,
)
from prompttodraft.backends.docker_backend import DockerBackend
from prompttodraft.backends.local_backend import LocalBackend
from prompttodraft.backends.state_manager import NoOpStateManager

load_dotenv()

# Common test task
TEST_TASK = """
Create a simple Python script called hello.py that prints "Hello, World!".
Then list the files in the directory to verify it was created.
"""


def test_langchain_agent_e2e() -> None:
    """Test LangChain agent end-to-end with file creation task."""
    # Setup
    project_id = "test-project-langchain"
    state_manager = NoOpStateManager()
    backend = LocalBackend(
        project_id=project_id,
        state_manager=state_manager,
    )

    # Create agent with HF model
    model = GPT_5_MINI_OPENAI_LANGCHAIN
    agent = LangChainAgent(
        backend=backend,
        model=model,
    )

    # Run task
    result = agent.run(task=TEST_TASK, reset_history=True)

    # Verify output
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0

    # Verify file was created
    backend.start()
    workspace_path = Path(backend.get_working_directory())
    hello_file = workspace_path / "hello.py"
    assert hello_file.exists(), "hello.py should be created"

    # Verify file content
    content = hello_file.read_text()
    assert "Hello, World!" in content or "Hello World" in content

    # Cleanup
    backend.shutdown()


def test_pydantic_ai_agent_e2e() -> None:
    """Test Pydantic AI agent end-to-end with file creation task."""
    # Setup
    project_id = "test-project-pydantic-ai"
    state_manager = NoOpStateManager()
    backend = LocalBackend(
        project_id=project_id,
        state_manager=state_manager,
    )

    # Create agent with HF model
    model = GPT_5_MINI_OPENAI_PYDANTIC_AI
    agent = PydanticAIAgent(
        backend=backend,
        model=model,
    )

    # Run task
    result = agent.run(task=TEST_TASK, reset_history=True)

    # Verify output
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0

    # Verify file was created
    backend.start()
    workspace_path = Path(backend.get_working_directory())
    hello_file = workspace_path / "hello.py"
    assert hello_file.exists(), "hello.py should be created"

    # Verify file content
    content = hello_file.read_text()
    assert "Hello, World!" in content or "Hello World" in content

    # Cleanup
    backend.shutdown()


def test_smolagent_agent_e2e() -> None:
    """Test SmolAgents agent end-to-end with file creation task."""
    # Setup
    project_id = "test-project-smolagent"
    state_manager = NoOpStateManager()
    backend = DockerBackend(
        project_id=project_id,
        state_manager=state_manager,
    )

    # Create agent with HF model
    model = GPT_OSS_120B_HF_SMOLAGENTS
    agent = SmolAgentAgent(
        backend=backend,
        model=model,
    )

    # Run task
    result = agent.run(task=TEST_TASK, reset_history=True)

    # Verify output
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0

    # Verify file was created
    backend.start()
    workspace_path = Path(backend.get_working_directory())
    hello_file = workspace_path / "hello.py"
    assert hello_file.exists(), "hello.py should be created"

    # Verify file content
    content = hello_file.read_text()
    assert "Hello, World!" in content or "Hello World" in content

    # Cleanup
    backend.shutdown()

if __name__ == "__main__":
    # test_langchain_agent_e2e()
    # test_pydantic_ai_agent_e2e()
    test_smolagent_agent_e2e()