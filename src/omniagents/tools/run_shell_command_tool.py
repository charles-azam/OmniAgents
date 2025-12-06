"""
Run shell command tool implementation.

This tool executes shell commands in the execution environment.
"""
from pathlib import Path
from pydantic import BaseModel, Field

from omniagents.tools.base_tool import CoreBackendTool
from omniagents.outputs.outputs import (
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
        working_dir = self.backend.get_working_directory()
        
        # When running locally, we need to handle the fact that shell commands run in the host temp dir
        # but the LLM thinks it's in /workspace.
        # If the user asks to 'cd subfolder', we can prepend 'cd subfolder &&'.
        # If the user asks to 'cd /workspace/subfolder', we have a problem locally.
        
        # Current implementation assumes inputs.directory is relative to project root.
        
        command = inputs.command
        
        if inputs.directory:
             # Just prepend cd relative_path
             # We rely on inputs.directory being relative
             command = f'cd "{inputs.directory}" && {command}'
        
        # Execute command
        result = self.backend.execute_command(
            command=command,
            timeout=120000,  # 2 minutes default
        )

        # Format output
        output_lines = []

        if inputs.description:
            output_lines.append(f"Description: {inputs.description}")

        output_lines.append(f"Command: {inputs.command}")
        if inputs.directory:
             output_lines.append(f"Directory: {inputs.directory}")
             
        output_lines.append(f"Working Directory: {working_dir}")
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
