# Gemini CLI file system tools

The Gemini CLI provides a comprehensive suite of tools for interacting with the
local file system. These tools allow the Gemini model to read from, write to,
list, search, and modify files and directories, all under your control and
typically with confirmation for sensitive operations.

**Note:** All file system tools operate within a `rootDirectory` (usually the
current working directory where you launched the CLI) for security. Paths that
you provide to these tools are generally expected to be absolute or are resolved
relative to this root directory.

## 1. `list_directory` (ReadFolder)

`list_directory` lists the names of files and subdirectories directly within a
specified directory path. It can optionally ignore entries matching provided
glob patterns.

- **Tool name:** `list_directory`
- **Display name:** ReadFolder
- **File:** `ls.ts`
- **Parameters:**
  - `path` (string, required): The absolute path to the directory to list.
  - `ignore` (array of strings, optional): A list of glob patterns to exclude
    from the listing (e.g., `["*.log", ".git"]`).
  - `respect_git_ignore` (boolean, optional): Whether to respect `.gitignore`
    patterns when listing files. Defaults to `true`.
- **Behavior:**
  - Returns a list of file and directory names.
  - Indicates whether each entry is a directory.
  - Sorts entries with directories first, then alphabetically.
- **Output (`llmContent`):** A string like:
  `Directory listing for /path/to/your/folder:\n[DIR] subfolder1\nfile1.txt\nfile2.png`
- **Confirmation:** No.

## 2. `read_file` (ReadFile)

`read_file` reads and returns the content of a specified file. This tool handles
text, images (PNG, JPG, GIF, WEBP, SVG, BMP), and PDF files. For text files, it
can read specific line ranges. Other binary file types are generally skipped.

- **Tool name:** `read_file`
- **Display name:** ReadFile
- **File:** `read-file.ts`
- **Parameters:**
  - `path` (string, required): The absolute path to the file to read.
  - `offset` (number, optional): For text files, the 0-based line number to
    start reading from. Requires `limit` to be set.
  - `limit` (number, optional): For text files, the maximum number of lines to
    read. If omitted, reads a default maximum (e.g., 2000 lines) or the entire
    file if feasible.
- **Behavior:**
  - For text files: Returns the content. If `offset` and `limit` are used,
    returns only that slice of lines. Indicates if content was truncated due to
    line limits or line length limits.
  - For image and PDF files: Returns the file content as a base64-encoded data
    structure suitable for model consumption.
  - For other binary files: Attempts to identify and skip them, returning a
    message indicating it's a generic binary file.
- **Output:** (`llmContent`):
  - For text files: The file content, potentially prefixed with a truncation
    message (e.g.,
    `[File content truncated: showing lines 1-100 of 500 total lines...]\nActual file content...`).
  - For image/PDF files: An object containing `inlineData` with `mimeType` and
    base64 `data` (e.g.,
    `{ inlineData: { mimeType: 'image/png', data: 'base64encodedstring' } }`).
  - For other binary files: A message like
    `Cannot display content of binary file: /path/to/data.bin`.
- **Confirmation:** No.

## 3. `write_file` (WriteFile)

`write_file` writes content to a specified file. If the file exists, it will be
overwritten. If the file doesn't exist, it (and any necessary parent
directories) will be created.

- **Tool name:** `write_file`
- **Display name:** WriteFile
- **File:** `write-file.ts`
- **Parameters:**
  - `file_path` (string, required): The absolute path to the file to write to.
  - `content` (string, required): The content to write into the file.
- **Behavior:**
  - Writes the provided `content` to the `file_path`.
  - Creates parent directories if they don't exist.
- **Output (`llmContent`):** A success message, e.g.,
  `Successfully overwrote file: /path/to/your/file.txt` or
  `Successfully created and wrote to new file: /path/to/new/file.txt`.
- **Confirmation:** Yes. Shows a diff of changes and asks for user approval
  before writing.

## 4. `glob` (FindFiles)

`glob` finds files matching specific glob patterns (e.g., `src/**/*.ts`,
`*.md`), returning absolute paths sorted by modification time (newest first).

- **Tool name:** `glob`
- **Display name:** FindFiles
- **File:** `glob.ts`
- **Parameters:**
  - `pattern` (string, required): The glob pattern to match against (e.g.,
    `"*.py"`, `"src/**/*.js"`).
  - `path` (string, optional): The absolute path to the directory to search
    within. If omitted, searches the tool's root directory.
  - `case_sensitive` (boolean, optional): Whether the search should be
    case-sensitive. Defaults to `false`.
  - `respect_git_ignore` (boolean, optional): Whether to respect .gitignore
    patterns when finding files. Defaults to `true`.
- **Behavior:**
  - Searches for files matching the glob pattern within the specified directory.
  - Returns a list of absolute paths, sorted with the most recently modified
    files first.
  - Ignores common nuisance directories like `node_modules` and `.git` by
    default.
- **Output (`llmContent`):** A message like:
  `Found 5 file(s) matching "*.ts" within src, sorted by modification time (newest first):\nsrc/file1.ts\nsrc/subdir/file2.ts...`
- **Confirmation:** No.

## 5. `search_file_content` (SearchText)

`search_file_content` searches for a regular expression pattern within the
content of files in a specified directory. Can filter files by a glob pattern.
Returns the lines containing matches, along with their file paths and line
numbers.

- **Tool name:** `search_file_content`
- **Display name:** SearchText
- **File:** `grep.ts`
- **Parameters:**
  - `pattern` (string, required): The regular expression (regex) to search for
    (e.g., `"function\s+myFunction"`).
  - `path` (string, optional): The absolute path to the directory to search
    within. Defaults to the current working directory.
  - `include` (string, optional): A glob pattern to filter which files are
    searched (e.g., `"*.js"`, `"src/**/*.{ts,tsx}"`). If omitted, searches most
    files (respecting common ignores).
- **Behavior:**
  - Uses `git grep` if available in a Git repository for speed; otherwise, falls
    back to system `grep` or a JavaScript-based search.
  - Returns a list of matching lines, each prefixed with its file path (relative
    to the search directory) and line number.
- **Output (`llmContent`):** A formatted string of matches, e.g.:
  ```
  Found 3 matches for pattern "myFunction" in path "." (filter: "*.ts"):
  ---
  File: src/utils.ts
  L15: export function myFunction() {
  L22:   myFunction.call();
  ---
  File: src/index.ts
  L5: import { myFunction } from './utils';
  ---
  ```
- **Confirmation:** No.

## 6. `replace` (Edit)

`replace` replaces text within a file. By default, replaces a single occurrence,
but can replace multiple occurrences when `expected_replacements` is specified.
This tool is designed for precise, targeted changes and requires significant
context around the `old_string` to ensure it modifies the correct location.

- **Tool name:** `replace`
- **Display name:** Edit
- **File:** `edit.ts`
- **Parameters:**
  - `file_path` (string, required): The absolute path to the file to modify.
  - `old_string` (string, required): The exact literal text to replace.

    **CRITICAL:** This string must uniquely identify the single instance to
    change. It should include at least 3 lines of context _before_ and _after_
    the target text, matching whitespace and indentation precisely. If
    `old_string` is empty, the tool attempts to create a new file at `file_path`
    with `new_string` as content.

  - `new_string` (string, required): The exact literal text to replace
    `old_string` with.
  - `expected_replacements` (number, optional): The number of occurrences to
    replace. Defaults to `1`.

- **Behavior:**
  - If `old_string` is empty and `file_path` does not exist, creates a new file
    with `new_string` as content.
  - If `old_string` is provided, it reads the `file_path` and attempts to find
    exactly one occurrence of `old_string`.
  - If one occurrence is found, it replaces it with `new_string`.
  - **Enhanced Reliability (Multi-Stage Edit Correction):** To significantly
    improve the success rate of edits, especially when the model-provided
    `old_string` might not be perfectly precise, the tool incorporates a
    multi-stage edit correction mechanism.
    - If the initial `old_string` isn't found or matches multiple locations, the
      tool can leverage the Gemini model to iteratively refine `old_string` (and
      potentially `new_string`).
    - This self-correction process attempts to identify the unique segment the
      model intended to modify, making the `replace` operation more robust even
      with slightly imperfect initial context.
- **Failure conditions:** Despite the correction mechanism, the tool will fail
  if:
  - `file_path` is not absolute or is outside the root directory.
  - `old_string` is not empty, but the `file_path` does not exist.
  - `old_string` is empty, but the `file_path` already exists.
  - `old_string` is not found in the file after attempts to correct it.
  - `old_string` is found multiple times, and the self-correction mechanism
    cannot resolve it to a single, unambiguous match.
- **Output (`llmContent`):**
  - On success:
    `Successfully modified file: /path/to/file.txt (1 replacements).` or
    `Created new file: /path/to/new_file.txt with provided content.`
  - On failure: An error message explaining the reason (e.g.,
    `Failed to edit, 0 occurrences found...`,
    `Failed to edit, expected 1 occurrences but found 2...`).
- **Confirmation:** Yes. Shows a diff of the proposed changes and asks for user
  approval before writing to the file.

These file system tools provide a foundation for the Gemini CLI to understand
and interact with your local project context.

# Shell Tool (`run_shell_command`)

This document describes the `run_shell_command` tool for the Gemini CLI.

## Description

Use `run_shell_command` to interact with the underlying system, run scripts, or
perform command-line operations. `run_shell_command` executes a given shell
command, including interactive commands that require user input (e.g., `vim`,
`git rebase -i`) if the `tools.shell.enableInteractiveShell` setting is set to
`true`.

On Windows, commands are executed with `powershell.exe -NoProfile -Command`
(unless you explicitly point `ComSpec` at another shell). On other platforms,
they are executed with `bash -c`.

### Arguments

`run_shell_command` takes the following arguments:

- `command` (string, required): The exact shell command to execute.
- `description` (string, optional): A brief description of the command's
  purpose, which will be shown to the user.
- `directory` (string, optional): The directory (relative to the project root)
  in which to execute the command. If not provided, the command runs in the
  project root.

## How to use `run_shell_command` with the Gemini CLI

When using `run_shell_command`, the command is executed as a subprocess.
`run_shell_command` can start background processes using `&`. The tool returns
detailed information about the execution, including:

- `Command`: The command that was executed.
- `Directory`: The directory where the command was run.
- `Stdout`: Output from the standard output stream.
- `Stderr`: Output from the standard error stream.
- `Error`: Any error message reported by the subprocess.
- `Exit Code`: The exit code of the command.
- `Signal`: The signal number if the command was terminated by a signal.
- `Background PIDs`: A list of PIDs for any background processes started.

Usage:

```
run_shell_command(command="Your commands.", description="Your description of the command.", directory="Your execution directory.")
```

## `run_shell_command` examples

List files in the current directory:

```
run_shell_command(command="ls -la")
```

Run a script in a specific directory:

```
run_shell_command(command="./my_script.sh", directory="scripts", description="Run my custom script")
```

Start a background server:

```
run_shell_command(command="npm run dev &", description="Start development server in background")
```

## Configuration

You can configure the behavior of the `run_shell_command` tool by modifying your
`settings.json` file or by using the `/settings` command in the Gemini CLI.

### Enabling Interactive Commands

To enable interactive commands, you need to set the
`tools.shell.enableInteractiveShell` setting to `true`. This will use `node-pty`
for shell command execution, which allows for interactive sessions. If
`node-pty` is not available, it will fall back to the `child_process`
implementation, which does not support interactive commands.

**Example `settings.json`:**

```json
{
  "tools": {
    "shell": {
      "enableInteractiveShell": true
    }
  }
}
```

### Showing Color in Output

To show color in the shell output, you need to set the `tools.shell.showColor`
setting to `true`. **Note: This setting only applies when
`tools.shell.enableInteractiveShell` is enabled.**

**Example `settings.json`:**

```json
{
  "tools": {
    "shell": {
      "showColor": true
    }
  }
}
```

### Setting the Pager

You can set a custom pager for the shell output by setting the
`tools.shell.pager` setting. The default pager is `cat`. **Note: This setting
only applies when `tools.shell.enableInteractiveShell` is enabled.**

**Example `settings.json`:**

```json
{
  "tools": {
    "shell": {
      "pager": "less"
    }
  }
}
```

## Interactive Commands

The `run_shell_command` tool now supports interactive commands by integrating a
pseudo-terminal (pty). This allows you to run commands that require real-time
user input, such as text editors (`vim`, `nano`), terminal-based UIs (`htop`),
and interactive version control operations (`git rebase -i`).

When an interactive command is running, you can send input to it from the Gemini
CLI. To focus on the interactive shell, press `ctrl+f`. The terminal output,
including complex TUIs, will be rendered correctly.

## Important notes

- **Security:** Be cautious when executing commands, especially those
  constructed from user input, to prevent security vulnerabilities.
- **Error handling:** Check the `Stderr`, `Error`, and `Exit Code` fields to
  determine if a command executed successfully.
- **Background processes:** When a command is run in the background with `&`,
  the tool will return immediately and the process will continue to run in the
  background. The `Background PIDs` field will contain the process ID of the
  background process.

## Environment Variables

When `run_shell_command` executes a command, it sets the `GEMINI_CLI=1`
environment variable in the subprocess's environment. This allows scripts or
tools to detect if they are being run from within the Gemini CLI.

## Command Restrictions

You can restrict the commands that can be executed by the `run_shell_command`
tool by using the `tools.core` and `tools.exclude` settings in your
configuration file.

- `tools.core`: To restrict `run_shell_command` to a specific set of commands,
  add entries to the `core` list under the `tools` category in the format
  `run_shell_command(<command>)`. For example,
  `"tools": {"core": ["run_shell_command(git)"]}` will only allow `git`
  commands. Including the generic `run_shell_command` acts as a wildcard,
  allowing any command not explicitly blocked.
- `tools.exclude`: To block specific commands, add entries to the `exclude` list
  under the `tools` category in the format `run_shell_command(<command>)`. For
  example, `"tools": {"exclude": ["run_shell_command(rm)"]}` will block `rm`
  commands.

The validation logic is designed to be secure and flexible:

1.  **Command Chaining Disabled**: The tool automatically splits commands
    chained with `&&`, `||`, or `;` and validates each part separately. If any
    part of the chain is disallowed, the entire command is blocked.
2.  **Prefix Matching**: The tool uses prefix matching. For example, if you
    allow `git`, you can run `git status` or `git log`.
3.  **Blocklist Precedence**: The `tools.exclude` list is always checked first.
    If a command matches a blocked prefix, it will be denied, even if it also
    matches an allowed prefix in `tools.core`.

### Command Restriction Examples

**Allow only specific command prefixes**

To allow only `git` and `npm` commands, and block all others:

```json
{
  "tools": {
    "core": ["run_shell_command(git)", "run_shell_command(npm)"]
  }
}
```

- `git status`: Allowed
- `npm install`: Allowed
- `ls -l`: Blocked

**Block specific command prefixes**

To block `rm` and allow all other commands:

```json
{
  "tools": {
    "core": ["run_shell_command"],
    "exclude": ["run_shell_command(rm)"]
  }
}
```

- `rm -rf /`: Blocked
- `git status`: Allowed
- `npm install`: Allowed

**Blocklist takes precedence**

If a command prefix is in both `tools.core` and `tools.exclude`, it will be
blocked.

```json
{
  "tools": {
    "core": ["run_shell_command(git)"],
    "exclude": ["run_shell_command(git push)"]
  }
}
```

- `git push origin main`: Blocked
- `git status`: Allowed

**Block all shell commands**

To block all shell commands, add the `run_shell_command` wildcard to
`tools.exclude`:

```json
{
  "tools": {
    "exclude": ["run_shell_command"]
  }
}
```

- `ls -l`: Blocked
- `any other command`: Blocked

## Security Note for `excludeTools`

Command-specific restrictions in `excludeTools` for `run_shell_command` are
based on simple string matching and can be easily bypassed. This feature is
**not a security mechanism** and should not be relied upon to safely execute
untrusted code. It is recommended to use `coreTools` to explicitly select
commands that can be executed.

# Multi File Read Tool (`read_many_files`)

This document describes the `read_many_files` tool for the Gemini CLI.

## Description

Use `read_many_files` to read content from multiple files specified by paths or
glob patterns. The behavior of this tool depends on the provided files:

- For text files, this tool concatenates their content into a single string.
- For image (e.g., PNG, JPEG), PDF, audio (MP3, WAV), and video (MP4, MOV)
  files, it reads and returns them as base64-encoded data, provided they are
  explicitly requested by name or extension.

`read_many_files` can be used to perform tasks such as getting an overview of a
codebase, finding where specific functionality is implemented, reviewing
documentation, or gathering context from multiple configuration files.

**Note:** `read_many_files` looks for files following the provided paths or glob
patterns. A directory path such as `"/docs"` will return an empty result; the
tool requires a pattern such as `"/docs/*"` or `"/docs/*.md"` to identify the
relevant files.

### Arguments

`read_many_files` takes the following arguments:

- `paths` (list[string], required): An array of glob patterns or paths relative
  to the tool's target directory (e.g., `["src/**/*.ts"]`,
  `["README.md", "docs/*", "assets/logo.png"]`).
- `exclude` (list[string], optional): Glob patterns for files/directories to
  exclude (e.g., `["**/*.log", "temp/"]`). These are added to default excludes
  if `useDefaultExcludes` is true.
- `include` (list[string], optional): Additional glob patterns to include. These
  are merged with `paths` (e.g., `["*.test.ts"]` to specifically add test files
  if they were broadly excluded, or `["images/*.jpg"]` to include specific image
  types).
- `recursive` (boolean, optional): Whether to search recursively. This is
  primarily controlled by `**` in glob patterns. Defaults to `true`.
- `useDefaultExcludes` (boolean, optional): Whether to apply a list of default
  exclusion patterns (e.g., `node_modules`, `.git`, non image/pdf binary files).
  Defaults to `true`.
- `respect_git_ignore` (boolean, optional): Whether to respect .gitignore
  patterns when finding files. Defaults to true.

## How to use `read_many_files` with the Gemini CLI

`read_many_files` searches for files matching the provided `paths` and `include`
patterns, while respecting `exclude` patterns and default excludes (if enabled).

- For text files: it reads the content of each matched file (attempting to skip
  binary files not explicitly requested as image/PDF) and concatenates it into a
  single string, with a separator `--- {filePath} ---` between the content of
  each file. Uses UTF-8 encoding by default.
- The tool inserts a `--- End of content ---` after the last file.
- For image and PDF files: if explicitly requested by name or extension (e.g.,
  `paths: ["logo.png"]` or `include: ["*.pdf"]`), the tool reads the file and
  returns its content as a base64 encoded string.
- The tool attempts to detect and skip other binary files (those not matching
  common image/PDF types or not explicitly requested) by checking for null bytes
  in their initial content.

Usage:

```
read_many_files(paths=["Your files or paths here."], include=["Additional files to include."], exclude=["Files to exclude."], recursive=False, useDefaultExcludes=false, respect_git_ignore=true)
```

## `read_many_files` examples

Read all TypeScript files in the `src` directory:

```
read_many_files(paths=["src/**/*.ts"])
```

Read the main README, all Markdown files in the `docs` directory, and a specific
logo image, excluding a specific file:

```
read_many_files(paths=["README.md", "docs/**/*.md", "assets/logo.png"], exclude=["docs/OLD_README.md"])
```

Read all JavaScript files but explicitly include test files and all JPEGs in an
`images` folder:

```
read_many_files(paths=["**/*.js"], include=["**/*.test.js", "images/**/*.jpg"], useDefaultExcludes=False)
```

## Important notes

- **Binary file handling:**
  - **Image/PDF/Audio/Video files:** The tool can read common image types (PNG,
    JPEG, etc.), PDF, audio (mp3, wav), and video (mp4, mov) files, returning
    them as base64 encoded data. These files _must_ be explicitly targeted by
    the `paths` or `include` patterns (e.g., by specifying the exact filename
    like `video.mp4` or a pattern like `*.mov`).
  - **Other binary files:** The tool attempts to detect and skip other types of
    binary files by examining their initial content for null bytes. The tool
    excludes these files from its output.
- **Performance:** Reading a very large number of files or very large individual
  files can be resource-intensive.
- **Path specificity:** Ensure paths and glob patterns are correctly specified
  relative to the tool's target directory. For image/PDF files, ensure the
  patterns are specific enough to include them.
- **Default excludes:** Be aware of the default exclusion patterns (like
  `node_modules`, `.git`) and use `useDefaultExcludes=False` if you need to
  override them, but do so cautiously.

# Memory Tool (`save_memory`)

This document describes the `save_memory` tool for the Gemini CLI.

## Description

Use `save_memory` to save and recall information across your Gemini CLI
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

Usage:

```
save_memory(fact="Your fact here.")
```

### `save_memory` examples

Remember a user preference:

```
save_memory(fact="My preferred programming language is Python.")
```

Store a project-specific detail:

```
save_memory(fact="The project I'm currently working on is called 'gemini-cli'.")
```

## Important notes

- **General usage:** This tool should be used for concise, important facts. It
  is not intended for storing large amounts of data or conversational history.
- **Memory file:** The memory file is a plain text Markdown file, so you can
  view and edit it manually if needed.


ok if you look at this code, 
'/Users/charlesazam/charloupioupiou/omniagents/src/omniagents/tools/backends/execution_backend.py''/Users/charlesazam/charloupioupiou/omniagents/src/omniagents/tools/backends/docker_backend.py''/Users/charlesazam/charloupioupiou/omniagents/src/omniagents/tools/backends/local_backend.py' you can see that I successfully wrote the backend to create tools for an AI coding agent, these tools can work in 3 kind of environments, locally, docker and e2b. What I want you to do is to write the tools from '/Users/charlesazam/charloupioupiou/omniagents/src/omniagents/tools/implementation/gemini_cli_tool.md' but in python. Write the tools here '/Users/charlesazam/charloupioupiou/omniagents/src/omniagents/tools/implementation' 

The tools must follow this structure, with the execute function and the metadata class so that they could be converted to smolagents, openai, pydantic-ai, autogen, etc. tools: 

from omniagents.tools.metadata import ToolMetadata
from omniagents.backends.execution_backend import ExecutionBackend
from omniagents.outputs.outputs import (
    FileInfo,
    FileListOutputModel,
    TextOutputModel,
    ErrorOutputModel,
    ToolOutputModel,
)

class LSToolCore:
    """
    Framework-agnostic directory listing tool.

    Extracted from smolcc/tools/ls_tool.py:21-149
    """

    # Metadata
    metadata = ToolMetadata(
        name="LS",
        description="Displays a directory's contents—files and sub-directories—at the location specified by **path**. The **path** argument must be an absolute path (it cannot be relative). You may optionally supply an **ignore** parameter: an array of glob patterns that should be skipped. If you already know the directories you want to scan, the Glob and Grep tools are generally the better choice.",
        inputs={
            "path": {
                "type": "string",
                "description": "The absolute path to the directory to list (must be absolute, not relative)"
            },
            "ignore": {
                "type": "array",
                "description": "List of glob patterns to ignore",
                "items": {"type": "string"},
                "nullable": True
            }
        },
        output_type="string"
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize LSToolCore with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    def execute(
        self,
        path: str,
        ignore: list[str] | None = None
    ) -> ToolOutputModel: