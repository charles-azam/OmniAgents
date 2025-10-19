"""
BashToolCore - Framework-agnostic bash command execution tool.

Extracted from smolcc/tools/bash_tool.py with business logic separated from execution.
"""
import os
import re
import shlex

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend
from prompttodraft.tools.outputs.models import (
    CodeOutputModel,
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)

# Constants (from bash_tool.py:20-28)
DEFAULT_TIMEOUT = 1800000  # 30 minutes in milliseconds
MAX_TIMEOUT = 600000  # 10 minutes in milliseconds
BANNED_COMMANDS = [
    "alias", "curl", "curlie", "wget", "axel", "aria2c", "nc", "telnet",
    "lynx", "w3m", "links", "httpie", "xh", "http-prompt", "chrome",
    "firefox", "safari"
]


class BashToolCore:
    """
    Framework-agnostic bash tool for executing shell commands.

    Extracted from smolcc/tools/bash_tool.py:31-433
    """

    # Metadata (from bash_tool.py:36-42)
    metadata = ToolMetadata(
        name="Bash",
        description="""Runs a supplied bash command inside a persistent shell session, with an optional timeout, while applying the required safety practices.

Before you launch the command, complete these steps:

1. Parent Directory Confirmation:
 - If the command will create new folders or files, first employ the LS tool to ensure the parent directory already exists and is the intended location.
 - Example: prior to executing "mkdir foo/bar", call LS to verify that "foo" exists and is truly the correct parent directory.

2. Safety Screening:
 - To reduce the risk of prompt-injection attacks, some commands are restricted or banned. If you attempt to run a blocked command, you will receive an error message explaining the limitation—pass that explanation along to the User.
 - Confirm that the command is not one of these prohibited commands: alias, curl, curlie, wget, axel, aria2c, nc, telnet, lynx, w3m, links, httpie, xh, http-prompt, chrome, firefox, safari.

3. Perform the Command:
 - Once proper quoting is verified, execute the command.
 - Capture the command's output.

Operational notes:
 - Supplying the command argument is mandatory.
 - A timeout in milliseconds may be provided (up to 600000 ms / 10 minutes). If omitted, the default timeout is 30 minutes.
 - If the output exceeds 30000 characters, it will be truncated before being returned.
 - VERY IMPORTANT: You MUST avoid search utilities like find and grep; instead, rely on GrepTool, GlobTool, or dispatch_agent. Likewise, avoid using cat, head, tail, and ls for reading—use View and LS.
 - When sending several commands, combine them with ';' or '&&' rather than newlines (newlines are acceptable only inside quoted strings).
 - IMPORTANT: All commands run within the same shell session. Environment variables, virtual environments, the current directory, and other state persist between commands. For instance, any environment variable you set will remain in subsequent commands.
 - Try to keep the working directory unchanged by using absolute paths and avoiding cd, unless the User explicitly instructs otherwise.""",
        inputs={
            "command": {
                "type": "string",
                "description": "The command to execute"
            },
            "timeout": {
                "type": "number",
                "description": "Optional timeout in milliseconds (max 600000)",
                "nullable": True
            }
        },
        output_type="string"
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize BashToolCore with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    def execute(
        self,
        command: str,
        timeout: int | None = None
    ) -> ToolOutputModel:
        """
        Execute a bash command with validation and formatting.

        Args:
            command: The bash command to execute
            timeout: Optional timeout in milliseconds (max 600000)

        Returns:
            A ToolOutputModel (CodeOutput or TextOutput or ErrorOutput)
        """
        # Security check for banned commands (from bash_tool.py:83-84)
        if self._is_banned_command(command=command):
            return ErrorOutputModel(
                error=f"Command contains one or more banned commands: {', '.join(BANNED_COMMANDS)}. Please use alternative tools for these operations.",
                error_type="SecurityError"
            )

        # Execute command via backend
        output, is_error = self.backend.execute_command(command=command, timeout=timeout)

        # Determine if the output is code based on the command (from bash_tool.py:98-104)
        if self._is_code_command(command=command):
            language = self._guess_language_from_command(command=command)
            return CodeOutputModel(content=output, language=language, line_numbers=True)
        elif is_error:
            return ErrorOutputModel(error=output, error_type="CommandError")
        else:
            return TextOutputModel(content=output)

    def _is_banned_command(self, command: str) -> bool:
        """
        Check if a command contains any banned commands (from bash_tool.py:231-259).

        Args:
            command: The command to check

        Returns:
            True if the command contains a banned command, False otherwise
        """
        # Split the command into tokens
        try:
            tokens = shlex.split(command)

            # Check each token against the banned commands list
            for token in tokens:
                if token in BANNED_COMMANDS:
                    return True

                # Also check for commands with paths
                cmd_name = os.path.basename(token)
                if cmd_name in BANNED_COMMANDS:
                    return True
        except Exception:
            # If we can't parse the command, be conservative and allow it
            # (the shell will fail if it's invalid syntax anyway)
            pass

        return False

    def _is_code_command(self, command: str) -> bool:
        """
        Determine if a command likely produces code output (from bash_tool.py:261-303).

        Args:
            command: The command to check

        Returns:
            True if the command likely produces code output, False otherwise
        """
        # Commands that often produce code-like output
        code_commands = [
            # File listing commands (that show source code)
            "cat", "head", "tail", "less", "more", "type",
            # Programming language commands
            "python", "python3", "node", "npm", "npx", "ruby", "perl", "php",
            "go", "rust", "cargo", "java", "javac", "scala", "clang", "gcc",
            # Build/Config commands
            "cmake", "make", "bazel", "gradle", "maven", "ant", "pip",
            # Source control
            "git diff", "git show", "svn diff",
            # File operations on code
            "diff", "patch"
        ]

        try:
            # Check if the command starts with any of the code commands
            for code_cmd in code_commands:
                if command.startswith(code_cmd + " ") or command == code_cmd:
                    return True

            # Check for shell script syntax that might indicate code
            if re.search(r'\bfor\b.*\bin\b.*\bdo\b', command) or \
               re.search(r'\bwhile\b.*\bdo\b', command) or \
               re.search(r'\bif\b.*\bthen\b', command) or \
               re.search(r'\bcase\b.*\bin\b', command):
                return True

        except Exception:
            # If we can't parse the command, assume it's not code
            pass

        return False

    def _guess_language_from_command(self, command: str) -> str:
        """
        Guess the programming language based on the command (from bash_tool.py:305-352).

        Args:
            command: The command to analyze

        Returns:
            Language name for syntax highlighting
        """
        # Map commands to languages
        command_language_map = {
            "python": "python",
            "python3": "python",
            "node": "javascript",
            "npm": "javascript",
            "npx": "javascript",
            "ruby": "ruby",
            "perl": "perl",
            "php": "php",
            "go": "go",
            "rust": "rust",
            "cargo": "rust",
            "java": "java",
            "javac": "java",
            "scala": "scala",
            "clang": "c",
            "gcc": "c"
        }

        # Check command start for language hints
        for cmd, lang in command_language_map.items():
            if command.startswith(cmd + " ") or command == cmd:
                return lang

        # Check if it's a git diff or git show command
        if command.startswith("git diff") or command.startswith("git show"):
            return "diff"

        # Check for shell script syntax
        if re.search(r'\bfor\b.*\bin\b.*\bdo\b', command) or \
           re.search(r'\bwhile\b.*\bdo\b', command) or \
           re.search(r'\bif\b.*\bthen\b', command) or \
           re.search(r'\bcase\b.*\bin\b', command):
            return "bash"

        # Default to bash for most commands
        return "bash"
