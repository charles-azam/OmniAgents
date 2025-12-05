"""
Generic preset with no special tools or initialization.
"""
from anyagent.presets.base import Preset, InitResult

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anyagent.backends.execution_backend import ExecutionBackend


class GenericPreset(Preset):
    """
    Generic preset with no language-specific tools.

    Use this when you want just the core file/shell tools
    without any language-specific tooling.
    """

    name = "generic"
    docker_image = None
    tool_classes = ()

    def is_initialized(self, backend: "ExecutionBackend") -> bool:
        return True

    def initialize_project(self, backend: "ExecutionBackend") -> InitResult:
        return InitResult(success=True, message="", first_run=False)
