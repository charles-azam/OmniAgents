"""
Save memory tool implementation.

This tool saves and recalls information across sessions by appending to a memory file.
"""
from pathlib import Path
from pydantic import BaseModel, Field

from anyagent.tools.base_tool import CoreBackendTool
from anyagent.outputs.outputs import (
    TextOutputModel,
    ToolOutputModel,
)


class SaveMemoryInput(BaseModel):
    """Input model for SaveMemoryTool."""
    fact: str = Field(description="The specific fact or piece of information to remember. This should be a clear, self-contained statement written in natural language (e.g., 'My preferred programming language is Python.' or 'The project I'm currently working on is called gemini-cli.').")


class SaveMemoryTool(CoreBackendTool[SaveMemoryInput, TextOutputModel]):
    """
    Framework-agnostic memory persistence tool.

    Saves and recalls information across sessions by appending facts to a
    memory file. This allows the system to remember key details across sessions.
    """

    name = "save_memory"
    description = "Saves and recalls information across sessions. Use this to direct the assistant to remember key details, enabling personalized and context-aware assistance in subsequent sessions. The tool appends the provided fact to a special memory file (GEMINI.md) located in the user's home directory (~/.gemini/). Once added, the facts are stored under a '## Gemini Added Memories' section and loaded as context in future sessions."

    # Default memory file location (in user's home directory)
    MEMORY_FILE_DIR = ".gemini"
    MEMORY_FILE_NAME = "GEMINI.md"
    MEMORY_SECTION_HEADER = "## Gemini Added Memories"

    def _get_memory_file_path(self) -> Path:
        """
        Get the path to the memory file.

        Returns:
            Absolute path to the memory file as a Path object
        """
        # Always use working directory to ensure we stay within sandbox
        return self.backend.get_working_directory() / self.MEMORY_FILE_DIR / self.MEMORY_FILE_NAME


    def execute(self, inputs: SaveMemoryInput) -> TextOutputModel:
        """
        Execute the save_memory tool.

        Args:
            inputs: Validated input model with fact

        Returns:
            TextOutputModel with success message
        """
        memory_file_path = self._get_memory_file_path()

        # Ensure the directory exists
        memory_dir = memory_file_path.parent
        dir_exists = self.backend.file_exists(path=memory_dir)

        if dir_exists is None:
            self.backend.create_directory(path=memory_dir, parents=True)

        # Check if memory file exists
        file_exists = self.backend.file_exists(path=memory_file_path)

        if file_exists is None:
            # Create new memory file with header
            initial_content = f"# Gemini Memory File\n\n{self.MEMORY_SECTION_HEADER}\n\n- {inputs.fact}\n"
            self.backend.write_file(file_path=memory_file_path, content=initial_content)
            return TextOutputModel(
                content=f"Memory saved: '{inputs.fact}' (created new memory file at {str(memory_file_path)})",
            )

        # File exists, read current content
        content = self.backend.read_file(file_path=memory_file_path)

        # Check if the memories section exists
        if self.MEMORY_SECTION_HEADER in content:
            # Append to existing section
            # Find the section and append after it
            new_content = content.rstrip() + f"\n- {inputs.fact}\n"
        else:
            # Add the section header and fact
            new_content = content.rstrip() + f"\n\n{self.MEMORY_SECTION_HEADER}\n\n- {inputs.fact}\n"

        # Write updated content
        self.backend.write_file(file_path=memory_file_path, content=new_content)

        return TextOutputModel(
            content=f"Memory saved: '{inputs.fact}' (appended to {str(memory_file_path)})",
        )
