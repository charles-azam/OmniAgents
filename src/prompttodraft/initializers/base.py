"""Base classes for project initialization."""

from abc import ABC, abstractmethod


class ProjectInitializer(ABC):
    """
    Abstract base class for project initialization.

    Each language implementation handles README.md, .gitignore, and tooling setup.
    """

    def __init__(self, backend: "ExecutionBackend"):
        """
        Initialize the project initializer.

        Args:
            backend: The execution backend to use for file operations
        """
        self.backend = backend
        self.working_dir = backend.get_working_directory()

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
