"""
Output data models for tools.

This module defines Pydantic models for tool outputs, separating data from presentation.
These models can be rendered differently for console, file, or API responses.
"""
from pydantic import BaseModel, Field
from datetime import datetime


class BaseOutputModel(BaseModel):
    """Base class for all tool output models."""

    metadata: dict[str, str | int | float | bool] | None = Field(
        default=None,
        description="Optional metadata about the output (timestamps, tool name, etc.)"
    )

    class Config:
        frozen = False  # Allow modification if needed
        extra = "allow"  # Allow additional fields


class TextOutputModel(BaseOutputModel):
    """Simple text output model."""

    content: str = Field(description="The text content")

    def __str__(self) -> str:
        return self.content


class CodeOutputModel(BaseOutputModel):
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


class FileListOutputModel(BaseOutputModel):
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


class TableOutputModel(BaseOutputModel):
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


class ErrorOutputModel(BaseOutputModel):
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


# Type alias for any output model
ToolOutputModel = (
    TextOutputModel |
    CodeOutputModel |
    FileListOutputModel |
    TableOutputModel |
    ErrorOutputModel
)
