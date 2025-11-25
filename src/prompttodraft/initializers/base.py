"""Base classes for project initialization."""

from __future__ import annotations

from abc import ABC, abstractmethod

from prompttodraft.backends.execution_backend import ExecutionBackend


class ProjectInitializer(ABC):
    """
    Abstract base class for project initialization.

    Each language implementation handles README.md, .gitignore, and tooling setup.
    """

    def __init__(self, backend: ExecutionBackend | None = None):
        """
        Initialize the project initializer.

        Args:
            backend: The execution backend to use for file operations.
                    Can be None initially if set later via attribute assignment.
        """
        self.backend = backend
        self.working_dir = backend.get_working_directory() if backend else ""

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

    @abstractmethod
    def get_docker_image(self) -> str:
        """
        Get the Docker image for this language.

        Returns:
            Docker image name with tag

        Examples:
            - Python: "ghcr.io/astral-sh/uv:debian"
            - TypeScript: "node:20-slim"
            - Rust: "rust:1.75-slim"
        """
        pass

    @abstractmethod
    def get_docker_env_vars(self) -> dict[str, str]:
        """
        Get Docker environment variables for this language.

        Returns:
            Dictionary of environment variables to set in container

        Examples:
            - Python (UV): {"UV_CACHE_DIR": "/workspace/.cache/uv", ...}
            - Node: {"NPM_CONFIG_CACHE": "/workspace/.npm", ...}
        """
        pass

    def get_package_manager_commands(self) -> dict[str, str]:
        """
        Get common package manager command patterns.

        Returns:
            Dictionary mapping operation to command template

        Examples:
            - Python: {
                "install": "uv add {package}",
                "run": "uv run {script}",
                "test": "uv run pytest {path}"
              }
            - TypeScript: {
                "install": "npm install {package}",
                "run": "npm run {script}",
                "test": "npm test {path}"
              }
        """
        return {}

    @property
    def language_name(self) -> str:
        """
        Get the human-readable language name.

        Returns:
            Language name (e.g., "Python", "TypeScript", "Rust")
        """
        return "Unknown"
