"""
E2E tests for utility functions.

Tests the initialize_project function with different backends (local, docker, e2b).
"""
import pytest

from conftest import cleanup_test_environment, initialize_project
from prompttodraft.backends.local_backend import LocalBackend
from prompttodraft.backends.docker_backend import DockerBackend
from prompttodraft.backends.e2b_backend import E2BBackend
from prompttodraft.backends.execution_backend import ExecutionBackend, BackendStatus
from prompttodraft.backends.state_manager import GCSStateManager
from prompttodraft.initializers.python_initializer import PythonInitializer


def run_initialize_project_test(backend: ExecutionBackend):
    """
    E2E test for initialize_project with any backend implementation.

    Args:
        backend: An initialized ExecutionBackend instance (local, docker, or e2b)
    """
    # === FRESH START CLEANUP ===
    cleanup_test_environment(backend=backend)

    try:
        # Start backend
        backend.start()
        assert backend.get_status() == BackendStatus.RUNNING
        working_dir = backend.get_working_directory()

        # TEST: Initialize project
        print("\n" + "="*80)
        print("TEST: Initialize project")
        print("="*80)

        result = initialize_project(backend=backend)

        assert result["success"] is True
        assert result["directory"] == working_dir

        # Verify project files were created
        pyproject_path = f"{working_dir}/pyproject.toml"
        assert backend.file_exists(path=pyproject_path)

        readme_path = f"{working_dir}/README.md"
        assert backend.file_exists(path=readme_path)

        gitignore_path = f"{working_dir}/.gitignore"
        assert backend.file_exists(path=gitignore_path)

        # Verify pyproject.toml has content
        content = backend.read_file(file_path=pyproject_path)
        assert len(content) > 0
        assert "[project]" in content or "name" in content

        # Verify gitignore has Python patterns
        gitignore_content = backend.read_file(file_path=gitignore_path)
        assert ".venv/" in gitignore_content
        assert "__pycache__/" in gitignore_content

        # TEST: Running initialize again should be idempotent
        print("\n" + "="*80)
        print("TEST: Idempotent initialization")
        print("="*80)

        result = initialize_project(backend=backend)
        assert result["success"] is True
        assert result["directory"] == working_dir

        print("\n" + "="*80)
        print("✅ ALL INITIALIZATION TESTS PASSED!")
        print("="*80)

        backend.shutdown()

    finally:
        try:
            backend.shutdown()
        except:
            pass
        cleanup_test_environment(backend=backend)


def test_initialize_project_local_backend():
    """Test initialize_project with LocalBackend."""
    initializer = PythonInitializer()
    backend = LocalBackend(project_id="test_init_local", state_manager=GCSStateManager(), initializer=initializer)
    initializer.backend = backend
    initializer.working_dir = backend.get_working_directory()
    run_initialize_project_test(backend=backend)


def test_initialize_project_docker_backend():
    """Test initialize_project with DockerBackend."""
    initializer = PythonInitializer()
    backend = DockerBackend(project_id="test_init_docker", state_manager=GCSStateManager(), initializer=initializer)
    initializer.backend = backend
    initializer.working_dir = backend.get_working_directory()
    run_initialize_project_test(backend=backend)


@pytest.mark.e2b
def test_initialize_project_e2b_backend():
    """Test initialize_project with E2BBackend."""
    initializer = PythonInitializer()
    backend = E2BBackend(project_id="test_init_e2b", state_manager=GCSStateManager(), initializer=initializer)
    initializer.backend = backend
    initializer.working_dir = backend.get_working_directory()
    run_initialize_project_test(backend=backend)


if __name__ == "__main__":
    # Run tests manually
    print("Testing with Local Backend...")
    test_initialize_project_local_backend()

    print("\nTesting with Docker Backend...")
    test_initialize_project_docker_backend()

    print("\nTesting with E2B Backend...")
    test_initialize_project_e2b_backend()
