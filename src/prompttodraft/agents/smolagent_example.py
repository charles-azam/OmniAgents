"""
Example usage of the SmolAgentAgent.

This demonstrates how to use the smolagent agent with different backends.
"""
from prompttodraft.agents.smolagent_agent import SmolAgentAgent, GPT_OSS_120B_HF_SMOLAGENTS, GPT_5_MINI_OPENAI_SMOLAGENTS
from prompttodraft.backends.local_backend import LocalBackend
from prompttodraft.backends.state_manager import GitStateManager


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
    model = GPT_OSS_120B_HF_SMOLAGENTS
    # Create the agent
    agent = SmolAgentAgent(
        backend=backend,
        model=model,
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
