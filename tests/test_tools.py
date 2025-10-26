"""
Comprehensive E2E tests for all tools.

Tests all 9 Gemini CLI-inspired tools with different backends (local, docker, e2b):
1. write_file - Create/overwrite files
2. read_file - Read file contents with offset/limit support
3. list_directory - List directory contents with filtering
4. glob - Find files matching patterns
5. search_file_content - Search for patterns in files (grep)
6. replace - Replace text in files
7. run_shell_command - Execute shell commands
8. read_many_files - Read multiple files at once
9. save_memory - Save facts to memory file
"""
import os
from pathlib import Path
import pytest

from prompttodraft.tools.backends.local_backend import LocalBackend
from prompttodraft.tools.backends.docker_backend import DockerBackend
from prompttodraft.tools.backends.e2b_backend import E2BBackend
from prompttodraft.tools.backends.execution_backend import ExecutionBackend, BackendStatus

from prompttodraft.tools.core.list_directory_tool import ListDirectoryTool
from prompttodraft.tools.core.read_file_tool import ReadFileTool
from prompttodraft.tools.core.write_file_tool import WriteFileTool
from prompttodraft.tools.core.glob_tool import GlobTool
from prompttodraft.tools.core.search_file_content_tool import SearchFileContentTool
from prompttodraft.tools.core.replace_tool import ReplaceTool
from prompttodraft.tools.core.run_shell_command_tool import RunShellCommandTool
from prompttodraft.tools.core.read_many_files_tool import ReadManyFilesTool
from prompttodraft.tools.core.save_memory_tool import SaveMemoryTool

from prompttodraft.tools.outputs.models import (
    FileListOutputModel,
    TextOutputModel,
    ErrorOutputModel,
)


def cleanup_backend(backend: ExecutionBackend) -> None:
    """Clean up backend storage and containers before/after tests."""
    from prompttodraft import storage_utils
    from prompttodraft.common import DATA_PATH
    import shutil

    # Clean bucket storage
    bucket = storage_utils.get_bucket()
    prefix = f"{backend.project_id}/"
    for blob in bucket.list_blobs(prefix=prefix):
        blob.delete()

    # Clean local data directory
    working_dir_path = DATA_PATH / backend.project_id
    if working_dir_path.exists():
        shutil.rmtree(working_dir_path)

    # Clean Docker container if applicable
    if isinstance(backend, DockerBackend):
        import docker
        client = docker.from_env()
        container_name = f"prompttodraft-{backend.project_id}"
        try:
            container = client.containers.get(container_name)
            container.stop()
            container.remove()
        except:
            pass


def run_tools_e2e_test(backend: ExecutionBackend):
    """
    E2E test for all 9 tools with any backend implementation.

    Args:
        backend: An initialized ExecutionBackend instance (local, docker, or e2b)
    """
    # Set console mode for testing
    os.environ["DISPLAY_MODE"] = "console"

    # Clean environment for fresh start
    cleanup_backend(backend=backend)

    try:
        # Start backend
        backend.start()
        assert backend.get_status() == BackendStatus.RUNNING
        working_dir = backend.get_working_directory()

        # TEST 1: write_file tool
        print("\n" + "="*80)
        print("TEST 1: write_file")
        print("="*80)

        write_tool = WriteFileTool(backend=backend)
        test_file = f"{working_dir}/test.py"

        # Create new file
        result = write_tool.execute(file_path=test_file, content="def hello():\n    print('world')\n")
        assert isinstance(result, TextOutputModel)
        assert "created" in result.content.lower() or "wrote" in result.content.lower()

        # Overwrite existing file
        result = write_tool.execute(file_path=test_file, content="def hello():\n    print('updated')\n")
        assert isinstance(result, TextOutputModel)
        assert "overwrote" in result.content.lower()

        # TEST 2: read_file
        print("\n" + "="*80)
        print("TEST 2: read_file")
        print("="*80)

        read_tool = ReadFileTool(backend=backend)

        # Read text file
        result = read_tool.execute(path=test_file)
        assert isinstance(result, TextOutputModel)
        assert "def hello()" in result.content and "updated" in result.content

        # Read with offset and limit
        large_file = f"{working_dir}/large.txt"
        backend.write_file(file_path=large_file, content="".join([f"Line {i}\n" for i in range(1, 101)]))
        result = read_tool.execute(path=large_file, offset=10, limit=5)
        assert isinstance(result, TextOutputModel)
        assert "Line 11" in result.content and "Line 15" in result.content
        assert "truncated" in result.content.lower()

        # Read non-existent file
        result = read_tool.execute(path=f"{working_dir}/nonexistent.txt")
        assert isinstance(result, ErrorOutputModel)
        assert "not exist" in result.error.lower()

        # TEST 3: list_directory
        print("\n" + "="*80)
        print("TEST 3: list_directory")
        print("="*80)

        list_dir_tool = ListDirectoryTool(backend=backend)

        # Create test directory structure
        backend.create_directory(path=f"{working_dir}/subdir", parents=True)
        for file_name, content in [("file1.py", "# file 1"), ("file2.txt", "text"),
                                     (".hidden", "hidden"), ("subdir/nested.py", "# nested")]:
            backend.write_file(file_path=f"{working_dir}/{file_name}", content=content)

        # Basic listing
        result = list_dir_tool.execute(path=working_dir, respect_git_ignore=False)
        assert isinstance(result, FileListOutputModel)
        assert result.total_count >= 5

        # Verify sorting: directories first
        file_names = [f.name for f in result.files]
        dirs = [f.name for f in result.files if f.is_dir]
        files = [f.name for f in result.files if not f.is_dir]
        for i, name in enumerate(file_names):
            if name in files:
                for j in range(i):
                    assert file_names[j] in dirs
                break

        # Listing with ignore patterns
        result = list_dir_tool.execute(path=working_dir, ignore=["*.txt", ".*"], respect_git_ignore=False)
        assert isinstance(result, FileListOutputModel)
        file_names = [f.name for f in result.files]
        assert all(name not in file_names for name in ["file2.txt", "large.txt", ".hidden"])
        assert "file1.py" in file_names

        # Non-existent directory
        result = list_dir_tool.execute(path=f"{working_dir}/nonexistent")
        assert isinstance(result, ErrorOutputModel)

        # TEST 4: glob
        print("\n" + "="*80)
        print("TEST 4: glob")
        print("="*80)

        glob_tool = GlobTool(backend=backend)

        # Find Python files
        result = glob_tool.execute(pattern="*.py", path=working_dir, respect_git_ignore=False)
        assert isinstance(result, FileListOutputModel)
        assert result.total_count >= 2
        assert all(f.name.endswith(".py") for f in result.files)

        # Recursive glob
        result = glob_tool.execute(pattern="**/*.py", path=working_dir, respect_git_ignore=False)
        assert isinstance(result, FileListOutputModel)
        assert result.total_count >= 3

        # TEST 5: search_file_content
        print("\n" + "="*80)
        print("TEST 5: search_file_content")
        print("="*80)

        search_tool = SearchFileContentTool(backend=backend)

        # Search for pattern
        result = search_tool.execute(pattern="def hello", path=working_dir)
        assert isinstance(result, TextOutputModel)
        assert "def hello" in result.content
        assert "test.py" in result.content or "test" in result.content

        # Search with include filter
        result = search_tool.execute(pattern="file", path=working_dir, include="*.py")
        assert isinstance(result, TextOutputModel)

        # No matches
        result = search_tool.execute(pattern="nonexistent_pattern_xyz", path=working_dir)
        assert isinstance(result, TextOutputModel)
        assert "0 matches" in result.content

        # TEST 6: replace
        print("\n" + "="*80)
        print("TEST 6: replace")
        print("="*80)

        replace_tool = ReplaceTool(backend=backend)
        replace_file = f"{working_dir}/replace_test.py"
        backend.write_file(
            file_path=replace_file,
            content="def old_function():\n    return 'old'\n\ndef other():\n    pass\n"
        )

        # Single replacement
        result = replace_tool.execute(
            file_path=replace_file,
            old_string="def old_function():\n    return 'old'",
            new_string="def new_function():\n    return 'new'",
            expected_replacements=1
        )
        assert isinstance(result, TextOutputModel)
        assert "successfully" in result.content.lower()
        content = backend.read_file(file_path=replace_file)
        assert "new_function" in content and "old_function" not in content

        # No match
        result = replace_tool.execute(
            file_path=replace_file,
            old_string="nonexistent code",
            new_string="new code",
            expected_replacements=1
        )
        assert isinstance(result, ErrorOutputModel)
        assert "0 occurrences" in result.error

        # Create new file with empty old_string
        new_file = f"{working_dir}/created_by_replace.py"
        result = replace_tool.execute(file_path=new_file, old_string="", new_string="# Created by replace tool\n")
        assert isinstance(result, TextOutputModel)
        assert "created" in result.content.lower()
        assert backend.file_exists(path=new_file)

        # TEST 7: run_shell_command
        print("\n" + "="*80)
        print("TEST 7: run_shell_command")
        print("="*80)

        shell_tool = RunShellCommandTool(backend=backend)

        # Basic command
        result = shell_tool.execute(command="echo 'Hello from shell'")
        assert isinstance(result, TextOutputModel)
        assert "Hello from shell" in result.content and "Exit Code: 0" in result.content

        # Command with description
        result = shell_tool.execute(command="ls -la", description="List all files")
        assert isinstance(result, TextOutputModel)
        assert "List all files" in result.content

        # Command in subdirectory
        result = shell_tool.execute(command="pwd", directory="subdir")
        assert isinstance(result, TextOutputModel)
        assert "subdir" in result.content

        # Non-zero exit code
        result = shell_tool.execute(command="exit 1")
        assert isinstance(result, TextOutputModel)
        assert "Exit Code: 1" in result.content and "warning" in result.content.lower()

        # TEST 8: read_many_files
        print("\n" + "="*80)
        print("TEST 8: read_many_files")
        print("="*80)

        read_many_tool = ReadManyFilesTool(backend=backend)

        # Read multiple files
        result = read_many_tool.execute(paths=["*.py"], useDefaultExcludes=False, respect_git_ignore=False)
        assert isinstance(result, TextOutputModel)
        assert "---" in result.content and "End of content" in result.content

        # With exclude patterns
        result = read_many_tool.execute(paths=["*"], exclude=["*.txt"], useDefaultExcludes=False, respect_git_ignore=False)
        assert isinstance(result, TextOutputModel)

        # With include patterns
        result = read_many_tool.execute(paths=["*.py"], include=["*.txt"], useDefaultExcludes=False, respect_git_ignore=False)
        assert isinstance(result, TextOutputModel)

        # TEST 9: save_memory
        print("\n" + "="*80)
        print("TEST 9: save_memory")
        print("="*80)

        memory_tool = SaveMemoryTool(backend=backend)

        # Save memories
        result = memory_tool.execute(fact="User prefers Python for coding")
        assert isinstance(result, TextOutputModel)
        assert "saved" in result.content.lower()

        result = memory_tool.execute(fact="Project name is prompttodraft")
        assert isinstance(result, TextOutputModel)
        assert "saved" in result.content.lower()

        # INTEGRATION TEST: Combined workflow
        print("\n" + "="*80)
        print("INTEGRATION TEST: Combined workflow")
        print("="*80)

        workflow_file = f"{working_dir}/workflow.py"
        write_tool.execute(file_path=workflow_file, content="def calculate(x):\n    return x * 2\n")
        search_result = search_tool.execute(pattern="calculate", path=working_dir)
        assert "calculate" in search_result.content

        replace_tool.execute(
            file_path=workflow_file,
            old_string="def calculate(x):\n    return x * 2",
            new_string="def calculate(x):\n    return x * 3"
        )

        read_result = read_tool.execute(path=workflow_file)
        assert "x * 3" in read_result.content

        list_result = list_dir_tool.execute(path=working_dir, respect_git_ignore=False)
        assert "workflow.py" in [f.name for f in list_result.files]

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)

        backend.shutdown()

    finally:
        backend.shutdown()
        cleanup_backend(backend=backend)


def test_tools_local_backend():
    """Test all tools with LocalBackend."""
    backend = LocalBackend(project_id="test_tools_local")
    run_tools_e2e_test(backend=backend)


def test_tools_docker_backend():
    """Test all tools with DockerBackend."""
    backend = DockerBackend(project_id="test_tools_docker")
    run_tools_e2e_test(backend=backend)


@pytest.mark.e2b
def test_tools_e2b_backend():
    """Test all tools with E2BBackend."""
    backend = E2BBackend(project_id="test_tools_e2b")
    run_tools_e2e_test(backend=backend)


if __name__ == "__main__":
    # Run tests manually
    print("Testing with Local Backend...")
    test_tools_local_backend()

    print("\nTesting with Docker Backend...")
    test_tools_docker_backend()

    print("\nTesting with E2B Backend...")
    test_tools_e2b_backend()
