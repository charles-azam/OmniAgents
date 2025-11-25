"""No-op initializer for testing or when initialization is not needed."""

from prompttodraft.initializers.base import ProjectInitializer


class NoOpInitializer(ProjectInitializer):
    """
    No-op initializer that does nothing.

    Useful for testing scenarios where you don't want any initialization,
    or when working with pre-initialized projects.
    """

    @property
    def language_name(self) -> str:
        """Get the language name."""
        return "Generic"

    def get_docker_image(self) -> str:
        """Get the Docker image for generic projects."""
        return "ubuntu:22.04"

    def get_docker_env_vars(self) -> dict[str, str]:
        """Get Docker environment variables for generic projects."""
        return {}

    def get_package_manager_commands(self) -> dict[str, str]:
        """Get package manager commands for generic projects."""
        return {}

    def is_initialized(self) -> bool:
        """
        Always returns True (project is considered initialized).

        Returns:
            True
        """
        return True

    def initialize(self) -> None:
        """Do nothing - no-op implementation."""
        pass
