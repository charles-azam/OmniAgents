"""
E2E tests for utility functions.

Tests the initialize_project function with different backends (local, docker, e2b).
"""
import pytest

from prompttodraft.backends.local_backend import LocalBackend
from prompttodraft.backends.docker_backend import DockerBackend
from prompttodraft.backends.e2b_backend import E2BBackend
from prompttodraft.backends.execution_backend import ExecutionBackend, BackendStatus
from prompttodraft.backends.state_manager import GCSStateManager
from prompttodraft.utils import initialize_project


def cleanup_backend(backend: ExecutionBackend) -> None:
    """Clean up backend storage and containers."""
    from prompttodraft import storage_utils
    from prompttodraft.common import LOCAL_BACKEND_PATH, DOCKER_BACKEND_PATH, GCP_DATA_PATH
    import shutil

    # 1. Clean bucket files
    bucket = storage_utils.get_bucket()
    prefix = f"{backend.project_id}/"
    for blob in bucket.list_blobs(prefix=prefix):
        try:
            blob.delete()
        except Exception:
            # Ignore errors if blob already deleted (eventual consistency)
            pass

    # 2. Clean local working directory (backend-specific paths)
    if isinstance(backend, LocalBackend):
        working_dir_path = LOCAL_BACKEND_PATH / backend.project_id
    elif isinstance(backend, DockerBackend):
        working_dir_path = DOCKER_BACKEND_PATH / backend.project_id
    else:  # E2BBackend
        working_dir_path = GCP_DATA_PATH / backend.project_id
    if working_dir_path.exists():
        shutil.rmtree(working_dir_path)

    # 3. Clean Docker container if exists
    if isinstance(backend, DockerBackend):
        import docker
        try:
            client = docker.from_env()
            container_name = f"prompttodraft-{backend.project_id}"
            container = client.containers.get(container_name)
            container.stop()
            container.remove()
        except:
            pass


def run_initialize_project_test(backend: ExecutionBackend):
    """
    E2E test for initialize_project with any backend implementation.

    Args:
        backend: An initialized ExecutionBackend instance (local, docker, or e2b)
    """
    # === FRESH START CLEANUP ===
    cleanup_backend(backend=backend)

    try:
        # Start backend
        backend.start()
        assert backend.get_status() == BackendStatus.RUNNING
        working_dir = backend.get_working_directory()

        # TEST 1: First run - should run uv init and uv sync
        print("\n" + "="*80)
        print("TEST 1: First run - should initialize project")
        print("="*80)

        result = initialize_project(backend=backend)

        assert result["success"] is True
        assert result["first_run"] is True
        assert result["directory"] == working_dir
        assert "uv init" in result["message"]
        assert "uv sync" in result["message"]
        assert "completed successfully" in result["message"]

        # Verify pyproject.toml was created
        pyproject_path = f"{working_dir}/pyproject.toml"
        assert backend.file_exists(path=pyproject_path)

        # Read pyproject.toml to verify it has content
        content = backend.read_file(file_path=pyproject_path)
        assert len(content) > 0
        assert "[project]" in content or "name" in content

        # TEST 2: Second run - should only run uv sync
        print("\n" + "="*80)
        print("TEST 2: Second run - should only sync")
        print("="*80)

        result = initialize_project(backend=backend)

        assert result["success"] is True
        assert result["first_run"] is False
        assert result["directory"] == working_dir
        assert "uv init" not in result["message"] or "Running 'uv init'..." not in result["message"]
        assert "uv sync" in result["message"]
        assert "completed successfully" in result["message"]

        print("\n" + "="*80)
        print("✅ ALL INITIALIZATION TESTS PASSED!")
        print("="*80)

        backend.shutdown()

    finally:
        try:
            backend.shutdown()
        except:
            pass
        cleanup_backend(backend=backend)


def test_initialize_project_local_backend():
    """Test initialize_project with LocalBackend."""
    backend = LocalBackend(project_id="test_init_local", state_manager=GCSStateManager())
    run_initialize_project_test(backend=backend)


def test_initialize_project_docker_backend():
    """Test initialize_project with DockerBackend."""
    backend = DockerBackend(project_id="test_init_docker", state_manager=GCSStateManager())
    run_initialize_project_test(backend=backend)


@pytest.mark.e2b
def test_initialize_project_e2b_backend():
    """Test initialize_project with E2BBackend."""
    backend = E2BBackend(project_id="test_init_e2b", state_manager=GCSStateManager())
    run_initialize_project_test(backend=backend)


if __name__ == "__main__":
    # Run tests manually
    print("Testing with Local Backend...")
    test_initialize_project_local_backend()

    print("\nTesting with Docker Backend...")
    test_initialize_project_docker_backend()

    print("\nTesting with E2B Backend...")
    test_initialize_project_e2b_backend()
