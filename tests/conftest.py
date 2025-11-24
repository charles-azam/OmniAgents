"""
Shared pytest fixtures and utilities for all tests.

This module contains common test utilities that are automatically
available to all test files in the tests directory.
"""
from pathlib import Path


def initialize_project(backend: "ExecutionBackend") -> dict[str, bool | str]:
    """
    Initialize a Python project for testing purposes.

    Ensures README.md, .gitignore exist, uv is installed, pyproject.toml exists,
    and dependencies are synchronized.

    Args:
        backend: The execution backend to use for running commands

    Returns:
        Dictionary with initialization results:
        - directory: str path to the initialized directory
        - success: bool indicating if initialization succeeded
        - message: str with status message

    Raises:
        RuntimeError: If initialization fails
    """
    from prompttodraft.initializers.python_initializer import PythonInitializer

    working_dir = backend.get_working_directory()

    # Use PythonInitializer to handle initialization
    initializer = PythonInitializer(backend=backend)
    initializer.initialize()

    return {
        "directory": working_dir,
        "success": True,
        "message": "✓ Project initialized successfully",
    }


def cleanup_test_environment(backend: "ExecutionBackend") -> None:
    """
    Clean all test artifacts for a backend instance.

    This function handles cleanup at all layers:
    - Storage (GCS/Git)
    - Docker containers (if DockerBackend)
    - Local working directories

    Can be called before tests (fresh start) or after tests (cleanup).

    Args:
        backend: ExecutionBackend instance (can be UNINITIALIZED)
    """
    from prompttodraft.backends.docker_backend import DockerBackend
    from prompttodraft.backends.local_backend import LocalBackend
    from prompttodraft.common import LOCAL_BACKEND_PATH, DOCKER_BACKEND_PATH, GCP_DATA_PATH
    import shutil

    # 1. Clean storage layer (GCS/Git)
    backend.cleanup()

    # 2. Clean Docker container if exists (for DockerBackend)
    if isinstance(backend, DockerBackend):
        import docker
        try:
            client = docker.from_env()
            container_name = f"prompttodraft-{backend.project_id}"
            container = client.containers.get(container_name)
            container.stop()
            container.remove()
        except:
            pass  # Container doesn't exist or already cleaned

    # 3. Clean local working directory (backend-specific paths)
    if isinstance(backend, LocalBackend):
        working_dir_path = LOCAL_BACKEND_PATH / backend.project_id
    elif isinstance(backend, DockerBackend):
        working_dir_path = DOCKER_BACKEND_PATH / backend.project_id
    else:  # E2BBackend
        working_dir_path = GCP_DATA_PATH / backend.project_id
    if working_dir_path.exists():
        shutil.rmtree(working_dir_path)
