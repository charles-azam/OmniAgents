# Omniagents

A **minimalist** multi-backend execution framework for AI coding agents.

## The Problem

You want to build a product where **each user gets their own AI coding agent**. Think:

- A SaaS where users describe features and the agent builds them
- An internal tool where each developer has an AI assistant
- A platform where clients submit coding tasks

You need:

1. **Isolated environments** - User A's code can't affect User B
2. **Persistent sessions** - Users close the browser, come back tomorrow, their files are still there
3. **Safe execution** - Untrusted code runs in sandboxes, not on your servers

Omniagents gives you exactly this: **10 coding tools + isolated backends + session persistence**.

## Multi-User Example

```python
from omniagents.backends.docker_backend import DockerBackend
from omniagents.backends.state_manager import GCSStateManager
from omniagents.agents.langchain_agent import LangChainAgent
from omniagents.presets.python import PythonUVPreset

def get_agent_for_user(user_id: str):
    """Each user gets their own isolated environment."""
    backend = DockerBackend(
        project_id=f"user-{user_id}",      # Unique per user
        state_manager=GCSStateManager(),    # Persists to cloud storage
    )
    backend.start()  # Loads user's previous files (if any)

    return LangChainAgent(
        backend=backend,
        model=your_llm,
        preset=PythonUVPreset(),
    )

# User "alice" connects
alice_agent = get_agent_for_user("alice")
alice_agent.run("Create a Flask app with user authentication")
alice_agent.backend.shutdown()  # Saves Alice's files to GCS

# User "bob" connects (completely isolated from Alice)
bob_agent = get_agent_for_user("bob")
bob_agent.run("Build a CLI calculator")
bob_agent.backend.shutdown()  # Saves Bob's files to GCS

# Alice comes back tomorrow
alice_agent = get_agent_for_user("alice")  # Her Flask app is still there
alice_agent.run("Add a /logout endpoint")
```

## Production Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Backend                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   User A    │  │   User B    │  │   User C    │         │
│  │   Agent     │  │   Agent     │  │   Agent     │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐         │
│  │   Docker    │  │   Docker    │  │   Docker    │         │
│  │  Container  │  │  Container  │  │  Container  │         │
│  │  (or E2B)   │  │  (or E2B)   │  │  (or E2B)   │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          │                                  │
│                   ┌──────▼──────┐                           │
│                   │    GCS/Git   │                          │
│                   │   (state)    │                          │
│                   └─────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

## The 10 Tools

These are the primitives your LLM uses to interact with code. They work identically across all backends - write once, run anywhere.

```python
from omniagents.backends.local_backend import LocalBackend
from omniagents.backends.state_manager import NoOpStateManager
from omniagents.tools.write_file_tool import WriteFileTool
from omniagents.tools.read_file_tool import ReadFileTool
from omniagents.tools.run_shell_command_tool import RunShellCommandTool

# Create a backend (where code runs)
backend = LocalBackend(project_id="demo", state_manager=NoOpStateManager())
backend.start()

# Use tools directly - no LLM needed
write = WriteFileTool(backend=backend)
write.execute(absolute_path="hello.py", content="print('Hello!')")

shell = RunShellCommandTool(backend=backend)
result = shell.execute(command="python hello.py")
print(result.content)  # "Hello!"

backend.shutdown()
```

| Tool | What it does |
|------|--------------|
| `WriteFileTool` | Create/overwrite files |
| `ReadFileTool` | Read text, images, PDFs |
| `ListDirectoryTool` | List directory contents |
| `GlobTool` | Find files by pattern |
| `SearchFileContentTool` | Grep with regex |
| `ReplaceTool` | Find and replace in files |
| `RunShellCommandTool` | Execute bash commands |
| `ReadManyFilesTool` | Batch read files |
| `SaveMemoryTool` | Persistent key-value store |
| `UVTool` | UV package manager |

## The 3 Backends

Backends determine **where** the code executes. Swap backends without changing your tools or agent code. Use `LocalBackend` for development, `DockerBackend` for self-hosted production, `E2BBackend` for fully managed cloud sandboxes.

| Backend | Runs on | Isolation | Use case |
|---------|---------|-----------|----------|
| `LocalBackend` | Your machine | None | Development only |
| `DockerBackend` | Docker container | Container | Self-hosted production |
| `E2BBackend` | E2B cloud | Full sandbox | Managed production |

## State Managers

State managers handle **session persistence**. When a user closes their browser and comes back tomorrow, their files are restored automatically. Essential for multi-user products where each user has ongoing projects.

```python
backend.start()    # Loads user's previous files (if any)
# ... user works ...
backend.shutdown() # Saves files for next session
```

| Manager | Storage | Use case |
|---------|---------|----------|
| `NoOpStateManager` | None | Testing, ephemeral tasks |
| `GitStateManager` | GitHub branches | Free, version-controlled |
| `GCSStateManager` | Google Cloud Storage | Enterprise, large files |

## Plug Into Any LLM Framework

Omniagents doesn't force you into a specific agent framework. The tools auto-convert to LangChain, Pydantic-AI, or smolagents format. Use whatever you're already comfortable with.

```python
from omniagents.agents.langchain_agent import LangChainAgent
from omniagents.agents.pydantic_ai_agent import PydanticAIAgent
from omniagents.agents.smolagents_agent import SmolagentsAgent

# Same backend + tools, different LLM frameworks
agent = LangChainAgent(backend=backend, model=model, preset=preset)
agent = PydanticAIAgent(backend=backend, model=model, preset=preset)
agent = SmolagentsAgent(backend=backend, model=model, preset=preset)
```

## What Omniagents Is NOT

- **Not an agent framework** - No prompts, no agent loops, no memory systems
- **Not opinionated** - Just primitives you compose yourself
- **Not a hosted service** - You run it, you own it

**It's just**: 10 tools + 3 backends + state persistence. ~2000 lines of code.

## Installation

```bash
uv add git+https://github.com/charlesazam/omniagents.git
# or
pip install git+https://github.com/charlesazam/omniagents.git
```

### Required Credentials

Depending on which components you use:

| Component | Environment Variable | How to get it |
|-----------|---------------------|---------------|
| **E2B Backend** | `E2B_API_KEY` | [e2b.dev](https://e2b.dev) |
| **Git State Manager** | `gh auth login` | [GitHub CLI](https://cli.github.com/) |
| **GCS State Manager** | `GOOGLE_APPLICATION_CREDENTIALS` | [GCP Console](https://console.cloud.google.com/iam-admin/serviceaccounts) |
| **GCS State Manager** | `BUCKET_OMNIAGENTS` | Your GCS bucket name |
| **LLM (OpenAI)** | `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com/api-keys) |
| **LLM (Anthropic)** | `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/) |
| **LLM (HuggingFace)** | `HF_TOKEN` | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |

## Quick Links

- [Installation](getting-started/installation.md) - Setup guide
- [Quick Start](getting-started/quickstart.md) - First agent in 5 minutes
- [Tools Reference](api/tools.md) - All 10 tools documented
- [Backends](concepts/backends.md) - Local vs Docker vs E2B
- [State Management](concepts/state-management.md) - Persistence deep dive
