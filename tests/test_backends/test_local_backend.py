from prompttodraft.tools.backends.local_backend import LocalBackend
from prompttodraft.tools.backends.execution_backend import BackendStatus, FileType


def test_local_backend_e2e():
    """E2E test for LocalBackend using only public API methods."""

    # Setup: Use a test project ID that will be created in DATA_PATH
    project_id = "test_backend_e2e"

    # Initialize backend
    backend = LocalBackend(project_id=project_id)

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
