"""
Save memory tool implementation.

This tool saves and recalls information across sessions by appending to a memory file.
"""
from pathlib import Path

from prompttodraft.agent.tools.base_tool import CoreTool
from prompttodraft.agent.tools.metadata import ToolMetadata
from prompttodraft.agent.backends.execution_backend import ExecutionBackend, FileType
from prompttodraft.agent.outputs.outputs import (
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


class SaveMemoryTool(CoreTool):
    """
    Framework-agnostic memory persistence tool.

    Saves and recalls information across sessions by appending facts to a
    memory file. This allows the system to remember key details across sessions.
    """

    metadata = ToolMetadata(
        name="save_memory",
        description="Saves and recalls information across sessions. Use this to direct the assistant to remember key details, enabling personalized and context-aware assistance in subsequent sessions. The tool appends the provided fact to a special memory file (GEMINI.md) located in the user's home directory (~/.gemini/). Once added, the facts are stored under a '## Gemini Added Memories' section and loaded as context in future sessions.",
        inputs={
            "fact": {
                "type": "string",
                "description": "The specific fact or piece of information to remember. This should be a clear, self-contained statement written in natural language (e.g., 'My preferred programming language is Python.' or 'The project I'm currently working on is called gemini-cli.').",
                "nullable": False,
            },
        },
        output_type="string",
    )

    # Default memory file location (in user's home directory)
    MEMORY_FILE_DIR = ".gemini"
    MEMORY_FILE_NAME = "GEMINI.md"
    MEMORY_SECTION_HEADER = "## Gemini Added Memories"

    def _get_memory_file_path(self) -> str:
        """
        Get the path to the memory file.

        Returns:
            Absolute path to the memory file
        """
        # For Docker and E2B backends, use working directory to avoid permission issues
        from prompttodraft.agent.backends.docker_backend import DockerBackend
        from prompttodraft.agent.backends.e2b_backend import E2BBackend

        if isinstance(self.backend, (DockerBackend, E2BBackend)):
            return str(Path(self.backend.get_working_directory()) / self.MEMORY_FILE_DIR / self.MEMORY_FILE_NAME)

        # For local backend, try to use home directory
        home_result = self.backend.execute_command(
            command="echo $HOME",
            timeout=5000,
        )

        if home_result.exit_code != 0 or not home_result.output:
            # Fallback to working directory
            return str(Path(self.backend.get_working_directory()) / self.MEMORY_FILE_DIR / self.MEMORY_FILE_NAME)

        home_dir = home_result.output.strip()
        return str(Path(home_dir) / self.MEMORY_FILE_DIR / self.MEMORY_FILE_NAME)

    def execute(self, fact: str) -> ToolOutputModel:
        """
        Execute the save_memory tool.

        Args:
            fact: The specific fact or piece of information to remember

        Returns:
            TextOutputModel with success message or ErrorOutputModel on failure
        """
        memory_file_path = self._get_memory_file_path()

        # Ensure the directory exists
        memory_dir = str(Path(memory_file_path).parent)
        dir_exists = self.backend.file_exists(path=memory_dir)

        if dir_exists is None:
            self.backend.create_directory(path=memory_dir, parents=True)

        # Check if memory file exists
        file_exists = self.backend.file_exists(path=memory_file_path)

        if file_exists is None:
            # Create new memory file with header
            initial_content = f"# Gemini Memory File\n\n{self.MEMORY_SECTION_HEADER}\n\n- {fact}\n"
            self.backend.write_file(file_path=memory_file_path, content=initial_content)
            return TextOutputModel(
                content=f"Memory saved: '{fact}' (created new memory file at {memory_file_path})",
            )

        # File exists, read current content
        content = self.backend.read_file(file_path=memory_file_path)

        # Check if the memories section exists
        if self.MEMORY_SECTION_HEADER in content:
            # Append to existing section
            # Find the section and append after it
            new_content = content.rstrip() + f"\n- {fact}\n"
        else:
            # Add the section header and fact
            new_content = content.rstrip() + f"\n\n{self.MEMORY_SECTION_HEADER}\n\n- {fact}\n"

        # Write updated content
        self.backend.write_file(file_path=memory_file_path, content=new_content)

        return TextOutputModel(
            content=f"Memory saved: '{fact}' (appended to {memory_file_path})",
        )
