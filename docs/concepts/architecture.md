# Architecture

Omniagents uses a clean 3-layer architecture that separates concerns and enables maximum flexibility.

## The Three Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Your Application                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LangChainAgent         SmolagentsAgent        PydanticAIAgent              │
│       │                      │                      │                       │
│       └──────────────────────┼──────────────────────┘                       │
│                              │                                              │
│                              ▼                                              │
│                      ┌─────────────────┐                                    │
│                      │  AgentFactory   │  ← Abstract base class             │
│                      └─────────────────┘                                    │
│                              │                                              │
│              ┌───────────────┼───────────────┐                              │
│              ▼               ▼               ▼                              │
│      ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│      │   Backend   │  │   Preset    │  │ Core Tools  │                      │
│      │ Local/Docker│  │ Python/Node │  │ 10 tools    │                      │
│      │    /E2B     │  │  /Generic   │  │             │                      │
│      └──────┬──────┘  └─────────────┘  └─────────────┘                      │
│             │                                                               │
│             ▼                                                               │
│      ┌─────────────┐                                                        │
│      │StateManager │                                                        │
│      │None/Git/GCS │                                                        │
│      └─────────────┘                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Layer 1: Execution Backends

The lowest layer provides primitive operations:

- **Execute commands** in bash
- **Read/write files**
- **List directories**
- **Manage lifecycle** (start, shutdown)

Three implementations:

| Backend | Environment | Isolation | Best For |
|---------|-------------|-----------|----------|
| `LocalBackend` | Host machine | None | Development |
| `DockerBackend` | Docker container | Container | Testing |
| `E2BBackend` | Cloud sandbox | Full | Production |

### Layer 2: Core Tools

Framework-agnostic coding tools that use backends for operations:

| Tool | Purpose |
|------|---------|
| `WriteFileTool` | Create/overwrite files |
| `ReadFileTool` | Read text, images, PDFs |
| `ListDirectoryTool` | List directory contents |
| `GlobTool` | Find files by pattern |
| `SearchFileContentTool` | Regex search (grep) |
| `ReplaceTool` | Precise text replacement |
| `RunShellCommandTool` | Execute shell commands |
| `ReadManyFilesTool` | Batch file reading |
| `SaveMemoryTool` | Persistent key-value storage |
| `UVTool` | UV package manager |

### Layer 3: Framework Integration

Adapters that convert core tools to framework-specific formats:

- **LangChainAgent** - Uses LangChain's tool format
- **SmolagentsAgent** - Uses smolagents' tool format
- **PydanticAIAgent** - Uses Pydantic-AI's tool format

## Data Flow

```
User Request: "Create a FastAPI server"
                    │
                    ▼
┌──────────────────────────────────────┐
│  Framework Agent (e.g., LangChain)   │
│  - Interprets task                   │
│  - Decides which tools to call       │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│  Core Tool (e.g., WriteFileTool)     │
│  - Validates input (Pydantic)        │
│  - Calls backend primitives          │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│  Backend (e.g., DockerBackend)       │
│  - Executes in target environment    │
│  - Returns raw result                │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│  ToolOutputModel                     │
│  - Formats result for framework      │
│  - Adapts to display mode            │
└──────────────────────────────────────┘
```

## Design Patterns

### Strategy Pattern

Swappable implementations at each layer:

```python
# Swap backends without changing tool code
backend = LocalBackend(...)  # or DockerBackend, E2BBackend

# Swap state managers without changing backend code
state_manager = GitStateManager()  # or GCSStateManager, NoOpStateManager
```

### Abstract Base Class

Consistent interfaces via ABCs:

```python
class ExecutionBackend(ABC):
    @abstractmethod
    def execute_command(self, command: str) -> CommandResult: ...

    @abstractmethod
    def read_file(self, path: str) -> str: ...
```

### Factory Pattern

`AgentFactory` handles common logic, subclasses implement framework-specific behavior:

```python
class AgentFactory(ABC, Generic[TModel, TNativeTool]):
    @abstractmethod
    def _convert_tool(self, tool: CoreBackendTool) -> TNativeTool: ...

    @abstractmethod
    def _run_agent(self, task: str) -> str: ...
```

## Benefits of This Architecture

1. **Write tools once** - Same code works in all environments
2. **Test in isolation** - Mock any layer for unit tests
3. **Mix and match** - Any backend + any framework + any storage
4. **Easy extension** - Add new backends, tools, or frameworks independently
5. **Clear boundaries** - Each layer has single responsibility
