"""
Generic package manager tool that adapts to the project's language.

This tool automatically adapts to the project's language (Python/UV, TypeScript/npm, etc.)
based on the initializer configuration.
"""
from prompttodraft.tools.base_tool import CoreTool
from prompttodraft.tools.metadata import ToolMetadata
from prompttodraft.outputs.outputs import TextOutputModel, ToolOutputModel


class PackageManagerTool(CoreTool):
    """
    Framework-agnostic package manager execution tool.

    Automatically adapts to the project's language (Python/UV, TypeScript/npm, etc.)
    based on the initializer configuration.
    """

    metadata = ToolMetadata(
        name="package_manager",
        description="Executes package manager commands for the current project language. Adapts to Python (uv), TypeScript (npm), or other configured languages. Use this to install packages, run scripts, execute tests, or perform other language-specific operations.",
        inputs={
            "operation": {
                "type": "string",
                "description": "The operation to perform (e.g., 'install', 'run', 'test', 'add', 'remove', 'sync', 'build'). Available operations depend on the project language.",
                "nullable": False,
            },
            "args": {
                "type": "string",
                "description": "Arguments for the operation (e.g., package name, script name, test path)",
                "nullable": False,
            },
            "description": {
                "type": "string",
                "description": "Optional: A brief description of what this command does",
                "nullable": True,
            },
        },
        output_type="string",
    )

    def execute(
        self,
        operation: str,
        args: str,
        description: str | None = None,
    ) -> ToolOutputModel:
        """
        Execute a package manager operation.

        Args:
            operation: Operation name (install, run, test, etc.)
            args: Arguments for the operation
            description: Optional description

        Returns:
            TextOutputModel with command output
        """
        # Get command template from initializer
        commands = self.backend.initializer.get_package_manager_commands()

        if operation not in commands:
            available_ops = ", ".join(commands.keys())
            return TextOutputModel(
                content=f"Error: Operation '{operation}' not supported by {self.backend.initializer.language_name}.\nAvailable operations: {available_ops}",
                metadata={"error": "unsupported_operation"},
            )

        # Build the command
        command_template = commands[operation]

        # Handle different template formats
        if "{package}" in command_template:
            command = command_template.format(package=args)
        elif "{script}" in command_template:
            command = command_template.format(script=args)
        elif "{path}" in command_template:
            command = command_template.format(path=args)
        else:
            command = f"{command_template} {args}"

        # Execute the command
        result = self.backend.execute_command(
            command=command,
            timeout=300000,
        )

        # Format output
        output_lines = []

        if description:
            output_lines.append(f"Description: {description}")

        output_lines.append(f"Language: {self.backend.initializer.language_name}")
        output_lines.append(f"Operation: {operation}")
        output_lines.append(f"Command: {command}")
        output_lines.append(f"Working Directory: {self.backend.get_working_directory()}")
        output_lines.append("")

        if result.output:
            output_lines.append("Output:")
            output_lines.append(result.output)
            output_lines.append("")

        output_lines.append(f"Exit Code: {result.exit_code}")

        if result.exit_code != 0:
            output_lines.append("")
            output_lines.append(f"Warning: Command exited with non-zero status code {result.exit_code}")

        return TextOutputModel(
            content="\n".join(output_lines),
            metadata={"exit_code": result.exit_code, "command": command},
        )
