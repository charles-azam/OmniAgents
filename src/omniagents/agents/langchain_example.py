"""
Example usage of the LangChainAgent.

This demonstrates how to use the LangChain agent with different backends and presets.
"""
from omniagents.agents.langchain_agent import LangChainAgent, get_langchain_model_example
from omniagents.backends.local_backend import LocalBackend
from omniagents.backends.state_manager import NoOpStateManager
from omniagents.presets.python import PythonUVPreset
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    """Run a simple coding task with the agent."""
    # Create a backend with no state persistence
    project_id = "example-project-langchain"
    state_manager = NoOpStateManager()
    backend = LocalBackend(
        project_id=project_id,
        state_manager=state_manager,
    )

    # Create the model
    model = get_langchain_model_example()

    # Create the agent with Python UV preset
    agent = LangChainAgent(
        backend=backend,
        model=model,
        preset=PythonUVPreset(),
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
