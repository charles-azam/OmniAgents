# PromptToDraft Architecture: 4 Independent Components

## The Problem

The current architecture has issues:

1. **Tight coupling to Python/uv**: The code assumes every project uses Python with the `uv` package manager
2. **Circular dependency**: `Backend` needs `StateManager`, but `StateManager` methods need `Backend` to read/write files
3. **Hard to extend**: Adding a new language (Node.js, Rust) requires changes everywhere

## The Solution: 4 Independent Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER CODE                                       │
│                                                                             │
│   backend = DockerBackend(state_manager=..., initializer=...)               │
│   agent = LangChainAgent(backend=backend)                                   │
│   agent.run("Create a web server")                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐                 │
│  │    BACKEND    │   │ STATE MANAGER │   │  INITIALIZER  │                 │
│  │               │   │               │   │               │                 │
│  │ - LocalBackend│   │ - GitState    │   │ - NoOpInit    │                 │
│  │ - DockerBack  │   │ - GCSState    │   │ - UVInit      │                 │
│  │ - E2BBackend  │   │ - NoOpState   │   │ - (NpmInit)   │                 │
│  │               │   │               │   │ - (CargoInit) │                 │
│  └───────┬───────┘   └───────┬───────┘   └───────┬───────┘                 │
│          │                   │                   │                          │
│          │                   │                   │                          │
│          ▼                   ▼                   ▼                          │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │                         TOOLS                                │           │
│  │  ReadFile, WriteFile, RunCommand, Glob, Search, Replace...  │           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │                         AGENT                                │           │
│  │         LangChain  /  PydanticAI  /  SmolAgents             │           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component 1: Backend

**What it is**: The execution environment where code runs.

**Responsibility**:
- Provide a place to run commands and store files
- Abstract away WHERE code runs (your machine, a container, the cloud)

**Implementations**:
| Backend | Where it runs | Use case |
|---------|--------------|----------|
| `LocalBackend` | Your machine's filesystem | Development, testing |
| `DockerBackend` | Inside a Docker container | Isolation, reproducibility |
| `E2BBackend` | Cloud sandbox (E2B service) | Serverless, scalability |

**Key methods**:
```python
backend.start()                    # Start the environment
backend.execute_command("ls -la")  # Run a shell command
backend.read_file("main.py")       # Read a file
backend.write_file("main.py", code)# Write a file
backend.shutdown()                 # Stop and save state
```

**The Backend doesn't know**:
- What language the project uses
- Where state is persisted
- Which AI framework calls it

---

## Component 2: StateManager

**What it is**: A storage service for project snapshots.

**Responsibility**:
- Save the current state of files (a "snapshot")
- Load the most recent snapshot
- Store snapshots somewhere persistent

**Implementations**:
| StateManager | Where it stores | Use case |
|--------------|----------------|----------|
| `GitStateManager` | GitHub branch | Version history, collaboration |
| `GCSStateManager` | Google Cloud Storage | Cloud projects |
| `NoOpStateManager` | Nowhere (ephemeral) | Scratch work, testing |

**Critical design decision**: StateManager works with **pure data only**.

```python
@dataclass
class FileSnapshot:
    relative_path: str  # e.g., "src/main.py"
    content: str        # The file contents

@dataclass
class ProjectSnapshot:
    project_id: str
    files: list[FileSnapshot]
    message: str
```

**Key methods**:
```python
# StateManager receives pure data, not a backend reference
snapshot_id = state_manager.save_snapshot(snapshot)  # Save files
snapshot = state_manager.load_latest(project_id)     # Load files
```

**Why pure data?**
- No circular dependency: StateManager never calls Backend
- Easy to test: Just pass mock data
- Works with ANY backend: Git doesn't know if files came from Docker or Local

---

## Component 3: Initializer

**What it is**: A project setup script.

**Responsibility**:
- Initialize a new project (run `uv init`, `npm init`, etc.)
- Check if project is already initialized
- Install dependencies if needed

**Implementations**:
| Initializer | What it does | Creates |
|-------------|-------------|---------|
| `NoOpInitializer` | Nothing | (empty project) |
| `UVInitializer` | Runs `uv init`, `uv sync` | `pyproject.toml`, `.venv/` |
| `NpmInitializer` (future) | Runs `npm init` | `package.json`, `node_modules/` |

**Key methods**:
```python
result = initializer.initialize(backend)  # Set up the project
is_ready = initializer.is_initialized(backend)  # Check if already set up
```

**The Initializer doesn't know**:
- Whether it's running in Docker, locally, or in E2B
- Where state is stored
- What AI framework will use the project

It just runs commands on whatever backend it's given.

---

## Component 4: Agent

**What it is**: The AI that writes code.

**Responsibility**:
- Take a task from the user
- Use tools to read/write files and run commands
- Produce working code

**Implementations**:
| Agent | Framework | Style |
|-------|-----------|-------|
| `LangChainAgent` | LangChain | Flexible, many integrations |
| `PydanticAIAgent` | Pydantic-AI | Type-safe, structured |
| `SmolAgentAgent` | smolagents | Lightweight, HuggingFace |

**The Agent doesn't know**:
- Whether files are in Docker or on your machine
- Whether state is saved to Git or GCS
- What language the project uses

It just uses tools, which talk to the Backend.

---

## How They Connect

The Backend is the **central hub**. It coordinates the other components:

```
                    ┌──────────────┐
                    │ StateManager │
                    │  (storage)   │
                    └──────┬───────┘
                           │ pure data (ProjectSnapshot)
                           │
┌──────────────┐    ┌──────▼───────┐    ┌──────────────┐
│  Initializer │───►│   BACKEND    │◄───│    Agent     │
│   (setup)    │    │   (hub)      │    │    (AI)      │
└──────────────┘    └──────────────┘    └──────────────┘
       │                   │                   │
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    runs commands via
                    Backend.execute_command()
```

---

## The Flow: Start to Finish

### 1. Backend starts
```python
backend = DockerBackend(
    project_id="my-app",
    state_manager=GitStateManager(),
    initializer=UVInitializer(),
    image="python:3.13-slim",
)
backend.start()
```

What happens inside `backend.start()`:
```
1. Create Docker container with python:3.13-slim image
2. Call state_manager.load_latest("my-app")
   → Returns ProjectSnapshot with files from last session (or None)
3. If snapshot exists, write files to container
4. Call initializer.initialize(backend)
   → UVInitializer runs "uv init" and "uv sync" inside container
5. Backend is ready
```

### 2. Agent works
```python
agent = LangChainAgent(backend=backend, model_id="gpt-4")
result = agent.run("Create a FastAPI server")
```

What happens:
```
1. Agent receives task
2. Agent calls tools (which call backend methods):
   - backend.write_file("main.py", "from fastapi import...")
   - backend.execute_command("uv add fastapi")
   - backend.read_file("main.py")
3. Agent returns result
```

### 3. Backend shuts down
```python
backend.shutdown()
```

What happens inside `backend.shutdown()`:
```
1. Collect all files from container → list[FileSnapshot]
2. Create ProjectSnapshot(project_id="my-app", files=files)
3. Call state_manager.save_snapshot(snapshot)
   → GitStateManager commits files to branch "state/my-app"
4. Destroy Docker container
```

---

## Why This Design?

### 1. No circular dependencies
Before:
```
Backend.__init__(state_manager)
StateManager.save(backend)  ← calls backend.read_file(), backend.list_directory()
```

After:
```
Backend.__init__(state_manager)
StateManager.save(snapshot)  ← receives pure data, never touches backend
```

### 2. Easy to test
```python
# Test StateManager without any backend
snapshot = ProjectSnapshot(
    project_id="test",
    files=[FileSnapshot("main.py", "print('hello')")]
)
state_manager = GitStateManager()
state_manager.save_snapshot(snapshot)  # Works without Docker/Local/E2B
```

### 3. Mix and match freely
```python
# Python in Docker with Git storage
DockerBackend(state_manager=GitStateManager(), initializer=UVInitializer())

# Node.js locally with no storage
LocalBackend(state_manager=NoOpStateManager(), initializer=NoOpInitializer())

# Any language in E2B with GCS storage
E2BBackend(state_manager=GCSStateManager(), initializer=NoOpInitializer())
```

### 4. Easy to extend
Want to add Rust support?
```python
class CargoInitializer(ProjectInitializer):
    def initialize(self, backend):
        backend.execute_command("cargo init")
        return InitializationResult(success=True, ...)
```

That's it. No changes to Backend, StateManager, or Agent.

---

## Summary

| Component | Responsibility | Knows about |
|-----------|---------------|-------------|
| **Backend** | Run commands, store files | StateManager, Initializer (coordinates them) |
| **StateManager** | Save/load snapshots | Nothing (pure data in/out) |
| **Initializer** | Set up project | Backend (runs commands on it) |
| **Agent** | AI coding | Backend (uses tools) |

The Backend is the hub. Everything else is pluggable.
