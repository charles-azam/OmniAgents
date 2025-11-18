"""
Run shell command tool implementation.

This tool executes shell commands in the execution environment.
"""
from pathlib import Path

from prompttodraft.agent.tools.base_tool import CoreTool
from prompttodraft.agent.tools.metadata import ToolMetadata
from prompttodraft.agent.backends.execution_backend import ExecutionBackend
from prompttodraft.agent.outputs.models import (
    TextOutputModel,
    ToolOutputModel,
)


class RunShellCommandTool(CoreTool):
    """
    Framework-agnostic shell command execution tool.

    Executes shell commands in the execution environment, returning detailed
    information about the execution including stdout, stderr, and exit code.
    """

    metadata = ToolMetadata(
        name="run_shell_command",
        description="Executes a shell command in the execution environment. Use this to interact with the underlying system, run scripts, or perform command-line operations. Returns detailed information about the execution including stdout, stderr, exit code, and any errors. Commands are executed with bash -c on Unix-like systems.",
        inputs={
            "command": {
                "type": "string",
                "description": "The exact shell command to execute.",
                "nullable": False,
            },
            "description": {
                "type": "string",
                "description": "Optional: A brief description of the command's purpose, which will be shown to the user.",
                "nullable": True,
            },
            "directory": {
                "type": "string",
                "description": "Optional: The directory (relative to the project root) in which to execute the command. If not provided, the command runs in the project root.",
                "nullable": True,
            },
        },
        output_type="string",
    )

    def execute(
        self,
        command: str,
        description: str | None = None,
        directory: str | None = None,
    ) -> ToolOutputModel:
        """
        Execute the run_shell_command tool.

        Args:
            command: The exact shell command to execute
            description: Optional description of the command's purpose
            directory: Optional directory to execute the command in

        Returns:
            TextOutputModel with command output or ErrorOutputModel on failure
        """
        # Determine execution directory
        working_dir = self.backend.get_working_directory()
        exec_dir = working_dir

        if directory:
            # Convert relative directory to absolute
            exec_dir = str(Path(working_dir) / directory)

        # Build the full command with directory change if needed
        if directory:
            full_command = f'cd "{exec_dir}" && {command}'
        else:
            full_command = command

        # Execute command
        result = self.backend.execute_command(
            command=full_command,
            timeout=120000,  # 2 minutes default
        )

        # Format output
        output_lines = []

        if description:
            output_lines.append(f"Description: {description}")

        output_lines.append(f"Command: {command}")
        output_lines.append(f"Directory: {exec_dir}")
        output_lines.append("")

        if result.output:
            output_lines.append("Output:")
            output_lines.append(result.output)
            output_lines.append("")

        output_lines.append(f"Exit Code: {result.exit_code}")

        # Check for non-zero exit code
        if result.exit_code != 0:
            output_lines.append("")
            output_lines.append(f"Warning: Command exited with non-zero status code {result.exit_code}")

        return TextOutputModel(
            content="\n".join(output_lines),
            metadata={"exit_code": result.exit_code, "command": command},
        )
