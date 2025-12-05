"""
Empty project profile for generic usage.
"""
from typing import Any

from prompttodraft.backends.execution_backend import ExecutionBackend
from prompttodraft.profiles.base_profile import ProjectProfile
from prompttodraft.tools.base_tool import CoreBackendTool


class EmptyProfile(ProjectProfile):
    """
    Profile for generic projects with no specific initialization or tools.
    """

    def initialize(self, backend: ExecutionBackend) -> dict[str, Any]:
        """
        No initialization needed.
        """
        return {
            "first_run": False,
            "directory": str(backend.get_working_directory()),
            "success": True,
            "message": "No initialization performed (EmptyProfile).",
        }

    def get_tools(self, backend: ExecutionBackend) -> list[CoreBackendTool]:
        """
        No specific tools.
        """
        return []

    def get_system_prompt_additions(self) -> str:
        """
        No specific instructions.
        """
        return ""
