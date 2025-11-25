"""
UV tool implementation.

This tool executes uv commands in the execution environment, ensuring uv is installed first.
"""
from prompttodraft.tools.base_tool import CoreTool
from prompttodraft.tools.metadata import ToolMetadata
from prompttodraft.backends.execution_backend import ExecutionBackend
from prompttodraft.outputs.outputs import (
    TextOutputModel,
    ToolOutputModel,
)


class UVTool(CoreTool):
    """
    Framework-agnostic UV command execution tool.

    Executes uv commands in the execution environment, automatically ensuring
    uv is installed first. Supports operations like running Python files,
    installing packages, and running tests.
    """

    metadata = ToolMetadata(
        name="uv",
        description="Executes uv package manager commands in the execution environment. Automatically ensures uv is installed before running commands. Use this to: run Python files (uv run script.py), install packages (uv add package-name), remove packages (uv remove package-name), sync dependencies (uv sync), run pytest (uv run pytest), or any other uv command. Returns detailed information about the execution including stdout, stderr, and exit code.",
        inputs={
            "command": {
                "type": "string",
                "description": "The uv command to execute (without the 'uv' prefix). Examples: 'run script.py', 'add requests', 'remove pandas', 'sync', 'run pytest tests/', 'run python -m module'.",
                "nullable": False,
            },
            "description": {
                "type": "string",
                "description": "Optional: A brief description of the command's purpose, which will be shown to the user.",
                "nullable": True,
            },
        },
        output_type="string",
    )

    def execute(
        self,
        command: str,
        description: str | None = None,
    ) -> ToolOutputModel:
        """
        Execute the uv tool.

        Args:
            command: The uv command to execute (without 'uv' prefix)
            description: Optional description of the command's purpose

        Returns:
            TextOutputModel with command output
        """
        # Build the full uv command with PATH set
        full_command = f'export PATH="$HOME/.local/bin:$PATH" && uv {command}'

        # Execute the command
        result = self.backend.execute_command(
            command=full_command,
            timeout=300000,  # 5 minutes default for potentially long operations
        )

        # Format output
        output_lines = []

        if description:
            output_lines.append(f"Description: {description}")

        output_lines.append(f"Command: uv {command}")
        output_lines.append(f"Working Directory: {self.backend.get_working_directory()}")
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
            metadata={"exit_code": result.exit_code, "command": f"uv {command}"},
        )
