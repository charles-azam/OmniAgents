"""
Tests for the OpenHands backend integration.

These tests verify that the OpenHandsBackend adapter correctly wraps
OpenHands runtimes and implements the ExecutionBackend interface.
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

from omniagents.backends import (
    OPENHANDS_AVAILABLE,
    BackendStatus,
    FileType,
    CommandResult,
)
from omniagents.backends.state_manager import NoOpStateManager


# Skip all tests if OpenHands is not installed
pytestmark = pytest.mark.skipif(
    not OPENHANDS_AVAILABLE,
    reason="OpenHands not installed. Install with: pip install omniagents[openhands]"
)


@dataclass
class MockCmdOutputObservation:
    """Mock OpenHands CmdOutputObservation."""
    content: str
    exit_code: int


@dataclass
class MockFileReadObservation:
    """Mock OpenHands FileReadObservation."""
    content: str
    path: str


@dataclass
class MockFileWriteObservation:
    """Mock OpenHands FileWriteObservation."""
    content: str
    path: str


@dataclass
class MockErrorObservation:
    """Mock OpenHands ErrorObservation."""
    content: str


class MockRuntime:
    """Mock OpenHands Runtime for testing."""

    def __init__(self):
        self._runtime_initialized = True
        self._workspace_root = Path("/workspace")
        self._files: dict[str, str] = {}

    @property
    def runtime_initialized(self) -> bool:
        return self._runtime_initialized

    @property
    def workspace_root(self) -> Path:
        return self._workspace_root

    def run(self, action) -> MockCmdOutputObservation:
        """Mock command execution."""
        return MockCmdOutputObservation(
            content=f"Executed: {action.command}",
            exit_code=0
        )

    def read(self, action) -> MockFileReadObservation | MockErrorObservation:
        """Mock file read."""
        path = action.path
        if path in self._files:
            return MockFileReadObservation(content=self._files[path], path=path)
        return MockErrorObservation(content=f"File not found: {path}")

    def write(self, action) -> MockFileWriteObservation:
        """Mock file write."""
        self._files[action.path] = action.content
        return MockFileWriteObservation(content="", path=action.path)

    def close(self):
        """Mock close."""
        pass


def test_openhands_backend_import():
    """Test that OpenHandsBackend can be imported when OpenHands is available."""
    from omniagents.backends.openhands_backend import OpenHandsBackend
    assert OpenHandsBackend is not None


def test_openhands_backend_creation():
    """Test creating an OpenHandsBackend with a mock runtime."""
    from omniagents.backends.openhands_backend import OpenHandsBackend

    mock_runtime = MockRuntime()
    state_manager = NoOpStateManager()

    backend = OpenHandsBackend(
        runtime=mock_runtime,
        project_id="test-project",
        state_manager=state_manager
    )

    assert backend.project_id == "test-project"
    assert backend.get_status() == BackendStatus.UNINITIALIZED


def test_openhands_backend_start():
    """Test starting the OpenHands backend."""
    from omniagents.backends.openhands_backend import OpenHandsBackend

    mock_runtime = MockRuntime()
    state_manager = NoOpStateManager()

    backend = OpenHandsBackend(
        runtime=mock_runtime,
        project_id="test-project",
        state_manager=state_manager
    )

    backend.start()
    assert backend.get_status() == BackendStatus.RUNNING


def test_openhands_backend_execute_command():
    """Test executing a command through the OpenHands backend."""
    from omniagents.backends.openhands_backend import OpenHandsBackend

    mock_runtime = MockRuntime()
    state_manager = NoOpStateManager()

    backend = OpenHandsBackend(
        runtime=mock_runtime,
        project_id="test-project",
        state_manager=state_manager
    )
    backend.start()

    result = backend.execute_command("echo hello")

    assert isinstance(result, CommandResult)
    assert result.exit_code == 0
    assert "echo hello" in result.output


def test_openhands_backend_working_directory():
    """Test getting the working directory."""
    from omniagents.backends.openhands_backend import OpenHandsBackend

    mock_runtime = MockRuntime()
    state_manager = NoOpStateManager()

    backend = OpenHandsBackend(
        runtime=mock_runtime,
        project_id="test-project",
        state_manager=state_manager
    )

    working_dir = backend.get_working_directory()
    assert working_dir == Path("/workspace")


def test_openhands_backend_file_operations():
    """Test file read/write operations."""
    from omniagents.backends.openhands_backend import OpenHandsBackend

    mock_runtime = MockRuntime()
    state_manager = NoOpStateManager()

    backend = OpenHandsBackend(
        runtime=mock_runtime,
        project_id="test-project",
        state_manager=state_manager
    )
    backend.start()

    # Write a file
    test_path = Path("/workspace/test.py")
    test_content = "print('hello')"
    backend.write_file(file_path=test_path, content=test_content)

    # Read it back
    content = backend.read_file(file_path=test_path)
    assert content == test_content


def test_openhands_backend_shutdown():
    """Test shutting down the OpenHands backend."""
    from omniagents.backends.openhands_backend import OpenHandsBackend

    mock_runtime = MockRuntime()
    state_manager = NoOpStateManager()

    backend = OpenHandsBackend(
        runtime=mock_runtime,
        project_id="test-project",
        state_manager=state_manager
    )
    backend.start()
    assert backend.get_status() == BackendStatus.RUNNING

    backend.shutdown()
    assert backend.get_status() == BackendStatus.STOPPED


def test_factory_list_backends():
    """Test that OpenHands backends appear in list_available_backends."""
    from omniagents.backends import list_available_backends

    backends = list_available_backends()

    assert "local" in backends
    assert "docker" in backends

    if OPENHANDS_AVAILABLE:
        assert "openhands-docker" in backends
        assert "openhands-local" in backends


def test_factory_create_backend_local():
    """Test creating a local backend via factory."""
    from omniagents.backends import create_backend

    backend = create_backend(
        backend_type="local",
        project_id="test-factory-local"
    )

    assert backend is not None
    assert backend.project_id == "test-factory-local"


def test_factory_unknown_backend():
    """Test that unknown backend type raises ValueError."""
    from omniagents.backends import create_backend

    with pytest.raises(ValueError, match="Unknown backend type"):
        create_backend(
            backend_type="unknown-backend",
            project_id="test"
        )


@pytest.mark.skipif(
    not OPENHANDS_AVAILABLE,
    reason="OpenHands not installed"
)
def test_openhands_backend_error_handling():
    """Test error handling when file operations fail."""
    from omniagents.backends.openhands_backend import OpenHandsBackend

    mock_runtime = MockRuntime()
    state_manager = NoOpStateManager()

    backend = OpenHandsBackend(
        runtime=mock_runtime,
        project_id="test-project",
        state_manager=state_manager
    )
    backend.start()

    # Try to read a non-existent file
    with pytest.raises(FileNotFoundError):
        backend.read_file(file_path=Path("/workspace/nonexistent.txt"))
