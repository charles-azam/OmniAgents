"""
Output data models for tools.

This module defines Pydantic models for tool outputs, separating data from presentation.
These models can be rendered differently for console, file, or API responses.
"""
import os
from abc import abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from rich.console import Console


class DisplayMode(Enum):
    """Display mode for output handling."""
    CONSOLE = "console"  # CLI application - print to terminal
    API = "api"          # FastAPI backend - return structured data
    HYBRID = "hybrid"    # API mode but also log to console for debugging


class ToolOutputModel(BaseModel):
    """Base class for all tool output models."""

    metadata: dict[str, str | int | float | bool] | None = Field(
        default=None,
        description="Optional metadata about the output (timestamps, tool name, etc.)"
    )

    class Config:
        frozen = False  # Allow modification if needed
        extra = "allow"  # Allow additional fields

    def handle(self) -> dict[str, Any] | str:
        """
        Main entry point - routes to appropriate handler based on DISPLAY_MODE env var.

        Returns:
            - str: In CONSOLE mode (formatted for terminal)
            - dict: In API/HYBRID mode (structured data for FastAPI)
        """
        mode_str = os.getenv("DISPLAY_MODE", "console").lower()
        mode = DisplayMode(mode_str)

        match mode:
            case DisplayMode.CONSOLE:
                return self.handle_console()

            case DisplayMode.API:
                return self.handle_api()

            case DisplayMode.HYBRID:
                # Log to console for debugging
                self.handle_console()
                # Return structured data for API response
                return self.handle_api()

    @abstractmethod
    def handle_console(self) -> str:
        """
        Handle console display (prints to terminal).

        This method has side effects - it prints to the console.
        Returns a string representation for compatibility.

        Returns:
            String representation of the output
        """
        pass

    @abstractmethod
    def handle_api(self) -> dict[str, Any]:
        """
        Handle API mode (returns structured data).

        Pure function - no side effects.
        Returns dict that FastAPI will serialize to JSON.

        Returns:
            Dict with structured data for JSON serialization
        """
        pass


class TextOutputModel(ToolOutputModel):
    """Simple text output model."""

    content: str = Field(description="The text content")

    def __str__(self) -> str:
        return self.content

    def handle_console(self) -> str:
        """Display text to console with Rich styling."""
        console = Console()

        if "\n" in self.content:
            lines = self.content.split("\n")
            first_line = lines[0]
            line_count = len(lines) - 1

            if line_count > 3:
                console.print(f"  ⎿  {first_line}", style="bright_black")
                console.print(f"     ... (+{line_count} lines)", style="bright_black")
            else:
                console.print(f"  ⎿  {self.content}", style="bright_black")
        else:
            console.print(f"  ⎿  {self.content}", style="bright_black")

        return self.content

    def handle_api(self) -> dict[str, Any]:
        """Return structured data for API."""
        return {
            "type": "text",
            "content": self.content,
            "metadata": self.metadata,
        }


class CodeOutputModel(ToolOutputModel):
    """Code output model with syntax highlighting information."""

    content: str = Field(description="The code content")
    language: str = Field(
        default="text",
        description="Programming language for syntax highlighting"
    )
    line_numbers: bool = Field(
        default=True,
        description="Whether line numbers should be displayed"
    )

    def __str__(self) -> str:
        return self.content

    def handle_console(self) -> str:
        """Display code with syntax highlighting."""
        from rich.syntax import Syntax

        console = Console()
        console.print("  ⎿", style="bright_black")

        if self.content.count("\n") > 10:
            lines = self.content.split("\n")
            first_few_lines = "\n".join(lines[:3])
            line_count = len(lines)

            syntax = Syntax(
                first_few_lines,
                self.language,
                theme="monokai",
                line_numbers=True
            )
            console.print(syntax)
            console.print(f"     ... (+{line_count-3} more lines)", style="bright_black")
        else:
            syntax = Syntax(
                self.content,
                self.language,
                theme="monokai",
                line_numbers=self.line_numbers
            )
            console.print(syntax)

        return self.content

    def handle_api(self) -> dict[str, Any]:
        """Return structured data for API."""
        return {
            "type": "code",
            "content": self.content,
            "language": self.language,
            "line_numbers": self.line_numbers,
            "metadata": self.metadata,
        }


class FileInfo(BaseModel):
    """Information about a single file or directory."""

    name: str = Field(description="File or directory name")
    path: str = Field(description="Full path to the file/directory")
    is_dir: bool = Field(description="Whether this is a directory")
    size: int | str = Field(
        default="",
        description="File size in bytes or formatted string"
    )
    modified: int | None = Field(
        default=None,
        description="Modification timestamp (Unix epoch)"
    )
    modified_date: str | None = Field(
        default=None,
        description="Formatted modification date"
    )

    class Config:
        extra = "allow"  # Allow additional fields like matches, first_match, etc.


class FileListOutputModel(ToolOutputModel):
    """File listing output model."""

    files: list[FileInfo] = Field(
        default_factory=list,
        description="List of files and directories"
    )
    path: str = Field(
        default="",
        description="Base path for the file listing"
    )
    total_count: int | None = Field(
        default=None,
        description="Total number of items (if different from len(files))"
    )
    truncated: bool = Field(
        default=False,
        description="Whether the results were truncated"
    )

    def __str__(self) -> str:
        return f"{len(self.files)} items in {self.path}"

    def handle_console(self) -> str:
        """Display file list as table."""
        from rich.table import Table

        console = Console()

        if self.path:
            console.print(f"  ⎿ Directory: {self.path}", style="bright_black")
        else:
            console.print("  ⎿", style="bright_black")

        table = Table(box=None, show_header=True, show_edge=False)
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Size", style="magenta")

        total_items = len(self.files)
        shown_items = min(10, total_items)

        for file in self.files[:shown_items]:
            file_type = "[DIR]" if file.is_dir else "[FILE]"
            size = file.size
            if isinstance(size, int):
                if size < 1024:
                    size = f"{size} B"
                elif size < 1024 * 1024:
                    size = f"{size / 1024:.1f} KB"
                else:
                    size = f"{size / (1024 * 1024):.1f} MB"

            table.add_row(file.name, file_type, str(size))

        console.print(table)

        if total_items > shown_items:
            console.print(f"... (+{total_items - shown_items} more items)", style="bright_black")

        return f"{total_items} items in {self.path}"

    def handle_api(self) -> dict[str, Any]:
        """Return structured data for API."""
        return {
            "type": "file_list",
            "files": [
                {
                    "name": f.name,
                    "path": f.path,
                    "is_dir": f.is_dir,
                    "size": f.size,
                    "modified": f.modified,
                    "modified_date": f.modified_date,
                }
                for f in self.files
            ],
            "path": self.path,
            "total_count": self.total_count,
            "truncated": self.truncated,
            "metadata": self.metadata,
        }


class TableOutputModel(ToolOutputModel):
    """Tabular data output model."""

    rows: list[list[str]] = Field(
        default_factory=list,
        description="Table rows, each row is a list of cell values"
    )
    headers: list[str] | None = Field(
        default=None,
        description="Optional column headers"
    )

    def __str__(self) -> str:
        if self.headers:
            return f"Table with {len(self.rows)} rows and {len(self.headers)} columns"
        return f"Table with {len(self.rows)} rows"

    def handle_console(self) -> str:
        """Display tabular data with UI styling."""
        from rich.table import Table
        from rich.box import ROUNDED

        console = Console()
        console.print("  ⎿", style="bright_black")

        table = Table(box=ROUNDED, show_header=bool(self.headers))

        if self.headers:
            for header in self.headers:
                table.add_column(header, style="cyan bold")
        else:
            if self.rows and self.rows[0]:
                for _ in range(len(self.rows[0])):
                    table.add_column()

        for row in self.rows:
            table.add_row(*[str(cell) for cell in row])

        console.print(table)

        return f"Table with {len(self.rows)} rows"

    def handle_api(self) -> dict[str, Any]:
        """Return structured data for API."""
        return {
            "type": "table",
            "rows": self.rows,
            "headers": self.headers,
            "metadata": self.metadata,
        }


class ErrorOutputModel(ToolOutputModel):
    """Error output model."""

    error: str = Field(description="Error message")
    error_type: str = Field(
        default="Error",
        description="Type of error (Error, Warning, Info, etc.)"
    )
    traceback: str | None = Field(
        default=None,
        description="Optional stack trace or detailed error info"
    )

    def __str__(self) -> str:
        return f"{self.error_type}: {self.error}"

    def handle_console(self) -> str:
        """Display error with red styling."""
        console = Console()
        console.print(f"  ⎿  {self.error_type}: {self.error}", style="red")

        if self.traceback:
            console.print(f"     {self.traceback}", style="bright_black")

        return f"{self.error_type}: {self.error}"

    def handle_api(self) -> dict[str, Any]:
        """Return structured error for API."""
        return {
            "type": "error",
            "error": self.error,
            "error_type": self.error_type,
            "traceback": self.traceback,
            "metadata": self.metadata,
        }


class MediaOutputModel(ToolOutputModel):
    """Media output model for images, PDFs, and other binary files."""

    filename: str = Field(description="The name of the media file")
    mime_type: str = Field(description="MIME type of the media (e.g., 'image/png', 'application/pdf')")
    base64_data: str = Field(description="Base64-encoded binary data")
    size_bytes: int | None = Field(
        default=None,
        description="Size of the file in bytes"
    )

    def __str__(self) -> str:
        size_str = f" ({self.size_bytes} bytes)" if self.size_bytes else ""
        return f"Media file: {self.filename} ({self.mime_type}){size_str}"

    def handle_console(self) -> str:
        """Display media file info in console."""
        console = Console()

        # Show basic file info
        size_str = ""
        if self.size_bytes:
            if self.size_bytes < 1024:
                size_str = f" ({self.size_bytes} B)"
            elif self.size_bytes < 1024 * 1024:
                size_str = f" ({self.size_bytes / 1024:.1f} KB)"
            else:
                size_str = f" ({self.size_bytes / (1024 * 1024):.1f} MB)"

        console.print(f"  ⎿  Media File: {self.filename}", style="bright_black")
        console.print(f"     MIME Type: {self.mime_type}{size_str}", style="bright_black")
        console.print(f"     Base64 data available ({len(self.base64_data)} characters)", style="bright_black")

        return f"Media file: {self.filename} ({self.mime_type})"

    def handle_api(self) -> dict[str, Any]:
        """Return structured media data for API."""
        return {
            "type": "media",
            "filename": self.filename,
            "mime_type": self.mime_type,
            "base64_data": self.base64_data,
            "size_bytes": self.size_bytes,
            "metadata": self.metadata,
        }
