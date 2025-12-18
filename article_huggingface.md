# I Accidentally Rebuilt OpenHands From Scratch — Here's What I Learned

I spent weeks building a framework for multi-tenant AI coding agents. Isolated environments, persistent sessions, framework-agnostic tools — the whole thing. Then I discovered [OpenHands](https://github.com/All-Hands-AI/OpenHands) (66k stars) already does this.

**I had accidentally rebuilt a chunk of OpenHands without knowing it existed.**

But here's the thing: I learned more about AI coding agents in those weeks than I would have just using someone else's solution. And I ended up with something different — not better, just simpler. ~2000 lines of code you can read in a few hours.

More importantly, I now deeply understand what's happening under the hood. I know where the costs come from and how to reduce them. I know how to adapt it to my specific use case — which is building an agent that generates 3D models through code. You can't do that confidently with a black-box solution.

This is what I learned.

## The Problem I Was Trying to Solve

Imagine you're building a SaaS where users describe features in plain English and an AI agent writes the code. Sounds simple until you realize:

1. **User A's code can't leak to User B** — you need isolation
2. **Users expect their work to persist** — close the browser, come back tomorrow, files are still there
3. **Untrusted code is dangerous** — you can't run `rm -rf /` on your production server

I looked at existing solutions:
- **Claude Code / Gemini CLI** — great for single users, but how do you run one per customer?
- **E2B** — provides sandboxes, but you still need to build the tools and state management
- **LangChain / smolagents / Pydantic-AI** — agent frameworks, but no execution isolation

I wanted something that combined all three: **tools + isolated execution + session persistence**.

## What I Built

Omniagents is ~2000 lines of Python that gives you:

### 10 Coding Tools (Inspired by Gemini CLI)

```python
from omniagents.tools.write_file_tool import WriteFileTool
from omniagents.tools.read_file_tool import ReadFileTool
from omniagents.tools.run_shell_command_tool import RunShellCommandTool
from omniagents.tools.glob_tool import GlobTool
from omniagents.tools.search_file_content_tool import SearchFileContentTool
from omniagents.tools.replace_tool import ReplaceTool
# + 4 more
```

These are framework-agnostic. They don't know about LangChain or smolagents — they just take a backend and execute operations.

### 3 Execution Backends

```python
from omniagents.backends.local_backend import LocalBackend      # Your machine
from omniagents.backends.docker_backend import DockerBackend    # Isolated container
from omniagents.backends.e2b_backend import E2BBackend          # Cloud sandbox
```

Same tools, different environments. Swap `LocalBackend` for `DockerBackend` and your code now runs in a container — zero changes to your agent logic.

### 3 State Managers

```python
from omniagents.backends.state_manager import (
    NoOpStateManager,    # No persistence
    GitStateManager,     # Save to GitHub branches
    GCSStateManager,     # Save to Google Cloud Storage
)
```

When a user's session ends, their workspace is saved. When they return, it's restored.

## The Multi-Tenant Pattern

Here's the core insight: **one backend per user, identified by project_id**.

```python
def get_agent_for_user(user_id: str):
    backend = DockerBackend(
        project_id=f"user-{user_id}",      # Unique per user
        state_manager=GCSStateManager(),    # Persists to cloud
    )
    backend.start()  # Loads previous state if exists

    return LangChainAgent(
        backend=backend,
        model=ChatOpenAI(model="gpt-4"),
        preset=PythonUVPreset(),
    )

# Alice gets her own container + persistent storage
alice = get_agent_for_user("alice")
alice.run("Create a Flask app")
alice.backend.shutdown()  # Saves to GCS

# Bob is completely isolated
bob = get_agent_for_user("bob")
bob.run("Build a CLI tool")
bob.backend.shutdown()

# Alice returns tomorrow — her Flask app is still there
alice = get_agent_for_user("alice")
alice.run("Add authentication")
```

That's it. Each user gets:
- Their own Docker container (or E2B sandbox)
- Their own persistent storage
- Complete isolation from other users

## Framework Agnostic by Design

I didn't want to force anyone into a specific LLM framework. The tools auto-convert:

```python
# Same tools work with any framework
agent = LangChainAgent(backend=backend, model=model, preset=preset)
agent = PydanticAIAgent(backend=backend, model=model, preset=preset)
agent = SmolagentsAgent(backend=backend, model=model, preset=preset)
```

Under the hood, each tool has conversion methods:
- `to_langchain_tool()`
- `to_pydantic_ai_tool()`
- `to_smolagents_tool()`

The core tool logic stays the same — only the schema wrapping changes.

## The Architecture

```
┌─────────────────────────────────────────┐
│         Your LLM Framework              │
│   (LangChain, Pydantic-AI, smolagents)  │
└───────────────────┬─────────────────────┘
                    │
┌───────────────────▼─────────────────────┐
│            10 Core Tools                │
│  (framework-agnostic, just functions)   │
└───────────────────┬─────────────────────┘
                    │
┌───────────────────▼─────────────────────┐
│        Execution Backend                │
│     (Local, Docker, or E2B)             │
└───────────────────┬─────────────────────┘
                    │
┌───────────────────▼─────────────────────┐
│          State Manager                  │
│      (Git, GCS, or nothing)             │
└─────────────────────────────────────────┘
```

Each layer is swappable. Want to add a Fly.io backend? Implement the `ExecutionBackend` interface. Want S3 storage? Implement `StateManager`. The tools don't care.

## What I Learned

### You can do a lot with a few tools

All coding agents (Claude Code, Gemini CLI, Mistral Vibe, Cursor Agent, etc.) are built with a few core tools (read a file, write a file, run a command, etc.). They are all roughly the same, and yet depending on the attention to detail, the quality of the agent can vary greatly.

Today the best agents implement these additional features:
- **Empowering tools**: any tool that enhances the agent's capabilities (e.g., browsing agent, search engine, etc.)
- **Task Tracker Tool (Plan Mode)**: helps the agent track its progress and stay on task — popularized by Claude Code and very effective
- **Think Tool**: for complex tasks, the agent can think about the task and generate a plan, then execute the plan step by step
- **Delegate Tool**: the agent can delegate tasks to sub-agents — very effective for complex multi-step tasks, and helps reduce context size

### Agent frameworks are useless (ok no but not that useful)

There are a lot of agent frameworks out there. To name a few:
- **smolagents**: very simple, best terminal logs in the market, but lacks powerful features. The tools don't support advanced schemas (like Pydantic models), which is a shame.
- **LangChain**: very close to Pydantic-AI now. Probably very powerful, but once you use LangGraph you enter a world of pain.
- **Pydantic-AI**: it flatters my software engineer soul. The telemetry is great but it is a shame the terminal logs are so hard to read.
- **openai-agents**: great if you want to be handcuffed to OpenAI.

But the moment you want to do something more complex — like adding an image at the start of each loop, or using model-specific features — you'll want to write your own loop with minimal abstraction.

### Use open source models for your personal projects

If you're new to AI, you might not know the pain of building a side project with a proprietary model. You'll quickly find out that not only are they expensive, but since you're a nobody, your rate limits are very low.

The best workaround is to use open source models. Check out HuggingFace — there are providers like Groq or Cerebras that offer very cheap open source models with generous rate limits.

### State Persistence Is Underrated

Most agent demos are stateless — run once, throw away. But real products need persistence:
- Users expect to resume work
- Debugging requires inspecting previous state
- Billing often ties to stored artifacts

Git-based storage turned out to be surprisingly good for small projects. Free, version-controlled, easy to inspect. GCS is better for larger files or enterprise requirements.

### OpenHands Exists (And That's OK)

After building this, I discovered [OpenHands](https://github.com/All-Hands-AI/OpenHands) — a much more complete solution. It has:
- More sophisticated agent logic
- Web UI
- More backends
- Active community

So why share Omniagents at all?

**Because it's simpler.** OpenHands is an application. Omniagents is a library. If you want a ready-to-use coding agent, use OpenHands. If you want primitives to build your own thing — maybe with custom tools, custom prompts, or embedded in a larger system — Omniagents might be easier to understand and modify.

~2000 lines of code. No magic. Read it in an afternoon.

## Try It

```bash
uv add git+https://github.com/charlesazam/omniagents.git
```

```python
from omniagents.backends.local_backend import LocalBackend
from omniagents.backends.state_manager import NoOpStateManager
from omniagents.tools.write_file_tool import WriteFileTool
from omniagents.tools.run_shell_command_tool import RunShellCommandTool

backend = LocalBackend(project_id="demo", state_manager=NoOpStateManager())
backend.start()

write = WriteFileTool(backend=backend)
write.execute(absolute_path="hello.py", content="print('Hello from Omniagents!')")

shell = RunShellCommandTool(backend=backend)
result = shell.execute(command="python hello.py")
print(result.content)  # "Hello from Omniagents!"

backend.shutdown()
```

The [documentation](https://github.com/charlesazam/omniagents/tree/main/docs) covers:
- All 10 tools
- Backend comparison
- State management deep dive
- Creating custom tools, backends, and presets

## What's Next?

I'm considering:
- **MCP server interface** — expose the tools via Model Context Protocol for Claude Desktop integration
- **More backends** — Fly.io, Modal, AWS Lambda
- **Better state management** — content-addressable storage for deduplication across users
- **Building with this**

If any of this is useful to you, let me know. And if you're building multi-tenant AI agents, I'd love to hear what challenges you're facing.

---

*[Omniagents on GitHub](https://github.com/charlesazam/omniagents)*
