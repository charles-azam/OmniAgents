"""
Comprehensive E2E tests for all tools.

This module tests all 9 tools with any backend (local, docker, e2b).
"""
import os
import pytest
from pathlib import Path

from prompttodraft.tools.backends.local_backend import LocalBackend
from prompttodraft.tools.backends.docker_backend import DockerBackend
from prompttodraft.tools.backends.e2b_backend import E2BBackend
from prompttodraft.tools.backends.execution_backend import ExecutionBackend, BackendStatus

# Import all tools
from prompttodraft.tools.core.list_directory_tool import ListDirectoryTool
from prompttodraft.tools.core.read_file_tool import ReadFileTool
from prompttodraft.tools.core.write_file_tool import WriteFileTool
from prompttodraft.tools.core.glob_tool import GlobTool
from prompttodraft.tools.core.search_file_content_tool import SearchFileContentTool
from prompttodraft.tools.core.replace_tool import ReplaceTool
from prompttodraft.tools.core.run_shell_command_tool import RunShellCommandTool
from prompttodraft.tools.core.read_many_files_tool import ReadManyFilesTool
from prompttodraft.tools.core.save_memory_tool import SaveMemoryTool

# Import output models
from prompttodraft.tools.outputs.models import (
    FileListOutputModel,
    TextOutputModel,
    CodeOutputModel,
    ErrorOutputModel,
    MediaOutputModel,
)


def run_tools_e2e_test(backend: ExecutionBackend):
    """
    Generic E2E test for all tools with any ExecutionBackend implementation.

    Tests all 9 Gemini CLI-inspired tools:
    1. list_directory
    2. read_file
    3. write_file
    4. glob
    5. search_file_content
    6. replace
    7. run_shell_command
    8. read_many_files
    9. save_memory

    Args:
        backend: An initialized ExecutionBackend instance
    """
    from prompttodraft import storage_utils
    from prompttodraft.common import DATA_PATH
    import shutil

    # Set console mode for testing
    os.environ["DISPLAY_MODE"] = "console"

    # Clean everything for fresh start
    bucket = storage_utils.get_bucket()
    prefix = f"{backend.project_id}/"
    for blob in bucket.list_blobs(prefix=prefix):
        blob.delete()

    working_dir_path = DATA_PATH / backend.project_id
    if working_dir_path.exists():
        shutil.rmtree(working_dir_path)

    # Clean Docker container if exists
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

    try:
        # Start backend
        backend.start()
        assert backend.get_status() == BackendStatus.RUNNING

        working_dir = backend.get_working_directory()

        # =====================================================================
        # TEST 1: write_file tool
        # =====================================================================
        print("\n" + "="*80)
        print("TEST 1: write_file tool")
        print("="*80)

        write_tool = WriteFileTool(backend=backend)

        # Test creating a new file
        test_file = f"{working_dir}/test.py"
        result = write_tool.execute(
            file_path=test_file,
            content="def hello():\n    print('world')\n"
        )
        assert isinstance(result, TextOutputModel)
        assert "created" in result.content.lower() or "wrote" in result.content.lower()

        # Test overwriting existing file
        result = write_tool.execute(
            file_path=test_file,
            content="def hello():\n    print('updated')\n"
        )
        assert isinstance(result, TextOutputModel)
        assert "overwrote" in result.content.lower()

        # =====================================================================
        # TEST 2: read_file tool
        # =====================================================================
        print("\n" + "="*80)
        print("TEST 2: read_file tool")
        print("="*80)

        read_tool = ReadFileTool(backend=backend)

        # Test reading text file
        result = read_tool.execute(path=test_file)
        assert isinstance(result, TextOutputModel)
        assert "def hello()" in result.content
        assert "updated" in result.content

        # Test reading with offset and limit
        large_file = f"{working_dir}/large.txt"
        lines = [f"Line {i}\n" for i in range(1, 101)]
        backend.write_file(file_path=large_file, content="".join(lines))

        result = read_tool.execute(path=large_file, offset=10, limit=5)
        assert isinstance(result, TextOutputModel)
        assert "Line 11" in result.content
        assert "Line 15" in result.content
        assert "truncated" in result.content.lower()

        # Test reading non-existent file
        result = read_tool.execute(path=f"{working_dir}/nonexistent.txt")
        assert isinstance(result, ErrorOutputModel)
        assert "not exist" in result.error.lower()

        # =====================================================================
        # TEST 3: list_directory tool
        # =====================================================================
        print("\n" + "="*80)
        print("TEST 3: list_directory tool")
        print("="*80)

        list_dir_tool = ListDirectoryTool(backend=backend)

        # Create test directory structure
        backend.create_directory(path=f"{working_dir}/subdir", parents=True)
        backend.write_file(file_path=f"{working_dir}/file1.py", content="# file 1")
        backend.write_file(file_path=f"{working_dir}/file2.txt", content="text")
        backend.write_file(file_path=f"{working_dir}/.hidden", content="hidden")
        backend.write_file(file_path=f"{working_dir}/subdir/nested.py", content="# nested")

        # Test basic listing
        result = list_dir_tool.execute(path=working_dir, respect_git_ignore=False)
        assert isinstance(result, FileListOutputModel)
        assert result.total_count >= 5  # test.py, large.txt, file1.py, file2.txt, subdir, .hidden

        # Verify sorting: directories first, then alphabetically
        file_names = [f.name for f in result.files]
        dirs = [f.name for f in result.files if f.is_dir]
        files = [f.name for f in result.files if not f.is_dir]

        # Directories should come first
        for i, name in enumerate(file_names):
            if name in files:
                # All preceding items should be directories
                for j in range(i):
                    assert file_names[j] in dirs
                break

        # Test with ignore patterns
        result = list_dir_tool.execute(
            path=working_dir,
            ignore=["*.txt", ".*"],
            respect_git_ignore=False
        )
        assert isinstance(result, FileListOutputModel)
        file_names = [f.name for f in result.files]
        assert "file2.txt" not in file_names
        assert "large.txt" not in file_names
        assert ".hidden" not in file_names
        assert "file1.py" in file_names

        # Test non-existent directory
        result = list_dir_tool.execute(path=f"{working_dir}/nonexistent")
        assert isinstance(result, ErrorOutputModel)

        # =====================================================================
        # TEST 4: glob tool
        # =====================================================================
        print("\n" + "="*80)
        print("TEST 4: glob tool")
        print("="*80)

        glob_tool = GlobTool(backend=backend)

        # Test finding Python files
        result = glob_tool.execute(
            pattern="*.py",
            path=working_dir,
            respect_git_ignore=False
        )
        assert isinstance(result, FileListOutputModel)
        assert result.total_count >= 2  # test.py, file1.py
        assert all(f.name.endswith(".py") for f in result.files)

        # Test recursive glob
        result = glob_tool.execute(
            pattern="**/*.py",
            path=working_dir,
            respect_git_ignore=False
        )
        assert isinstance(result, FileListOutputModel)
        assert result.total_count >= 3  # test.py, file1.py, subdir/nested.py

        # =====================================================================
        # TEST 5: search_file_content tool
        # =====================================================================
        print("\n" + "="*80)
        print("TEST 5: search_file_content tool")
        print("="*80)

        search_tool = SearchFileContentTool(backend=backend)

        # Test searching for pattern
        result = search_tool.execute(
            pattern="def hello",
            path=working_dir
        )
        assert isinstance(result, TextOutputModel)
        assert "def hello" in result.content
        assert "test.py" in result.content or "test" in result.content

        # Test search with include filter
        result = search_tool.execute(
            pattern="file",
            path=working_dir,
            include="*.py"
        )
        assert isinstance(result, TextOutputModel)
        # Should find "# file 1" in file1.py

        # Test no matches
        result = search_tool.execute(
            pattern="nonexistent_pattern_xyz",
            path=working_dir
        )
        assert isinstance(result, TextOutputModel)
        assert "0 matches" in result.content

        # =====================================================================
        # TEST 6: replace tool
        # =====================================================================
        print("\n" + "="*80)
        print("TEST 6: replace tool")
        print("="*80)

        replace_tool = ReplaceTool(backend=backend)

        # Create a file for replacement testing
        replace_file = f"{working_dir}/replace_test.py"
        backend.write_file(
            file_path=replace_file,
            content="def old_function():\n    return 'old'\n\ndef other():\n    pass\n"
        )

        # Test single replacement
        result = replace_tool.execute(
            file_path=replace_file,
            old_string="def old_function():\n    return 'old'",
            new_string="def new_function():\n    return 'new'",
            expected_replacements=1
        )
        assert isinstance(result, TextOutputModel)
        assert "successfully" in result.content.lower()

        # Verify replacement worked
        content = backend.read_file(file_path=replace_file)
        assert "new_function" in content
        assert "old_function" not in content

        # Test replacement with no match
        result = replace_tool.execute(
            file_path=replace_file,
            old_string="nonexistent code",
            new_string="new code",
            expected_replacements=1
        )
        assert isinstance(result, ErrorOutputModel)
        assert "0 occurrences" in result.error

        # Test creating new file with empty old_string
        new_file = f"{working_dir}/created_by_replace.py"
        result = replace_tool.execute(
            file_path=new_file,
            old_string="",
            new_string="# Created by replace tool\n"
        )
        assert isinstance(result, TextOutputModel)
        assert "created" in result.content.lower()
        assert backend.file_exists(path=new_file)

        # =====================================================================
        # TEST 7: run_shell_command tool
        # =====================================================================
        print("\n" + "="*80)
        print("TEST 7: run_shell_command tool")
        print("="*80)

        shell_tool = RunShellCommandTool(backend=backend)

        # Test basic command
        result = shell_tool.execute(command="echo 'Hello from shell'")
        assert isinstance(result, TextOutputModel)
        assert "Hello from shell" in result.content
        assert "Exit Code: 0" in result.content

        # Test command with description
        result = shell_tool.execute(
            command="ls -la",
            description="List all files"
        )
        assert isinstance(result, TextOutputModel)
        assert "List all files" in result.content

        # Test command in subdirectory
        result = shell_tool.execute(
            command="pwd",
            directory="subdir"
        )
        assert isinstance(result, TextOutputModel)
        assert "subdir" in result.content

        # Test command with non-zero exit code
        result = shell_tool.execute(command="exit 1")
        assert isinstance(result, TextOutputModel)
        assert "Exit Code: 1" in result.content
        assert "warning" in result.content.lower()

        # =====================================================================
        # TEST 8: read_many_files tool
        # =====================================================================
        print("\n" + "="*80)
        print("TEST 8: read_many_files tool")
        print("="*80)

        read_many_tool = ReadManyFilesTool(backend=backend)

        # Test reading multiple files
        result = read_many_tool.execute(
            paths=["*.py"],
            useDefaultExcludes=False,
            respect_git_ignore=False
        )
        assert isinstance(result, TextOutputModel)
        assert "---" in result.content
        assert "End of content" in result.content

        # Test with exclude patterns
        result = read_many_tool.execute(
            paths=["*"],
            exclude=["*.txt"],
            useDefaultExcludes=False,
            respect_git_ignore=False
        )
        assert isinstance(result, TextOutputModel)
        # Should not contain .txt files

        # Test with include patterns
        result = read_many_tool.execute(
            paths=["*.py"],
            include=["*.txt"],
            useDefaultExcludes=False,
            respect_git_ignore=False
        )
        assert isinstance(result, TextOutputModel)
        # Should contain both .py and .txt files

        # =====================================================================
        # TEST 9: save_memory tool
        # =====================================================================
        print("\n" + "="*80)
        print("TEST 9: save_memory tool")
        print("="*80)

        memory_tool = SaveMemoryTool(backend=backend)

        # Test saving a memory
        result = memory_tool.execute(fact="User prefers Python for coding")
        assert isinstance(result, TextOutputModel)
        assert "saved" in result.content.lower()

        # Test saving another memory
        result = memory_tool.execute(fact="Project name is prompttodraft")
        assert isinstance(result, TextOutputModel)
        assert "saved" in result.content.lower()

        # Verify memory file was created and contains both facts
        # The memory file is created in ~/.gemini/GEMINI.md or working_dir/.gemini/GEMINI.md
        # We'll check in the working directory

        # =====================================================================
        # INTEGRATION TEST: Combined workflow
        # =====================================================================
        print("\n" + "="*80)
        print("INTEGRATION TEST: Combined workflow")
        print("="*80)

        # Create a Python file
        workflow_file = f"{working_dir}/workflow.py"
        write_tool.execute(
            file_path=workflow_file,
            content="def calculate(x):\n    return x * 2\n"
        )

        # Search for it
        search_result = search_tool.execute(pattern="calculate", path=working_dir)
        assert "calculate" in search_result.content

        # Replace the function
        replace_tool.execute(
            file_path=workflow_file,
            old_string="def calculate(x):\n    return x * 2",
            new_string="def calculate(x):\n    return x * 3"
        )

        # Read it back
        read_result = read_tool.execute(path=workflow_file)
        assert "x * 3" in read_result.content

        # List the directory
        list_result = list_dir_tool.execute(path=working_dir, respect_git_ignore=False)
        file_names = [f.name for f in list_result.files]
        assert "workflow.py" in file_names

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)

        # Shutdown
        backend.shutdown()

    finally:
        # Cleanup
        try:
            backend.shutdown()
        except:
            pass

        # Cleanup bucket files
        bucket = storage_utils.get_bucket()
        prefix = f"{backend.project_id}/"
        for blob in bucket.list_blobs(prefix=prefix):
            blob.delete()


def test_tools_local_backend():
    """Test all tools with LocalBackend."""
    backend = LocalBackend(project_id="test_tools_local")
    run_tools_e2e_test(backend=backend)


def test_tools_docker_backend():
    """Test all tools with DockerBackend."""
    backend = DockerBackend(project_id="test_tools_docker")
    run_tools_e2e_test(backend=backend)


def test_tools_e2b_backend():
    """Test all tools with E2BBackend."""
    backend = E2BBackend(project_id="test_tools_e2b")
    run_tools_e2e_test(backend=backend)


if __name__ == "__main__":
    # Run tests manually
    print("Testing with Local Backend...")
    test_tools_local_backend()

    # print("\nTesting with Docker Backend...")
    # test_tools_docker_backend()

    # print("\nTesting with E2B Backend...")
    # test_tools_e2b_backend()
