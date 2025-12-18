# Agents API Reference

## AgentFactory (Abstract Base)

All framework agents inherit from `AgentFactory`.

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
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `backend` | `ExecutionBackend` | Execution environment |
| `model` | `TModel` | Framework-specific LLM model |
| `preset` | `Preset \| None` | Language preset (Python, etc.) |
| `extra_tool_classes` | `list[type[CoreBackendTool]]` | Additional custom tools |
| `native_tools` | `list[TNativeTool]` | Framework-native tools |

### Methods

```python
def run(self, task: str, reset_history: bool = True) -> str:
    """
    Execute a coding task.

    Args:
        task: Natural language description of the task
        reset_history: Clear conversation history (default: True)

    Returns:
        Agent's final response as string
    """

@abstractmethod
def _convert_tool(self, tool: CoreBackendTool) -> TNativeTool:
    """Convert CoreBackendTool to framework-specific format."""

@abstractmethod
def _run_agent(self, task: str) -> str:
    """Execute the framework-specific agent logic."""
```

---

## LangChainAgent

Uses LangChain for agent execution.

```python
from omniagents.agents.langchain_agent import LangChainAgent
from langchain_openai import ChatOpenAI

agent = LangChainAgent(
    backend=backend,
    model=ChatOpenAI(model="gpt-4"),
    preset=PythonUVPreset(),
    extra_tool_classes=[MyCustomTool],
    native_tools=[DuckDuckGoSearchRun()],
)

result = agent.run("Create a REST API")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `backend` | `ExecutionBackend` | Required |
| `model` | `BaseChatModel` | LangChain chat model |
| `preset` | `Preset` | Optional language preset |
| `extra_tool_classes` | `list[type[CoreBackendTool]]` | Custom tools |
| `native_tools` | `list[LangChainTool]` | LangChain tools |

**Features**:

- LangSmith tracing (set `LANGCHAIN_TRACING_V2=true`)
- Uses `create_agent` for tool calling
- Supports all LangChain chat models

**Supported Models**:

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

model = ChatOpenAI(model="gpt-4")
model = ChatAnthropic(model="claude-3-sonnet")
model = ChatGoogleGenerativeAI(model="gemini-pro")
```

---

## PydanticAIAgent

Uses Pydantic-AI for type-safe agent execution.

```python
from omniagents.agents.pydantic_ai_agent import PydanticAIAgent
from pydantic_ai.models.openai import OpenAIModel

agent = PydanticAIAgent(
    backend=backend,
    model=OpenAIModel("gpt-4"),
    preset=PythonUVPreset(),
)

result = agent.run("Create a CLI tool")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `backend` | `ExecutionBackend` | Required |
| `model` | `OpenAIChatModel` | Pydantic-AI model |
| `preset` | `Preset` | Optional language preset |
| `extra_tool_classes` | `list[type[CoreBackendTool]]` | Custom tools |

**Features**:

- Logfire instrumentation support
- Strict mode for OpenAI compatibility
- Type-safe tool definitions

**Supported Models**:

```python
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.anthropic import AnthropicModel

model = OpenAIModel("gpt-4")
model = AnthropicModel("claude-3-sonnet")
```

---

## SmolagentsAgent

Uses HuggingFace smolagents for execution.

```python
from omniagents.agents.smolagents_agent import SmolagentsAgent
from smolagents import HfApiModel, InferenceClientModel

agent = SmolagentsAgent(
    backend=backend,
    model=HfApiModel(model_id="Qwen/Qwen2.5-Coder-32B-Instruct"),
    preset=PythonUVPreset(),
    max_steps=30,
)

result = agent.run("Create a data pipeline")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `backend` | `ExecutionBackend` | Required |
| `model` | `HfApiModel \| InferenceClientModel` | smolagents model |
| `preset` | `Preset` | Optional language preset |
| `extra_tool_classes` | `list[type[CoreBackendTool]]` | Custom tools |
| `max_steps` | `int` | Max agent iterations (default: 30) |

**Features**:

- HuggingFace Inference API integration
- Configurable max steps
- ToolCallingAgent with telemetry

**Supported Models**:

```python
from smolagents import HfApiModel, InferenceClientModel

model = HfApiModel(model_id="Qwen/Qwen2.5-Coder-32B-Instruct")
model = InferenceClientModel(model_id="meta-llama/Llama-3-70B-Instruct")
```

---

## Core Tools

All agents automatically include these tools:

| Tool | Purpose |
|------|---------|
| `ListDirectoryTool` | List directory contents |
| `ReadFileTool` | Read files |
| `WriteFileTool` | Write files |
| `GlobTool` | Find files by pattern |
| `SearchFileContentTool` | Search file contents |
| `ReplaceTool` | Replace text in files |
| `RunShellCommandTool` | Execute commands |
| `ReadManyFilesTool` | Read multiple files |
| `SaveMemoryTool` | Persistent memory |

Plus any tools from the preset (e.g., `UVTool` for `PythonUVPreset`).

---

## Usage Patterns

### Single Task

```python
result = agent.run("Create a hello world script")
```

### Multi-turn Conversation

```python
result1 = agent.run("Create a User model")
result2 = agent.run("Add validation", reset_history=False)
result3 = agent.run("Add tests", reset_history=False)
```

### Custom System Prompt

System prompts are defined in `omniagents/prompts/system_prompt.py`. Modify for custom behavior.

### Adding Custom Tools

```python
from omniagents.tools.base_tool import CoreBackendTool
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    query: str = Field(description="Search query")

class WebSearchTool(CoreBackendTool[SearchInput, TextOutputModel]):
    name = "web_search"
    description = "Search the web"

    def execute(self, inputs: SearchInput) -> TextOutputModel:
        # Implementation
        return TextOutputModel(content="results...")

agent = LangChainAgent(
    backend=backend,
    model=model,
    preset=preset,
    extra_tool_classes=[WebSearchTool],
)
```
