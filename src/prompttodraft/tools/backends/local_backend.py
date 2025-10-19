"""
Local execution backend.

This module implements the ExecutionBackend for local execution using
standard Python libraries (subprocess, os, glob, re, etc.).

Code extracted from smolcc tools with all primitive operations.
"""
import os
import re
import subprocess
import time
import signal
import glob as glob_module
import fnmatch
from pathlib import Path
from datetime import datetime

from prompttodraft.tools.backends.execution_backend import ExecutionBackend

# Constants
DEFAULT_TIMEOUT = 1800000  # 30 minutes in milliseconds
MAX_TIMEOUT = 600000  # 10 minutes in milliseconds
MAX_OUTPUT_CHARS = 30000
MAX_LINES = 2000
MAX_LINE_LENGTH = 2000
TRUNCATED_LINE_SUFFIX = "... (line truncated)"


class LocalBackend(ExecutionBackend):
    """Local execution backend using standard Python operations."""

    def __init__(self):
        """Initialize the local backend with a persistent shell."""
        self.shell_process = None
        self.output_marker = None
        self._initialize_shell()

    def _initialize_shell(self) -> None:
        """Start a persistent shell session (from bash_tool.py:51-65)."""
        # Create a persistent bash process
        self.shell_process = subprocess.Popen(
            ["/bin/bash"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Set up a unique marker for command output separation
        self.output_marker = f"__COMMAND_OUTPUT_MARKER_{int(time.time())}_"

    def execute_command(
        self,
        command: str,
        timeout: int | None = None
    ) -> tuple[str, bool]:
        """
        Execute a bash command (from bash_tool.py:67-106).

        Args:
            command: The bash command to execute
            timeout: Optional timeout in milliseconds

        Returns:
            Tuple of (command output, is_error)
        """
        # Check if shell process is alive, restart if needed
        if self.shell_process is None or self.shell_process.poll() is not None:
            self._initialize_shell()

        # Set timeout
        if timeout is None:
            timeout_ms = DEFAULT_TIMEOUT
        else:
            timeout_ms = min(int(timeout), MAX_TIMEOUT)
        timeout_sec = timeout_ms / 1000

        # Execute command with timeout
        output, is_error = self._execute_command_with_timeout(command=command, timeout_sec=timeout_sec)
        return output, is_error

    def _execute_command_with_timeout(
        self,
        command: str,
        timeout_sec: float
    ) -> tuple[str, bool]:
        """
        Execute a command with timeout (from bash_tool.py:108-181).

        Args:
            command: The command to execute
            timeout_sec: Timeout in seconds

        Returns:
            Tuple of (command output, is_error)
        """
        # Add echo commands to mark the beginning and end of output
        full_command = f"{command}; echo {self.output_marker}\n"

        # Send the command to the shell process
        self.shell_process.stdin.write(full_command)
        self.shell_process.stdin.flush()

        # Read output until we get to our marker
        stdout_lines = []
        stderr_lines = []
        start_time = time.time()

        while True:
            # Check if we've exceeded the timeout
            if time.time() - start_time > timeout_sec:
                self._kill_current_command()
                return f"Command timed out after {timeout_sec} seconds", True

            # Try to read a line from stdout or stderr
            output_line, is_stderr = self._read_line_nonblocking_with_source()
            if output_line is None:
                # No data available, sleep a bit and try again
                time.sleep(0.1)
                continue

            # Check if we've reached our marker
            if self.output_marker in output_line:
                break

            # Add the line to our output (separate stdout and stderr)
            if is_stderr:
                stderr_lines.append(output_line)
            else:
                stdout_lines.append(output_line)

            # Check if we've exceeded the max output size
            total_length = sum(len(line) for line in stdout_lines) + sum(len(line) for line in stderr_lines)
            if total_length > MAX_OUTPUT_CHARS:
                # Truncate in the middle
                stdout_text = "".join(stdout_lines)
                stdout_lines = [self._format_truncated_output(content=stdout_text)]
                # Continue reading until we find the marker, but don't save more output
                while self.output_marker not in self._read_line_blocking():
                    pass
                break

        # Combine all output lines
        stdout = "".join(stdout_lines)
        stderr = "".join(stderr_lines)

        # Remove trailing newline if present
        stdout = stdout.rstrip('\n')

        # If there's stderr content, combine them appropriately
        if stderr:
            return self._format_result_with_stderr(stdout=stdout, stderr=stderr), True

        return stdout, False

    def _read_line_nonblocking_with_source(self) -> tuple[str | None, bool]:
        """
        Try to read a line from stdout or stderr without blocking (from bash_tool.py:183-203).

        Returns:
            A tuple of (line of output or None, is_stderr)
        """
        # Check if there's data available on stdout
        if self.shell_process.stdout.readable():
            line = self.shell_process.stdout.readline()
            if line:
                return line, False

        # Check if there's data available on stderr
        if self.shell_process.stderr.readable():
            line = self.shell_process.stderr.readline()
            if line:
                return line, True

        return None, False

    def _read_line_blocking(self) -> str:
        """
        Read a line from stdout or stderr, blocking until data is available (from bash_tool.py:205-215).

        Returns:
            A line of output
        """
        line = self.shell_process.stdout.readline()
        if not line:
            line = self.shell_process.stderr.readline()
        return line

    def _kill_current_command(self) -> None:
        """
        Kill the currently running command in the shell process (from bash_tool.py:217-229).
        """
        # Send SIGINT to the shell process to interrupt the current command
        try:
            self.shell_process.send_signal(signal.SIGINT)
            time.sleep(0.5)  # Give the shell a moment to process the signal
        except Exception:
            # If sending SIGINT fails, try to restart the shell
            self._initialize_shell()

    def _format_truncated_output(self, content: str) -> str:
        """
        Format large output with truncation in the middle (from bash_tool.py:374-396).

        Args:
            content: The content to truncate

        Returns:
            Truncated content with a message in the middle
        """
        if len(content) <= MAX_OUTPUT_CHARS:
            return content

        half_length = MAX_OUTPUT_CHARS // 2
        start = content[:half_length]
        end = content[-half_length:]

        # Count how many lines were truncated in the middle
        middle_content = content[half_length:-half_length]
        truncated_lines = middle_content.count('\n')

        truncated = f"{start}\n\n... [{truncated_lines} lines truncated] ...\n\n{end}"
        return truncated

    def _format_result_with_stderr(self, stdout: str, stderr: str) -> str:
        """
        Format the result with both stdout and stderr (from bash_tool.py:398-419).

        Args:
            stdout: Standard output content
            stderr: Standard error content

        Returns:
            Combined output string
        """
        # Trim whitespace from both
        stdout_trimmed = stdout.strip()
        stderr_trimmed = stderr.strip()

        # If both have content, combine them with a newline
        if stdout_trimmed and stderr_trimmed:
            return f"{stdout_trimmed}\n{stderr_trimmed}"
        elif stderr_trimmed:
            return stderr_trimmed
        else:
            return stdout_trimmed

    def read_file(
        self,
        file_path: str,
        offset: int = 0,
        limit: int | None = None
    ) -> str:
        """
        Read a file from the filesystem (from view_tool.py:117-222).

        Args:
            file_path: Absolute path to the file
            offset: Line number to start reading from (0-indexed)
            limit: Maximum number of lines to read

        Returns:
            File contents with line numbers
        """
        # Setup limits
        if limit is None:
            limit = MAX_LINES
        else:
            limit = min(int(limit), MAX_LINES)

        # Ensure offset is valid
        offset = max(0, int(offset))

        result = ""
        total_length = 0
        line_count = 0
        displayed_lines = 0
        truncated = False

        # Try different encodings if needed
        encodings = ['utf-8', 'latin-1', 'cp1252']
        file_content = None

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    file_content = f.readlines()
                break
            except UnicodeDecodeError:
                continue

        # If we couldn't read with any encoding, try as binary
        if file_content is None:
            raise ValueError("This file contains binary content that cannot be displayed as text.")

        line_count = len(file_content)
        # Prepare the formatted output with line numbers
        for i, line in enumerate(file_content):

            # Skip lines before offset
            if i < offset:
                continue

            # Stop after limit lines
            if displayed_lines >= limit:
                truncated = True
                break

            # Truncate lines that are too long
            if len(line) > MAX_LINE_LENGTH:
                line = line[:MAX_LINE_LENGTH] + TRUNCATED_LINE_SUFFIX

            # Add line with line number
            line_number = i + 1  # i is 0-indexed but we want to show 1-indexed line numbers
            display_line = f"{line_number:6d}\t{line}"
            result += display_line if display_line.endswith('\n') else display_line + '\n'
            displayed_lines += 1
            total_length += len(display_line)

        # Add a message if the file was truncated
        if truncated:
            result += f"\n(Result truncated - total length: {total_length} characters)\n"

        return result

    def write_file(
        self,
        file_path: str,
        content: str
    ) -> None:
        """
        Write content to a file (from replace_tool.py:69-86).

        Args:
            file_path: Absolute path to the file
            content: Content to write

        Raises:
            IOError: If file cannot be written
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def list_directory(
        self,
        path: str
    ) -> list[dict[str, str | int | bool]]:
        """
        List contents of a directory (from ls_tool.py:61-117).

        Args:
            path: Absolute path to the directory

        Returns:
            List of file info dictionaries
        """
        file_info = []

        # Get all entries in the directory
        entries = os.listdir(path)

        # Sort entries alphabetically
        entries.sort()

        # Process each entry
        for entry in entries:
            entry_path = os.path.join(path, entry)

            try:
                # Get file stats
                stats = os.stat(entry_path)
                is_dir = os.path.isdir(entry_path)

                # Create file info dictionary
                info = {
                    "name": entry,
                    "is_dir": is_dir,
                    "size": stats.st_size,
                    "modified": int(stats.st_mtime),
                    "modified_date": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "path": entry_path
                }

                file_info.append(info)

                if len(file_info) >= 1000:  # MAX_FILES
                    break
            except (PermissionError, FileNotFoundError):
                # Skip entries we can't access
                continue

        # Sort the list - directories first, then files alphabetically
        file_info.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

        return file_info

    def file_exists(
        self,
        path: str
    ) -> bool:
        """
        Check if a file or directory exists.

        Args:
            path: Absolute path to check

        Returns:
            True if exists, False otherwise
        """
        return os.path.exists(path)

    def is_file(
        self,
        path: str
    ) -> bool:
        """
        Check if a path is a file.

        Args:
            path: Absolute path to check

        Returns:
            True if path is a file, False otherwise
        """
        return os.path.isfile(path)

    def is_directory(
        self,
        path: str
    ) -> bool:
        """
        Check if a path is a directory.

        Args:
            path: Absolute path to check

        Returns:
            True if path is a directory, False otherwise
        """
        return os.path.isdir(path)

    def glob_files(
        self,
        pattern: str,
        path: str | None = None
    ) -> list[str]:
        """
        Find files matching a glob pattern (from glob_tool.py:89-156).

        Args:
            pattern: Glob pattern (e.g., "**/*.py")
            path: Base directory to search (defaults to current working directory)

        Returns:
            List of matching file paths
        """
        search_path = path or os.getcwd()

        # Handle brace expansion for patterns like "**/*.{js,ts}"
        if "{" in pattern and "}" in pattern:
            before_brace, rest = pattern.split("{", 1)
            options, after_brace = rest.split("}", 1)
            options_list = options.split(",")
            patterns = [f"{before_brace}{opt}{after_brace}" for opt in options_list]
        elif "?(" in pattern:
            # For "**/*.ts?(x)" pattern, we'll look for both .ts and .tsx files
            if pattern.endswith("?(x)"):
                base_pattern = pattern[:-4]  # Remove "?(x)"
                patterns = [f"{base_pattern}", f"{base_pattern}x"]
            else:
                # For other ?() patterns, split into multiple patterns
                parts = pattern.split("?(")
                if len(parts) == 2 and parts[1].endswith(")"):
                    optional_part = parts[1][:-1]  # Remove trailing ")"
                    patterns = [f"{parts[0]}", f"{parts[0]}{optional_part}"]
                else:
                    patterns = [pattern]
        else:
            patterns = [pattern]

        all_matches = []
        for p in patterns:
            # Handle "**" recursive patterns correctly
            if "**" in p:
                # Use glob.glob with recursive=True for ** patterns
                matches = glob_module.glob(
                    os.path.join(search_path, p),
                    recursive=True
                )
                for match in matches:
                    if os.path.isfile(match):  # Only include files, not directories
                        all_matches.append(match)
            else:
                # Use standard pathlib.glob for non-recursive patterns
                base_path = Path(search_path)
                all_matches.extend([str(path) for path in base_path.glob(p) if path.is_file()])

        # Remove duplicates that might have been added from multiple patterns
        all_matches = list(set(all_matches))

        # Sort by modification time (oldest first)
        all_matches.sort(key=lambda p: os.path.getmtime(p))

        return all_matches

    def search_files(
        self,
        pattern: str,
        include: str | None = None,
        path: str | None = None
    ) -> list[dict[str, str | int | list]]:
        """
        Search file contents using regex (from grep_tool.py:44-110).

        Args:
            pattern: Regular expression pattern
            include: File pattern to include (e.g., "*.py")
            path: Base directory to search

        Returns:
            List of match info dictionaries
        """
        search_path = path or os.getcwd()

        # Compile the regex pattern
        regex = re.compile(pattern)

        # Find files to search
        all_files = self._find_files_for_search(base_path=search_path, include=include)

        # Search for pattern in files and get matches
        file_matches = []
        for file_path in all_files:
            try:
                file_match_info = self._get_file_matches(file_path=file_path, regex=regex)
                if file_match_info:
                    file_matches.append(file_match_info)
            except Exception:
                # Silently skip files that can't be read
                continue

        # Sort results by modification time (newest first)
        file_matches.sort(key=lambda f: os.path.getmtime(f['path']), reverse=True)

        return file_matches

    def _find_files_for_search(
        self,
        base_path: str,
        include: str | None = None
    ) -> list[str]:
        """
        Find files to search based on include pattern (from grep_tool.py:112-181).

        Args:
            base_path: The base directory to search in
            include: File pattern to include (e.g., "*.js")

        Returns:
            List of file paths to search
        """
        all_files = []

        # If include pattern is specified
        if include:
            # Handle glob patterns with multiple extensions like "*.{js,ts}"
            if "{" in include and "}" in include:
                # Extract patterns from the brace expression
                prefix = include.split("{")[0]
                extensions = include.split("{")[1].split("}")[0].split(",")
                patterns = [f"{prefix}{ext}" for ext in extensions]

                for pattern in patterns:
                    # Handle "**/" recursive patterns
                    if "**" in pattern:
                        full_pattern = os.path.join(base_path, pattern)
                        matches = glob_module.glob(full_pattern, recursive=True)
                        file_matches = [m for m in matches if os.path.isfile(m)]
                        all_files.extend(file_matches)
                    else:
                        # Use non-recursive glob for regular patterns
                        for root, _, files in os.walk(base_path):
                            matched_files = []
                            for file in files:
                                if fnmatch.fnmatch(file, pattern.split("/")[-1]):
                                    matched_files.append(os.path.join(root, file))
                            all_files.extend(matched_files)
            else:
                # Handle "**/" recursive patterns
                if "**" in include:
                    full_pattern = os.path.join(base_path, include)
                    matches = glob_module.glob(full_pattern, recursive=True)
                    file_matches = [m for m in matches if os.path.isfile(m)]
                    all_files.extend(file_matches)
                else:
                    # Use non-recursive glob for regular patterns
                    for root, _, files in os.walk(base_path):
                        matched_files = []
                        for file in files:
                            if fnmatch.fnmatch(file, include.split("/")[-1]):
                                matched_files.append(os.path.join(root, file))
                        all_files.extend(matched_files)
        else:
            # If no include pattern, search all regular files
            for root, _, files in os.walk(base_path):
                file_paths = []
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.isfile(file_path):
                        file_paths.append(file_path)
                all_files.extend(file_paths)

        # Remove duplicate files
        unique_files = list(set(all_files))

        # Limit to first 1000 files for performance reasons
        if len(unique_files) > 1000:
            unique_files = unique_files[:1000]

        return unique_files

    def _get_file_matches(
        self,
        file_path: str,
        regex: re.Pattern
    ) -> dict[str, str | int | list] | None:
        """
        Get matches for a regex pattern in a file with context (from grep_tool.py:183-250).

        Args:
            file_path: Path to the file to search
            regex: Compiled regex pattern

        Returns:
            Dictionary with match information or None if no matches
        """
        # Skip binary files
        if self._is_binary_file(file_path=file_path):
            return None

        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252']

        file_content = None
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    file_content = f.read()
                break  # Successfully read file, break the encoding loop
            except UnicodeDecodeError:
                continue
            except Exception:
                # Skip files that can't be read
                return None

        if file_content is None:
            return None

        # Get all matches with context
        lines = file_content.split('\n')
        matches = []

        for i, line in enumerate(lines):
            for match in regex.finditer(line):
                # Get context (3 lines before and after)
                start_line = max(0, i - 3)
                end_line = min(len(lines) - 1, i + 3)

                # Extract the match and context
                context_lines = lines[start_line:end_line + 1]
                match_line_index = i - start_line

                matches.append({
                    'line_number': i + 1,  # 1-indexed line number
                    'context': context_lines,
                    'match_line_index': match_line_index,
                    'match_span': match.span(),
                    'match_text': match.group(0)
                })

        if not matches:
            return None

        # Get file extension for syntax highlighting
        _, ext = os.path.splitext(file_path)

        return {
            'path': file_path,
            'language': ext.lstrip('.') if ext else 'text',
            'matches': matches,
            'modified': os.path.getmtime(file_path)
        }

    def _is_binary_file(self, file_path: str) -> bool:
        """
        Check if a file appears to be binary (from grep_tool.py:341-405).

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file appears to be binary, False otherwise
        """
        # Check file extension for common binary types
        binary_extensions = [
            '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff',
            '.exe', '.dll', '.so', '.dylib', '.zip', '.tar', '.gz',
            '.rar', '.7z', '.mp3', '.mp4', '.avi', '.mov', '.wmv'
        ]

        if any(file_path.lower().endswith(ext) for ext in binary_extensions):
            return True

        # Try to read as text first
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1024)
                return False  # If we can read it as text, it's not binary
        except UnicodeDecodeError:
            pass
        except Exception:
            return True

        # More robust binary check
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)

                # Empty file is not binary
                if not chunk:
                    return False

                # Detect null bytes - strong indicator of binary content
                if b'\x00' in chunk:
                    return True

                # Count control characters
                control_chars = sum(1 for c in chunk if c < 9 or (c > 13 and c < 32) or c > 126)
                ratio = control_chars / len(chunk)

                # If more than 10% are control chars, likely binary
                if ratio > 0.1:
                    return True

                return False

        except Exception:
            return True

        return False

    def get_file_stats(
        self,
        path: str
    ) -> dict[str, str | int]:
        """
        Get file statistics.

        Args:
            path: Absolute path to the file

        Returns:
            Dictionary with file stats
        """
        stats = os.stat(path)
        return {
            "size": stats.st_size,
            "modified": int(stats.st_mtime),
            "modified_date": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "is_dir": os.path.isdir(path),
            "is_file": os.path.isfile(path)
        }

    def __del__(self):
        """Clean up the shell process when the backend is destroyed."""
        if self.shell_process:
            try:
                self.shell_process.terminate()
                self.shell_process.wait(timeout=1)
            except Exception:
                pass
