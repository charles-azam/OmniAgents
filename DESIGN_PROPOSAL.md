# Multi-Language Support Design Proposal

## Overview
This document outlines the design for extending prompttodraft to support multiple programming languages while maintaining opinionated tooling choices per language.

## Current State
- **Initializers**: Already exist (PythonInitializer, TypeScriptInitializer, NoOpInitializer)
- **Hardcoded Dependencies**: Docker image, environment variables, execute_uv method, UV tool

## Architecture: Initializer-Driven Configuration

### Core Principle
The `ProjectInitializer` should be the single source of truth for all language-specific configuration. Backends should query the initializer for language-specific settings.

---

## Proposed Changes

### 1. Extend ProjectInitializer Base Class

**File**: `src/prompttodraft/initializers/base.py`

Add methods to provide language-specific configuration:

```python
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prompttodraft.tools.base_tool import CoreTool

class ProjectInitializer(ABC):
    """Base class for project initialization."""

    # ... existing methods ...

    @abstractmethod
    def get_docker_image(self) -> str:
        """
        Get the Docker image for this language.

        Returns:
            Docker image name with tag

        Examples:
            - Python: "ghcr.io/astral-sh/uv:debian"
            - TypeScript: "node:20-slim"
            - Rust: "rust:1.75-slim"
        """
        pass

    @abstractmethod
    def get_docker_env_vars(self) -> dict[str, str]:
        """
        Get Docker environment variables for this language.

        Returns:
            Dictionary of environment variables to set in container

        Examples:
            - Python (UV): {"UV_CACHE_DIR": "/workspace/.cache/uv", ...}
            - Node: {"NPM_CONFIG_CACHE": "/workspace/.npm", ...}
        """
        pass

    def get_package_manager_commands(self) -> dict[str, str]:
        """
        Get common package manager command patterns.

        Returns:
            Dictionary mapping operation to command template

        Examples:
            - Python: {
                "install": "uv add {package}",
                "run": "uv run {script}",
                "test": "uv run pytest {path}"
              }
            - TypeScript: {
                "install": "npm install {package}",
                "run": "npm run {script}",
                "test": "npm test {path}"
              }
        """
        return {}

    @property
    def language_name(self) -> str:
        """
        Get the human-readable language name.

        Returns:
            Language name (e.g., "Python", "TypeScript", "Rust")
        """
        return "Unknown"
```

---

### 2. Update DockerBackend to Use Initializer Config

**File**: `src/prompttodraft/backends/docker_backend.py`

Remove hardcoded values and query initializer:

```python
# REMOVE these constants:
# DOCKER_IMAGE = "ghcr.io/astral-sh/uv:debian"  # DELETE

class DockerBackend(ExecutionBackend):
    def start(self) -> None:
        # ... existing code ...

        # Get Docker image from initializer instead of constant
        docker_image = self.initializer.get_docker_image()

        # Pull image if not present
        try:
            self._client.images.get(docker_image)
        except docker.errors.ImageNotFound:
            self._client.images.pull(docker_image)

        # Get environment variables from initializer
        env_vars = self.initializer.get_docker_env_vars()

        # Create container with language-specific config
        container_kwargs = {
            "image": docker_image,
            "name": self._container_name,
            "command": "sleep infinity",
            "volumes": {str(self._project_path): {"bind": CONTAINER_WORKSPACE, "mode": "rw"}},
            "working_dir": CONTAINER_WORKSPACE,
            "detach": True,
            "remove": False,
            "environment": env_vars,  # Use initializer's env vars
        }

        # ... rest of existing code ...
```

---

### 3. Remove execute_uv from Base ExecutionBackend

**File**: `src/prompttodraft/backends/execution_backend.py`

The `execute_uv` method should be removed from the base class and replaced with a more generic approach:

**Option A: Generic Package Manager Method**
```python
class ExecutionBackend(ABC):
    def execute_package_manager(
        self,
        operation: str,
        args: str = "",
        timeout: int | None = None
    ) -> CommandResult:
        """
        Execute a package manager command based on the initializer's configuration.

        Args:
            operation: Operation name (e.g., "install", "run", "test")
            args: Arguments for the operation
            timeout: Optional timeout in milliseconds

        Returns:
            CommandResult with output and exit_code

        Examples:
            - backend.execute_package_manager("install", "requests")
            - backend.execute_package_manager("run", "main.py")
        """
        commands = self.initializer.get_package_manager_commands()
        if operation not in commands:
            return CommandResult(
                output=f"Operation '{operation}' not supported by {self.initializer.language_name}",
                exit_code=1
            )

        command_template = commands[operation]
        full_command = command_template.format(args=args) if "{args}" in command_template else f"{command_template} {args}"

        return self.execute_command(command=full_command, timeout=timeout)
```

**Option B: Remove from Base Class Entirely**
- Remove `execute_uv()` from ExecutionBackend
- Let tools handle package manager operations directly
- Use `execute_command()` with commands from initializer

**Recommendation**: Option B is cleaner - keep the base ExecutionBackend minimal and language-agnostic.

---

### 4. Create Generic PackageManager Tool

**File**: `src/prompttodraft/tools/package_manager_tool.py` (NEW)

Replace the UV-specific tool with a generic one:

```python
"""
Generic package manager tool that adapts to the project's language.
"""
from prompttodraft.tools.base_tool import CoreTool
from prompttodraft.tools.metadata import ToolMetadata
from prompttodraft.outputs.outputs import TextOutputModel, ToolOutputModel


class PackageManagerTool(CoreTool):
    """
    Framework-agnostic package manager execution tool.

    Automatically adapts to the project's language (Python/UV, TypeScript/npm, etc.)
    based on the initializer configuration.
    """

    metadata = ToolMetadata(
        name="package_manager",
        description="Executes package manager commands for the current project language. Adapts to Python (uv), TypeScript (npm), or other configured languages. Use this to install packages, run scripts, execute tests, or perform other language-specific operations.",
        inputs={
            "operation": {
                "type": "string",
                "description": "The operation to perform (e.g., 'install', 'run', 'test', 'add', 'remove')",
                "nullable": False,
            },
            "args": {
                "type": "string",
                "description": "Arguments for the operation (e.g., package name, script name, test path)",
                "nullable": False,
            },
            "description": {
                "type": "string",
                "description": "Optional: A brief description of what this command does",
                "nullable": True,
            },
        },
        output_type="string",
    )

    def execute(
        self,
        operation: str,
        args: str,
        description: str | None = None,
    ) -> ToolOutputModel:
        """
        Execute a package manager operation.

        Args:
            operation: Operation name (install, run, test, etc.)
            args: Arguments for the operation
            description: Optional description

        Returns:
            TextOutputModel with command output
        """
        # Get command template from initializer
        commands = self.backend.initializer.get_package_manager_commands()

        if operation not in commands:
            available_ops = ", ".join(commands.keys())
            return TextOutputModel(
                content=f"Error: Operation '{operation}' not supported by {self.backend.initializer.language_name}.\nAvailable operations: {available_ops}",
                metadata={"error": "unsupported_operation"}
            )

        # Build the command
        command_template = commands[operation]

        # Handle different template formats
        if "{package}" in command_template:
            command = command_template.format(package=args)
        elif "{script}" in command_template:
            command = command_template.format(script=args)
        elif "{path}" in command_template:
            command = command_template.format(path=args)
        else:
            command = f"{command_template} {args}"

        # Execute the command
        result = self.backend.execute_command(
            command=command,
            timeout=300000,  # 5 minutes
        )

        # Format output
        output_lines = []

        if description:
            output_lines.append(f"Description: {description}")

        output_lines.append(f"Language: {self.backend.initializer.language_name}")
        output_lines.append(f"Operation: {operation}")
        output_lines.append(f"Command: {command}")
        output_lines.append(f"Working Directory: {self.backend.get_working_directory()}")
        output_lines.append("")

        if result.output:
            output_lines.append("Output:")
            output_lines.append(result.output)
            output_lines.append("")

        output_lines.append(f"Exit Code: {result.exit_code}")

        if result.exit_code != 0:
            output_lines.append("")
            output_lines.append(f"Warning: Command exited with non-zero status code {result.exit_code}")

        return TextOutputModel(
            content="\n".join(output_lines),
            metadata={"exit_code": result.exit_code, "command": command}
        )
```

---

### 5. Update Language-Specific Initializers

**File**: `src/prompttodraft/initializers/python_initializer.py`

```python
class PythonInitializer(ProjectInitializer):
    # ... existing methods ...

    def get_docker_image(self) -> str:
        return "ghcr.io/astral-sh/uv:debian"

    def get_docker_env_vars(self) -> dict[str, str]:
        return {
            "HOME": "/workspace",  # Will be replaced with CONTAINER_WORKSPACE constant
            "UV_CACHE_DIR": "/workspace/.cache/uv",
            "UV_TOOL_DIR": "/workspace/.local/bin",
            "UV_PYTHON_INSTALL_DIR": "/workspace/.local/share/uv/python",
        }

    def get_package_manager_commands(self) -> dict[str, str]:
        return {
            "run": "uv run {script}",
            "add": "uv add {package}",
            "remove": "uv remove {package}",
            "sync": "uv sync",
            "test": "uv run pytest {path}",
            "install": "uv add {package}",  # Alias for add
        }

    @property
    def language_name(self) -> str:
        return "Python"
```

**File**: `src/prompttodraft/initializers/typescript_initializer.py`

```python
class TypeScriptInitializer(ProjectInitializer):
    # ... existing methods ...

    def get_docker_image(self) -> str:
        return "node:20-slim"

    def get_docker_env_vars(self) -> dict[str, str]:
        return {
            "NPM_CONFIG_CACHE": "/workspace/.npm",
            "NODE_PATH": "/workspace/node_modules",
        }

    def get_package_manager_commands(self) -> dict[str, str]:
        return {
            "run": "npm run {script}",
            "install": "npm install {package}",
            "uninstall": "npm uninstall {package}",
            "test": "npm test -- {path}",
            "build": "npm run build",
        }

    @property
    def language_name(self) -> str:
        return "TypeScript"
```

**File**: `src/prompttodraft/initializers/noop_initializer.py`

```python
class NoOpInitializer(ProjectInitializer):
    # ... existing methods ...

    def get_docker_image(self) -> str:
        return "ubuntu:22.04"  # Generic base image

    def get_docker_env_vars(self) -> dict[str, str]:
        return {}

    def get_package_manager_commands(self) -> dict[str, str]:
        return {}

    @property
    def language_name(self) -> str:
        return "Generic"
```

---

## Migration Strategy

### Phase 1: Add New Abstractions (Non-Breaking)
1. Add new methods to `ProjectInitializer` base class
2. Implement methods in existing initializers
3. Create `PackageManagerTool`

### Phase 2: Update Backends (Breaking Changes)
1. Modify `DockerBackend` to use `initializer.get_docker_image()`
2. Modify `DockerBackend` to use `initializer.get_docker_env_vars()`
3. Remove `execute_uv()` from `ExecutionBackend`

### Phase 3: Update Tools and Examples
1. Deprecate `UVTool` (or keep as legacy for Python-only projects)
2. Update example code to use new patterns
3. Update tests

---

## Adding New Languages

With this architecture, adding a new language is straightforward:

### Example: Rust Support

```python
# src/prompttodraft/initializers/rust_initializer.py
class RustInitializer(ProjectInitializer):
    def is_initialized(self) -> bool:
        cargo_toml_path = f"{self.working_dir}/Cargo.toml"
        return self.backend.file_exists(path=cargo_toml_path) is not None

    def initialize(self) -> None:
        # Create README.md
        readme_path = f"{self.working_dir}/README.md"
        if self.backend.file_exists(path=readme_path) is None:
            self.backend.write_file(file_path=readme_path, content="# Rust Project\n")

        # Create .gitignore with Rust patterns
        gitignore_path = f"{self.working_dir}/.gitignore"
        if self.backend.file_exists(path=gitignore_path) is None:
            gitignore_patterns = [
                "target/",
                "Cargo.lock",
                "*.pdb",
            ]
            self.backend.write_file(
                file_path=gitignore_path,
                content="\n".join(gitignore_patterns) + "\n"
            )

        # Run cargo init if Cargo.toml doesn't exist
        cargo_toml_path = f"{self.working_dir}/Cargo.toml"
        if self.backend.file_exists(path=cargo_toml_path) is None:
            result = self.backend.execute_command(
                command=f'cd "{self.working_dir}" && cargo init',
                timeout=120000
            )
            if result.exit_code != 0:
                raise RuntimeError(f"cargo init failed: {result.output}")

    def get_docker_image(self) -> str:
        return "rust:1.75-slim"

    def get_docker_env_vars(self) -> dict[str, str]:
        return {
            "CARGO_HOME": "/workspace/.cargo",
        }

    def get_package_manager_commands(self) -> dict[str, str]:
        return {
            "run": "cargo run --bin {script}",
            "build": "cargo build",
            "test": "cargo test {path}",
            "add": "cargo add {package}",
            "remove": "cargo remove {package}",
        }

    @property
    def language_name(self) -> str:
        return "Rust"
```

---

## Benefits of This Approach

1. **Single Source of Truth**: All language-specific configuration lives in one place (the initializer)
2. **Open/Closed Principle**: Easy to add new languages without modifying existing code
3. **Opinionated Tools**: Each language can specify its preferred tooling (UV for Python, npm for TypeScript, cargo for Rust)
4. **Backend Agnostic**: Works with Docker, Local, E2B backends without changes
5. **Tool Reusability**: The `PackageManagerTool` works for all languages
6. **Clear Separation**: Backends handle execution, initializers handle language specifics

---

## Alternative Approaches Considered

### 1. Language Detection
**Approach**: Auto-detect language from files (package.json, pyproject.toml, Cargo.toml)
**Rejected**: Less explicit, harder to handle polyglot projects

### 2. Separate Backend Classes per Language
**Approach**: PythonDockerBackend, TypeScriptDockerBackend, etc.
**Rejected**: Causes combinatorial explosion (3 backends × N languages)

### 3. Configuration Files
**Approach**: Use YAML/JSON config files for language settings
**Rejected**: Less type-safe, harder to extend programmatically

---

## Open Questions

1. **Polyglot Projects**: How to handle projects with multiple languages?
   - **Proposal**: Allow composite initializers or multiple initializers per backend

2. **Tool Discovery**: Should tools be automatically registered based on initializer?
   - **Proposal**: Keep explicit tool registration, but allow initializers to suggest tools

3. **Version Management**: Should initializers specify tool versions?
   - **Proposal**: Yes, include in `get_docker_image()` via image tags

4. **LocalBackend**: How to ensure tools are installed locally?
   - **Proposal**: Add `ensure_tools_installed()` method to initializer

---

## Implementation Checklist

- [ ] Update `ProjectInitializer` base class with new abstract methods
- [ ] Implement new methods in `PythonInitializer`
- [ ] Implement new methods in `TypeScriptInitializer`
- [ ] Implement new methods in `NoOpInitializer`
- [ ] Update `DockerBackend` to use initializer config
- [ ] Remove `execute_uv()` from `ExecutionBackend`
- [ ] Create `PackageManagerTool`
- [ ] Update tests
- [ ] Update documentation
- [ ] Add migration guide for existing users
