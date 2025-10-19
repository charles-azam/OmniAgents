"""
Output renderers for tool outputs.

This module provides different renderers for displaying tool outputs:
- ConsoleRenderer: Rich console output with styling
- FileRenderer: Save outputs to files
- APIRenderer: Convert to JSON for FastAPI responses
"""
from abc import ABC, abstractmethod
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from rich.box import ROUNDED

from prompttodraft.tools.outputs.models import (
    TextOutputModel,
    CodeOutputModel,
    FileListOutputModel,
    TableOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class BaseRenderer(ABC):
    """Abstract base class for output renderers."""

    @abstractmethod
    def render_text(self, output: TextOutputModel) -> str:
        """Render text output."""
        pass

    @abstractmethod
    def render_code(self, output: CodeOutputModel) -> str:
        """Render code output."""
        pass

    @abstractmethod
    def render_file_list(self, output: FileListOutputModel) -> str:
        """Render file list output."""
        pass

    @abstractmethod
    def render_table(self, output: TableOutputModel) -> str:
        """Render table output."""
        pass

    @abstractmethod
    def render_error(self, output: ErrorOutputModel) -> str:
        """Render error output."""
        pass

    def render(self, output: ToolOutputModel) -> str:
        """Render any output model."""
        if isinstance(output, TextOutputModel):
            return self.render_text(output=output)
        elif isinstance(output, CodeOutputModel):
            return self.render_code(output=output)
        elif isinstance(output, FileListOutputModel):
            return self.render_file_list(output=output)
        elif isinstance(output, TableOutputModel):
            return self.render_table(output=output)
        elif isinstance(output, ErrorOutputModel):
            return self.render_error(output=output)
        else:
            return str(output)


class ConsoleRenderer(BaseRenderer):
    """
    Console renderer using Rich for styled terminal output.

    Copied display logic from smolcc/tool_output.py and adapted for Pydantic models.
    """

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def render_text(self, output: TextOutputModel) -> str:
        """Display text with UI styling."""
        # For multiline results
        if "\n" in output.content:
            lines = output.content.split("\n")
            first_line = lines[0]
            line_count = len(lines) - 1

            if line_count > 3:
                self.console.print(f"  ⎿  {first_line}", style="bright_black")
                self.console.print(f"     ... (+{line_count} lines)", style="bright_black")
            else:
                self.console.print(f"  ⎿  {output.content}", style="bright_black")
        else:
            self.console.print(f"  ⎿  {output.content}", style="bright_black")

        return output.content

    def render_code(self, output: CodeOutputModel) -> str:
        """Display code with syntax highlighting."""
        # Start with the result indicator
        self.console.print("  ⎿", style="bright_black")

        # Show a preview and summary for long code blocks
        if output.content.count("\n") > 10:
            lines = output.content.split("\n")
            first_few_lines = "\n".join(lines[:3])
            line_count = len(lines)

            # Show preview with syntax highlighting
            syntax = Syntax(
                first_few_lines,
                output.language,
                theme="monokai",
                line_numbers=True
            )
            self.console.print(syntax)
            self.console.print(f"     ... (+{line_count-3} more lines)", style="bright_black")
        else:
            # For shorter code, show the whole thing with syntax highlighting
            syntax = Syntax(
                output.content,
                output.language,
                theme="monokai",
                line_numbers=output.line_numbers
            )
            self.console.print(syntax)

        return output.content

    def render_file_list(self, output: FileListOutputModel) -> str:
        """Display file listing with UI styling."""
        # Start with the result indicator and immediately add path
        if output.path:
            self.console.print(f"  ⎿ Directory: {output.path}", style="bright_black")
        else:
            self.console.print("  ⎿", style="bright_black")

        # Create a table for the file listing
        table = Table(box=None, show_header=True, show_edge=False)
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Size", style="magenta")

        total_items = len(output.files)
        shown_items = min(10, total_items)  # Limit to 10 items for display

        # Add rows for the files
        for i, file in enumerate(output.files[:shown_items]):
            file_type = "[DIR]" if file.is_dir else "[FILE]"
            size = file.size
            if isinstance(size, int):
                # Format size nicely
                if size < 1024:
                    size = f"{size} B"
                elif size < 1024 * 1024:
                    size = f"{size / 1024:.1f} KB"
                else:
                    size = f"{size / (1024 * 1024):.1f} MB"

            table.add_row(file.name, file_type, str(size))

        self.console.print(table)

        # Show a summary if items were truncated
        if total_items > shown_items:
            self.console.print(f"... (+{total_items - shown_items} more items)", style="bright_black")

        return f"{total_items} items in {output.path}"

    def render_table(self, output: TableOutputModel) -> str:
        """Display tabular data with UI styling."""
        # Start with the result indicator
        self.console.print("  ⎿", style="bright_black")

        table = Table(box=ROUNDED, show_header=bool(output.headers))

        # Add headers if provided
        if output.headers:
            for header in output.headers:
                table.add_column(header, style="cyan bold")
        else:
            # Add columns based on the first row
            if output.rows and output.rows[0]:
                for _ in range(len(output.rows[0])):
                    table.add_column()

        # Add rows
        for row in output.rows:
            table.add_row(*[str(cell) for cell in row])

        self.console.print(table)

        return f"Table with {len(output.rows)} rows"

    def render_error(self, output: ErrorOutputModel) -> str:
        """Display error with styling."""
        self.console.print(f"  ⎿  {output.error_type}: {output.error}", style="red")

        if output.traceback:
            self.console.print(f"     {output.traceback}", style="bright_black")

        return f"{output.error_type}: {output.error}"


class FileRenderer(BaseRenderer):
    """Renderer for saving outputs to files."""

    def render_text(self, output: TextOutputModel) -> str:
        """Return plain text."""
        return output.content

    def render_code(self, output: CodeOutputModel) -> str:
        """Return code with language marker."""
        return f"```{output.language}\n{output.content}\n```"

    def render_file_list(self, output: FileListOutputModel) -> str:
        """Return file list as formatted text."""
        lines = [f"Directory: {output.path}", ""]
        for file in output.files:
            file_type = "[DIR]" if file.is_dir else "[FILE]"
            lines.append(f"{file_type} {file.name}")
        return "\n".join(lines)

    def render_table(self, output: TableOutputModel) -> str:
        """Return table as CSV or markdown."""
        lines = []

        if output.headers:
            lines.append(" | ".join(output.headers))
            lines.append(" | ".join(["---"] * len(output.headers)))

        for row in output.rows:
            lines.append(" | ".join(str(cell) for cell in row))

        return "\n".join(lines)

    def render_error(self, output: ErrorOutputModel) -> str:
        """Return error as plain text."""
        result = f"{output.error_type}: {output.error}"
        if output.traceback:
            result += f"\n\n{output.traceback}"
        return result


class APIRenderer(BaseRenderer):
    """Renderer for converting outputs to JSON for FastAPI responses."""

    def render_text(self, output: TextOutputModel) -> str:
        """Return JSON-serializable dict."""
        return output.model_dump_json()

    def render_code(self, output: CodeOutputModel) -> str:
        """Return JSON-serializable dict."""
        return output.model_dump_json()

    def render_file_list(self, output: FileListOutputModel) -> str:
        """Return JSON-serializable dict."""
        return output.model_dump_json()

    def render_table(self, output: TableOutputModel) -> str:
        """Return JSON-serializable dict."""
        return output.model_dump_json()

    def render_error(self, output: ErrorOutputModel) -> str:
        """Return JSON-serializable dict."""
        return output.model_dump_json()
