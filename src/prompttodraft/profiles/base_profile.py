"""
Base class for project profiles.

A project profile defines how a project is initialized and what tools are available
for a specific language or framework.
"""
from abc import ABC, abstractmethod
from typing import Any

from prompttodraft.backends.execution_backend import ExecutionBackend
from prompttodraft.tools.base_tool import CoreBackendTool


class ProjectProfile(ABC):
    """
    Abstract base class for project profiles.
    """

    @abstractmethod
    def initialize(self, backend: ExecutionBackend) -> dict[str, Any]:
        """
        Initialize the project in the backend.

        Args:
            backend: The execution backend to use.

        Returns:
            Dictionary with initialization results.
        """
        pass

    @abstractmethod
    def get_tools(self, backend: ExecutionBackend) -> list[CoreBackendTool]:
        """
        Get the list of tools specific to this profile.

        Args:
            backend: The execution backend to use.

        Returns:
            List of tool instances.
        """
        pass

    @abstractmethod
    def get_system_prompt_additions(self) -> str:
        """
        Get additional instructions for the system prompt.

        Returns:
            String containing additional instructions.
        """
        pass
