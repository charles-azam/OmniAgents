"""
Test Git storage functionality across all backends.

This module tests Git-based state persistence, including first-start scenarios
where no remote branch exists yet.
"""
import os
import shutil
from pathlib import Path

import pytest

from prompttodraft.common import DOCKER_BACKEND_PATH, GCP_DATA_PATH, LOCAL_BACKEND_PATH
from prompttodraft.agent.backends.docker_backend import DockerBackend
from prompttodraft.agent.backends.e2b_backend import E2BBackend
from prompttodraft.agent.backends.execution_backend import BackendStatus, ExecutionBackend, FileType
from prompttodraft.agent.backends.local_backend import LocalBackend
from prompttodraft.agent.backends.state_manager import GitStateManager, StorageType


def get_project_id(base_name: str) -> str:
    """
    Get project ID with CI prefix if running in CI.

    Args:
        base_name: Base project name

    Returns:
        Project ID with 'ci-' prefix if CI=true, otherwise base_name
    """
    is_ci = os.getenv("CI", "").lower() == "true"
    return f"ci-{base_name}" if is_ci else base_name


def run_backend_git_first_start_test(backend: ExecutionBackend):
    """
    Generic test for Git storage first-start (no existing branch).

    Tests that backend correctly handles starting with no existing Git branch:
    - Creates working directory and initializes git
    - Creates files for the first time
    - Commits and persists files locally
    - Reloads files on subsequent start

    Args:
        backend: An initialized ExecutionBackend instance with Git storage
    """
    git_manager = GitStateManager()

    try:
        # === ENSURE CLEAN STATE ===
        # Delete branch if it exists
        git_manager.cleanup(project_id=backend.project_id)

        # Clean local working directory
        if isinstance(backend, LocalBackend):
            working_dir_path = LOCAL_BACKEND_PATH / backend.project_id
        elif isinstance(backend, DockerBackend):
            working_dir_path = DOCKER_BACKEND_PATH / backend.project_id
        else:  # E2BBackend
            working_dir_path = GCP_DATA_PATH / backend.project_id

        if working_dir_path.exists():
            shutil.rmtree(working_dir_path)

        # Clean Docker container if exists (for DockerBackend)
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

        # Verify no snapshots exist
        snapshots = git_manager.list_snapshots(project_id=backend.project_id)
        assert len(snapshots) == 0, f"Branch should not exist yet, but found {len(snapshots)} commits"

        # === TEST FIRST START ===
        # Start backend (should succeed even though branch doesn't exist)
        backend.start()
        assert backend.get_status() == BackendStatus.RUNNING

        working_dir = backend.get_working_directory()
        assert working_dir is not None

        # Working directory should be empty (except for .git directory created during load)
        files = backend.list_directory(path=working_dir)
        # Should only have .git directory if any files (git was initialized during load attempt)
        non_git_files = [f for f in files if f.name != ".git"]
        assert len(non_git_files) == 0, f"Expected empty directory (except .git), but found: {[f.name for f in non_git_files]}"

        # === CREATE FILES ===
        test_file = f"{working_dir}/hello.py"
        backend.write_file(file_path=test_file, content="print('Hello from first start')")

        config_file = f"{working_dir}/config.json"
        backend.write_file(file_path=config_file, content='{"first_start": true}')

        # === SHUTDOWN (should create branch and commit) ===
        backend.shutdown()
        assert backend.get_status() == BackendStatus.STOPPED
        
        snapshots = git_manager.list_snapshots(project_id=backend.project_id)
        assert len(snapshots) == 1, f"Branch should have 1 commit, but found {len(snapshots)} commits"
        assert snapshots[0]["message"] == "Shutdown snapshot", f"Commit message should be 'Shutdown snapshot', but found {snapshots[0]['message']}"

        # === RESTART AND VERIFY FILES LOADED ===
        backend.start()
        assert backend.get_status() == BackendStatus.RUNNING

        # Get working dir again (may be different after restart for some backends)
        working_dir = backend.get_working_directory()

        # Verify git was initialized and commit was created locally
        # (We check locally because the remote repo may not exist in test environment)
        log_result = backend.execute_command(command="git log --oneline")
        assert log_result.exit_code == 0, "Git log should work after restart"
        assert len(log_result.output.strip()) > 0, "Should have at least one commit"

        # Verify files were loaded from git
        test_file = f"{working_dir}/hello.py"
        config_file = f"{working_dir}/config.json"

        assert backend.file_exists(path=test_file) == FileType.FILE
        loaded_content = backend.read_file(file_path=test_file)
        assert loaded_content == "print('Hello from first start')"

        assert backend.file_exists(path=config_file) == FileType.FILE
        config_content = backend.read_file(file_path=config_file)
        assert config_content == '{"first_start": true}'

        backend.shutdown()

        print("✓ Git storage first-start test passed")

    finally:
        # Cleanup
        try:
            backend.shutdown()
        except:
            pass

        # Delete git branch
        git_manager.cleanup(project_id=backend.project_id)

        # Clean local directory
        if isinstance(backend, LocalBackend):
            working_dir_path = LOCAL_BACKEND_PATH / backend.project_id
        elif isinstance(backend, DockerBackend):
            working_dir_path = DOCKER_BACKEND_PATH / backend.project_id
        else:
            working_dir_path = GCP_DATA_PATH / backend.project_id

        if working_dir_path.exists():
            shutil.rmtree(working_dir_path)

        # Clean Docker container
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


def test_local_backend_git_first_start():
    """Test LocalBackend Git storage first-start."""
    project_id = get_project_id(base_name="test_git_first_start_local")
    backend = LocalBackend(project_id=project_id, storage=StorageType.GIT)
    run_backend_git_first_start_test(backend=backend)


def test_docker_backend_git_first_start():
    """Test DockerBackend Git storage first-start."""
    project_id = get_project_id(base_name="test_git_first_start_docker")
    backend = DockerBackend(project_id=project_id, storage=StorageType.GIT)
    run_backend_git_first_start_test(backend=backend)


@pytest.mark.e2b
def test_e2b_backend_git_first_start():
    """Test E2BBackend Git storage first-start."""
    project_id = get_project_id(base_name="test_git_first_start_e2b")
    backend = E2BBackend(project_id=project_id, storage=StorageType.GIT)
    run_backend_git_first_start_test(backend=backend)

if __name__ == "__main__":
    test_local_backend_git_first_start()
    test_docker_backend_git_first_start()
    test_e2b_backend_git_first_start()