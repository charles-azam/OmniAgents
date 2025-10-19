"""
CodingTool abstract class and implementations.

This module defines the CodingTool interface and provides implementations
for different execution environments (Local, Docker, E2B).
"""
from abc import ABC, abstractmethod

from prompttodraft.tools.backends.local_backend import LocalBackend
from prompttodraft.tools.core.bash_tool_core import BashToolCore
from prompttodraft.tools.core.edit_tool_core import EditToolCore
from prompttodraft.tools.core.glob_tool_core import GlobToolCore
from prompttodraft.tools.core.grep_tool_core import GrepToolCore
from prompttodraft.tools.core.ls_tool_core import LSToolCore
from prompttodraft.tools.core.replace_tool_core import ReplaceToolCore
from prompttodraft.tools.core.user_input_tool_core import UserInputToolCore
from prompttodraft.tools.core.view_tool_core import ViewToolCore
from prompttodraft.tools.outputs.models import ToolOutputModel


# Type alias for output
Output = ToolOutputModel


class CodingTool(ABC):
    """Abstract base class for coding tools with different execution environments."""

    @abstractmethod
    def bash_tool(self, command: str, timeout: int | None = None) -> Output:
        """Execute a bash command."""
        pass

    @abstractmethod
    def edit_tool(self, file_path: str, old_string: str, new_string: str) -> Output:
        """Edit a file by replacing old_string with new_string."""
        pass

    @abstractmethod
    def glob_tool(self, pattern: str, path: str | None = None) -> Output:
        """Find files matching a glob pattern."""
        pass

    @abstractmethod
    def grep_tool(self, pattern: str, include: str | None = None, path: str | None = None) -> Output:
        """Search file contents using regex."""
        pass

    @abstractmethod
    def ls_tool(self, path: str) -> Output:
        """List directory contents."""
        pass

    @abstractmethod
    def replace_tool(self, file_path: str, content: str) -> Output:
        """Replace entire file contents."""
        pass

    @abstractmethod
    def user_input_tool(self, question: str) -> Output:
        """Ask the user for input."""
        pass

    @abstractmethod
    def view_tool(self, file_path: str) -> Output:
        """Read a file."""
        pass


class CodingToolLocal(CodingTool):
    """CodingTool implementation for local execution."""

    def __init__(self):
        """Initialize CodingToolLocal with LocalBackend."""
        backend = LocalBackend()

        # Create core tool instances with the backend
        self._bash = BashToolCore(backend=backend)
        self._edit = EditToolCore(backend=backend)
        self._glob = GlobToolCore(backend=backend)
        self._grep = GrepToolCore(backend=backend)
        self._ls = LSToolCore(backend=backend)
        self._replace = ReplaceToolCore(backend=backend)
        self._user_input = UserInputToolCore(backend=backend)
        self._view = ViewToolCore(backend=backend)

    def bash_tool(self, command: str, timeout: int | None = None) -> Output:
        """Execute a bash command."""
        return self._bash.execute(command=command, timeout=timeout)

    def edit_tool(self, file_path: str, old_string: str, new_string: str) -> Output:
        """Edit a file by replacing old_string with new_string."""
        return self._edit.execute(file_path=file_path, old_string=old_string, new_string=new_string)

    def glob_tool(self, pattern: str, path: str | None = None) -> Output:
        """Find files matching a glob pattern."""
        return self._glob.execute(pattern=pattern, path=path)

    def grep_tool(self, pattern: str, include: str | None = None, path: str | None = None) -> Output:
        """Search file contents using regex."""
        return self._grep.execute(pattern=pattern, include=include, path=path)

    def ls_tool(self, path: str) -> Output:
        """List directory contents."""
        return self._ls.execute(path=path, ignore=None)

    def replace_tool(self, file_path: str, content: str) -> Output:
        """Replace entire file contents."""
        return self._replace.execute(file_path=file_path, content=content)

    def user_input_tool(self, question: str) -> Output:
        """Ask the user for input."""
        return self._user_input.execute(question=question)

    def view_tool(self, file_path: str) -> Output:
        """Read a file."""
        return self._view.execute(file_path=file_path, offset=None, limit=None)


class CodingToolDocker(CodingTool):
    """CodingTool implementation for Docker execution (not yet implemented)."""

    def __init__(self):
        raise NotImplementedError("Docker backend not yet implemented")

    def bash_tool(self, command: str, timeout: int | None = None) -> Output:
        raise NotImplementedError

    def edit_tool(self, file_path: str, old_string: str, new_string: str) -> Output:
        raise NotImplementedError

    def glob_tool(self, pattern: str, path: str | None = None) -> Output:
        raise NotImplementedError

    def grep_tool(self, pattern: str, include: str | None = None, path: str | None = None) -> Output:
        raise NotImplementedError

    def ls_tool(self, path: str) -> Output:
        raise NotImplementedError

    def replace_tool(self, file_path: str, content: str) -> Output:
        raise NotImplementedError

    def user_input_tool(self, question: str) -> Output:
        raise NotImplementedError

    def view_tool(self, file_path: str) -> Output:
        raise NotImplementedError


class CodingToolE2B(CodingTool):
    """CodingTool implementation for E2B execution (not yet implemented)."""

    def __init__(self):
        raise NotImplementedError("E2B backend not yet implemented")

    def bash_tool(self, command: str, timeout: int | None = None) -> Output:
        raise NotImplementedError

    def edit_tool(self, file_path: str, old_string: str, new_string: str) -> Output:
        raise NotImplementedError

    def glob_tool(self, pattern: str, path: str | None = None) -> Output:
        raise NotImplementedError

    def grep_tool(self, pattern: str, include: str | None = None, path: str | None = None) -> Output:
        raise NotImplementedError

    def ls_tool(self, path: str) -> Output:
        raise NotImplementedError

    def replace_tool(self, file_path: str, content: str) -> Output:
        raise NotImplementedError

    def user_input_tool(self, question: str) -> Output:
        raise NotImplementedError

    def view_tool(self, file_path: str) -> Output:
        raise NotImplementedError