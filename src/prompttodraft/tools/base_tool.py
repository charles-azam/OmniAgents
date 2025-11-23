"""
Base class for all core tools.

This module defines the abstract base class that all core tools inherit from.
"""
from abc import ABC, abstractmethod

from prompttodraft.tools.metadata import ToolMetadata
from prompttodraft.backends.execution_backend import ExecutionBackend
from prompttodraft.outputs.outputs import ToolOutputModel


class CoreTool(ABC):
    """
    Abstract base class for all core tools.

    All tools must define metadata and implement the execute method.
    This base class ensures consistency across all tools and enables
    automatic adapter generation.
    """

    metadata: ToolMetadata

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize the tool with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    @abstractmethod
    def execute(self, **kwargs) -> ToolOutputModel:
        """
        Execute the tool with given arguments.

        Args:
            **kwargs: Tool-specific arguments defined in metadata.inputs

        Returns:
            ToolOutputModel with the tool's output
        """
        pass
