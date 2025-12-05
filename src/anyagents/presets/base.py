"""
Base class for development environment presets.

A Preset defines the tools and project initialization for a specific
development environment (e.g., Python with UV, Node.js with NPM).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prompttodraft.backends.execution_backend import ExecutionBackend
    from prompttodraft.tools.base_tool import CoreBackendTool


@dataclass(frozen=True)
class InitResult:
    """Result of project initialization."""

    success: bool
    message: str
    first_run: bool


class Preset(ABC):
    """
    Abstract base class for development environment presets.

    A preset defines:
    - Which tools are available (tool_classes)
    - How to initialize a new project (initialize_project)
    - Suggested Docker image for containerized execution (docker_image)

    Attributes to define in subclasses:
        name: Identifier for this preset (e.g., "python-uv")
        docker_image: Suggested Docker image, or None
        tool_classes: Tuple of CoreBackendTool classes

    Methods to override (optional):
        initialize_project(): Setup logic for new projects
        is_initialized(): Check if project needs setup

    Example:
        class PythonUVPreset(Preset):
            name = "python-uv"
            docker_image = "ghcr.io/astral-sh/uv:debian"
            tool_classes = (UVTool,)

            def is_initialized(self, backend):
                return backend.file_exists(backend.get_working_directory() / "pyproject.toml")

            def initialize_project(self, backend):
                result = backend.execute_command("uv init && uv sync")
                return InitResult(success=result.exit_code == 0, message=result.output, first_run=True)
    """

    name: str
    docker_image: str | None = None
    tool_classes: tuple[type["CoreBackendTool"], ...] = ()

    @abstractmethod
    def initialize_project(self, backend: "ExecutionBackend") -> InitResult:
        """
        Initialize a new project in this preset's environment.

        Called automatically when is_initialized() returns False.

        Args:
            backend: The execution backend to run commands on

        Returns:
            InitResult with success status and message
        """
        ...

    @abstractmethod
    def is_initialized(self, backend: "ExecutionBackend") -> bool:
        """
        Check if the project is already initialized.

        Args:
            backend: The execution backend to check

        Returns:
            True if project is initialized, False if initialization needed
        """
        ...
