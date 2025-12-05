"""
E2E tests for preset initialization.

Tests the PythonUVPreset.initialize_project with different backends (local, docker, e2b).
"""
import pytest
from pathlib import Path

from anyagents.test_utils import cleanup_test_environment
from anyagents.backends.local_backend import LocalBackend
from anyagents.backends.docker_backend import DockerBackend
from anyagents.backends.e2b_backend import E2BBackend
from anyagents.backends.execution_backend import ExecutionBackend, BackendStatus
from anyagents.backends.state_manager import GCSStateManager
from anyagents.presets.python import PythonUVPreset


def run_initialize_project_test(backend: ExecutionBackend):
    """
    E2E test for PythonUVPreset.initialize_project with any backend implementation.

    Args:
        backend: An initialized ExecutionBackend instance (local, docker, or e2b)
    """
    preset = PythonUVPreset()

    # === FRESH START CLEANUP ===
    cleanup_test_environment(backend=backend)

    try:
        # Start backend
        backend.start()
        assert backend.get_status() == BackendStatus.RUNNING
        working_dir = str(backend.get_working_directory())

        # TEST 1: First run - should run uv init and uv sync
        print("\n" + "=" * 80)
        print("TEST 1: First run - should initialize project")
        print("=" * 80)

        assert not preset.is_initialized(backend=backend)
        result = preset.initialize_project(backend=backend)

        assert result.success is True
        assert result.first_run is True
        assert "uv init" in result.message
        assert "uv sync" in result.message
        assert "completed successfully" in result.message

        # Verify pyproject.toml was created
        pyproject_path = f"{working_dir}/pyproject.toml"
        assert backend.file_exists(path=Path(pyproject_path))

        # Read pyproject.toml to verify it has content
        content = backend.read_file(file_path=Path(pyproject_path))
        assert len(content) > 0
        assert "[project]" in content or "name" in content

        # TEST 2: Second run - should only run uv sync
        print("\n" + "=" * 80)
        print("TEST 2: Second run - should only sync")
        print("=" * 80)

        assert preset.is_initialized(backend=backend)
        result = preset.initialize_project(backend=backend)

        assert result.success is True
        assert result.first_run is False
        assert "Running 'uv init'..." not in result.message
        assert "uv sync" in result.message
        assert "completed successfully" in result.message

        print("\n" + "=" * 80)
        print("ALL INITIALIZATION TESTS PASSED!")
        print("=" * 80)

        backend.shutdown()

    finally:
        try:
            backend.shutdown()
        except:
            pass
        cleanup_test_environment(backend=backend)


def test_initialize_project_local_backend():
    """Test PythonUVPreset.initialize_project with LocalBackend."""
    backend = LocalBackend(project_id="test_init_local", state_manager=GCSStateManager())
    run_initialize_project_test(backend=backend)


def test_initialize_project_docker_backend():
    """Test PythonUVPreset.initialize_project with DockerBackend."""
    preset = PythonUVPreset()
    backend = DockerBackend(
        project_id="test_init_docker",
        state_manager=GCSStateManager(),
        image=preset.docker_image,
    )
    run_initialize_project_test(backend=backend)


@pytest.mark.e2b
def test_initialize_project_e2b_backend():
    """Test PythonUVPreset.initialize_project with E2BBackend."""
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
