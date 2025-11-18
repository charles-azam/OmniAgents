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
    working_dir = backend.get_working_directory()

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
    pyproject_path = str(Path(working_dir) / "pyproject.toml")
    is_first_run = not backend.file_exists(path=pyproject_path)

    if is_first_run:
        # First run: execute uv init
        messages.append("Running 'uv init'...")
        init_command = f'export PATH="$HOME/.local/bin:$PATH" && cd "{working_dir}" && uv init'
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
    sync_command = f'export PATH="$HOME/.local/bin:$PATH" && cd "{working_dir}" && uv sync'
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
