"""
save_memory tool - Framework-agnostic memory persistence tool.

Implements the Gemini CLI Memory tool specification.
"""
from pathlib import Path
from datetime import datetime

from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend, FileType
from prompttodraft.tools.outputs.models import (
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)


MEMORY_FILE_NAME = "GEMINI.md"
MEMORY_SECTION = "## Gemini Added Memories"


class SaveMemoryToolCore:
    """
    save_memory tool for persisting information across sessions.

    Implements the Gemini CLI Memory specification.
    """

    metadata = ToolMetadata(
        name="save_memory",
        description="""Use `save_memory` to save and recall information across your Gemini CLI
sessions. With `save_memory`, you can direct the CLI to remember key details
across sessions, providing personalized and directed assistance.

### Arguments

`save_memory` takes one argument:

- `fact` (string, required): The specific fact or piece of information to
  remember. This should be a clear, self-contained statement written in natural
  language.

## How to use `save_memory` with the Gemini CLI

The tool appends the provided `fact` to a special `GEMINI.md` file located in
the user's home directory (`~/.gemini/GEMINI.md`). This file can be configured
to have a different name.

Once added, the facts are stored under a `## Gemini Added Memories` section.
This file is loaded as context in subsequent sessions, allowing the CLI to
recall the saved information.

## Important notes

- **General usage:** This tool should be used for concise, important facts. It
  is not intended for storing large amounts of data or conversational history.
- **Memory file:** The memory file is a plain text Markdown file, so you can
  view and edit it manually if needed.""",
        inputs={
            "fact": {
                "type": "string",
                "description": "The specific fact or piece of information to remember. Should be a clear, self-contained statement."
            }
        },
        output_type="string"
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize SaveMemoryToolCore with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    def execute(self, fact: str) -> ToolOutputModel:
        """
        Save a fact to the memory file.

        Args:
            fact: The fact to remember

        Returns:
            A ToolOutputModel indicating success or failure
        """
        # Determine memory file path (~/.gemini/GEMINI.md)
        try:
            # Get home directory
            result = self.backend.execute_command(
                command="echo $HOME",
                timeout=5000
            )
            if result.exit_code != 0:
                return ErrorOutputModel(
                    error="Failed to determine home directory",
                    error_type="IOError"
                )

            home_dir = result.output.strip()
            gemini_dir = Path(home_dir) / ".gemini"
            memory_file = gemini_dir / MEMORY_FILE_NAME

            # Create .gemini directory if it doesn't exist
            if self.backend.file_exists(path=str(gemini_dir)) is None:
                try:
                    self.backend.create_directory(path=str(gemini_dir), parents=True)
                except Exception as e:
                    return ErrorOutputModel(
                        error=f"Failed to create .gemini directory: {str(e)}",
                        error_type="IOError"
                    )

            # Read existing file content or create new
            if self.backend.file_exists(path=str(memory_file)) == FileType.FILE:
                try:
                    existing_content = self.backend.read_file(file_path=str(memory_file))
                except Exception as e:
                    return ErrorOutputModel(
                        error=f"Failed to read memory file: {str(e)}",
                        error_type="IOError"
                    )
            else:
                existing_content = ""

            # Add the new fact
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_fact_entry = f"- [{timestamp}] {fact}\n"

            # Check if memory section exists
            if MEMORY_SECTION in existing_content:
                # Append to existing section
                # Find the section and add the fact after it
                lines = existing_content.split('\n')
                section_index = -1
                for i, line in enumerate(lines):
                    if line.strip() == MEMORY_SECTION:
                        section_index = i
                        break

                if section_index >= 0:
                    # Insert fact after section header
                    lines.insert(section_index + 1, new_fact_entry.rstrip())
                    new_content = '\n'.join(lines)
                else:
                    # Section not found (shouldn't happen), append at end
                    new_content = existing_content + f"\n{MEMORY_SECTION}\n{new_fact_entry}"
            else:
                # Create new section
                if existing_content.strip():
                    new_content = f"{existing_content}\n\n{MEMORY_SECTION}\n{new_fact_entry}"
                else:
                    new_content = f"{MEMORY_SECTION}\n{new_fact_entry}"

            # Write updated content
            try:
                self.backend.write_file(file_path=str(memory_file), content=new_content)
            except Exception as e:
                return ErrorOutputModel(
                    error=f"Failed to write memory file: {str(e)}",
                    error_type="IOError"
                )

            return TextOutputModel(
                content=f"Successfully saved fact to memory: {fact}"
            )

        except Exception as e:
            return ErrorOutputModel(
                error=f"Error saving memory: {str(e)}",
                error_type="IOError"
            )
