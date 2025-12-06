"""
Python development presets.
"""
from anyagents.presets.base import Preset, InitResult
from anyagents.tools.uv_tool import UVTool
from anyagents.uv_utils import ensure_uv_installed, execute_uv_command

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anyagents.backends.execution_backend import ExecutionBackend


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

        # Ensure UV is installed
        success, message = ensure_uv_installed(backend=backend)
        if not success:
            return InitResult(
                success=False,
                message=message,
                first_run=is_first_run,
            )

        if "installed successfully" in message.lower():
            messages.append(message)

        if is_first_run:
            messages.append("Running 'uv init'...")
            result = execute_uv_command(backend=backend, uv_command='init', timeout=120000)

            if result.exit_code != 0:
                return InitResult(
                    success=False,
                    message=f"'uv init' failed with exit code {result.exit_code}. Output: {result.output}",
                    first_run=is_first_run,
                )
            messages.append("uv init completed successfully")

        # Always run uv sync
        messages.append("Running 'uv sync'...")
        result = execute_uv_command(backend=backend, uv_command='sync', timeout=300000)

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
