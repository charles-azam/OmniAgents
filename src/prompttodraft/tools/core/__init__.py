"""
Core tools for the prompttodraft framework.

This module exports all Gemini CLI tools implemented using the backend system.
"""

from prompttodraft.tools.core.ls_tool_core import ListDirectoryToolCore
from prompttodraft.tools.core.view_tool_core import ReadFileToolCore
from prompttodraft.tools.core.write_file_tool_core import WriteFileToolCore
from prompttodraft.tools.core.glob_tool_core import GlobToolCore
from prompttodraft.tools.core.grep_tool_core import SearchFileContentToolCore
from prompttodraft.tools.core.replace_tool_core import ReplaceToolCore
from prompttodraft.tools.core.bash_tool_core import RunShellCommandToolCore
from prompttodraft.tools.core.read_many_files_tool_core import ReadManyFilesToolCore
from prompttodraft.tools.core.save_memory_tool_core import SaveMemoryToolCore
from prompttodraft.tools.core.metadata import ToolMetadata

__all__ = [
    # Gemini CLI Tools
    "ListDirectoryToolCore",      # list_directory (ReadFolder)
    "ReadFileToolCore",            # read_file (ReadFile)
    "WriteFileToolCore",           # write_file (WriteFile)
    "GlobToolCore",                # glob (FindFiles)
    "SearchFileContentToolCore",   # search_file_content (SearchText)
    "ReplaceToolCore",             # replace (Edit)
    "RunShellCommandToolCore",     # run_shell_command (Shell)
    "ReadManyFilesToolCore",       # read_many_files (Multi File Read)
    "SaveMemoryToolCore",          # save_memory (Memory)
    # Metadata
    "ToolMetadata",
]
