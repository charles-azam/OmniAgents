"""No-op initializer for testing or when initialization is not needed."""

from prompttodraft.initializers.base import ProjectInitializer


class NoOpInitializer(ProjectInitializer):
    """
    No-op initializer that does nothing.

    Useful for testing scenarios where you don't want any initialization,
    or when working with pre-initialized projects.
    """

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
