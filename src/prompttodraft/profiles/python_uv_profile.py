"""
Python project profile using uv package manager.
"""
from typing import Any

from prompttodraft.backends.execution_backend import ExecutionBackend
from prompttodraft.profiles.base_profile import ProjectProfile
from prompttodraft.tools.base_tool import CoreBackendTool
from prompttodraft.tools.uv_tool import UVTool
from prompttodraft.utils import initialize_python_project


class PythonUVProfile(ProjectProfile):
    """
    Profile for Python projects using uv.
    """

    def initialize(self, backend: ExecutionBackend) -> dict[str, Any]:
        """
        Initialize a Python project using uv.
        """
        return initialize_python_project(backend)

    def get_tools(self, backend: ExecutionBackend) -> list[CoreBackendTool]:
        """
        Get Python/uv specific tools.
        """
        return [UVTool(backend=backend)]

    def get_system_prompt_additions(self) -> str:
        """
        Get Python/uv specific instructions.
        """
        return """
You are working in a Python environment managed by 'uv'.
You have access to the 'uv' tool to run scripts, install packages, and manage dependencies.
Always use 'uv run' to execute Python scripts or tests (e.g., 'uv run script.py', 'uv run pytest').
"""
