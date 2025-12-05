"""
Utility functions for UV package manager.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anyagent.backends.execution_backend import ExecutionBackend, CommandResult

# UV installation path - where UV is installed by the install script
UV_PATH_EXPORT = 'export PATH="$HOME/.local/bin:$PATH"'


def ensure_uv_installed(backend: "ExecutionBackend") -> tuple[bool, str]:
    """
    Ensure UV is installed in the backend, installing it if necessary.

    Args:
        backend: The execution backend to check and install UV in

    Returns:
        Tuple of (success: bool, message: str)
        - success: True if UV is available (was already installed or successfully installed)
        - message: Description of what happened
    """
    # Check if uv is already installed
    uv_check = backend.execute_command(
        command=f'{UV_PATH_EXPORT} && command -v uv',
        timeout=10000,
    )

    if uv_check.exit_code == 0:
        return True, "UV is already installed"

    # Install uv
    install_command = "curl -LsSf https://astral.sh/uv/install.sh | sh"
    install_result = backend.execute_command(
        command=install_command,
        timeout=120000,
    )

    if install_result.exit_code == 0:
        return True, "UV installed successfully"

    return False, f"Failed to install UV. Exit code: {install_result.exit_code}. Output: {install_result.output}"


def execute_uv_command(backend: "ExecutionBackend", uv_command: str, timeout: int = 300000) -> "CommandResult":
    """
    Execute a UV command with proper PATH setup.

    Args:
        backend: The execution backend to run the command in
        uv_command: The UV command to execute (without 'uv' prefix). Examples: 'init', 'add requests', 'run script.py'
        timeout: Command timeout in milliseconds (default: 5 minutes)

    Returns:
        CommandResult with the command output and exit code
    """
    full_command = f'{UV_PATH_EXPORT} && uv {uv_command}'
    return backend.execute_command(command=full_command, timeout=timeout)
