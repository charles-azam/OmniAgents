"""
Run shell command tool implementation.

This tool executes shell commands in the execution environment.
"""
from pathlib import Path
from pydantic import BaseModel, Field

from prompttodraft.tools.base_tool import CoreBackendTool
from prompttodraft.outputs.outputs import (
    TextOutputModel,
    ToolOutputModel,
)


class RunShellCommandInput(BaseModel):
    """Input model for RunShellCommandTool."""
    command: str = Field(description="The exact shell command to execute.")
    description: str | None = Field(default=None, description="Optional: A brief description of the command's purpose, which will be shown to the user.")
    directory: str | None = Field(default=None, description="Optional: The directory (relative to the project root) in which to execute the command. If not provided, the command runs in the project root.")


class RunShellCommandTool(CoreBackendTool[RunShellCommandInput, TextOutputModel]):
    """
    Framework-agnostic shell command execution tool.

    Executes shell commands in the execution environment, returning detailed
    information about the execution including stdout, stderr, and exit code.
    """

    name = "run_shell_command"
    description = "Executes a shell command in the execution environment. Use this to interact with the underlying system, run scripts, or perform command-line operations. Returns detailed information about the execution including stdout, stderr, exit code, and any errors. Commands are executed with bash -c on Unix-like systems."

    def execute(self, inputs: RunShellCommandInput) -> TextOutputModel:
        """
        Execute the run_shell_command tool.

        Args:
            inputs: Validated input model with command, description, and directory

        Returns:
            TextOutputModel with command output
        """
        # Determine execution directory
        working_dir = self.backend.get_working_directory()
        exec_dir = working_dir

        if inputs.directory:
            # Convert relative directory to absolute
            exec_dir = str(Path(working_dir) / inputs.directory)

        # Build the full command with directory change if needed
        if inputs.directory:
            full_command = f'cd "{exec_dir}" && {inputs.command}'
        else:
            full_command = inputs.command

        # Execute command
        result = self.backend.execute_command(
            command=full_command,
            timeout=120000,  # 2 minutes default
        )

        # Format output
        output_lines = []

        if inputs.description:
            output_lines.append(f"Description: {inputs.description}")

        output_lines.append(f"Command: {inputs.command}")
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
            metadata={"exit_code": result.exit_code, "command": inputs.command},
        )
