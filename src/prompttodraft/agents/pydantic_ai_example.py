"""
Example usage of the PydanticAIAgent.

This demonstrates how to use the pydantic_ai agent with different backends.
"""
from prompttodraft.agents.pydantic_ai_agent import PydanticAIAgent
from prompttodraft.backends.docker_backend import DockerBackend
from prompttodraft.backends.state_manager import GitStateManager
from dotenv import load_dotenv

load_dotenv()


def main(reset_history: bool = True) -> None:
    """Run a simple coding task with the agent."""
    # Create a backend with git storage
    project_id = "example-project-pydantic-ai"
    state_manager = GitStateManager()
    backend = DockerBackend(
        project_id=project_id,
        state_manager=state_manager,
    )

    # Start the backend (loads from git if exists)
    backend.start()

    # Create the agent
    # Note: The backend is passed here but will be injected into tools
    # via pydantic_ai's deps (AgentDependencies) at runtime
    agent = PydanticAIAgent(
        backend=backend,
        model_id="gpt-5-mini",
        provider="openai",
    )

    # Run a task
    # The backend is automatically passed to tools through RunContext[AgentDependencies]
    task = """
    Create a simple Python script called hello.py that prints "Hello, World!".
    Run it.
    Install the matplotlib library.
    Then list the files in the directory to verify it was created.
    """

    print("Running task...")
    result = agent.run(task=task)
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
