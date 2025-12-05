"""
Test Git storage functionality across all backends.

This module tests Git-based state persistence, including first-start scenarios
where no remote branch exists yet.
"""
import os
from pathlib import Path

import pytest

from anyagents.test_utils import cleanup_test_environment
from anyagents.backends.docker_backend import DockerBackend
from anyagents.backends.e2b_backend import E2BBackend
from anyagents.backends.execution_backend import BackendStatus, ExecutionBackend, FileType
from anyagents.backends.local_backend import LocalBackend
from anyagents.backends.state_manager import GitStateManager


def get_project_id(base_name: str) -> str:
    """
    Get project ID with CI prefix and branch name if running in CI.

    Args:
        base_name: Base project name

    Returns:
        Project ID with 'ci-{branch_name}-' prefix if CI=true, otherwise base_name
    """
    is_ci = os.getenv("CI", "").lower() == "true"
    if is_ci:
        branch_name = os.getenv("CI_BRANCH_NAME", "unknown")
        # Sanitize branch name for use in identifiers (remove special chars, limit length)
        sanitized_branch = branch_name.replace("/", "-").replace("_", "-")[:20]
        return f"ci-{sanitized_branch}-{base_name}"
    return base_name


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
        cleanup_test_environment(backend=backend)

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
        test_file = working_dir / "hello.py"
        backend.write_file(file_path=test_file, content="print('Hello from first start')")

        config_file = working_dir / "config.json"
        backend.write_file(file_path=config_file, content='{"first_start": true}')

        # === SHUTDOWN (should create branch and commit) ===
        backend.shutdown()
        assert backend.get_status() == BackendStatus.STOPPED

        # Verify via GitHub API with retry logic (may have propagation delay)
        import time
        max_retries = 5
        retry_delay = 0.5
        snapshots = []
        for attempt in range(max_retries):
            snapshots = git_manager.list_snapshots(project_id=backend.project_id)
            if len(snapshots) == 1:
                break
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 1.5

        assert len(snapshots) == 1, f"Branch should have 1 commit, but found {len(snapshots)} commits after {max_retries} retries"
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
        test_file = working_dir / "hello.py"
        config_file = working_dir / "config.json"

        assert backend.file_exists(path=test_file) == FileType.FILE
        loaded_content = backend.read_file(file_path=test_file)
        assert loaded_content == "print('Hello from first start')"

        assert backend.file_exists(path=config_file) == FileType.FILE
        config_content = backend.read_file(file_path=config_file)
        assert config_content == '{"first_start": true}'

        backend.shutdown()

        print("✓ Git storage first-start test passed")

    finally:
        # Cleanup: shutdown first, then clean environment
        try:
            backend.shutdown()
        except:
            pass

        cleanup_test_environment(backend=backend)


def test_local_backend_git_first_start():
    """Test LocalBackend Git storage first-start."""
    project_id = get_project_id(base_name="test_git_first_start_local")
    backend = LocalBackend(project_id=project_id, state_manager=GitStateManager())
    run_backend_git_first_start_test(backend=backend)


def test_docker_backend_git_first_start():
    """Test DockerBackend Git storage first-start."""
    project_id = get_project_id(base_name="test_git_first_start_docker")
    backend = DockerBackend(project_id=project_id, state_manager=GitStateManager())
    run_backend_git_first_start_test(backend=backend)


@pytest.mark.e2b
def test_e2b_backend_git_first_start():
    """Test E2BBackend Git storage first-start."""
    project_id = get_project_id(base_name="test_git_first_start_e2b")
    backend = E2BBackend(project_id=project_id, state_manager=GitStateManager())
    run_backend_git_first_start_test(backend=backend)

if __name__ == "__main__":
    test_local_backend_git_first_start()
    test_docker_backend_git_first_start()
    test_e2b_backend_git_first_start()