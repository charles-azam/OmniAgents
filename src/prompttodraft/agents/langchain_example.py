"""
Example usage of the LangChainAgent.

This demonstrates how to use the LangChain agent with different backends.
"""
from prompttodraft.agents.langchain_agent import LangChainAgent
from prompttodraft.backends.local_backend import LocalBackend
from prompttodraft.backends.state_manager import GitStateManager
from prompttodraft.initializers.python_initializer import PythonInitializer
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    """Run a simple coding task with the agent."""
    # Create a backend with git storage
    project_id = "example-project-langchain"
    state_manager = GitStateManager()

    # Create initializer (backend will be set after backend creation)
    initializer = PythonInitializer()

    backend = LocalBackend(
        project_id=project_id,
        state_manager=state_manager,
        initializer=initializer,
    )

    # Set backend reference in initializer (resolves circular dependency)
    initializer.backend = backend
    initializer.working_dir = backend.get_working_directory()

    # Start the backend (loads from git if exists)
    backend.start()

    # Initialize the project if not already initialized
    if not initializer.is_initialized():
        initializer.initialize()

    # Create the agent
    agent = LangChainAgent(
        backend=backend,
        model_id="gpt-5-mini",
        provider="openai",
    )

    # Run a task
    task = """
    Create a simple Python script called hello.py that prints "Hello, World!".
    Then list the files in the directory to verify it was created.
    """

    print("Running task...")
    result = agent.run(task=task)
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
