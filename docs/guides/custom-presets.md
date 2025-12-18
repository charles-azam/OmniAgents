# Creating Custom Presets

This guide shows how to create presets for different languages and toolchains.

## What is a Preset?

A preset defines:

1. **Docker image** - Suggested container image
2. **Tools** - Language-specific tools to include
3. **Initialization** - How to set up a new project
4. **Detection** - How to check if a project is already initialized

## Preset Interface

```python
from abc import ABC, abstractmethod
from omniagents.backends.execution_backend import ExecutionBackend
from omniagents.tools.base_tool import CoreBackendTool
from dataclasses import dataclass

@dataclass
class InitResult:
    success: bool
    message: str
    first_run: bool

class Preset(ABC):
    name: str                    # e.g., "node-npm"
    docker_image: str | None     # e.g., "node:22-slim"
    tool_classes: tuple[type[CoreBackendTool], ...]  # e.g., (NPMTool,)

    @abstractmethod
    def is_initialized(self, backend: ExecutionBackend) -> bool:
        """Check if project is already set up."""

    @abstractmethod
    def initialize_project(self, backend: ExecutionBackend) -> InitResult:
        """Initialize a new project."""
```

## Example: Node.js/npm Preset

### Step 1: Create the Tool (Optional)

```python
# omniagents/tools/npm_tool.py
from omniagents.tools.base_tool import CoreBackendTool
from omniagents.outputs.outputs import TextOutputModel, ErrorOutputModel
from pydantic import BaseModel, Field

class NPMToolInput(BaseModel):
    npm_command: str = Field(
        description="NPM command to run (e.g., 'install express', 'run build')"
    )

class NPMTool(CoreBackendTool[NPMToolInput, TextOutputModel]):
    name = "npm"
    description = "Execute npm commands. Examples: 'install express', 'run dev', 'test'"

    def execute(self, inputs: NPMToolInput) -> TextOutputModel | ErrorOutputModel:
        result = self.backend.execute_command(f"npm {inputs.npm_command}")

        if result.exit_code != 0:
            return ErrorOutputModel(
                error_type="NPMError",
                message=result.output
            )

        return TextOutputModel(content=result.output)
```

### Step 2: Create the Preset

```python
# omniagents/presets/node.py
from omniagents.presets.base import Preset, InitResult
from omniagents.backends.execution_backend import ExecutionBackend
from omniagents.tools.npm_tool import NPMTool

class NodeNPMPreset(Preset):
    name = "node-npm"
    docker_image = "node:22-slim"
    tool_classes = (NPMTool,)

    def is_initialized(self, backend: ExecutionBackend) -> bool:
        """Check if package.json exists."""
        return backend.file_exists("package.json") is not None

    def initialize_project(self, backend: ExecutionBackend) -> InitResult:
        """Initialize with npm init."""
        result = backend.execute_command("npm init -y")

        return InitResult(
            success=result.exit_code == 0,
            message=result.output,
            first_run=True
        )
```

### Step 3: Use the Preset

```python
from omniagents.presets.node import NodeNPMPreset
from omniagents.backends.docker_backend import DockerBackend
from omniagents.agents.langchain_agent import LangChainAgent

preset = NodeNPMPreset()

backend = DockerBackend(
    project_id="my-node-app",
    state_manager=state_manager,
    image=preset.docker_image,  # "node:22-slim"
)
backend.start()

agent = LangChainAgent(
    backend=backend,
    model=model,
    preset=preset,  # Adds NPMTool, handles initialization
)

result = agent.run("Create an Express.js API server")
backend.shutdown()
```

## Example: Rust/Cargo Preset

```python
from omniagents.presets.base import Preset, InitResult
from omniagents.backends.execution_backend import ExecutionBackend

class RustCargoPreset(Preset):
    name = "rust-cargo"
    docker_image = "rust:1.75-slim"
    tool_classes = ()  # Use generic shell for cargo commands

    def is_initialized(self, backend: ExecutionBackend) -> bool:
        """Check if Cargo.toml exists."""
        return backend.file_exists("Cargo.toml") is not None

    def initialize_project(self, backend: ExecutionBackend) -> InitResult:
        """Initialize with cargo init."""
        # Get project name from directory
        cwd = backend.get_working_directory()
        project_name = cwd.split("/")[-1]

        result = backend.execute_command(f"cargo init --name {project_name}")

        return InitResult(
            success=result.exit_code == 0,
            message=result.output,
            first_run=True
        )
```

## Example: Go Preset

```python
from omniagents.presets.base import Preset, InitResult
from omniagents.backends.execution_backend import ExecutionBackend

class GoModPreset(Preset):
    name = "go-mod"
    docker_image = "golang:1.22-alpine"
    tool_classes = ()

    def is_initialized(self, backend: ExecutionBackend) -> bool:
        """Check if go.mod exists."""
        return backend.file_exists("go.mod") is not None

    def initialize_project(self, backend: ExecutionBackend) -> InitResult:
        """Initialize with go mod init."""
        # Default module name based on project ID
        cwd = backend.get_working_directory()
        module_name = f"github.com/user/{cwd.split('/')[-1]}"

        result = backend.execute_command(f"go mod init {module_name}")

        return InitResult(
            success=result.exit_code == 0,
            message=result.output,
            first_run=True
        )
```

## Example: Java/Maven Preset

```python
from omniagents.presets.base import Preset, InitResult
from omniagents.backends.execution_backend import ExecutionBackend

class JavaMavenPreset(Preset):
    name = "java-maven"
    docker_image = "maven:3.9-eclipse-temurin-21"
    tool_classes = ()

    def is_initialized(self, backend: ExecutionBackend) -> bool:
        """Check if pom.xml exists."""
        return backend.file_exists("pom.xml") is not None

    def initialize_project(self, backend: ExecutionBackend) -> InitResult:
        """Initialize with Maven archetype."""
        cwd = backend.get_working_directory()
        artifact_id = cwd.split("/")[-1]

        cmd = f"""mvn archetype:generate \
            -DgroupId=com.example \
            -DartifactId={artifact_id} \
            -DarchetypeArtifactId=maven-archetype-quickstart \
            -DinteractiveMode=false"""

        result = backend.execute_command(cmd)

        # Move generated files to workspace root
        if result.exit_code == 0:
            backend.execute_command(f"mv {artifact_id}/* . && rm -rf {artifact_id}")

        return InitResult(
            success=result.exit_code == 0,
            message=result.output,
            first_run=True
        )
```

## Advanced: Preset with Custom Tool

Create a specialized tool for your preset:

```python
# DenoTool for Deno preset
from omniagents.tools.base_tool import CoreBackendTool
from omniagents.outputs.outputs import TextOutputModel
from pydantic import BaseModel, Field

class DenoToolInput(BaseModel):
    deno_command: str = Field(
        description="Deno command (e.g., 'run main.ts', 'compile main.ts', 'test')"
    )

class DenoTool(CoreBackendTool[DenoToolInput, TextOutputModel]):
    name = "deno"
    description = "Execute Deno commands. Examples: 'run main.ts', 'test', 'compile'"

    def execute(self, inputs: DenoToolInput) -> TextOutputModel:
        result = self.backend.execute_command(f"deno {inputs.deno_command}")
        return TextOutputModel(content=result.output)


class DenoPreset(Preset):
    name = "deno"
    docker_image = "denoland/deno:latest"
    tool_classes = (DenoTool,)

    def is_initialized(self, backend: ExecutionBackend) -> bool:
        # Deno doesn't require initialization
        return True

    def initialize_project(self, backend: ExecutionBackend) -> InitResult:
        # Create a basic deno.json
        config = '{"tasks": {"dev": "deno run --watch main.ts"}}'
        backend.write_file("deno.json", config)

        return InitResult(
            success=True,
            message="Created deno.json",
            first_run=True
        )
```

## Best Practices

### 1. Use Descriptive Names

```python
name = "python-uv"      # Good: specific toolchain
name = "python"         # Bad: ambiguous
```

### 2. Provide Appropriate Docker Image

Choose minimal images when possible:

```python
docker_image = "python:3.13-slim"  # Good: minimal
docker_image = "python:3.13"       # Larger, but has more tools
```

### 3. Handle Existing Projects

Your `initialize_project` should be idempotent:

```python
def initialize_project(self, backend: ExecutionBackend) -> InitResult:
    if self.is_initialized(backend):
        return InitResult(
            success=True,
            message="Project already initialized",
            first_run=False
        )
    # ... actual initialization
```

### 4. Test Your Preset

```python
def test_node_preset_initialization():
    backend = LocalBackend(project_id="test", state_manager=NoOpStateManager())
    backend.start()

    preset = NodeNPMPreset()

    # Should not be initialized
    assert not preset.is_initialized(backend)

    # Initialize
    result = preset.initialize_project(backend)
    assert result.success
    assert result.first_run

    # Should be initialized now
    assert preset.is_initialized(backend)

    # Second init should detect existing project
    result2 = preset.initialize_project(backend)
    assert not result2.first_run

    backend.shutdown()
```
