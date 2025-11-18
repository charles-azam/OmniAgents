"""
Minimalist smolagents agent implementation.

This module provides a simple interface to create and run a smolagents CodeAgent
with manually defined tools, working across any execution backend.
"""
import os
from smolagents import Tool, ToolCallingAgent, OpenAIModel, InferenceClientModel

from prompttodraft.agent.backends.execution_backend import ExecutionBackend
from prompttodraft.agent.tools.write_file_tool import WriteFileTool
from prompttodraft.agent.tools.read_file_tool import ReadFileTool
from prompttodraft.agent.tools.list_directory_tool import ListDirectoryTool
from prompttodraft.agent.tools.glob_tool import GlobTool
from prompttodraft.agent.tools.search_file_content_tool import SearchFileContentTool
from prompttodraft.agent.tools.replace_tool import ReplaceTool
from prompttodraft.agent.tools.run_shell_command_tool import RunShellCommandTool
from prompttodraft.agent.tools.read_many_files_tool import ReadManyFilesTool
from prompttodraft.agent.tools.save_memory_tool import SaveMemoryTool
from prompttodraft.agent.tools.uv_tool import UVTool


def create_model(provider: str, model_id: str):
    """
    Create a smolagents model from provider and model_id.

    Args:
        provider: Provider name (openai, huggingface, xai).
        model_id: Model identifier.

    Returns:
        Configured smolagents model.
    """
    if provider == "openai":
        return OpenAIModel(model_id=model_id)
    elif provider == "huggingface":
        return InferenceClientModel(model_id=model_id)
    elif provider == "xai":
        return OpenAIModel(
            model_id=model_id,
            api_key=os.getenv("XAI_API_KEY"),
            api_base="https://api.x.ai/v1"
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")


# Manual smolagents Tool definitions
class WriteFileSmolagentsTool(Tool):
    """Manual smolagents tool for writing files."""

    name = WriteFileTool.metadata.name
    description = WriteFileTool.metadata.description
    inputs = {
        "file_path": {"type": "string", "description": "The absolute path to the file to write to"},
        "content": {"type": "string", "description": "The content to write into the file"},
    }
    output_type = "string"

    def __init__(self, backend: ExecutionBackend):
        self.core_tool = WriteFileTool(backend=backend)
        super().__init__()

    def forward(self, file_path: str, content: str) -> str:
        """Execute the write_file tool."""
        result = self.core_tool.execute(file_path=file_path, content=content)
        return str(result)


class ReadFileSmolagentsTool(Tool):
    """Manual smolagents tool for reading files."""

    name = ReadFileTool.metadata.name
    description = ReadFileTool.metadata.description
    inputs = {
        "path": {"type": "string", "description": "The absolute path to the file to read"},
        "offset": {"type": "number", "description": "Optional: For text files, the 0-based line number to start reading from", "nullable": True},
        "limit": {"type": "number", "description": "Optional: For text files, maximum number of lines to read", "nullable": True},
    }
    output_type = "string"

    def __init__(self, backend: ExecutionBackend):
        self.core_tool = ReadFileTool(backend=backend)
        super().__init__()

    def forward(self, path: str, offset: int | None = None, limit: int | None = None) -> str:
        """Execute the read_file tool."""
        result = self.core_tool.execute(path=path, offset=offset, limit=limit)
        return str(result)


class ListDirectorySmolagentsTool(Tool):
    """Manual smolagents tool for listing directory contents."""

    name = ListDirectoryTool.metadata.name
    description = ListDirectoryTool.metadata.description
    inputs = {
        "path": {"type": "string", "description": "The absolute path to the directory to list"},
        "ignore": {"type": "array", "items": {"type": "string"}, "description": "Optional: List of glob patterns to ignore", "nullable": True},
        "respect_git_ignore": {"type": "boolean", "description": "Optional: Whether to respect .gitignore patterns", "nullable": True},
    }
    output_type = "string"

    def __init__(self, backend: ExecutionBackend):
        self.core_tool = ListDirectoryTool(backend=backend)
        super().__init__()

    def forward(self, path: str, ignore: list[str] | None = None, respect_git_ignore: bool = True) -> str:
        """Execute the list_directory tool."""
        result = self.core_tool.execute(path=path, ignore=ignore, respect_git_ignore=respect_git_ignore)
        return str(result)


class GlobSmolagentsTool(Tool):
    """Manual smolagents tool for finding files by glob patterns."""

    name = GlobTool.metadata.name
    description = GlobTool.metadata.description
    inputs = {
        "pattern": {"type": "string", "description": "The glob pattern to match against"},
        "path": {"type": "string", "description": "Optional: The absolute path to the directory to search within", "nullable": True},
        "case_sensitive": {"type": "boolean", "description": "Optional: Whether the search should be case-sensitive", "nullable": True},
        "respect_git_ignore": {"type": "boolean", "description": "Optional: Whether to respect .gitignore patterns", "nullable": True},
    }
    output_type = "string"

    def __init__(self, backend: ExecutionBackend):
        self.core_tool = GlobTool(backend=backend)
        super().__init__()

    def forward(self, pattern: str, path: str | None = None, case_sensitive: bool = False, respect_git_ignore: bool = True) -> str:
        """Execute the glob tool."""
        result = self.core_tool.execute(pattern=pattern, path=path, case_sensitive=case_sensitive, respect_git_ignore=respect_git_ignore)
        return str(result)


class SearchFileContentSmolagentsTool(Tool):
    """Manual smolagents tool for searching file contents."""

    name = SearchFileContentTool.metadata.name
    description = SearchFileContentTool.metadata.description
    inputs = {
        "pattern": {"type": "string", "description": "The regular expression to search for in file contents"},
        "path": {"type": "string", "description": "Optional: The absolute path to the directory to search within", "nullable": True},
        "include": {"type": "string", "description": "Optional: File pattern to include in the search", "nullable": True},
    }
    output_type = "string"

    def __init__(self, backend: ExecutionBackend):
        self.core_tool = SearchFileContentTool(backend=backend)
        super().__init__()

    def forward(self, pattern: str, path: str | None = None, include: str | None = None) -> str:
        """Execute the search_file_content tool."""
        result = self.core_tool.execute(pattern=pattern, path=path, include=include)
        return str(result)


class ReplaceSmolagentsTool(Tool):
    """Manual smolagents tool for replacing text in files."""

    name = ReplaceTool.metadata.name
    description = ReplaceTool.metadata.description
    inputs = {
        "file_path": {"type": "string", "description": "The absolute path to the file to modify"},
        "old_string": {"type": "string", "description": "The exact literal text to replace"},
        "new_string": {"type": "string", "description": "The exact literal text to replace old_string with"},
        "expected_replacements": {"type": "number", "description": "Number of replacements expected", "nullable": True},
    }
    output_type = "string"

    def __init__(self, backend: ExecutionBackend):
        self.core_tool = ReplaceTool(backend=backend)
        super().__init__()

    def forward(self, file_path: str, old_string: str, new_string: str, expected_replacements: int = 1) -> str:
        """Execute the replace tool."""
        result = self.core_tool.execute(file_path=file_path, old_string=old_string, new_string=new_string, expected_replacements=expected_replacements)
        return str(result)


class RunShellCommandSmolagentsTool(Tool):
    """Manual smolagents tool for running shell commands."""

    name = RunShellCommandTool.metadata.name
    description = RunShellCommandTool.metadata.description
    inputs = {
        "command": {"type": "string", "description": "The exact shell command to execute"},
        "description": {"type": "string", "description": "Optional: A brief description of the command's purpose", "nullable": True},
        "directory": {"type": "string", "description": "Optional: The directory in which to execute the command", "nullable": True},
    }
    output_type = "string"

    def __init__(self, backend: ExecutionBackend):
        self.core_tool = RunShellCommandTool(backend=backend)
        super().__init__()

    def forward(self, command: str, description: str | None = None, directory: str | None = None) -> str:
        """Execute the run_shell_command tool."""
        result = self.core_tool.execute(command=command, description=description, directory=directory)
        return str(result)


class ReadManyFilesSmolagentsTool(Tool):
    """Manual smolagents tool for reading multiple files."""

    name = ReadManyFilesTool.metadata.name
    description = ReadManyFilesTool.metadata.description
    inputs = {
        "paths": {"type": "array", "items": {"type": "string"}, "description": "An array of glob patterns or paths"},
        "exclude": {"type": "array", "items": {"type": "string"}, "description": "Optional: Glob patterns to exclude", "nullable": True},
        "include": {"type": "array", "items": {"type": "string"}, "description": "Optional: Additional glob patterns to include", "nullable": True},
        "recursive": {"type": "boolean", "description": "Optional: Whether to search recursively", "nullable": True},
        "useDefaultExcludes": {"type": "boolean", "description": "Optional: Whether to apply default exclusion patterns", "nullable": True},
        "respect_git_ignore": {"type": "boolean", "description": "Optional: Whether to respect .gitignore patterns", "nullable": True},
    }
    output_type = "string"

    def __init__(self, backend: ExecutionBackend):
        self.core_tool = ReadManyFilesTool(backend=backend)
        super().__init__()

    def forward(
        self,
        paths: list[str],
        exclude: list[str] | None = None,
        include: list[str] | None = None,
        recursive: bool = True,
        useDefaultExcludes: bool = True,
        respect_git_ignore: bool = True,
    ) -> str:
        """Execute the read_many_files tool."""
        result = self.core_tool.execute(
            paths=paths,
            exclude=exclude,
            include=include,
            recursive=recursive,
            useDefaultExcludes=useDefaultExcludes,
            respect_git_ignore=respect_git_ignore,
        )
        return str(result)


class SaveMemorySmolagentsTool(Tool):
    """Manual smolagents tool for saving memories."""

    name = SaveMemoryTool.metadata.name
    description = SaveMemoryTool.metadata.description
    inputs = {
        "fact": {"type": "string", "description": "The specific fact or piece of information to remember"},
    }
    output_type = "string"

    def __init__(self, backend: ExecutionBackend):
        self.core_tool = SaveMemoryTool(backend=backend)
        super().__init__()

    def forward(self, fact: str) -> str:
        """Execute the save_memory tool."""
        result = self.core_tool.execute(fact=fact)
        return str(result)


class UVSmolagentsTool(Tool):
    """Manual smolagents tool for executing uv commands."""

    name = UVTool.metadata.name
    description = UVTool.metadata.description
    inputs = {
        "command": {"type": "string", "description": "The uv command to execute (without the 'uv' prefix)"},
        "description": {"type": "string", "description": "Optional: A brief description of the command's purpose", "nullable": True},
    }
    output_type = "string"

    def __init__(self, backend: ExecutionBackend):
        self.core_tool = UVTool(backend=backend)
        super().__init__()

    def forward(self, command: str, description: str | None = None) -> str:
        """Execute the uv tool."""
        result = self.core_tool.execute(command=command, description=description)
        return str(result)


class SmolAgentAgent:
    """
    A minimalist smolagents-based coding agent.

    This agent combines:
    - Any execution backend (Local, Docker, E2B)
    - Core tools with manually defined smolagents wrappers
    - Dynamic system prompt with project context
    """

    def __init__(
        self,
        backend: ExecutionBackend,
        model_id: str = "openai/gpt-oss-120b",
        provider: str = "huggingface",
        additional_tools: list | None = None,
        max_steps: int = 30,
    ) -> None:
        """
        Initialize the smolagent agent.

        Args:
            backend: Execution backend (LocalBackend, DockerBackend, or E2BBackend)
            model_id: Model identifier
            provider: Provider name (openai, huggingface, xai)
            additional_tools: Optional additional smolagents tools to add
            max_steps: Maximum number of agent steps
        """
        self.backend = backend
        self.model_id = model_id

        # Create core tools manually
        self.tools = [
            WriteFileSmolagentsTool(backend=backend),
            ReadFileSmolagentsTool(backend=backend),
            ListDirectorySmolagentsTool(backend=backend),
            GlobSmolagentsTool(backend=backend),
            SearchFileContentSmolagentsTool(backend=backend),
            ReplaceSmolagentsTool(backend=backend),
            RunShellCommandSmolagentsTool(backend=backend),
            ReadManyFilesSmolagentsTool(backend=backend),
            SaveMemorySmolagentsTool(backend=backend),
            UVSmolagentsTool(backend=backend),
        ]

        # Add any additional tools
        if additional_tools:
            self.tools.extend(additional_tools)

        # Initialize the smolagents agent
        self.model = create_model(provider=provider, model_id=model_id)
        self.agent = ToolCallingAgent(
            tools=self.tools,
            model=self.model,
            max_steps=max_steps,
        )

    def run(self, task: str, reset_history: bool = True) -> str:
        """
        Run the agent on a task.

        Args:
            task: The task or question to run
            reset_history: Whether to reset conversation history before running

        Returns:
            The agent's final answer as a string
        """
        self.backend.start()
        if reset_history:
            self.backend.cleanup()

        # Run the agent
        result = self.agent.run(task=task)

        self.backend.shutdown()

        return result
