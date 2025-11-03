"""
LangChain framework adapter.

This module provides clean LangChain tool wrappers for all core tools.
"""
from langchain_core.tools import tool

from prompttodraft.agent.backends.execution_backend import ExecutionBackend


def create_langchain_tools(backend: ExecutionBackend) -> list:
    """
    Create LangChain-compatible tools for the execution backend.

    Args:
        backend: The execution backend instance.

    Returns:
        List of LangChain tool objects.
    """

    @tool
    def write_file(file_path: str, content: str) -> str:
        """
        Write content to a file, creating it if it doesn't exist.

        Args:
            file_path: Path to the file to write.
            content: Content to write to the file.

        Returns:
            Success message.
        """
        backend.write_file(file_path=file_path, content=content)
        return f"Successfully wrote to {file_path}"

    @tool
    def read_file(file_path: str) -> str:
        """
        Read the contents of a file.

        Args:
            file_path: Path to the file to read.

        Returns:
            The file contents.
        """
        return backend.read_file(file_path=file_path)

    @tool
    def list_directory(path: str, recursive: bool = False) -> str:
        """
        List the contents of a directory.

        Args:
            path: Path to the directory.
            recursive: Whether to list recursively.

        Returns:
            List of files and directories.
        """
        files = backend.list_directory(path=path, recursive=recursive)
        return "\n".join([f"{f.type.value}: {f.path}" for f in files])

    @tool
    def glob_files(pattern: str, path: str | None = None) -> str:
        """
        Find files matching a glob pattern.

        Args:
            pattern: Glob pattern to match (e.g., "*.py", "src/**/*.ts").
            path: Optional directory to search in.

        Returns:
            List of matching file paths.
        """
        matches = backend.glob_files(pattern=pattern, path=path)
        return "\n".join(matches) if matches else "No files found matching pattern"

    @tool
    def search_file_content(pattern: str, path: str | None = None, file_pattern: str | None = None) -> str:
        """
        Search for a pattern in file contents using grep.

        Args:
            pattern: Text or regex pattern to search for.
            path: Optional directory to search in.
            file_pattern: Optional glob pattern to filter files.

        Returns:
            Search results with file paths and line numbers.
        """
        result = backend.execute_command(
            command=f"grep -rn '{pattern}' {path or '.'}" + (f" --include='{file_pattern}'" if file_pattern else "")
        )
        return result.output if result.exit_code == 0 else "No matches found"

    @tool
    def replace_in_file(file_path: str, old_text: str, new_text: str) -> str:
        """
        Replace text in a file.

        Args:
            file_path: Path to the file.
            old_text: Text to replace.
            new_text: Text to replace with.

        Returns:
            Success message.
        """
        content = backend.read_file(file_path=file_path)
        updated_content = content.replace(old_text, new_text)
        backend.write_file(file_path=file_path, content=updated_content)
        return f"Successfully replaced text in {file_path}"

    @tool
    def run_shell_command(command: str, timeout: int | None = None) -> str:
        """
        Execute a shell command.

        Args:
            command: The shell command to execute.
            timeout: Optional timeout in milliseconds.

        Returns:
            Command output and exit code.
        """
        result = backend.execute_command(command=command, timeout=timeout)
        return f"Exit code: {result.exit_code}\nOutput:\n{result.output}"

    @tool
    def read_many_files(file_paths: str) -> str:
        """
        Read multiple files at once.

        Args:
            file_paths: Comma-separated list of file paths.

        Returns:
            Contents of all files.
        """
        paths = [p.strip() for p in file_paths.split(",")]
        results = []
        for path in paths:
            try:
                content = backend.read_file(file_path=path)
                results.append(f"=== {path} ===\n{content}\n")
            except Exception as e:
                results.append(f"=== {path} ===\nError: {str(e)}\n")
        return "\n".join(results)

    @tool
    def save_memory(content: str) -> str:
        """
        Save information to persistent memory (.gemini/GEMINI.md).

        Args:
            content: Content to save to memory.

        Returns:
            Success message.
        """
        working_dir = backend.get_working_directory()
        memory_dir = f"{working_dir}/.gemini"
        memory_file = f"{memory_dir}/GEMINI.md"

        # Create directory if needed
        backend.create_directory(path=memory_dir, parents=True)

        # Append to memory file
        existing = ""
        if backend.file_exists(path=memory_file):
            existing = backend.read_file(file_path=memory_file)

        backend.write_file(file_path=memory_file, content=f"{existing}\n{content}".strip())
        return "Successfully saved to memory"

    @tool
    def run_uv_command(uv_command: str, timeout: int | None = None) -> str:
        """
        Execute a uv command (Python package manager).

        Args:
            uv_command: The uv command to run (e.g., "run script.py", "add requests").
            timeout: Optional timeout in milliseconds.

        Returns:
            Command output and exit code.
        """
        result = backend.execute_uv(uv_command=uv_command, timeout=timeout)
        return f"Exit code: {result.exit_code}\nOutput:\n{result.output}"

    return [
        write_file,
        read_file,
        list_directory,
        glob_files,
        search_file_content,
        replace_in_file,
        run_shell_command,
        read_many_files,
        save_memory,
        run_uv_command,
    ]
