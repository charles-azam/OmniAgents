"""
run_shell_command tool - Framework-agnostic shell command execution tool.

Implements the Gemini CLI Shell tool specification.
"""
from pathlib import Path
import re

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend
from prompttodraft.tools.outputs.models import (
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class RunShellCommandToolCore:
    """
    run_shell_command tool for executing shell commands.

    Implements the Gemini CLI Shell specification.
    """

    metadata = ToolMetadata(
        name="run_shell_command",
        description="""Use `run_shell_command` to interact with the underlying system, run scripts, or
perform command-line operations. `run_shell_command` executes a given shell
command, including interactive commands that require user input if enabled.

On Windows, commands are executed with `powershell.exe -NoProfile -Command`
unless you explicitly point `ComSpec` at another shell. On other platforms,
they are executed with `bash -c`.

### Arguments

`run_shell_command` takes the following arguments:

- `command` (string, required): The exact shell command to execute.
- `description` (string, optional): A brief description of the command's
  purpose, which will be shown to the user.
- `directory` (string, optional): The directory (relative to the project root)
  in which to execute the command. If not provided, the command runs in the
  project root.

## How to use `run_shell_command`

When using `run_shell_command`, the command is executed as a subprocess.
`run_shell_command` can start background processes using `&`. The tool returns
detailed information about the execution, including:

- `Command`: The command that was executed.
- `Directory`: The directory where the command was run.
- `Stdout`: Output from the standard output stream.
- `Stderr`: Output from the standard error stream.
- `Error`: Any error message reported by the subprocess.
- `Exit Code`: The exit code of the command.
- `Signal`: The signal number if the command was terminated by a signal.
- `Background PIDs`: A list of PIDs for any background processes started.

## Important notes

- **Security:** Be cautious when executing commands, especially those
  constructed from user input, to prevent security vulnerabilities.
- **Error handling:** Check the `Stderr`, `Error`, and `Exit Code` fields to
  determine if a command executed successfully.
- **Background processes:** When a command is run in the background with `&`,
  the tool will return immediately and the process will continue to run in the
  background. The `Background PIDs` field will contain the process ID of the
  background process.

## Environment Variables

When `run_shell_command` executes a command, it sets the `GEMINI_CLI=1`
environment variable in the subprocess's environment.""",
        inputs={
            "command": {
                "type": "string",
                "description": "The exact shell command to execute."
            },
            "description": {
                "type": "string",
                "description": "A brief description of the command's purpose.",
                "nullable": True
            },
            "directory": {
                "type": "string",
                "description": "The directory (relative to the project root) in which to execute the command.",
                "nullable": True
            }
        },
        output_type="string"
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize RunShellCommandToolCore with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    def execute(
        self,
        command: str,
        description: str | None = None,
        directory: str | None = None
    ) -> ToolOutputModel:
        """
        Execute a shell command.

        Args:
            command: The shell command to execute
            description: Optional description of the command
            directory: Optional directory to execute in (relative to project root)

        Returns:
            A ToolOutputModel (TextOutput or ErrorOutput)
        """
        # Determine execution directory
        if directory is None:
            exec_dir = self.backend.get_working_directory()
        else:
            # Make directory relative to working directory
            if Path(directory).is_absolute():
                exec_dir = directory
            else:
                exec_dir = str(Path(self.backend.get_working_directory()) / directory)

        # Build command with environment variable and directory change
        # Set GEMINI_CLI=1 environment variable
        full_command = f"cd '{exec_dir}' && GEMINI_CLI=1 {command}"

        # Execute command
        try:
            result = self.backend.execute_command(
                command=full_command,
                timeout=120000  # 2 minutes default timeout
            )
        except Exception as e:
            return ErrorOutputModel(
                error=f"Error executing command: {str(e)}",
                error_type="CommandError"
            )

        # Detect background processes (commands ending with &)
        background_pids = []
        if command.strip().endswith('&'):
            # Try to extract PID from output if available
            pid_pattern = r'\[[\d]+\]\s+(\d+)'
            matches = re.findall(pid_pattern, result.output)
            background_pids = [int(pid) for pid in matches]

        # Format output
        output_lines = []

        if description:
            output_lines.append(f"Description: {description}")

        output_lines.append(f"Command: {command}")
        output_lines.append(f"Directory: {exec_dir}")

        if result.exit_code == 0:
            output_lines.append("Exit Code: 0 (Success)")
        else:
            output_lines.append(f"Exit Code: {result.exit_code} (Error)")

        if result.output:
            output_lines.append(f"\nOutput:\n{result.output}")

        if background_pids:
            output_lines.append(f"\nBackground PIDs: {', '.join(map(str, background_pids))}")

        output_text = "\n".join(output_lines)

        # Return error if exit code is non-zero
        if result.exit_code != 0:
            return ErrorOutputModel(
                error=output_text,
                error_type="CommandError"
            )

        return TextOutputModel(content=output_text)
