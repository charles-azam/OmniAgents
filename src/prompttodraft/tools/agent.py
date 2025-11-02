"""
Tool Agent for the 3-layer architecture with improved output formatting.

This module provides an agent implementation that uses Rich for
better terminal output, including spinners for long-running operations
and formatted tool outputs.
"""
import os
import time
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from smolagents import AgentLogger, LogLevel, Tool, ToolCallingAgent, ApiModel, InferenceClientModel

from prompttodraft.tools.outputs.models import (
    CodeOutputModel,
    ErrorOutputModel,
    FileListOutputModel,
    TableOutputModel,
    TextOutputModel,
    ToolOutputModel,
)

from phoenix.otel import register
from openinference.instrumentation.smolagents import SmolagentsInstrumentor

register()
SmolagentsInstrumentor().instrument()


class RichConsoleLogger(AgentLogger):
    """
    Custom logger that suppresses default AgentLogger output but provides
    a Rich console for enhanced display.
    """

    def __init__(self, level: LogLevel = LogLevel.INFO, log_file: str | None = None):
        """
        Initialize the logger.

        Args:
            level: Logging level
            log_file: Optional path to log file
        """
        # Create the Rich console for output
        self.console = Console()
        super().__init__(level=level)

        # Set up file logging if requested
        self.log_file = log_file
        if log_file:
            # Create or truncate the log file
            with open(log_file, "w") as f:
                f.write("RichConsoleLogger initialized\n")

    def log(self, *args: Any, level: int = LogLevel.INFO, **kwargs: Any) -> None:
        """
        Override to suppress default AgentLogger output.

        Args:
            *args: Log arguments
            level: Log level
            **kwargs: Additional keyword arguments
        """
        if self.log_file and level <= self.level:
            with open(self.log_file, "a") as f:
                f.write(f"LOG: {args}\n")

    def log_error(self, error_message: str) -> None:
        """
        Display errors prominently.

        Args:
            error_message: Error message to display
        """
        if self.log_file:
            with open(self.log_file, "a") as f:
                f.write(f"ERROR: {error_message}\n")

        self.console.print(f"[bold red]Error:[/bold red] {error_message}")

    def log_task(
        self, content: str, subtitle: str, title: str | None = None, level: LogLevel = LogLevel.INFO
    ) -> None:
        """
        Suppress task headers.

        Args:
            content: Task content
            subtitle: Task subtitle
            title: Optional task title
            level: Log level
        """
        if self.log_file and level <= self.level:
            with open(self.log_file, "a") as f:
                f.write(f"TASK: {content}\nSubtitle: {subtitle}\nTitle: {title}\n")

    def log_rule(self, title: str, level: int = LogLevel.INFO) -> None:
        """
        Suppress rule dividers.

        Args:
            title: Rule title
            level: Log level
        """
        if self.log_file and level <= self.level:
            with open(self.log_file, "a") as f:
                f.write(f"RULE: {title}\n")

    def log_markdown(
        self, content: str, title: str | None = None, level: LogLevel = LogLevel.INFO, style: Any = None
    ) -> None:
        """
        Suppress markdown output.

        Args:
            content: Markdown content
            title: Optional title
            level: Log level
            style: Optional style
        """
        if self.log_file and level <= self.level:
            with open(self.log_file, "a") as f:
                f.write(f"MARKDOWN: {title}\n{content}\n")


class ToolAgent(ToolCallingAgent):
    """
    Tool Agent with improved terminal output for the 3-layer architecture.

    This agent extends the ToolCallingAgent with better terminal output,
    including spinners for long-running operations and formatted tool outputs.
    """

    def __init__(
        self,
        tools: list[Tool],
        model: ApiModel,
        system_prompt: str | None = None,
        log_file: str | None = None,
    ):
        """
        Initialize the ToolAgent.

        Args:
            tools: List of tools available to the agent
            model: The language model to use
            system_prompt: Optional system prompt to prepend to user input
            log_file: Optional path to log file
        """
        # Store application system prompt
        self.app_system_prompt = system_prompt

        # Create our custom logger
        logger = RichConsoleLogger(level=LogLevel.INFO, log_file=log_file)

        # Initialize the parent class
        super().__init__(tools=tools, model=model, logger=logger)

        # Get the console from the logger
        self.console = self.logger.console

    def _display_tool_call(self, tool_name: str, tool_arguments: dict[str, Any]) -> None:
        """
        Display a tool call with formatting.

        Args:
            tool_name: Name of the tool being called
            tool_arguments: Arguments passed to the tool
        """
        # Format the tool call string
        param_str = ", ".join([f"{k}: {repr(v)}" for k, v in tool_arguments.items()])
        tool_call = f"{tool_name}({param_str})"

        # Truncate if too long
        if len(tool_call) > 80:
            tool_call = tool_call[:77] + "..."

        self.console.print(f"⏺ {tool_call}…", style="yellow")

    def _display_output_model(self, output: ToolOutputModel) -> None:
        """
        Display a ToolOutputModel with appropriate formatting.

        Args:
            output: The output model to display
        """
        if isinstance(output, TextOutputModel):
            self._display_text_output(output)
        elif isinstance(output, CodeOutputModel):
            self._display_code_output(output)
        elif isinstance(output, FileListOutputModel):
            self._display_filelist_output(output)
        elif isinstance(output, ErrorOutputModel):
            self._display_error_output(output)
        elif isinstance(output, TableOutputModel):
            self._display_table_output(output)
        else:
            # Fallback
            self.console.print(f"  ⎿  {str(output)}", style="bright_black")

    def _display_text_output(self, output: TextOutputModel) -> None:
        """Display TextOutputModel."""
        content = output.content
        if "\n" in content:
            lines = content.split("\n")
            first_line = lines[0]
            line_count = len(lines) - 1

            if line_count > 3:
                self.console.print(f"  ⎿  {first_line}", style="bright_black")
                self.console.print(f"     ... (+{line_count} lines)", style="bright_black")
            else:
                self.console.print(f"  ⎿  {content}", style="bright_black")
        else:
            self.console.print(f"  ⎿  {content}", style="bright_black")

    def _display_code_output(self, output: CodeOutputModel) -> None:
        """Display CodeOutputModel."""
        self.console.print("  ⎿", style="bright_black")

        code = output.content
        if code.count("\n") > 10:
            lines = code.split("\n")
            first_few_lines = "\n".join(lines[:3])
            line_count = len(lines)

            syntax = Syntax(first_few_lines, output.language, theme="monokai", line_numbers=True)
            self.console.print(syntax)
            self.console.print(f"     ... (+{line_count-3} more lines)", style="bright_black")
        else:
            syntax = Syntax(code, output.language, theme="monokai", line_numbers=output.line_numbers)
            self.console.print(syntax)

    def _display_filelist_output(self, output: FileListOutputModel) -> None:
        """Display FileListOutputModel."""
        if output.path:
            self.console.print(f"  ⎿ Directory: {output.path}", style="bright_black")
        else:
            self.console.print("  ⎿", style="bright_black")

        table = Table(box=None, show_header=True, show_edge=False)
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Size", style="magenta")

        total_items = len(output.files)
        shown_items = min(10, total_items)

        for file in output.files[:shown_items]:
            file_type = "[DIR]" if file.is_dir else "[FILE]"
            size = file.size
            if isinstance(size, int):
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
            else:
                size_str = str(size)

            table.add_row(file.name, file_type, size_str)

        self.console.print(table)

        if total_items > shown_items:
            self.console.print(f"... (+{total_items - shown_items} more items)", style="bright_black")

    def _display_error_output(self, output: ErrorOutputModel) -> None:
        """Display ErrorOutputModel."""
        self.console.print(f"  ⎿  [bold red]Error:[/bold red] {output.error}", style="bright_black")

    def _display_table_output(self, output: TableOutputModel) -> None:
        """Display TableOutputModel."""
        self.console.print("  ⎿", style="bright_black")

        table = Table(box=None, show_header=bool(output.headers))

        if output.headers:
            for header in output.headers:
                table.add_column(header, style="cyan bold")
        else:
            if output.rows and output.rows[0]:
                for _ in range(len(output.rows[0])):
                    table.add_column()

        for row in output.rows:
            table.add_row(*[str(cell) for cell in row])

        self.console.print(table)

    def execute_tool_call(self, tool_name: str, tool_arguments: dict[str, Any]) -> Any:
        """
        Execute a tool call with visual feedback.

        Args:
            tool_name: Name of the tool to execute
            tool_arguments: Arguments to pass to the tool

        Returns:
            The result of the tool execution
        """
        # Special handling for final_answer or final_output
        is_final_answer = tool_name.lower() in ("final_answer", "final_output")

        # Display the tool call
        self._display_tool_call(tool_name=tool_name, tool_arguments=tool_arguments)

        # Get the tool instance
        try:
            tool = self.get_tool(tool_name=tool_name)
        except ValueError as e:
            self.logger.log_error(f"Tool not found: {tool_name}")
            return f"Error: {str(e)}"

        # Execute the tool
        start_time = time.time()
        result = tool(**tool_arguments)
        execution_time = time.time() - start_time

        # Display the output (skip for final_answer)
        if not is_final_answer:
            # If result is a ToolOutputModel, display it
            if isinstance(result, ToolOutputModel):
                self._display_output_model(output=result)
            else:
                # For smolagents adapters that return strings
                self.console.print(f"  ⎿  {str(result)}", style="bright_black")

            # Log execution time if it was slow
            if execution_time > 1.0:
                self.console.print(f"  ⏱️ {execution_time:.2f}s", style="bright_black")

            # Add a blank line after each tool output
            self.console.print()

        # Return the raw result for the agent to use
        return result

    def run(self, user_input: str, stream: bool = False) -> str:
        """
        Run the agent with visual feedback.

        Args:
            user_input: The user's input query
            stream: Whether to stream the response

        Returns:
            The agent's response
        """
        # Prepend system prompt to user input if provided
        if self.app_system_prompt:
            user_input = f"{self.app_system_prompt}\n\n{user_input}"

        # Run the agent
        result = super().run(user_input, stream=stream)

        # Add blank line before final answer
        self.console.print()

        # Display the result as an assistant message
        self.console.print(f"{result}", style="white")

        # Add blank line after the response
        self.console.print()

        return result

    def format_messages_for_llm(self, prompt: str) -> list[dict[str, str]]:
        """
        Override to provide visual feedback when preparing messages for the LLM.

        Args:
            prompt: The user's prompt

        Returns:
            The formatted messages for the LLM
        """
        # Show a thinking spinner during LLM formatting
        with Progress(
            SpinnerColumn(),
            TextColumn("[yellow]Thinking...[/yellow]"),
            console=self.console,
            transient=True,
        ) as progress:
            progress.add_task("Thinking...", total=None)
            messages = super().format_messages_for_llm(prompt)

        return messages

    def get_tool(self, tool_name: str) -> Tool:
        """
        Get a tool by name.

        Args:
            tool_name: Name of the tool to get

        Returns:
            The tool instance

        Raises:
            ValueError: If the tool is not found
        """
        # In ToolCallingAgent, self.tools is a dictionary with tool names as keys
        if tool_name in self.tools:
            return self.tools[tool_name]

        # If we didn't find it, raise an error
        raise ValueError(f"Tool not found: {tool_name}")


def create_agent(
    cwd: str | None = None,
    backend: "ExecutionBackend | None" = None,
    model: ApiModel | None = None,
    log_file: str | None = "tool_agent.log",
    storage: "StorageType" = None,  # Will import StorageType in function body
) -> ToolAgent:
    """
    Create a tool agent with all available tools using the new 3-layer architecture.

    Args:
        cwd: Current working directory (defaults to os.getcwd())
        backend: ExecutionBackend instance (defaults to LocalBackend if None)
        model: LLM model to use (defaults to Groq gpt-oss-120b if None)
        log_file: Path to log file or None to disable logging
        storage: Storage backend for state persistence:
            - StorageType.GIT: Use GitHub branches (default)
            - StorageType.GCS: Use Google Cloud Storage buckets
            - StorageType.NONE: No state persistence

    Returns:
        A ToolAgent instance
    """
    from dotenv import load_dotenv

    from prompttodraft.tools.backends.execution_backend import ExecutionBackend
    from prompttodraft.tools.backends.local_backend import LocalBackend
    from prompttodraft.tools.backends.state_manager import StorageType
    from prompttodraft.tools.factory import ToolFactory
    from prompttodraft.tools.system_prompt import get_system_prompt
    from prompttodraft.utils import initialize_project

    # Initialize environment variables
    load_dotenv()

    # Use the provided working directory or current one
    if cwd is None:
        cwd = os.getcwd()

    # Create backend if not provided
    if backend is None:
        # Default to GIT storage if not specified
        if storage is None:
            storage = StorageType.GIT
        backend = LocalBackend(project_id="local", storage=storage)
        # Start the backend
        backend.start()

    # Initialize the project (runs uv init on first run, uv sync always)
    initialize_project(backend=backend)

    # Create default model if not provided
    if model is None:
        model = InferenceClientModel(model_id="groq/gpt-oss-120b")

    # Get the dynamic system prompt with model ID
    model_id = getattr(model, "model_id", "groq/gpt-oss-120b")
    system_prompt = get_system_prompt(backend=backend, model_id=model_id)

    # Create tool instances using the ToolFactory
    tool_instances = ToolFactory.create_smolagents_tools(backend=backend)

    # Initialize the agent with all tools and system prompt
    agent = ToolAgent(tools=tool_instances, model=model, log_file=log_file, system_prompt=system_prompt)

    return agent
