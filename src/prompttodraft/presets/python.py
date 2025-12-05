"""
Python development presets.
"""
from prompttodraft.presets.base import Preset, InitResult
from prompttodraft.tools.uv_tool import UVTool

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prompttodraft.backends.execution_backend import ExecutionBackend


class PythonUVPreset(Preset):
    """
    Python preset using UV package manager.

    Provides:
    - UVTool for running uv commands
    - Project initialization with uv init + uv sync
    - Suggested Docker image: ghcr.io/astral-sh/uv:debian
    """

    name = "python-uv"
    docker_image = "ghcr.io/astral-sh/uv:debian"
    tool_classes = (UVTool,)

    def is_initialized(self, backend: "ExecutionBackend") -> bool:
        pyproject_path = backend.get_working_directory() / "pyproject.toml"
        return backend.file_exists(path=pyproject_path) is not None

    def initialize_project(self, backend: "ExecutionBackend") -> InitResult:
        """
        Initialize a Python project using UV package manager.

        On first run (no pyproject.toml), executes 'uv init' and 'uv sync'.
        On subsequent runs, only executes 'uv sync' to synchronize dependencies.
        Ensures uv is installed before attempting initialization.
        """
        messages: list[str] = []
        is_first_run = not self.is_initialized(backend=backend)

        # Check if uv is installed, install if not
        uv_check = backend.execute_command(
            command='export PATH="$HOME/.local/bin:$PATH" && command -v uv',
            timeout=10000,
        )

        if uv_check.exit_code != 0:
            messages.append("Installing uv package manager...")
            install_command = "curl -LsSf https://astral.sh/uv/install.sh | sh"
            install_result = backend.execute_command(
                command=install_command,
                timeout=120000,
            )

            if install_result.exit_code != 0:
                return InitResult(
                    success=False,
                    message=f"Failed to install uv. Exit code: {install_result.exit_code}. Output: {install_result.output}",
                    first_run=is_first_run,
                )
            messages.append("uv installed successfully")

        if is_first_run:
            messages.append("Running 'uv init'...")
            init_command = 'export PATH="$HOME/.local/bin:$PATH" && uv init'
            result = backend.execute_command(
                command=init_command,
                timeout=120000,
            )

            if result.exit_code != 0:
                return InitResult(
                    success=False,
                    message=f"'uv init' failed with exit code {result.exit_code}. Output: {result.output}",
                    first_run=is_first_run,
                )
            messages.append("uv init completed successfully")

        # Always run uv sync
        messages.append("Running 'uv sync'...")
        sync_command = 'export PATH="$HOME/.local/bin:$PATH" && uv sync'
        result = backend.execute_command(
            command=sync_command,
            timeout=300000,
        )

        if result.exit_code != 0:
            return InitResult(
                success=False,
                message=f"'uv sync' failed with exit code {result.exit_code}. Output: {result.output}",
                first_run=is_first_run,
            )
        messages.append("uv sync completed successfully")

        return InitResult(
            success=True,
            message="\n".join(messages),
            first_run=is_first_run,
        )


class PythonPipPreset(Preset):
    """
    Python preset using pip + venv.

    Provides:
    - No special tools (uses shell commands for pip)
    - Project initialization with venv creation
    - Suggested Docker image: python:3.13-slim
    """

    name = "python-pip"
    docker_image = "python:3.13-slim"
    tool_classes = ()

    def is_initialized(self, backend: "ExecutionBackend") -> bool:
        venv_path = backend.get_working_directory() / ".venv"
        return backend.file_exists(path=venv_path) is not None

    def initialize_project(self, backend: "ExecutionBackend") -> InitResult:
        """Initialize a Python project with venv."""
        is_first_run = not self.is_initialized(backend=backend)

        if is_first_run:
            result = backend.execute_command(
                command="python3 -m venv .venv",
                timeout=60000,
            )

            if result.exit_code != 0:
                return InitResult(
                    success=False,
                    message=f"Failed to create venv: {result.output}",
                    first_run=True,
                )

            return InitResult(
                success=True,
                message="Created Python virtual environment (.venv)",
                first_run=True,
            )

        return InitResult(success=True, message="", first_run=False)
