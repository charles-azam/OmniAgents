"""
Example usage of the SmolagentsAgent.

This demonstrates how to use the smolagent agent with different backends and presets.
"""
from anyagent.agents.smolagent_agent import SmolagentsAgent, get_smolagents_model_example
from anyagent.backends.local_backend import LocalBackend
from anyagent.backends.state_manager import GitStateManager
from anyagent.presets.python import PythonUVPreset


def main() -> None:
    """Run a simple coding task with the agent."""
    # Create a backend with git storage
    project_id = "example-project-smolagent"
    state_manager = GitStateManager()
    backend = LocalBackend(
        project_id=project_id,
        state_manager=state_manager,
    )

    # Create the model
    model = get_smolagents_model_example()

    # Create the agent with Python UV preset
    agent = SmolagentsAgent(
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
