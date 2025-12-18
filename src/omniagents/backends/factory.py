"""
Factory functions for creating execution backends.

This module provides a simple API for creating backends with sensible defaults.
"""
from omniagents.backends.execution_backend import ExecutionBackend
from omniagents.backends.state_manager import StateManager, NoOpStateManager
from omniagents.backends.local_backend import LocalBackend
from omniagents.backends.docker_backend import DockerBackend
from omniagents.backends import E2B_AVAILABLE, OPENHANDS_AVAILABLE


def create_backend(
    backend_type: str,
    project_id: str,
    state_manager: StateManager | None = None,
    **kwargs,
) -> ExecutionBackend:
    """
    Create an execution backend by type.

    Args:
        backend_type: One of "local", "docker", "e2b", "openhands-docker",
                      "openhands-local", "openhands-k8s", "openhands-remote"
        project_id: Unique identifier for this project
        state_manager: Optional state manager (defaults to NoOpStateManager)
        **kwargs: Additional arguments passed to the backend constructor

    Returns:
        ExecutionBackend instance

    Raises:
        ValueError: If backend_type is unknown or required package not installed

    Example:
        ```python
        # Simple local backend
        backend = create_backend("local", "my-project")

        # Docker backend with custom image
        backend = create_backend(
            "docker",
            "my-project",
            image="python:3.13-slim"
        )

        # OpenHands Docker runtime (requires openhands extra)
        backend = create_backend(
            "openhands-docker",
            "my-project",
            openhands_config=my_config
        )
        ```
    """
    state_manager = state_manager or NoOpStateManager()

    if backend_type == "local":
        return LocalBackend(
            project_id=project_id,
            state_manager=state_manager,
            **kwargs
        )

    elif backend_type == "docker":
        return DockerBackend(
            project_id=project_id,
            state_manager=state_manager,
            **kwargs
        )

    elif backend_type == "e2b":
        if not E2B_AVAILABLE:
            raise ValueError(
                "E2B backend requires the 'e2b' extra. "
                "Install with: pip install omniagents[e2b]"
            )
        from omniagents.backends.e2b_backend import E2BBackend
        return E2BBackend(
            project_id=project_id,
            state_manager=state_manager,
            **kwargs
        )

    elif backend_type.startswith("openhands-"):
        if not OPENHANDS_AVAILABLE:
            raise ValueError(
                "OpenHands backend requires the 'openhands' extra. "
                "Install with: pip install omniagents[openhands]"
            )
        return _create_openhands_backend(
            runtime_type=backend_type.replace("openhands-", ""),
            project_id=project_id,
            state_manager=state_manager,
            **kwargs
        )

    else:
        raise ValueError(
            f"Unknown backend type: {backend_type}. "
            f"Available: local, docker, e2b, openhands-docker, "
            f"openhands-local, openhands-k8s, openhands-remote"
        )


def _create_openhands_backend(
    runtime_type: str,
    project_id: str,
    state_manager: StateManager,
    openhands_config: "OpenHandsConfig | None" = None,
    **kwargs,
) -> ExecutionBackend:
    """
    Create an OpenHands-backed backend.

    Args:
        runtime_type: One of "docker", "local", "k8s", "remote"
        project_id: Project identifier
        state_manager: State manager instance
        openhands_config: OpenHands configuration (optional, will create default)
        **kwargs: Additional arguments for the runtime

    Returns:
        OpenHandsBackend instance wrapping the specified runtime
    """
    from omniagents.backends.openhands_backend import OpenHandsBackend

    # Import OpenHands components
    from openhands.core.config import OpenHandsConfig
    from openhands.events import EventStream
    from openhands.llm.llm_registry import LLMRegistry
    from openhands.storage.files import LocalFileStore

    # Create default config if not provided
    if openhands_config is None:
        openhands_config = OpenHandsConfig()

    # Create required OpenHands components
    file_store = LocalFileStore(openhands_config.file_store_path)
    event_stream = EventStream(sid=project_id, file_store=file_store)
    llm_registry = LLMRegistry()

    # Select runtime class based on type
    if runtime_type == "docker":
        from openhands.runtime.impl.docker.docker_runtime import DockerRuntime
        runtime = DockerRuntime(
            config=openhands_config,
            event_stream=event_stream,
            llm_registry=llm_registry,
            sid=project_id,
            **kwargs
        )

    elif runtime_type == "local":
        from openhands.runtime.impl.local.local_runtime import LocalRuntime
        runtime = LocalRuntime(
            config=openhands_config,
            event_stream=event_stream,
            llm_registry=llm_registry,
            sid=project_id,
            **kwargs
        )

    elif runtime_type == "k8s":
        from openhands.runtime.impl.kubernetes.kubernetes_runtime import (
            KubernetesRuntime
        )
        runtime = KubernetesRuntime(
            config=openhands_config,
            event_stream=event_stream,
            llm_registry=llm_registry,
            sid=project_id,
            **kwargs
        )

    elif runtime_type == "remote":
        from openhands.runtime.impl.remote.remote_runtime import RemoteRuntime
        runtime = RemoteRuntime(
            config=openhands_config,
            event_stream=event_stream,
            llm_registry=llm_registry,
            sid=project_id,
            **kwargs
        )

    else:
        raise ValueError(
            f"Unknown OpenHands runtime type: {runtime_type}. "
            f"Available: docker, local, k8s, remote"
        )

    return OpenHandsBackend(
        runtime=runtime,
        project_id=project_id,
        state_manager=state_manager,
    )


def list_available_backends() -> list[str]:
    """
    List all available backend types.

    Returns:
        List of backend type strings that can be used with create_backend()
    """
    backends = ["local", "docker"]

    if E2B_AVAILABLE:
        backends.append("e2b")

    if OPENHANDS_AVAILABLE:
        backends.extend([
            "openhands-docker",
            "openhands-local",
            "openhands-k8s",
            "openhands-remote",
        ])

    return backends
