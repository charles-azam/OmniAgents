from omniagents.backends.local_backend import LocalBackend
from omniagents.backends.docker_backend import DockerBackend
from omniagents.backends.e2b_backend import E2BBackend
from omniagents.backends.fly_backend import FlyBackend
from omniagents.backends.execution_backend import ExecutionBackend, BackendStatus, FileType
from omniagents.backends.state_manager import GCSStateManager, GitStateManager
from omniagents.test_utils import cleanup_test_environment
from omniagents.uv_utils import execute_uv_command
from pathlib import Path
import pytest
import os


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


def run_backend_e2e_test(backend: ExecutionBackend):
    """
    Generic E2E test for any ExecutionBackend implementation.

    This function tests all backend API methods to ensure compliance with the interface.
    Can be reused for local, docker, e2b, or any other backend implementation.

    Args:
        backend: An initialized (but not yet init() called) ExecutionBackend instance
    """
    from omniagents import storage_utils
    from omniagents.common import GCP_DATA_PATH

    # === FRESH START CLEANUP ===
    # Clean everything to ensure fresh test environment for debugging/reloading
    cleanup_test_environment(backend=backend)

    try:
        # Pre-populate bucket with test archive to verify load_from_bucket works
        from datetime import datetime, timezone
        import tarfile
        import io

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")

        # Create tar.gz archive with test files
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
            # Add preloaded.py
            content = "# This file was preloaded from bucket"
            tarinfo = tarfile.TarInfo(name="preloaded.py")
            tarinfo.size = len(content.encode('utf-8'))
            tar.addfile(tarinfo=tarinfo, fileobj=io.BytesIO(content.encode('utf-8')))

            # Add config.json
            content = '{"preloaded": true}'
            tarinfo = tarfile.TarInfo(name="config.json")
            tarinfo.size = len(content.encode('utf-8'))
            tar.addfile(tarinfo=tarinfo, fileobj=io.BytesIO(content.encode('utf-8')))

            # Add config_2.json
            content = '{"preloaded": true}'
            tarinfo = tarfile.TarInfo(name="config_2.json")
            tarinfo.size = len(content.encode('utf-8'))
            tar.addfile(tarinfo=tarinfo, fileobj=io.BytesIO(content.encode('utf-8')))

        # Upload archive to bucket
        archive_path = GCP_DATA_PATH / backend.project_id / f"{timestamp}.tar.gz"
        storage_utils.write_to_storage(
            file_path=archive_path,
            content=tar_buffer.getvalue()
        )

        # Test status before start
        assert backend.get_status() == BackendStatus.UNINITIALIZED

        # Test start (should load preloaded files from bucket)
        backend.start()
        assert backend.get_status() == BackendStatus.RUNNING

        # Get working directory for constructing paths
        working_dir = backend.get_working_directory()
        assert working_dir is not None
        assert len(str(working_dir)) > 0

        # Verify preloaded files were loaded from bucket
        assert backend.file_exists(path=working_dir / "preloaded.py") == FileType.FILE
        assert backend.file_exists(path=working_dir / "config.json") == FileType.FILE
        preloaded_content = backend.read_file(file_path=working_dir / "preloaded.py")
        assert preloaded_content == "# This file was preloaded from bucket"
        config_content = backend.read_file(file_path=working_dir / "config.json")
        assert config_content == '{"preloaded": true}'

        # Clean up preloaded files for rest of test
        backend.delete_file(path=working_dir / "preloaded.py")
        backend.delete_file(path=backend.convert_to_path(path="./config.json"))  # relative path
        backend.delete_file(path=working_dir / "config_2.json")  # using pathlib
        
        with pytest.raises(FileNotFoundError):
            backend.list_directory(path=working_dir / "nonexistent_dir")

        with pytest.raises(FileNotFoundError):
            backend.read_file(file_path=working_dir / "config.json")

        with pytest.raises(FileNotFoundError):
            backend.delete_file(path=working_dir / "config_2.json")

        # Test write_file
        test_file = working_dir / "test.txt"
        backend.write_file(file_path=test_file, content="Hello World")
        backend.shutdown()
        backend.start()
        backend.start()

        # Test read_file
        content = backend.read_file(file_path=test_file)
        assert content == "Hello World"

        # Test file_exists
        file_type = backend.file_exists(path=test_file)
        assert file_type == FileType.FILE

        # Test create_directory
        test_subdir = working_dir / "subdir"
        backend.create_directory(path=test_subdir, parents=True)
        assert backend.file_exists(path=test_subdir) == FileType.DIRECTORY

        # Test write file in subdirectory
        nested_file = test_subdir / "nested.txt"
        backend.write_file(file_path=nested_file, content="Nested content")
        assert backend.file_exists(path=backend.convert_to_path(path="subdir/nested.txt")) == FileType.FILE

        # Test list_directory (non-recursive)
        files = backend.list_directory(path=working_dir, recursive=False)
        assert len(files) == 2  # test.txt and subdir
        file_names = {f.name for f in files}
        assert "test.txt" in file_names
        assert "subdir" in file_names

        # Test list_directory (recursive)
        files_recursive = backend.list_directory(path=working_dir, recursive=True)
        assert len(files_recursive) == 3  # test.txt, subdir, nested.txt
        all_paths = {f.path for f in files_recursive}
        assert nested_file in all_paths

        # Test copy_file
        copy_dest = working_dir / "test_copy.txt"
        backend.copy_file(src=test_file, dst=copy_dest)
        assert backend.file_exists(path=copy_dest) == FileType.FILE
        assert backend.read_file(file_path=copy_dest) == "Hello World"

        # Test move_file
        move_dest = working_dir / "test_moved.txt"
        backend.move_file(src=copy_dest, dst=move_dest)
        assert backend.file_exists(path=move_dest) == FileType.FILE
        assert backend.file_exists(path=copy_dest) is None

        # Test execute_command
        result = backend.execute_command(command="echo 'test output'", timeout=10)
        assert result.exit_code == 0
        assert "test output" in result.output

        # Test absolute path command execution (virtual path /workspace)
        # This verifies that LocalBackend correctly translates /workspace to host path
        # and Docker/E2B handle it natively.
        result_abs = backend.execute_command(command="ls -la /workspace", timeout=10)
        assert result_abs.exit_code == 0
        assert "test.txt" in result_abs.output

        # === COMMAND EDGE CASES ===
        # Test various command patterns to ensure all backends handle paths correctly

        # Edge case 1: Command with no path (ls)
        result_no_path = backend.execute_command(command="ls", timeout=10)
        assert result_no_path.exit_code == 0
        assert "test.txt" in result_no_path.output

        # Edge case 2: Command with relative path (ls subdir)
        result_rel_path = backend.execute_command(command="ls subdir", timeout=10)
        assert result_rel_path.exit_code == 0
        assert "nested.txt" in result_rel_path.output

        # Edge case 3: cd with relative path then ls
        result_cd_rel = backend.execute_command(command="cd subdir && ls", timeout=10)
        assert result_cd_rel.exit_code == 0
        assert "nested.txt" in result_cd_rel.output

        # Edge case 4: cd with absolute /workspace path then ls
        result_cd_abs = backend.execute_command(command="cd /workspace/subdir && ls", timeout=10)
        assert result_cd_abs.exit_code == 0
        assert "nested.txt" in result_cd_abs.output

        # Edge case 5: cat with absolute /workspace path
        result_cat = backend.execute_command(command="cat /workspace/test.txt", timeout=10)
        assert result_cat.exit_code == 0
        assert "Hello World" in result_cat.output

        # Edge case 6: pwd returns virtual path (/workspace)
        result_pwd = backend.execute_command(command="pwd", timeout=10)
        assert result_pwd.exit_code == 0
        assert "/workspace" in result_pwd.output

        # Edge case 7: realpath should show /workspace paths (for LocalBackend, tests output translation)
        result_realpath = backend.execute_command(command="realpath test.txt", timeout=10)
        assert result_realpath.exit_code == 0
        assert "/workspace/test.txt" in result_realpath.output

        # Edge case 8: Commands with multiple /workspace references
        result_multi = backend.execute_command(command="cp /workspace/test.txt /workspace/test_copy2.txt", timeout=10)
        assert result_multi.exit_code == 0
        assert backend.file_exists(path=working_dir / "test_copy2.txt") == FileType.FILE

        # Edge case 9: find with /workspace path
        result_find = backend.execute_command(command="find /workspace -name 'test.txt' -type f", timeout=10)
        assert result_find.exit_code == 0
        assert "test.txt" in result_find.output

        # Edge case 10: echo with /workspace in string literal
        # For LocalBackend: string replacement will replace /workspace (known limitation)
        # For Docker/E2B: /workspace is preserved naturally
        result_echo = backend.execute_command(command='echo "Path is /workspace/test"', timeout=10)
        assert result_echo.exit_code == 0
        # Just check command succeeded; output format varies by backend
        assert "/test" in result_echo.output

        # Clean up edge case test file
        backend.delete_file(path=working_dir / "test_copy2.txt")

        # Test command with non-zero exit code
        result_error = backend.execute_command(command="exit 42", timeout=10)
        assert result_error.exit_code == 42

        # Test command independence - each command should be independent
        # Set an environment variable in first command
        result1 = backend.execute_command(command="export TEST_VAR=hello", timeout=10)
        assert result1.exit_code == 0

        # Try to access it in second command - should not exist (commands are independent)
        result2 = backend.execute_command(command="echo $TEST_VAR", timeout=10)
        assert result2.exit_code == 0
        assert result2.output.strip() == ""  # Variable should not persist
        
            
        result2 = backend.execute_command(command="export TEST_VAR=hello && echo $TEST_VAR", timeout=10)
        assert result2.exit_code == 0
        assert result2.output.strip() == "hello"  # Variable should persist
        
            

        # Test working directory independence
        # Get initial working directory
        result3 = backend.execute_command(command="pwd", timeout=10)
        assert result3.exit_code == 0
        initial_pwd = result3.output.strip()

        # Change directory in next command
        result4 = backend.execute_command(command="cd /tmp && pwd", timeout=10)
        assert result4.exit_code == 0
        assert "/tmp" in result4.output

        # Check working directory in next command - should be back to initial
        result5 = backend.execute_command(command="pwd", timeout=10)
        assert result5.exit_code == 0
        assert result5.output.strip() == initial_pwd

        # Test shell variable independence
        result6 = backend.execute_command(command="MY_VAR=test; echo $MY_VAR", timeout=10)
        assert result6.exit_code == 0
        assert "test" in result6.output

        # Variable should not persist to next command
        result7 = backend.execute_command(command="echo $MY_VAR", timeout=10)
        assert result7.exit_code == 0
        assert result7.output.strip() == ""

        # Test glob_files
        backend.write_file(file_path=working_dir / "file1.py", content="# python")
        backend.write_file(file_path=working_dir / "file2.py", content="# python")
        backend.write_file(file_path=working_dir / "file3.txt", content="text")

        py_files = backend.glob_files(pattern="*.py", path=working_dir)
        assert len(py_files) == 2
        assert all(f.endswith(".py") for f in py_files)

        # Test delete_file
        backend.delete_file(path=move_dest)
        assert backend.file_exists(path=move_dest) is None

        # Test delete_directory
        backend.delete_directory(path=test_subdir)
        assert backend.file_exists(path=test_subdir) is None

        # Test uv commands via execute_command
        # Use PythonUVPreset to initialize project (handles UV installation if needed)
        from omniagents.presets.python import PythonUVPreset

        preset = PythonUVPreset()
        init_result = preset.initialize_project(backend=backend)
        assert init_result.success, f"Failed to initialize project with UV: {init_result.message}"

        # Verify pyproject.toml was created
        pyproject_path = working_dir / "pyproject.toml"
        assert backend.file_exists(path=pyproject_path) == FileType.FILE

        # Read initial pyproject.toml content
        initial_pyproject = backend.read_file(file_path=pyproject_path)
        assert "[project]" in initial_pyproject or "name" in initial_pyproject

        # Test uv add - add a package and verify pyproject.toml is modified
        uv_add_result = execute_uv_command(backend=backend, uv_command='add requests', timeout=120000)
        assert uv_add_result.exit_code == 0

        # Read modified pyproject.toml and verify requests was added
        modified_pyproject = backend.read_file(file_path=pyproject_path)
        assert modified_pyproject != initial_pyproject, "pyproject.toml should be modified after uv add"
        assert "requests" in modified_pyproject, "requests should appear in dependencies"

        # Test uv run python - create and run a Python script
        uv_test_script = working_dir / "uv_test.py"
        backend.write_file(file_path=uv_test_script, content="print('UV run test successful')")

        uv_run_result = execute_uv_command(backend=backend, uv_command='run uv_test.py', timeout=60000)
        assert uv_run_result.exit_code == 0
        assert "UV run test successful" in uv_run_result.output

        # Clean up uv test files
        backend.delete_file(path=uv_test_script)

        # Test sync/load with shutdown/start cycle
        # Modify test.txt before shutdown
        backend.write_file(file_path=test_file, content="Modified content for sync test")

        # Create a new file that should be synced
        sync_test_file = working_dir / "sync_test.py"
        backend.write_file(file_path=sync_test_file, content="# File created before shutdown")

        # Test shutdown (should sync files to bucket as archive)
        backend.shutdown()
        assert backend.get_status() == BackendStatus.STOPPED

        # Verify archive was created in bucket
        bucket = storage_utils.get_bucket()
        prefix = f"{backend.project_id}/"

        # Find archives (there should be at least one from the shutdown)
        archives = [blob for blob in bucket.list_blobs(prefix=prefix) if blob.name.endswith('.tar.gz')]

        assert len(archives) > 0, "No archives found in bucket"
        latest_archive = max(archives, key=lambda b: b.name)

        # Download and verify archive contents
        archive_bytes = latest_archive.download_as_bytes()
        tar_buffer = io.BytesIO(archive_bytes)
        with tarfile.open(fileobj=tar_buffer, mode='r:gz') as tar:
            member_names = tar.getnames()

            # Verify test.txt is in archive
            assert "test.txt" in member_names, f"test.txt not found in archive"
            test_txt_content = tar.extractfile("test.txt").read().decode('utf-8')
            assert test_txt_content == "Modified content for sync test"

            # Verify sync_test.py is in archive
            assert "sync_test.py" in member_names, f"sync_test.py not found in archive"
            sync_test_content = tar.extractfile("sync_test.py").read().decode('utf-8')
            assert sync_test_content == "# File created before shutdown"

        # Test start (should load files from bucket)
        backend.start()
        assert backend.get_status() == BackendStatus.RUNNING

        # Verify files were loaded back and content persisted
        assert backend.file_exists(path=test_file) == FileType.FILE
        loaded_content = backend.read_file(file_path=test_file)
        assert loaded_content == "Modified content for sync test"

        assert backend.file_exists(path=sync_test_file) == FileType.FILE
        sync_loaded_content = backend.read_file(file_path=sync_test_file)
        assert sync_loaded_content == "# File created before shutdown"

        # Clean up sync test file
        backend.delete_file(path=sync_test_file)

        # Restore test.txt to original content for final verification
        backend.write_file(file_path=test_file, content="Hello World")

        # Final verification using file_exists API (before shutdown)
        assert backend.file_exists(path=test_file) == FileType.FILE
        assert backend.file_exists(path=working_dir / "file1.py") == FileType.FILE
        assert backend.file_exists(path=working_dir / "file2.py") == FileType.FILE
        assert backend.file_exists(path=working_dir / "file3.txt") == FileType.FILE
        assert backend.file_exists(path=move_dest) is None  # was deleted
        assert backend.file_exists(path=test_subdir) is None  # was deleted

        # Test clean() method
        # Verify we have files before clean
        files_before_clean = backend.list_directory(path=working_dir, recursive=False)
        non_git_files_before = [f for f in files_before_clean if f.name != '.git']
        assert len(non_git_files_before) > 0, "Expected files before clean()"

        # Call clean()
        backend.clean(cleanup_state_manager=False)
        backend.save_snapshot(message="clean")

        # Verify files were removed (except .git for Git storage and README.md marker)
        files_after_clean = backend.list_directory(path=working_dir, recursive=False)
        non_git_files_after = [f for f in files_after_clean if f.name not in ['.git', 'README.md']]
        assert len(non_git_files_after) == 0, f"Expected only README.md after clean, found {len(non_git_files_after)}: {[f.name for f in non_git_files_after]}"

        # Verify README.md exists and is empty
        readme_path = working_dir / "README.md"
        assert backend.file_exists(path=readme_path) == FileType.FILE, "README.md should exist after clean()"
        readme_content = backend.read_file(file_path=readme_path)
        assert readme_content == "", f"README.md should be empty, got: {readme_content}"

        # Verify snapshot was created with message "clean"
        snapshots = backend.list_snapshots()
        assert len(snapshots) >= 1, "Expected at least one snapshot after clean()"

        # For Git storage, verify the latest commit has message "clean"
        if isinstance(backend.state_manager, GitStateManager):
            latest_snapshot = snapshots[0]
            assert latest_snapshot["message"] == "clean", f"Expected commit message 'clean', got '{latest_snapshot['message']}'"

        # Shutdown and restart to verify clean state persists
        backend.shutdown()
        backend.start()

        # Verify working directory only has README.md after restart
        files_after_restart = backend.list_directory(path=working_dir, recursive=False)
        non_git_files_after_restart = [f for f in files_after_restart if f.name not in ['.git', 'README.md']]
        assert len(non_git_files_after_restart) == 0, f"Expected only README.md after restart, found {len(non_git_files_after_restart)}: {[f.name for f in non_git_files_after_restart]}"

        # Verify README.md still exists and is empty
        assert backend.file_exists(path=readme_path) == FileType.FILE, "README.md should exist after restart"
        readme_content_after = backend.read_file(file_path=readme_path)
        assert readme_content_after == "", f"README.md should still be empty after restart, got: {readme_content_after}"

        # Test shutdown
        backend.shutdown()
        assert backend.get_status() == BackendStatus.STOPPED

    finally:
        # Cleanup: shutdown first (syncs files), then clean environment
        try:
            backend.shutdown()
        except:
            pass  # May fail if already shutdown

        cleanup_test_environment(backend=backend)


def test_local_backend_e2e():
    """Test LocalBackend implementation using generic backend test."""
    project_id = get_project_id(base_name="test_backend_e2e")
    backend = LocalBackend(project_id=project_id, state_manager=GCSStateManager())
    run_backend_e2e_test(backend=backend)


def test_docker_backend_e2e():
    """Test DockerBackend implementation using generic backend test."""
    project_id = get_project_id(base_name="test_docker_backend_e2e")
    backend = DockerBackend(project_id=project_id, state_manager=GCSStateManager())
    run_backend_e2e_test(backend=backend)


@pytest.mark.e2b
def test_e2b_backend_e2e():
    """Test E2BBackend implementation using generic backend test."""
    project_id = get_project_id(base_name="test_e2b_backend_e2e")
    backend = E2BBackend(project_id=project_id, state_manager=GCSStateManager())
    run_backend_e2e_test(backend=backend)


def test_docker_backend_container_reuse():
    """Test that DockerBackend properly reuses existing containers."""
    import docker

    project_id = get_project_id(base_name="test_docker_reuse")

    try:
        # Create first backend and start
        backend1 = DockerBackend(project_id=project_id, state_manager=GCSStateManager())
        backend1.start()
        assert backend1.get_status() == BackendStatus.RUNNING

        # Write a test file
        working_dir = backend1.get_working_directory()
        test_file = working_dir / "reuse_test.txt"
        backend1.write_file(file_path=test_file, content="container reuse test")

        # Execute a command to verify it's working
        result = backend1.execute_command(command="echo 'first backend'")
        assert result.exit_code == 0

        # Get container name for verification
        container_name = backend1._container_name

        # Shutdown the backend (stops container but keeps it, syncs to bucket)
        backend1.shutdown()
        assert backend1.get_status() == BackendStatus.STOPPED

        # Create second backend instance with same project_id
        backend2 = DockerBackend(project_id=project_id, state_manager=GCSStateManager())
        assert backend2.get_status() == BackendStatus.UNINITIALIZED

        # Start should connect to existing container
        backend2.start()
        assert backend2.get_status() == BackendStatus.RUNNING
        assert backend2._container_name == container_name

        # Verify the file from first backend is still there (loaded from bucket)
        content = backend2.read_file(file_path=test_file)
        assert content == "container reuse test"

        # Execute command on second backend
        result2 = backend2.execute_command(command="echo 'second backend'")
        assert result2.exit_code == 0

        # Test idempotent start: calling start() again on already running container
        backend2.start()  # Should not fail
        assert backend2.get_status() == BackendStatus.RUNNING

        # Cleanup
        backend2.shutdown()

    finally:
        # Ensure cleanup even if test fails
        try:
            client = docker.from_env()
            container = client.containers.get(f"omniagents-{project_id}")
            container.stop(timeout=0)
            container.remove()
        except:
            pass


def run_backend_git_e2e_test(backend: ExecutionBackend):
    """
    E2E test for ExecutionBackend with Git storage.

    Tests that state is properly saved/loaded from Git branches instead of GCS.

    Args:
        backend: An initialized ExecutionBackend instance with StorageType.GIT
    """
    import subprocess
    from omniagents.backends.state_manager import GitStateManager

    # === FRESH START CLEANUP ===
    # Clean everything to ensure fresh test environment
    cleanup_test_environment(backend=backend)

    # Get git manager for setting up test data
    git_manager = GitStateManager()

    try:
        # Pre-populate Git branch with test files to verify load works
        # We'll manually create a commit on the state branch
        branch_name = git_manager._get_branch_name(project_id=backend.project_id)
        auth_url = git_manager._get_authenticated_url()

        # Create temp directory with initial files
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
            subprocess.run(["git", "remote", "add", "origin", auth_url], cwd=tmp_path, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True, capture_output=True)
            subprocess.run(["git", "checkout", "-b", branch_name], cwd=tmp_path, check=True, capture_output=True)

            # Create test files
            (tmp_path / "preloaded.py").write_text("# This file was preloaded from git")
            (tmp_path / "config.json").write_text('{"preloaded": true}')
            (tmp_path / ".gitignore").write_text(".venv/\n__pycache__/\n*.pyc\n")

            # Commit and push
            subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial preloaded state"], cwd=tmp_path, check=True, capture_output=True)
            subprocess.run(["git", "push", "origin", branch_name, "--force"], cwd=tmp_path, check=True, capture_output=True)

        # Test status before start
        assert backend.get_status() == BackendStatus.UNINITIALIZED

        # Test start (should load preloaded files from git)
        backend.start()
        assert backend.get_status() == BackendStatus.RUNNING

        # Get working directory
        working_dir = backend.get_working_directory()
        assert working_dir is not None

        # Verify preloaded files were loaded from git
        assert backend.file_exists(path=working_dir / "preloaded.py") == FileType.FILE
        assert backend.file_exists(path=working_dir / "config.json") == FileType.FILE
        preloaded_content = backend.read_file(file_path=working_dir / "preloaded.py")
        assert preloaded_content == "# This file was preloaded from git"
        config_content = backend.read_file(file_path=working_dir / "config.json")
        assert config_content == '{"preloaded": true}'

        # Verify .gitignore was loaded
        assert backend.file_exists(path=working_dir / ".gitignore") == FileType.FILE

        # Clean up preloaded files
        backend.delete_file(path=working_dir / "preloaded.py")
        backend.delete_file(path=working_dir / "config.json")

        # Test write_file
        test_file = working_dir / "test.txt"
        backend.write_file(file_path=test_file, content="Hello Git World")

        # Test sync/load with shutdown/start cycle
        sync_test_file = working_dir / "sync_test.py"
        backend.write_file(file_path=sync_test_file, content="# File created before shutdown")

        # Test shutdown (should commit and push to git)
        backend.shutdown()
        assert backend.get_status() == BackendStatus.STOPPED

        # Verify files were synced to git by checking the remote branch (with retry for API propagation)
        import time
        max_retries = 5
        retry_delay = 0.5
        snapshots = []
        for attempt in range(max_retries):
            snapshots = git_manager.list_snapshots(project_id=backend.project_id)
            if len(snapshots) >= 1:
                break
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 1.5

        assert len(snapshots) >= 1, f"No commits found on git branch after {max_retries} retries"

        # Start again and verify files were loaded
        backend.start()
        assert backend.get_status() == BackendStatus.RUNNING

        # Verify files were loaded back
        assert backend.file_exists(path=test_file) == FileType.FILE
        loaded_content = backend.read_file(file_path=test_file)
        assert loaded_content == "Hello Git World"

        assert backend.file_exists(path=sync_test_file) == FileType.FILE
        sync_loaded_content = backend.read_file(file_path=sync_test_file)
        assert sync_loaded_content == "# File created before shutdown"

        # Test that deleted files don't come back
        backend.delete_file(path=sync_test_file)
        backend.shutdown()
        backend.start()

        # sync_test.py should not exist after reload
        assert backend.file_exists(path=sync_test_file) is None

        # Test final state
        backend.write_file(file_path=test_file, content="Final state")
        backend.shutdown()

        # Verify final commit exists (with retry for API propagation)
        max_retries = 5
        retry_delay = 0.5
        final_snapshots = []
        for attempt in range(max_retries):
            final_snapshots = git_manager.list_snapshots(project_id=backend.project_id)
            if len(final_snapshots) >= 2:
                break
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 1.5

        assert len(final_snapshots) >= 2, f"Should have multiple commits, found {len(final_snapshots)} after {max_retries} retries"

    finally:
        # Cleanup: shutdown first, then clean environment
        try:
            backend.shutdown()
        except:
            pass

        cleanup_test_environment(backend=backend)

def test_local_backend_git_storage():
    """Test LocalBackend with Git storage."""
    project_id = get_project_id(base_name="test_backend_git_local")
    backend = LocalBackend(project_id=project_id, state_manager=GitStateManager())
    run_backend_git_e2e_test(backend=backend)


def test_docker_backend_git_storage():
    """Test DockerBackend with Git storage."""
    project_id = get_project_id(base_name="test_backend_git_docker")
    backend = DockerBackend(project_id=project_id, state_manager=GitStateManager())
    run_backend_git_e2e_test(backend=backend)


@pytest.mark.e2b
def test_e2b_backend_git_storage():
    """Test E2BBackend with Git storage."""
    project_id = get_project_id(base_name="test_backend_git_e2b")
    backend = E2BBackend(project_id=project_id, state_manager=GitStateManager())
    run_backend_git_e2e_test(backend=backend)


@pytest.mark.fly
def test_fly_backend_e2e():
    """Test FlyBackend implementation using generic backend test."""
    project_id = get_project_id(base_name="test_fly_backend_e2e")
    app_name = os.getenv("FLY_APP_NAME", "omniagents-sandbox")
    backend = FlyBackend(
        project_id=project_id,
        state_manager=GCSStateManager(),
        app_name=app_name,
    )
    run_backend_e2e_test(backend=backend)


@pytest.mark.fly
def test_fly_backend_git_storage():
    """Test FlyBackend with Git storage."""
    project_id = get_project_id(base_name="test_backend_git_fly")
    app_name = os.getenv("FLY_APP_NAME", "omniagents-sandbox")
    backend = FlyBackend(
        project_id=project_id,
        state_manager=GitStateManager(),
        app_name=app_name,
    )
    run_backend_git_e2e_test(backend=backend)


if __name__ == "__main__":
    test_e2b_backend_git_storage()