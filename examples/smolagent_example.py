"""
Example usage of the SmolAgentAgent.

This demonstrates how to use the smolagent agent with different backends.
"""
from prompttodraft.agent.smolagent_agent import SmolAgentAgent
from prompttodraft.agent.backends.local_backend import LocalBackend
from prompttodraft.agent.backends.state_manager import GitStateManager


def main() -> None:
    """Run a simple coding task with the agent."""
    # Create a backend with git storage
    project_id = "example-project-smolagent"
    state_manager = GitStateManager()
    backend = LocalBackend(
        project_id=project_id,
        state_manager=state_manager,
    )

    # Start the backend (loads from git if exists)
    backend.start()

    # Create the agent
    agent = SmolAgentAgent(
        backend=backend,
        model_id="openai/gpt-oss-120b",
        provider="huggingface",
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
