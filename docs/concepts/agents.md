# Agents

Agents combine an LLM with tools to perform coding tasks autonomously. Omniagents supports three AI frameworks.

## Framework Comparison

| Framework | Best For | Model Support |
|-----------|----------|---------------|
| **LangChain** | Complex chains, extensive integrations | OpenAI, Anthropic, many more |
| **Pydantic-AI** | Type-safe applications | OpenAI, Anthropic |
| **smolagents** | HuggingFace ecosystem | HuggingFace Inference API |

## LangChainAgent

Uses LangChain's tool-calling agents with LangSmith tracing.

```python
from omniagents.agents.langchain_agent import LangChainAgent
from omniagents.backends.local_backend import LocalBackend
from omniagents.backends.state_manager import NoOpStateManager
from omniagents.presets.python import PythonUVPreset
from langchain_openai import ChatOpenAI

backend = LocalBackend(project_id="demo", state_manager=NoOpStateManager())
backend.start()

agent = LangChainAgent(
    backend=backend,
    model=ChatOpenAI(model="gpt-4"),
    preset=PythonUVPreset(),
)

result = agent.run("Create a REST API with FastAPI")
print(result)

backend.shutdown()
```

**Features:**

- LangSmith tracing (set `LANGCHAIN_TRACING_V2=true`)
- Supports all LangChain chat models
- Tool execution via `create_agent`

## PydanticAIAgent

Uses Pydantic-AI for type-safe agent interactions.

```python
from omniagents.agents.pydantic_ai_agent import PydanticAIAgent
from omniagents.backends.local_backend import LocalBackend
from omniagents.backends.state_manager import NoOpStateManager
from omniagents.presets.python import PythonUVPreset
from pydantic_ai.models.openai import OpenAIModel

backend = LocalBackend(project_id="demo", state_manager=NoOpStateManager())
backend.start()

agent = PydanticAIAgent(
    backend=backend,
    model=OpenAIModel("gpt-4"),
    preset=PythonUVPreset(),
)

result = agent.run("Create a CLI calculator")
print(result)

backend.shutdown()
```

**Features:**

- Logfire instrumentation support
- Strict mode for OpenAI compatibility
- Type-safe tool definitions

## SmolagentsAgent

Uses HuggingFace's smolagents for tool-calling.

```python
from omniagents.agents.smolagents_agent import SmolagentsAgent
from omniagents.backends.local_backend import LocalBackend
from omniagents.backends.state_manager import NoOpStateManager
from omniagents.presets.python import PythonUVPreset
from smolagents import HfApiModel

backend = LocalBackend(project_id="demo", state_manager=NoOpStateManager())
backend.start()

agent = SmolagentsAgent(
    backend=backend,
    model=HfApiModel(model_id="Qwen/Qwen2.5-Coder-32B-Instruct"),
    preset=PythonUVPreset(),
    max_steps=30,  # Optional: limit iterations
)

result = agent.run("Create a web scraper")
print(result)

backend.shutdown()
```

**Features:**

- HuggingFace Inference API integration
- Configurable max steps
- ToolCallingAgent with telemetry

## AgentFactory Pattern

All agents inherit from `AgentFactory`, which handles common logic:

```python
class AgentFactory(ABC, Generic[TModel, TNativeTool]):
    def __init__(
        self,
        backend: ExecutionBackend,
        model: TModel,
        preset: Preset | None = None,
        extra_tool_classes: list[type[CoreBackendTool]] | None = None,
        native_tools: list[TNativeTool] | None = None,
    ): ...

    @abstractmethod
    def _convert_tool(self, tool: CoreBackendTool) -> TNativeTool: ...

    @abstractmethod
    def _run_agent(self, task: str) -> str: ...

    def run(self, task: str) -> str: ...
```

## Adding Custom Tools

Add your own tools alongside the core tools:

```python
from omniagents.tools.base_tool import CoreBackendTool
from omniagents.outputs.outputs import TextOutputModel
from pydantic import BaseModel, Field

# Define custom tool
class MyToolInput(BaseModel):
    query: str = Field(description="Search query")

class MySearchTool(CoreBackendTool[MyToolInput, TextOutputModel]):
    name = "my_search"
    description = "Search for information"

    def execute(self, inputs: MyToolInput) -> TextOutputModel:
        # Your logic here
        return TextOutputModel(content=f"Results for: {inputs.query}")

# Use with any agent
agent = LangChainAgent(
    backend=backend,
    model=model,
    preset=PythonUVPreset(),
    extra_tool_classes=[MySearchTool],  # Add custom tools
)
```

## Adding Native Framework Tools

Add tools specific to your framework:

```python
from langchain_community.tools import DuckDuckGoSearchRun

agent = LangChainAgent(
    backend=backend,
    model=model,
    preset=PythonUVPreset(),
    native_tools=[DuckDuckGoSearchRun()],  # LangChain-specific tools
)
```

## Managing Agent History

By default, `run()` resets conversation history. Keep history for multi-turn conversations:

```python
# First task
result1 = agent.run("Create a User model")

# Follow-up (keeps context)
result2 = agent.run("Add email validation to User", reset_history=False)

# New task (clears history)
result3 = agent.run("Create a Product model", reset_history=True)
```
