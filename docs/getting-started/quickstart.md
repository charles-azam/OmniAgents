# Quick Start

This guide will help you create your first AI coding agent in under 5 minutes.

## Step 1: Create a Backend

The backend determines where your code runs. Start with `LocalBackend` for development:

```python
from omniagents.backends.local_backend import LocalBackend
from omniagents.backends.state_manager import NoOpStateManager

backend = LocalBackend(
    project_id="my-first-agent",
    state_manager=NoOpStateManager()  # No persistence for now
)
backend.start()
```

## Step 2: Use Tools Directly

You can use tools without an AI agent:

```python
from omniagents.tools.write_file_tool import WriteFileTool
from omniagents.tools.run_shell_command_tool import RunShellCommandTool

# Write a Python file
write_tool = WriteFileTool(backend=backend)
write_tool.execute(
    absolute_path="hello.py",
    content="print('Hello from Omniagents!')"
)

# Run it
shell_tool = RunShellCommandTool(backend=backend)
result = shell_tool.execute(command="python hello.py")
print(result.content)  # "Hello from Omniagents!"
```

## Step 3: Create an AI Agent

Now let's add an AI model to automate coding tasks:

=== "LangChain"

    ```python
    from omniagents.agents.langchain_agent import LangChainAgent
    from omniagents.presets.python import PythonUVPreset
    from langchain_openai import ChatOpenAI

    agent = LangChainAgent(
        backend=backend,
        model=ChatOpenAI(model="gpt-4"),
        preset=PythonUVPreset(),
    )

    result = agent.run("Create a function that calculates fibonacci numbers")
    ```

=== "Pydantic-AI"

    ```python
    from omniagents.agents.pydantic_ai_agent import PydanticAIAgent
    from omniagents.presets.python import PythonUVPreset
    from pydantic_ai.models.openai import OpenAIModel

    agent = PydanticAIAgent(
        backend=backend,
        model=OpenAIModel("gpt-4"),
        preset=PythonUVPreset(),
    )

    result = agent.run("Create a function that calculates fibonacci numbers")
    ```

=== "smolagents"

    ```python
    from omniagents.agents.smolagents_agent import SmolagentsAgent
    from omniagents.presets.python import PythonUVPreset
    from smolagents import HfApiModel

    agent = SmolagentsAgent(
        backend=backend,
        model=HfApiModel(model_id="Qwen/Qwen2.5-Coder-32B-Instruct"),
        preset=PythonUVPreset(),
    )

    result = agent.run("Create a function that calculates fibonacci numbers")
    ```

## Step 4: Add State Persistence

Save your work between sessions with Git:

```python
from omniagents.backends.state_manager import GitStateManager

backend = LocalBackend(
    project_id="my-project",
    state_manager=GitStateManager()
)
backend.start()  # Loads previous state from Git

# ... do work ...

backend.shutdown()  # Saves state to Git
```

## Step 5: Run in Docker (Isolated)

For production or when you need isolation:

```python
from omniagents.backends.docker_backend import DockerBackend
from omniagents.presets.python import PythonUVPreset

preset = PythonUVPreset()

backend = DockerBackend(
    project_id="isolated-project",
    state_manager=GitStateManager(),
    image=preset.docker_image,  # Uses preset's recommended image
)
backend.start()  # Creates Docker container

agent = LangChainAgent(backend=backend, model=model, preset=preset)
result = agent.run("Install pandas and create a data analysis script")

backend.shutdown()  # Stops container, saves state
```

## Complete Example

Here's a complete working example:

```python
from omniagents.agents.langchain_agent import LangChainAgent
from omniagents.backends.local_backend import LocalBackend
from omniagents.backends.state_manager import NoOpStateManager
from omniagents.presets.python import PythonUVPreset
from langchain_openai import ChatOpenAI
import os

# Set your OpenAI API key
os.environ["OPENAI_API_KEY"] = "your-key-here"

# Create backend
backend = LocalBackend(
    project_id="quickstart-demo",
    state_manager=NoOpStateManager()
)
backend.start()

# Create agent
agent = LangChainAgent(
    backend=backend,
    model=ChatOpenAI(model="gpt-4"),
    preset=PythonUVPreset(),
)

# Run a task
result = agent.run("""
Create a simple CLI calculator that:
1. Takes two numbers and an operation (+, -, *, /)
2. Prints the result
3. Handles division by zero
""")

print(result)

# Clean up
backend.shutdown()
```

## Next Steps

- [Architecture](../concepts/architecture.md) - Understand how Omniagents works
- [Backends](../concepts/backends.md) - Learn about Local, Docker, and E2B
- [Tools Reference](../api/tools.md) - See all 10 available tools
