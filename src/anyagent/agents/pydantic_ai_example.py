"""
Example usage of the PydanticAIAgent.

This demonstrates how to use the pydantic_ai agent with different backends and presets.
"""
from anyagent.agents.pydantic_ai_agent import PydanticAIAgent, get_pydantic_ai_model_example
from anyagent.backends.docker_backend import DockerBackend
from anyagent.backends.state_manager import GitStateManager
from anyagent.presets.python import PythonUVPreset
from dotenv import load_dotenv

load_dotenv()


def main(reset_history: bool = True) -> None:
    """Run a simple coding task with the agent."""
    # Create a backend with git storage
    project_id = "example-project-pydantic-ai"
    state_manager = GitStateManager()

    # Create preset
    preset = PythonUVPreset()

    # Create backend with preset's suggested Docker image
    backend = DockerBackend(
        project_id=project_id,
        state_manager=state_manager,
        image=preset.docker_image,
    )

    # Create the model
    model = get_pydantic_ai_model_example()

    # Create the agent with Python UV preset
    agent = PydanticAIAgent(
        backend=backend,
        model=model,
        preset=preset,
    )

    # Run a task
    task = """
    Create a simple Python script called hello.py that prints "Hello, World!".
    Run it.
    Install the matplotlib library.
    Then list the files in the directory to verify it was created.
    """

    print("Running task...")
    result = agent.run(task=task, reset_history=reset_history)
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
