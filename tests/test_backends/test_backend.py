from prompttodraft.tools.backends.local_backend import LocalBackend
from prompttodraft.tools.backends.docker_backend import DockerBackend
from prompttodraft.tools.backends.execution_backend import ExecutionBackend, BackendStatus, FileType


def run_backend_e2e_test(backend: ExecutionBackend):
    """
    Generic E2E test for any ExecutionBackend implementation.

    This function tests all backend API methods to ensure compliance with the interface.
    Can be reused for local, docker, e2b, or any other backend implementation.

    Args:
        backend: An initialized (but not yet init() called) ExecutionBackend instance
    """
    try:
        # Test status before init
        assert backend.get_status() == BackendStatus.UNINITIALIZED

        # Test init
        backend.init()
        assert backend.get_status() == BackendStatus.RUNNING

        # Get working directory for constructing paths
        working_dir = backend.get_working_directory()
        assert working_dir is not None
        assert len(working_dir) > 0

        # Test write_file
        test_file = f"{working_dir}/test.txt"
        backend.write_file(file_path=test_file, content="Hello World")

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
        assert backend.file_exists(path=nested_file) == FileType.FILE

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

        # Test state management methods
        backend.sync_to_bucket()  # Should be no-op for local
        backend.load_from_bucket(person_id="test_person", task_id="test_task")  # Should be no-op

        # Test pause
        backend.pause()
        assert backend.get_status() == BackendStatus.PAUSED

        # Test resume
        backend.resume()
        assert backend.get_status() == BackendStatus.RUNNING

        # Test shutdown
        backend.shutdown()
        assert backend.get_status() == BackendStatus.STOPPED

        # Final verification using file_exists API
        assert backend.file_exists(path=test_file) == FileType.FILE
        assert backend.file_exists(path=f"{working_dir}/file1.py") == FileType.FILE
        assert backend.file_exists(path=f"{working_dir}/file2.py") == FileType.FILE
        assert backend.file_exists(path=f"{working_dir}/file3.txt") == FileType.FILE
        assert backend.file_exists(path=move_dest) is None  # was deleted
        assert backend.file_exists(path=test_subdir) is None  # was deleted

    finally:
        # Cleanup using public API
        working_dir = backend.get_working_directory()
        backend.delete_directory(path=working_dir)


def test_local_backend_e2e():
    """Test LocalBackend implementation using generic backend test."""
    backend = LocalBackend(project_id="test_backend_e2e")
    run_backend_e2e_test(backend=backend)


def test_docker_backend_e2e():
    """Test DockerBackend implementation using generic backend test."""
    backend = DockerBackend(project_id="test_docker_backend_e2e")
    run_backend_e2e_test(backend=backend)


def test_docker_backend_container_reuse():
    """Test that DockerBackend properly reuses existing containers."""
    import docker

    project_id = "test_docker_reuse"

    try:
        # Create first backend and initialize
        backend1 = DockerBackend(project_id=project_id)
        backend1.init()
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

        # Pause the backend (stops container but keeps it)
        backend1.pause()
        assert backend1.get_status() == BackendStatus.PAUSED

        # Create second backend instance with same project_id
        backend2 = DockerBackend(project_id=project_id)
        assert backend2.get_status() == BackendStatus.UNINITIALIZED

        # Init should connect to existing container
        backend2.init()
        assert backend2.get_status() == BackendStatus.RUNNING
        assert backend2._container_name == container_name

        # Verify the file from first backend is still there (container was reused)
        content = backend2.read_file(file_path=test_file)
        assert content == "container reuse test"

        # Execute command on second backend
        result2 = backend2.execute_command(command="echo 'second backend'")
        assert result2.exit_code == 0

        # Test idempotent init: calling init() again on already running container
        backend2.init()  # Should not fail
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
    # test_local_backend_e2e()
    # test_docker_backend_e2e()
    test_docker_backend_container_reuse()