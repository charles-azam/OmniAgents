"""Base classes for project initialization."""

from __future__ import annotations

from abc import ABC, abstractmethod

from prompttodraft.backends.execution_backend import ExecutionBackend


class ProjectInitializer(ABC):
    """
    Abstract base class for project initialization.

    Each language implementation handles README.md, .gitignore, and tooling setup.
    """

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize the project initializer.

        Args:
            backend: The execution backend to use for file operations
        """
        self.backend = backend
        self.working_dir = backend.get_working_directory()

    @abstractmethod
    def is_initialized(self) -> bool:
        """
        Check if the project is already initialized.

        Returns:
            True if project is initialized, False otherwise

        Examples:
            - Python: Check if pyproject.toml exists
            - TypeScript: Check if package.json exists
        """
        pass

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the project with README.md, .gitignore, and language-specific setup.

        Each implementation should:
        1. Ensure README.md exists
        2. Ensure .gitignore exists with language-specific patterns
        3. Set up language tooling (e.g., uv for Python, npm for TypeScript)
        """
        pass
