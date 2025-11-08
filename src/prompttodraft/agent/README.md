# AI Coding Agent Tools

A flexible toolkit for building AI coding agents that can operate in multiple execution environments (local, Docker, E2B) and integrate with multiple AI frameworks (smolagents, OpenAI, Pydantic-AI, Autogen).

## Overview

This toolkit provides **Gemini CLI-inspired coding tools** with a **3-layer architecture** that separates execution environments from business logic and framework integration:

```
┌─────────────────────────────────────────┐
│    Framework Integrations (Layer 3)     │
│  smolagents, Pydantic-AI, LangChain     │
│  - Manual tool wrappers per framework   │
│  - Converts to framework-specific API   │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│    Core Tools (Layer 2)                 │
│  Gemini CLI-based tools                 │
│  - list_directory, read_file, etc.      │
│  - Business logic & validation          │
│  - Returns ToolOutputModel instances    │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│    Execution Backends (Layer 1)         │
│  Local, Docker, E2B                     │
│  - Primitive operations only            │
│  - execute_command, read_file, etc.     │
└─────────────────────────────────────────┘
```

## Gemini CLI Tools

The toolkit implements these tools from Gemini CLI:

1. **`list_directory`** - List directory contents with filtering
2. **`read_file`** - Read text, images, and PDFs
3. **`write_file`** - Write content to files
4. **`glob`** - Find files matching patterns
5. **`search_file_content`** - Search with regex (grep)
6. **`replace`** - Precise text replacement with context
7. **`run_shell_command`** - Execute shell commands
8. **`read_many_files`** - Read multiple files at once
9. **`save_memory`** - Persistent memory across sessions
10. **`uv`** - Execute uv package manager commands

## Key Design Principles

### 1. Execution Environment Independence

Tools work across **any execution environment** without code changes:
- **Local**: Direct filesystem and subprocess execution
- **Docker**: Isolated container environment
- **E2B**: Remote sandbox with persistent state

### 2. Framework Agnostic Core

Core tools have **zero framework dependencies**. Framework-specific integrations wrap core tools:
- **smolagents**: Manual `Tool` wrappers in `smolagent_agent.py`
- **Pydantic-AI**: Tool definitions in `pydantic_ai_agent.py`
- **LangChain**: Tool wrappers in `langchain_agent.py`

### 3. Output Separation

Tools return **Pydantic output models** that handle their own display:
- **Console mode**: Rich terminal output with syntax highlighting
- **API mode**: JSON serialization for web APIs
- **Hybrid mode**: Both console output and JSON return

## Directory Structure

```
agent/
├── backends/          # Execution environments
│   ├── execution_backend.py    # Abstract interface
│   ├── local_backend.py        # Local implementation
│   ├── docker_backend.py       # Docker container
│   ├── e2b_backend.py          # E2B sandbox
│   └── state_manager.py        # State persistence (Git/GCS/None)
├── core/              # Framework-agnostic tools
│   ├── base_tool.py           # CoreTool abstract base class
│   ├── metadata.py            # Tool metadata definition
│   ├── list_directory_tool.py # list_directory
│   ├── read_file_tool.py      # read_file
│   ├── write_file_tool.py     # write_file
│   ├── glob_tool.py           # glob
│   ├── search_file_content_tool.py  # search_file_content
│   ├── replace_tool.py        # replace
│   ├── run_shell_command_tool.py    # run_shell_command
│   ├── read_many_files_tool.py      # read_many_files
│   ├── save_memory_tool.py    # save_memory
│   └── uv_tool.py             # uv
├── outputs/           # Output models
│   ├── models.py              # Pydantic models
│   └── README.md
├── smolagent_agent.py  # smolagents framework integration
├── pydantic_ai_agent.py # Pydantic-AI framework integration
└── langchain_agent.py  # LangChain framework integration
```

## Architecture Benefits

### Mix and Match

Combine **any execution environment** with **any framework** and **any storage**:

```python
from prompttodraft.agent.smolagent_agent import SmolAgentAgent
from prompttodraft.agent.backends.local_backend import LocalBackend
from prompttodraft.agent.backends.docker_backend import DockerBackend
from prompttodraft.agent.backends.state_manager import GitStateManager, GCSStateManager

# Local execution with smolagents + Git storage
backend = LocalBackend(project_id="my-project", state_manager=GitStateManager())
backend.start()
agent = SmolAgentAgent(backend=backend, provider="huggingface", model_id="Qwen/Qwen2.5-Coder-32B-Instruct")

# Docker execution with smolagents + GCS storage
docker_backend = DockerBackend(project_id="my-project", state_manager=GCSStateManager())
docker_backend.start()
agent = SmolAgentAgent(backend=docker_backend, provider="huggingface", model_id="Qwen/Qwen2.5-Coder-32B-Instruct")
```

### Write Once, Use Anywhere

- Business logic written **once** in core tools
- Execution logic written **once** in backends
- Framework integration is **thin adapters only**

### Easy to Extend

**Add a new environment**:
1. Implement `ExecutionBackend` interface
2. All tools work automatically

**Add a new framework**:
1. Create a new agent file (e.g., `myframework_agent.py`)
2. Wrap core tools in framework-specific format
3. See `smolagent_agent.py` as example

**Add a new tool**:
1. Create core tool inheriting from `CoreTool` with metadata
2. Add manual wrappers in framework agent files
3. Works in all environments

## Quick Start

### Using Core Tools Directly

```python
from prompttodraft.agent.backends.local_backend import LocalBackend
from prompttodraft.agent.core.read_file_tool import ReadFileTool

# Create backend
backend = LocalBackend(project_id="my-project")
backend.start()

# Create and use tool
tool = ReadFileTool(backend=backend)
result = tool.execute(absolute_path="/path/to/file.py")

# Handle output (console mode by default)
output = result.handle()
```

### Using with smolagents

```python
from prompttodraft.agent.smolagent_agent import SmolAgentAgent
from prompttodraft.agent.backends.local_backend import LocalBackend
from prompttodraft.agent.backends.state_manager import GitStateManager

# Create backend (with Git storage)
backend = LocalBackend(project_id="my-project", state_manager=GitStateManager())
backend.start()

# Create agent
agent = SmolAgentAgent(backend=backend, provider="huggingface", model_id="Qwen/Qwen2.5-Coder-32B-Instruct")

# Use agent
result = agent.run("List all Python files")
```

## Output Models

All tools return `ToolOutputModel` instances that adapt to the environment:

```python
import os
os.environ["DISPLAY_MODE"] = "console"  # Rich terminal output (default)
os.environ["DISPLAY_MODE"] = "api"      # JSON dict for APIs
os.environ["DISPLAY_MODE"] = "hybrid"   # Both console + JSON

# Tool execution
result = tool.execute(...)
output = result.handle()  # Automatically adapts based on DISPLAY_MODE
```

## State Management

Backends handle persistent state with cloud storage using two storage options:

### Storage Types

**Git Storage** (default):
- Uses GitHub branches for state persistence
- Each project gets its own branch
- Automatic commit and push on `save_snapshot()`
- Fast and free for small/medium projects

**GCS Storage**:
- Uses Google Cloud Storage buckets
- Timestamped snapshots for each save
- Better for large files or non-git workflows
- Requires GCS credentials

### Usage

```python
from prompttodraft.agent.backends.local_backend import LocalBackend
from prompttodraft.agent.backends.state_manager import GitStateManager, GCSStateManager, NoOpStateManager

# Using Git storage (default)
backend = LocalBackend(project_id="my-project", state_manager=GitStateManager())
backend.start()  # Loads from git branch

# Using GCS storage
backend = LocalBackend(project_id="my-project", state_manager=GCSStateManager())
backend.start()  # Loads from GCS bucket

# No persistence
backend = LocalBackend(project_id="my-project", state_manager=NoOpStateManager())
```

### Lifecycle Methods

- `start()`: Load files from storage, create environment
- `shutdown()`: Save state and destroy environment
- State is managed via `StateManager`:
  - `save_snapshot()`: Save current state (timestamped snapshots)
  - `load_latest()`: Restore latest state

## Testing

All layers are independently testable:

```python
# Mock backend for unit testing
class MockBackend(ExecutionBackend):
    def execute_command(self, command, timeout):
        return CommandResult(output="mocked", exit_code=0)

# Test core tool
tool = RunShellCommandTool(backend=MockBackend())
result = tool.execute(command="echo test")
```

## Design Patterns

- **Strategy Pattern**: Swappable backends (Local, Docker, E2B)
- **Adapter Pattern**: Framework adapters (smolagents, OpenAI, etc.)
- **Abstract Base Class**: `CoreTool` ensures consistent tool interface
- **Separation of Concerns**: Data (models) vs. Presentation (display)

## See Also

- [`backends/README.md`](backends/README.md) - Execution backend details
- [`core/README.md`](core/README.md) - Core tools and Gemini CLI reference
- [`outputs/README.md`](outputs/README.md) - Output models and display modes


