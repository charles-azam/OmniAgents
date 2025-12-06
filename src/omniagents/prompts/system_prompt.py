"""
System prompt generation utilities for the agent.

This module provides functions to generate dynamic system prompts
with directory structure and git information.
"""
import datetime
import platform
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omniagents.backends.execution_backend import ExecutionBackend


def get_directory_structure(backend: "ExecutionBackend", start_path: str, ignore_patterns: list[str] | None = None) -> str:
    """
    Generate a nested directory structure as a string using backend operations.

    Args:
        backend: ExecutionBackend instance to use for filesystem operations
        start_path: The starting directory path (command path, e.g., /workspace for Docker)
        ignore_patterns: List of patterns to ignore

    Returns:
        String representation of the directory structure
    """
    if ignore_patterns is None:
        ignore_patterns = [
            ".git",
            "__pycache__",
            ".venv",
            ".env",
            "node_modules",
            ".pytest_cache",
            ".cache",
        ]

    # Convert string path to Path and then use convert_to_path for proper host path resolution
    path_for_listing = backend.convert_to_path(path=start_path)

    # Get all files recursively using backend
    files = backend.list_directory(path=path_for_listing, recursive=True)

    # Create formatted string
    structure = f"- {start_path}/\n"
    dir_structure = []
    max_files = 100
    file_count = 0

    # Group files by directory
    dirs_seen = set()

    for file_info in files:
        # Skip if we've reached max files
        if file_count >= max_files:
            if len(dir_structure) > 0 and not dir_structure[-1].endswith("(truncated)"):
                dir_structure.append("  ... (truncated for brevity)")
            break

        rel_path = Path(file_info.path).relative_to(start_path)

        # Skip ignored patterns
        if any(pattern in str(rel_path).split("/") for pattern in ignore_patterns):
            continue

        # Skip lock files and other large generated files
        if str(rel_path).endswith((".lock", ".sum", ".mod", ".bin", ".whl")):
            continue

        # Calculate indentation level
        level = len(rel_path.parts) - 1 if not file_info.is_dir else len(rel_path.parts)
        indent = "  " * (level + 1)

        # Add parent directories if not seen
        parent = rel_path.parent
        if parent != Path(".") and str(parent) not in dirs_seen:
            dirs_seen.add(str(parent))
            parent_level = len(parent.parts)
            parent_indent = "  " * (parent_level + 1)
            dir_structure.append(f"{parent_indent}- {parent.name}/")

        # Add file or directory
        if file_info.is_dir:
            if str(rel_path) not in dirs_seen:
                dirs_seen.add(str(rel_path))
                dir_structure.append(f"{indent}- {rel_path.name}/")
        else:
            dir_structure.append(f"{indent}- {rel_path.name}")
            file_count += 1

    return "".join([structure] + [f"{line}\n" for line in dir_structure])


def is_git_repo(backend: "ExecutionBackend") -> bool:
    """
    Check if the working directory is a git repository.

    Args:
        backend: ExecutionBackend instance to use for command execution

    Returns:
        True if working directory is a git repository
    """
    result = backend.execute_command(command="git rev-parse --is-inside-work-tree")
    return result.exit_code == 0 and result.output.strip() == "true"


def get_git_status(backend: "ExecutionBackend") -> str:
    """
    Get git status information for the context using backend.

    Args:
        backend: ExecutionBackend instance to use for command execution

    Returns:
        Formatted git status string
    """
    # Get current branch
    branch_result = backend.execute_command(command="git rev-parse --abbrev-ref HEAD")
    branch = branch_result.output.strip() if branch_result.exit_code == 0 else "unknown"

    # Get remote main branch
    main_result = backend.execute_command(command="git remote show origin")
    main_branch = "main"
    if main_result.exit_code == 0:
        for line in main_result.output.splitlines():
            if "HEAD branch" in line:
                main_branch = line.split(":")[-1].strip()

    # Get status
    status_result = backend.execute_command(command="git status --porcelain")
    if status_result.exit_code == 0 and status_result.output.strip():
        status = status_result.output.strip()
    else:
        status = "(clean)"

    # Get recent commits
    log_result = backend.execute_command(command="git log --oneline --max-count=5")
    log_output = log_result.output.strip() if log_result.exit_code == 0 else ""

    git_status_text = f"""This is the git status at the start of the conversation. Note that this status is a snapshot in time, and will not update during the conversation.
Current branch: {branch}

Main branch (you will usually use this for PRs): {main_branch}

Status:
{status}

Recent commits:
{log_output}"""
    return git_status_text


def load_memory(backend: "ExecutionBackend") -> str:
    """
    Load memory from .gemini/GEMINI.md if it exists.

    Args:
        backend: ExecutionBackend instance to use for file operations

    Returns:
        Memory content or empty string if file doesn't exist
    """
    # Use file operations working directory (host path)
    working_dir = backend.get_working_directory()
    memory_file = working_dir / ".gemini" / "GEMINI.md"

    if backend.file_exists(path=memory_file):
        content = backend.read_file(file_path=memory_file).strip()
        if content:
            return content
    return ""


def get_system_prompt(backend: "ExecutionBackend", model_id: str) -> str:
    """
    Generate the system prompt with dynamic values filled in.

    Args:
        backend: ExecutionBackend instance to use for filesystem/command operations
        model_id: Model identifier to include in the prompt

    Returns:
        Formatted system prompt string
    """
    cwd = str(backend.get_working_directory())

    # The system message template is in the same directory as this file
    template_path = Path(__file__).parent / "system_message.txt"

    with open(template_path, "r") as f:
        system_message = f.read()

    # Get current date in format M/D/YYYY
    today = datetime.datetime.now().strftime("%-m/%-d/%Y")

    # Check if directory is a git repo
    is_repo = is_git_repo(backend=backend)

    # Get directory structure
    dir_structure = get_directory_structure(backend=backend, start_path=cwd)

    # Replace placeholders in the template with actual values
    system_message = system_message.replace("{working_directory}", cwd)
    system_message = system_message.replace("{is_git_repo}", "Yes" if is_repo else "No")
    system_message = system_message.replace("{platform}", platform.system().lower())
    system_message = system_message.replace("{date}", today)
    system_message = system_message.replace("{model}", model_id)

    # Replace the directory structure placeholder
    system_message = system_message.replace("{directory_structure}", dir_structure)

    # Add git status if it's a git repository
    if is_repo:
        git_status = get_git_status(backend=backend)
        system_message = system_message + f'\n<context name="gitStatus">{git_status}</context>\n'

    # Load and append memory from .gemini/GEMINI.md if it exists
    memory_content = load_memory(backend=backend)
    if memory_content:
        system_message = system_message + f'\n\n<context name="memory">User Memory (from .gemini/GEMINI.md):\n\n{memory_content}</context>\n'

    # TODO: check this
    return system_message
