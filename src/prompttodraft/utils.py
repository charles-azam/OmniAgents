"""
Utility functions for prompttodraft.

This module provides utility functions for project initialization and other common tasks.
"""
from pathlib import Path

from prompttodraft.backends.execution_backend import ExecutionBackend


def initialize_project(backend: ExecutionBackend) -> dict[str, bool | str]:
    """
    Initialize a Python project using uv package manager.

    On first run (no pyproject.toml exists), executes 'uv init' and 'uv sync'.
    On subsequent runs, only executes 'uv sync' to synchronize dependencies.
    Ensures uv is installed before attempting initialization.

    Args:
        backend: The execution backend to use for running commands

    Returns:
        Dictionary with initialization results:
        - first_run: bool indicating if this was the first initialization
        - directory: str path to the initialized directory
        - success: bool indicating if initialization succeeded
        - message: str with status message

    Raises:
        RuntimeError: If uv installation, uv init, or uv sync fails
    """
    # Get working directory
    working_dir = str(backend.get_working_directory())

    messages = []

    # Check if uv is installed, install if not
    uv_check = backend.execute_command(
        command='export PATH="$HOME/.local/bin:$PATH" && command -v uv',
        timeout=10000,
    )

    if uv_check.exit_code != 0:
        # uv is not installed, install it
        messages.append("Installing uv package manager...")
        install_command = "curl -LsSf https://astral.sh/uv/install.sh | sh"
        install_result = backend.execute_command(
            command=install_command,
            timeout=120000,
        )

        if install_result.exit_code != 0:
            raise RuntimeError(
                f"Failed to install uv. Exit code: {install_result.exit_code}. Output: {install_result.output}"
            )

        messages.append("✓ uv installed successfully")

    # Check if this is the first run
    pyproject_path = Path(working_dir) / "pyproject.toml"
    is_first_run = not backend.file_exists(path=pyproject_path)

    if is_first_run:
        # First run: execute uv init
        messages.append("Running 'uv init'...")
        # For LocalBackend, we are in a temp directory, but LLM sees /workspace.
        # We need to run uv init in the current working directory of the shell.
        # backend.execute_command runs in the project root by default.
        # So we don't need to cd anywhere if we want to init in project root.
        # However, previously we used 'cd "{working_dir}"'. 
        # On Docker/E2B, working_dir is /workspace, which is correct.
        # On Local, working_dir is /workspace, which DOES NOT EXIST.
        
        # Solution: Don't cd to working_dir if it's the default.
        # Or, let the backend handle CWD.
        # backend.execute_command already sets CWD to project root.
        
        init_command = 'export PATH="$HOME/.local/bin:$PATH" && uv init'
        result = backend.execute_command(
            command=init_command,
            timeout=120000,
        )

        if result.exit_code != 0:
            raise RuntimeError(
                f"'uv init' failed with exit code {result.exit_code}. Output: {result.output}"
            )

        messages.append("✓ uv init completed successfully")

    # Always run uv sync
    messages.append("Running 'uv sync'...")
    sync_command = 'export PATH="$HOME/.local/bin:$PATH" && uv sync'
    result = backend.execute_command(
        command=sync_command,
        timeout=300000,
    )

    if result.exit_code != 0:
        raise RuntimeError(
            f"'uv sync' failed with exit code {result.exit_code}. Output: {result.output}"
        )

    messages.append("✓ uv sync completed successfully")

    return {
        "first_run": is_first_run,
        "directory": working_dir,
        "success": True,
        "message": "\n".join(messages),
    }
