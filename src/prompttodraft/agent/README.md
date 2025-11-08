# AI Coding Agent Tools

A flexible toolkit for building AI coding agents that can operate in multiple execution environments (local, Docker, E2B) and integrate with multiple AI frameworks (smolagents, OpenAI, Pydantic-AI, Autogen).

## Overview

This toolkit provides **Gemini CLI-inspired coding tools** with a **3-layer architecture** that separates execution environments from business logic and framework integration:

```
┌─────────────────────────────────────────┐
│    Framework Adapters (Layer 3)         │ 
│  smolagents, OpenAI, Pydantic-AI, etc.  │
│  - Reads metadata from core tools       │
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

Core tools have **zero framework dependencies**. Adapters translate tool metadata to framework-specific formats:
- **smolagents**: `Tool` class with `forward()` method
- **OpenAI**: Function calling schema
- **Pydantic-AI**: Tool definitions
- **Autogen**: Agent tools

### 3. Output Separation

Tools return **Pydantic output models** that handle their own display:
- **Console mode**: Rich terminal output with syntax highlighting
- **API mode**: JSON serialization for web APIs
- **Hybrid mode**: Both console output and JSON return

## Directory Structure

```
tools/
├── backends/          # Execution environments
│   ├── execution_backend.py    # Abstract interface
│   ├── local_backend.py        # Local implementation
│   ├── docker_backend.py       # Docker container
│   └── e2b_backend.py          # E2B sandbox
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
└── adapters/          # Framework integrations
    └── smolagents_adapter.py  # smolagents integration
```

## Architecture Benefits

### Mix and Match

Combine **any execution environment** with **any framework** and **any storage**:

```python
from prompttodraft.agent.adapters.smolagents_adapter import create_smolagents_tools
from prompttodraft.agent.backends.local_backend import LocalBackend
from prompttodraft.agent.backends.docker_backend import DockerBackend
from prompttodraft.agent.backends.state_manager import StorageType

# Local execution with smolagents + Git storage
backend = LocalBackend(project_id="my-project", storage=StorageType.GIT)
backend.start()
tools = create_smolagents_tools(backend=backend)

# Docker execution with smolagents + GCS storage
docker_backend = DockerBackend(project_id="my-project", storage=StorageType.GCS)
docker_backend.start()
tools = create_smolagents_tools(backend=docker_backend)
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
1. Create adapter that reads tool metadata
2. Transform to framework-specific format

**Add a new tool**:
1. Create core tool inheriting from `CoreTool` with metadata
2. Add to `create_smolagents_tools()` in adapter
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
from prompttodraft.agent.adapters.smolagents_adapter import create_smolagents_tools
from prompttodraft.agent.backends.local_backend import LocalBackend
from prompttodraft.agent.backends.state_manager import StorageType
from smolagents import CodeAgent

# Create backend and tools (with Git storage)
backend = LocalBackend(project_id="my-project", storage=StorageType.GIT)
backend.start()
tools = create_smolagents_tools(backend=backend)

# Use with agent
agent = CodeAgent(tools=tools, model=...)
agent.run("List all Python files")
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
- Automatic commit and push on `sync_to_bucket()`
- Fast and free for small/medium projects

**GCS Storage**:
- Uses Google Cloud Storage buckets
- Timestamped snapshots for each save
- Better for large files or non-git workflows
- Requires GCS credentials

### Usage

```python
from prompttodraft.agent.backends.local_backend import LocalBackend
from prompttodraft.agent.backends.state_manager import StorageType

# Using Git storage (default)
backend = LocalBackend(project_id="my-project", storage=StorageType.GIT)
backend.start()  # Loads from git branch

# Using GCS storage
backend = LocalBackend(project_id="my-project", storage=StorageType.GCS)
backend.start()  # Loads from GCS bucket

# No persistence
backend = LocalBackend(project_id="my-project", storage=StorageType.NONE)
```

### Lifecycle Methods

- `start()`: Load files from storage, create environment
- `shutdown()`: Sync files to storage, destroy environment
- `sync_to_bucket()`: Save current state (timestamped snapshots)
- `load_from_bucket()`: Restore latest state

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


