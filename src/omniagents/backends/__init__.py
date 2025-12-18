"""
Execution backends for omniagents.

Available backends:
- LocalBackend: Execute on local machine (no isolation)
- DockerBackend: Execute in Docker containers (isolated)
- E2BBackend: Execute in E2B cloud sandboxes (requires e2b extra)
- OpenHandsBackend: Wrap OpenHands runtimes (requires openhands extra)

Install optional backends:
    pip install omniagents[e2b]       # E2B support
    pip install omniagents[openhands] # OpenHands support
    pip install omniagents[all]       # All backends
"""

# Core backends (always available)
from omniagents.backends.execution_backend import (
    ExecutionBackend,
    BackendStatus,
    FileType,
    FileInfo,
    CommandResult,
)
from omniagents.backends.state_manager import (
    StateManager,
    NoOpStateManager,
    GCSStateManager,
    GitStateManager,
)
from omniagents.backends.local_backend import LocalBackend
from omniagents.backends.docker_backend import DockerBackend

# Optional backends with graceful fallback
E2B_AVAILABLE = False
OPENHANDS_AVAILABLE = False

# E2B backend (optional)
try:
    from omniagents.backends.e2b_backend import E2BBackend
    E2B_AVAILABLE = True
except ImportError:
    E2BBackend = None  # type: ignore

# OpenHands backend (optional)
try:
    from omniagents.backends.openhands_backend import OpenHandsBackend
    OPENHANDS_AVAILABLE = True
except ImportError:
    OpenHandsBackend = None  # type: ignore


__all__ = [
    # Base classes
    "ExecutionBackend",
    "BackendStatus",
    "FileType",
    "FileInfo",
    "CommandResult",
    # State managers
    "StateManager",
    "NoOpStateManager",
    "GCSStateManager",
    "GitStateManager",
    # Core backends
    "LocalBackend",
    "DockerBackend",
    # Optional backends
    "E2BBackend",
    "OpenHandsBackend",
    # Availability flags
    "E2B_AVAILABLE",
    "OPENHANDS_AVAILABLE",
]
