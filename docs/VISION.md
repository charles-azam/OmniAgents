# omniagents: The Compatibility Layer for AI Coding Agents

## The Problem

The AI coding agent ecosystem is fragmented:

- **Agent Frameworks**: smolagents, pydantic-ai, langchain, openai-agents - each with different tool interfaces
- **Execution Backends**: Local, Docker, E2B, Kubernetes - each with different APIs
- **Full Solutions**: OpenHands, Aider, Claude Code - powerful but monolithic, locked to their own agent architecture

**If you want to build a product with an embedded coding agent, you face hard choices:**

1. Use OpenHands → Locked into their CodeActAgent, hard to embed
2. Use E2B directly → Build your own agent, tools, state management
3. Use smolagents/pydantic-ai → Build your own sandboxing, no enterprise backends

There's no way to mix and match: use your preferred agent framework with enterprise-grade backends.

---

## The Solution

**omniagents** is the compatibility layer that lets you use **any agent framework** with **any execution backend**.

```
┌─────────────────────────────────────────────────────────────┐
│                      Your Application                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                       omniagents                             │
│                                                              │
│   ┌─────────────────┐    ┌─────────────────────────────┐   │
│   │ Agent Frameworks │    │ Execution Backends          │   │
│   │                 │    │                             │   │
│   │ • smolagents    │    │ • Local (your machine)      │   │
│   │ • pydantic-ai   │◄──►│ • Docker (isolated)         │   │
│   │ • langchain     │    │ • E2B (cloud sandboxes)     │   │
│   │ • openai-agents │    │ • OpenHands Docker/K8s      │   │
│   └─────────────────┘    └─────────────────────────────┘   │
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ Shared: 10 Coding Tools + State Persistence         │   │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Value Proposition

### For Developers Building AI Products

**Before omniagents:**
- Choose between flexibility (build everything yourself) or power (use OpenHands, lose control)
- Agent framework lock-in: smolagents tools don't work with pydantic-ai
- Backend lock-in: E2B code doesn't work with Kubernetes

**With omniagents:**
```python
from omniagents.backends import create_backend
from omniagents.agents import PydanticAIAgent

# Use OpenHands' enterprise Docker runtime
backend = create_backend("openhands-docker", project_id="user-123")

# With pydantic-ai's agent framework
agent = PydanticAIAgent(backend=backend, model="gpt-4o")

# Your product gets both: enterprise infra + framework flexibility
result = agent.run("Build a REST API for user management")
```

### For Teams Evaluating Agent Frameworks

**Apples-to-apples comparison**: Run the same tools, same backend, same prompts - only change the agent framework.

```python
# Same tools, same backend - compare frameworks
for framework in ["smolagents", "pydantic-ai", "langchain"]:
    agent = create_agent(framework=framework, backend=backend)
    result = agent.run(task)
    benchmark_results[framework] = result
```

### For OpenHands Users Who Want More Control

**Use OpenHands' infrastructure without their agent:**

- OpenHands has the best runtimes: Docker, Kubernetes, Remote
- But forces you into CodeActAgent
- omniagents wraps OpenHands runtimes, lets you use any agent

---

## How It Works

### Layer 1: Execution Backends

Unified interface for running code in isolated environments:

| Backend | Use Case | Isolation | Setup |
|---------|----------|-----------|-------|
| `local` | Development | None | Zero config |
| `docker` | Testing | Container | Docker installed |
| `e2b` | Production | Cloud VM | E2B API key |
| `openhands-docker` | Enterprise | Container | OpenHands + Docker |
| `openhands-k8s` | Scale | Kubernetes | K8s cluster |

```python
from omniagents.backends import create_backend

# All backends have the same interface
backend = create_backend("openhands-docker", project_id="my-app")
backend.start()
backend.execute_command("python --version")
backend.write_file(Path("/workspace/main.py"), "print('hello')")
backend.shutdown()
```

### Layer 2: Coding Tools

10 framework-agnostic tools that work with any backend:

| Tool | Purpose |
|------|---------|
| `write_file` | Create/overwrite files |
| `read_file` | Read text, images, PDFs |
| `read_many_files` | Batch file reading |
| `replace` | Precise text replacement |
| `list_directory` | Browse workspace |
| `glob` | Find files by pattern |
| `search_file_content` | Regex search (grep) |
| `run_shell_command` | Execute bash commands |
| `save_memory` | Persist agent notes |
| `uv` | Python package management |

### Layer 3: Agent Framework Adapters

Same tools, automatically converted for each framework:

```python
# smolagents
from omniagents.agents import SmolagentsAgent
agent = SmolagentsAgent(backend=backend, model=model)

# pydantic-ai
from omniagents.agents import PydanticAIAgent
agent = PydanticAIAgent(backend=backend, model=model)

# langchain
from omniagents.agents import LangChainAgent
agent = LangChainAgent(backend=backend, model=model)
```

### Layer 4: State Persistence

Save and restore workspace state across sessions:

```python
from omniagents.backends import GCSStateManager

state_manager = GCSStateManager(bucket="my-bucket", project_id="user-123")
backend = create_backend("docker", project_id="user-123", state_manager=state_manager)

# On start: loads latest state from GCS
backend.start()

# ... user does work ...

# On shutdown: saves state to GCS
backend.shutdown()

# Next session: state is restored automatically
```

---

## Comparison with Alternatives

| Feature | omniagents | OpenHands | E2B | Raw Docker |
|---------|------------|-----------|-----|------------|
| Multiple agent frameworks | ✅ | ❌ (CodeActAgent only) | ❌ (bring your own) | ❌ |
| Multiple backends | ✅ | ✅ | ❌ (E2B only) | ❌ |
| Pre-built coding tools | ✅ | ✅ | ❌ | ❌ |
| State persistence | ✅ | ✅ | ❌ | ❌ |
| Embeddable library | ✅ | ❌ (full app) | ✅ | ✅ |
| OpenHands compatibility | ✅ | N/A | ❌ | ❌ |
| Framework-agnostic | ✅ | ❌ | ✅ | ✅ |

---

## Use Cases

### 1. Build a SaaS with Embedded Coding Agent

```python
# Backend: Each user gets isolated Docker environment
# Framework: pydantic-ai for type safety
# State: GCS for persistence across sessions

@app.post("/api/code")
async def run_agent(user_id: str, prompt: str):
    backend = create_backend(
        "openhands-docker",
        project_id=f"user-{user_id}",
        state_manager=GCSStateManager(bucket="user-workspaces")
    )
    agent = PydanticAIAgent(backend=backend, model="gpt-4o")
    return agent.run(prompt)
```

### 2. Benchmark Agent Frameworks

```python
# Same task, same backend, different frameworks
results = {}
for framework in ["smolagents", "pydantic-ai", "langchain"]:
    backend = create_backend("docker", project_id=f"bench-{framework}")
    agent = create_agent(framework=framework, backend=backend)

    start = time.time()
    result = agent.run("Create a Flask app with user auth")
    elapsed = time.time() - start

    results[framework] = {
        "success": result.success,
        "time": elapsed,
        "tokens": result.token_usage
    }
```

### 3. Migrate from E2B to Kubernetes

```python
# Development: E2B for simplicity
backend = create_backend("e2b", project_id="dev")

# Production: Kubernetes for scale
backend = create_backend("openhands-k8s", project_id="prod")

# Same agent code works with both
agent = PydanticAIAgent(backend=backend, model="gpt-4o")
```

---

## Getting Started

### Installation

```bash
# Core (local + docker backends)
pip install omniagents

# With OpenHands integration
pip install omniagents[openhands]

# With E2B
pip install omniagents[e2b]

# Everything
pip install omniagents[all]
```

### Quick Start

```python
from omniagents.backends import create_backend
from omniagents.agents import PydanticAIAgent

# Create backend
backend = create_backend("docker", project_id="quickstart")
backend.start()

# Create agent
agent = PydanticAIAgent(backend=backend, model="gpt-4o")

# Run task
result = agent.run("Create a Python script that fetches weather data")

# Cleanup
backend.shutdown()
```

### See Available Backends

```python
from omniagents.backends import list_available_backends

print(list_available_backends())
# ['local', 'docker', 'e2b', 'openhands-docker', 'openhands-local', 'openhands-k8s', 'openhands-remote']
```

---

## Roadmap

### Phase 1: Foundation (Current)
- [x] 10 coding tools
- [x] 3 native backends (local, docker, e2b)
- [x] OpenHands backend integration
- [x] 3 framework adapters (smolagents, pydantic-ai, langchain)
- [x] State persistence (GCS, Git)

### Phase 2: Distribution
- [ ] MCP server interface (Claude Desktop / Cursor integration)
- [ ] Fly.io / Modal backend support
- [ ] Content-addressable state storage (deduplication)
- [ ] PyPI package release

### Phase 3: Ecosystem
- [ ] Benchmark suite for agent frameworks
- [ ] Example applications (CAD generator, data pipeline builder)
- [ ] Enterprise features (SSO, audit logs)

---

## The Pitch

> "OpenHands is great but forces you into their agent architecture. E2B is powerful but you build everything yourself. omniagents is the compatibility layer - use any agent framework with any backend. It's what LangChain did for LLMs, but for coding agents."

---

## Contributing

omniagents is open source. Contributions welcome:

- New backend integrations (Fly.io, Modal, AWS Fargate)
- New framework adapters
- Improved tools
- Documentation and examples

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.
