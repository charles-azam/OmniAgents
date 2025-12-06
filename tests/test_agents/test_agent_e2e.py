"""
End-to-end tests for all agent implementations.

This module tests LangChain, Pydantic AI, and SmolAgents agents
with a common task to verify they all work correctly.
"""
from pathlib import Path
from dotenv import load_dotenv
import pytest
from smolagents.utils import AgentGenerationError

from omniagents.agents.langchain_agent import (
    LangChainAgent,
    get_langchain_model_example,
)
from omniagents.agents.pydantic_ai_agent import (
    PydanticAIAgent,
    get_pydantic_ai_model_example,
)
from omniagents.agents.smolagent_agent import (
    SmolagentsAgent,
    get_smolagents_model_example,
)
from omniagents.backends.docker_backend import DockerBackend
from omniagents.backends.local_backend import LocalBackend
from omniagents.backends.state_manager import NoOpStateManager

load_dotenv()

# Common test task
TEST_TASK = """
Create a simple Python script called hello.py that prints "Hello, World!".
Then list the files in the directory to verify it was created.
"""


@pytest.mark.llm
def test_smolagent_agent_e2e_local() -> None:
    """Test SmolAgents agent end-to-end with file creation task."""
    # Setup
    project_id = "test-project-smolagent"
    state_manager = NoOpStateManager()
    backend = LocalBackend(
        project_id=project_id,
        state_manager=state_manager,
    )

    # Create agent with HF model
    model = get_smolagents_model_example()
    agent = SmolagentsAgent(
        backend=backend,
        model=model,
    )

    # Run task
    result = agent.run(task=TEST_TASK, reset_history=True)

    # Verify output
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0

    # Verify file was created (this is the real test)
    backend.start()
    # For verification, we need to access the file using backend methods
    # which now expect virtual paths (/workspace/...)
    hello_file_virtual = Path("/workspace/hello.py")
    
    # Check existence using backend method which handles virtual->host mapping
    assert backend.file_exists(hello_file_virtual), "hello.py should be created"

    # Verify file content
    content = backend.read_file(hello_file_virtual)
    assert "Hello, World!" in content or "Hello World" in content

    # Cleanup
    backend.shutdown()



@pytest.mark.llm
def test_smolagent_agent_e2e_docker() -> None:
    """Test SmolAgents agent end-to-end with file creation task."""
    # Setup
    project_id = "test-project-smolagent"
    state_manager = NoOpStateManager()
    backend = DockerBackend(
        project_id=project_id,
        state_manager=state_manager,
    )

    # Create agent with HF model
    model = get_smolagents_model_example()
    agent = SmolagentsAgent(
        backend=backend,
        model=model,
    )

    # Run task
    result = agent.run(task=TEST_TASK, reset_history=True)

    # Verify output
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0

    # Verify file was created (this is the real test)
    backend.start()
    # For verification, we need to access the file using backend methods
    # which now expect virtual paths (/workspace/...)
    hello_file_virtual = Path("/workspace/hello.py")
    
    # Check existence using backend method which handles virtual->host mapping
    assert backend.file_exists(hello_file_virtual), "hello.py should be created"

    # Verify file content
    content = backend.read_file(hello_file_virtual)
    assert "Hello, World!" in content or "Hello World" in content

    # Cleanup
    backend.shutdown()



@pytest.mark.llm
def test_pydantic_ai_agent_e2e_local() -> None:
    """Test Pydantic AI agent end-to-end with file creation task."""
    # Setup
    project_id = "test-project-pydantic-ai"
    state_manager = NoOpStateManager()
    backend = LocalBackend(
        project_id=project_id,
        state_manager=state_manager,
    )

    # Create agent with HF model
    model = get_pydantic_ai_model_example()
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

    # Verify file was created (this is the real test)
    backend.start()
    # For verification, we need to access the file using backend methods
    # which now expect virtual paths (/workspace/...)
    hello_file_virtual = Path("/workspace/hello.py")
    
    # Check existence using backend method which handles virtual->host mapping
    assert backend.file_exists(hello_file_virtual), "hello.py should be created"

    # Verify file content
    content = backend.read_file(hello_file_virtual)
    assert "Hello, World!" in content or "Hello World" in content

    # Cleanup
    backend.shutdown()



@pytest.mark.llm
def test_pydantic_ai_agent_e2e_docker() -> None:
    """Test Pydantic AI agent end-to-end with file creation task."""
    # Setup
    project_id = "test-project-pydantic-ai"
    state_manager = NoOpStateManager()
    backend = DockerBackend(
        project_id=project_id,
        state_manager=state_manager,
    )

    # Create agent with HF model
    model = get_pydantic_ai_model_example()
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

    # Verify file was created (this is the real test)
    backend.start()
    # For verification, we need to access the file using backend methods
    # which now expect virtual paths (/workspace/...)
    hello_file_virtual = Path("/workspace/hello.py")
    
    # Check existence using backend method which handles virtual->host mapping
    assert backend.file_exists(hello_file_virtual), "hello.py should be created"

    # Verify file content
    content = backend.read_file(hello_file_virtual)
    assert "Hello, World!" in content or "Hello World" in content

    # Cleanup
    backend.shutdown()



@pytest.mark.llm
def test_langchain_agent_e2e_local() -> None:
    """Test LangChain agent end-to-end with file creation task."""
    # Setup
    project_id = "test-project-langchain"
    state_manager = NoOpStateManager()
    backend = LocalBackend(
        project_id=project_id,
        state_manager=state_manager,
    )

    # Create agent with HF model
    model = get_langchain_model_example()
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

    # Verify file was created (this is the real test)
    backend.start()
    # For verification, we need to access the file using backend methods
    # which now expect virtual paths (/workspace/...)
    hello_file_virtual = Path("/workspace/hello.py")
    
    # Check existence using backend method which handles virtual->host mapping
    assert backend.file_exists(hello_file_virtual), "hello.py should be created"

    # Verify file content
    content = backend.read_file(hello_file_virtual)
    assert "Hello, World!" in content or "Hello World" in content

    # Cleanup
    backend.shutdown()



@pytest.mark.llm
def test_langchain_agent_e2e_docker() -> None:
    """Test LangChain agent end-to-end with file creation task."""
    # Setup
    project_id = "test-project-langchain"
    state_manager = NoOpStateManager()
    backend = DockerBackend(
        project_id=project_id,
        state_manager=state_manager,
    )

    # Create agent with HF model
    model = get_langchain_model_example()
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

    # Verify file was created (this is the real test)
    backend.start()
    # For verification, we need to access the file using backend methods
    # which now expect virtual paths (/workspace/...)
    hello_file_virtual = Path("/workspace/hello.py")
    
    # Check existence using backend method which handles virtual->host mapping
    assert backend.file_exists(hello_file_virtual), "hello.py should be created"

    # Verify file content
    content = backend.read_file(hello_file_virtual)
    assert "Hello, World!" in content or "Hello World" in content

    # Cleanup
    backend.shutdown()



if __name__ == "__main__":
    test_smolagent_agent_e2e_docker()
    test_smolagent_agent_e2e_local()
    test_langchain_agent_e2e_docker()
    test_langchain_agent_e2e_local()
    test_pydantic_ai_agent_e2e_docker()
    test_pydantic_ai_agent_e2e_local()