from prompttodraft.tools.backends.local_backend import LocalBackend
from prompttodraft.tools.backends.docker_backend import DockerBackend
from prompttodraft.tools.backends.e2b_backend import E2BBackend
from prompttodraft.tools.backends.execution_backend import ExecutionBackend, BackendStatus, FileType
from pathlib import Path
import pytest

def run_backend_e2e_test(backend: ExecutionBackend):
    """
    Generic E2E test for any ExecutionBackend implementation.

    This function tests all backend API methods to ensure compliance with the interface.
    Can be reused for local, docker, e2b, or any other backend implementation.

    Args:
        backend: An initialized (but not yet init() called) ExecutionBackend instance
    """
    from prompttodraft import storage_utils
    from prompttodraft.common import LOCAL_BACKEND_PATH, DOCKER_BACKEND_PATH, GCP_DATA_PATH
    import shutil

    # === FRESH START CLEANUP ===
    # Clean everything to ensure fresh test environment for debugging/reloading

    # 1. Clean bucket files from previous runs
    bucket = storage_utils.get_bucket()
    prefix = f"{backend.project_id}/"
    for blob in bucket.list_blobs(prefix=prefix):
        try:
            blob.delete()
        except Exception:
            # Ignore errors if blob already deleted (eventual consistency)
            pass

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

    try:
        # Pre-populate bucket with test files to verify load_from_bucket works
        # Use timestamp format: project_id/timestamp/file.py
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        project_data_path = GCP_DATA_PATH / backend.project_id / timestamp

        storage_utils.write_to_storage(
            file_path=project_data_path / "preloaded.py",
            content="# This file was preloaded from bucket"
        )
        storage_utils.write_to_storage(
            file_path=project_data_path / "config.json",
            content='{"preloaded": true}'
        )
        storage_utils.write_to_storage(
            file_path=project_data_path / "config_2.json",
            content='{"preloaded": true}'
        )

        # Test status before start
        assert backend.get_status() == BackendStatus.UNINITIALIZED

        # Test start (should load preloaded files from bucket)
        backend.start()
        assert backend.get_status() == BackendStatus.RUNNING

        # Get working directory for constructing paths
        working_dir = backend.get_working_directory()
        assert working_dir is not None
        assert len(working_dir) > 0

        # Verify preloaded files were loaded from bucket
        assert backend.file_exists(path=f"{working_dir}/preloaded.py") == FileType.FILE
        assert backend.file_exists(path=f"{working_dir}/config.json") == FileType.FILE
        preloaded_content = backend.read_file(file_path=f"{working_dir}/preloaded.py")
        assert preloaded_content == "# This file was preloaded from bucket"
        config_content = backend.read_file(file_path=f"{working_dir}/config.json")
        assert config_content == '{"preloaded": true}'

        # Clean up preloaded files for rest of test
        backend.delete_file(path=f"{working_dir}/preloaded.py")
        backend.delete_file(path=f"./config.json") # relative path
        backend.delete_file(path=Path(working_dir) / "config_2.json") # using pathlib
        
        with pytest.raises(FileNotFoundError):
            backend.read_file(file_path=f"{working_dir}/config.json")
            
        with pytest.raises(FileNotFoundError):
            backend.delete_file(path=Path(working_dir) / "config_2.json")

        # Test write_file
        test_file = f"{working_dir}/test.txt"
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
        test_subdir = f"{working_dir}/subdir"
        backend.create_directory(path=test_subdir, parents=True)
        assert backend.file_exists(path=test_subdir) == FileType.DIRECTORY

        # Test write file in subdirectory
        nested_file = f"{test_subdir}/nested.txt"
        backend.write_file(file_path=nested_file, content="Nested content")
        assert backend.file_exists(path=Path("subdir") / "nested.txt") == FileType.FILE

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
        copy_dest = f"{working_dir}/test_copy.txt"
        backend.copy_file(src=test_file, dst=copy_dest)
        assert backend.file_exists(path=copy_dest) == FileType.FILE
        assert backend.read_file(file_path=copy_dest) == "Hello World"

        # Test move_file
        move_dest = f"{working_dir}/test_moved.txt"
        backend.move_file(src=copy_dest, dst=move_dest)
        assert backend.file_exists(path=move_dest) == FileType.FILE
        assert backend.file_exists(path=copy_dest) is None

        # Test execute_command
        result = backend.execute_command(command="echo 'test output'", timeout=10)
        assert result.exit_code == 0
        assert "test output" in result.output

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
        backend.write_file(file_path=f"{working_dir}/file1.py", content="# python")
        backend.write_file(file_path=f"{working_dir}/file2.py", content="# python")
        backend.write_file(file_path=f"{working_dir}/file3.txt", content="text")

        py_files = backend.glob_files(pattern="*.py", path=working_dir)
        assert len(py_files) == 2
        assert all(f.endswith(".py") for f in py_files)

        # Test delete_file
        backend.delete_file(path=move_dest)
        assert backend.file_exists(path=move_dest) is None

        # Test delete_directory
        backend.delete_directory(path=test_subdir)
        assert backend.file_exists(path=test_subdir) is None

        # Test execute_uv
        # First, initialize project with uv
        uv_init_result = backend.execute_uv(uv_command="init", timeout=120000)
        assert uv_init_result.exit_code == 0

        # Verify pyproject.toml was created
        pyproject_path = f"{working_dir}/pyproject.toml"
        assert backend.file_exists(path=pyproject_path) == FileType.FILE

        # Read initial pyproject.toml content
        initial_pyproject = backend.read_file(file_path=pyproject_path)
        assert "[project]" in initial_pyproject or "name" in initial_pyproject

        # Test uv add - add a package and verify pyproject.toml is modified
        uv_add_result = backend.execute_uv(uv_command="add requests", timeout=120000)
        assert uv_add_result.exit_code == 0

        # Read modified pyproject.toml and verify requests was added
        modified_pyproject = backend.read_file(file_path=pyproject_path)
        assert modified_pyproject != initial_pyproject, "pyproject.toml should be modified after uv add"
        assert "requests" in modified_pyproject, "requests should appear in dependencies"

        # Test uv run python - create and run a Python script
        uv_test_script = f"{working_dir}/uv_test.py"
        backend.write_file(file_path=uv_test_script, content="print('UV run test successful')")

        uv_run_result = backend.execute_uv(uv_command="run uv_test.py", timeout=60000)
        assert uv_run_result.exit_code == 0
        assert "UV run test successful" in uv_run_result.output

        # Clean up uv test files
        backend.delete_file(path=uv_test_script)

        # Test sync/load with shutdown/start cycle
        # Modify test.txt before shutdown
        backend.write_file(file_path=test_file, content="Modified content for sync test")

        # Create a new file that should be synced
        sync_test_file = f"{working_dir}/sync_test.py"
        backend.write_file(file_path=sync_test_file, content="# File created before shutdown")

        # Test shutdown (should sync files to bucket)
        backend.shutdown()
        assert backend.get_status() == BackendStatus.STOPPED

        # Verify files were synced to bucket under a timestamp directory
        bucket = storage_utils.get_bucket()
        prefix = f"{backend.project_id}/"

        # Find the latest timestamp (there should be at least one from the shutdown)
        timestamps = set()
        for blob in bucket.list_blobs(prefix=prefix):
            parts = blob.name.split('/')
            if len(parts) >= 2:
                timestamps.add(parts[1])

        assert len(timestamps) > 0, "No timestamp directories found in bucket"
        latest_timestamp = max(timestamps)

        # Verify test.txt was synced
        test_txt_blob = bucket.blob(blob_name=f"{backend.project_id}/{latest_timestamp}/test.txt")
        assert test_txt_blob.exists(), f"test.txt not found in {backend.project_id}/{latest_timestamp}/"
        assert test_txt_blob.download_as_text() == "Modified content for sync test"

        # Verify sync_test.py was synced
        sync_test_blob = bucket.blob(blob_name=f"{backend.project_id}/{latest_timestamp}/sync_test.py")
        assert sync_test_blob.exists(), f"sync_test.py not found in {backend.project_id}/{latest_timestamp}/"
        assert sync_test_blob.download_as_text() == "# File created before shutdown"

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
        assert backend.file_exists(path=f"{working_dir}/file1.py") == FileType.FILE
        assert backend.file_exists(path=f"{working_dir}/file2.py") == FileType.FILE
        assert backend.file_exists(path=f"{working_dir}/file3.txt") == FileType.FILE
        assert backend.file_exists(path=move_dest) is None  # was deleted
        assert backend.file_exists(path=test_subdir) is None  # was deleted

        # Test shutdown
        backend.shutdown()
        assert backend.get_status() == BackendStatus.STOPPED

    finally:
        # Cleanup: shutdown first (syncs files), then delete local directory
        try:
            backend.shutdown()
        except:
            pass  # May fail if already shutdown

        working_dir = backend.get_working_directory()
        try:
            backend.delete_directory(path=working_dir)
        except:
            pass  # May fail if directory doesn't exist

        # Cleanup bucket files and GCP staging
        from prompttodraft import storage_utils
        from prompttodraft.common import GCP_DATA_PATH
        import shutil

        bucket = storage_utils.get_bucket()
        prefix = f"{backend.project_id}/"
        for blob in bucket.list_blobs(prefix=prefix):
            blob.delete()

        # Clean GCP staging directory
        gcp_staging_path = GCP_DATA_PATH / backend.project_id
        if gcp_staging_path.exists():
            shutil.rmtree(gcp_staging_path)


def test_local_backend_e2e():
    """Test LocalBackend implementation using generic backend test."""
    backend = LocalBackend(project_id="test_backend_e2e")
    run_backend_e2e_test(backend=backend)


def test_docker_backend_e2e():
    """Test DockerBackend implementation using generic backend test."""
    backend = DockerBackend(project_id="test_docker_backend_e2e")
    run_backend_e2e_test(backend=backend)


@pytest.mark.e2b
def test_e2b_backend_e2e():
    """Test E2BBackend implementation using generic backend test."""
    backend = E2BBackend(project_id="test_e2b_backend_e2e")
    run_backend_e2e_test(backend=backend)


def test_docker_backend_container_reuse():
    """Test that DockerBackend properly reuses existing containers."""
    import docker

    project_id = "test_docker_reuse"

    try:
        # Create first backend and start
        backend1 = DockerBackend(project_id=project_id)
        backend1.start()
        assert backend1.get_status() == BackendStatus.RUNNING

        # Write a test file
        working_dir = backend1.get_working_directory()
        test_file = f"{working_dir}/reuse_test.txt"
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
        backend2 = DockerBackend(project_id=project_id)
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
            container = client.containers.get(f"prompttodraft-{project_id}")
            container.stop()
            container.remove()
        except:
            pass


if __name__ == "__main__":
    test_local_backend_e2e()
    test_docker_backend_e2e()
    test_docker_backend_container_reuse()
    test_e2b_backend_e2e()