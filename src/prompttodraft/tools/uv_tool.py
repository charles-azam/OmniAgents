"""
UV tool implementation.

This tool executes uv commands in the execution environment, ensuring uv is installed first.
"""
from pydantic import BaseModel, Field

from prompttodraft.tools.base_tool import CoreBackendTool
from prompttodraft.outputs.outputs import (
    TextOutputModel,
    ToolOutputModel,
)


class UVInput(BaseModel):
    """Input model for UVTool."""
    command: str = Field(description="The uv command to execute (without the 'uv' prefix). Examples: 'run script.py', 'add requests', 'remove pandas', 'sync', 'run pytest tests/', 'run python -m module'.")
    description: str | None = Field(default=None, description="Optional: A brief description of the command's purpose, which will be shown to the user.")


class UVTool(CoreBackendTool[UVInput, TextOutputModel]):
    """
    Framework-agnostic UV command execution tool.

    Executes uv commands in the execution environment, automatically ensuring
    uv is installed first. Supports operations like running Python files,
    installing packages, and running tests.
    """

    name = "uv"
    description = "Executes uv package manager commands in the execution environment. Automatically ensures uv is installed before running commands. Use this to: run Python files (uv run script.py), install packages (uv add package-name), remove packages (uv remove package-name), sync dependencies (uv sync), run pytest (uv run pytest), or any other uv command. Returns detailed information about the execution including stdout, stderr, and exit code."

    def execute(self, inputs: UVInput) -> TextOutputModel:
        """
        Execute the uv tool.

        Args:
            inputs: Validated input model with command and description

        Returns:
            TextOutputModel with command output
        """
        # Execute the uv command using the backend's execute_uv method
        result = self.backend.execute_uv(
            uv_command=inputs.command,
            timeout=300000,  # 5 minutes default for potentially long operations
        )

        # Format output
        output_lines = []

        if inputs.description:
            output_lines.append(f"Description: {inputs.description}")

        output_lines.append(f"Command: uv {inputs.command}")
        output_lines.append(f"Working Directory: {str(self.backend.get_working_directory())}")
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
            metadata={"exit_code": result.exit_code, "command": f"uv {inputs.command}"},
        )
