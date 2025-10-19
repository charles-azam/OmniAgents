# Tools Architecture

This directory contains a **3-layer architecture** for tool execution that separates concerns and enables maximum flexibility and reusability.

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│         Framework Adapter Layer                 │
│  (Smolagents, OpenAI, PydanticAI, Autogen)     │
│  - Reads metadata from Core Layer              │
│  - Transforms to framework-specific format     │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│         Core Tool Layer                         │
│  ★ METADATA STORED HERE ★                      │
│  (BashToolCore, EditToolCore, etc.)            │
│  - name, description, inputs, outputs          │
│  - Business logic (validation, formatting)     │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│         Execution Backend Layer                 │
│  (LocalBackend, DockerBackend, E2BBackend)     │
│  - Primitive operations only                   │
└─────────────────────────────────────────────────┘
```

## Design Principles

### 1. Separation of Concerns

**Three distinct layers** with clear responsibilities:

- **Execution Backends**: Handle primitive operations (execute command, read file, write file, etc.)
- **Core Tools**: Contain business logic (validation, formatting, metadata) - framework-agnostic
- **Framework Adapters**: Convert core tools to framework-specific formats (smolagents, OpenAI, etc.)

### 2. Output Separation

**Data separated from presentation**:

- **Output Models** (Pydantic): Pure data structures with no display logic
- **Renderers**: Handle how outputs are displayed (console, file, API)

Benefits:
- Same data can be rendered differently for console, web UI, or API
- Easy to serialize for FastAPI backends
- Type-safe with full Pydantic validation

### 3. Two Orthogonal Dimensions

The architecture supports **independent variation** along two axes:

1. **Execution Environment**: Local, Docker, E2B (or any future environment)
2. **Framework**: smolagents, OpenAI, Pydantic-AI, Autogen (or any future framework)

You can combine any execution environment with any framework.

## Directory Structure

```
src/prompttodraft/tools/
├── outputs/                    # Output layer
│   ├── models.py              # Pydantic models (data only)
│   └── renderers.py           # Console, File, API renderers
├── backends/                  # Execution layer
│   ├── execution_backend.py   # Abstract interface
│   └── local_backend.py       # Local implementation
├── core/                      # Business logic layer
│   ├── metadata.py            # Tool metadata definition
│   ├── bash_tool_core.py      # Bash tool (framework-agnostic)
│   ├── edit_tool_core.py      # Edit tool
│   ├── view_tool_core.py      # View tool
│   ├── replace_tool_core.py   # Replace tool
│   ├── glob_tool_core.py      # Glob tool
│   ├── grep_tool_core.py      # Grep tool
│   ├── ls_tool_core.py        # LS tool
│   └── user_input_tool_core.py # User input tool
├── adapters/                  # Framework integration layer
│   └── smolagents_adapter.py  # Smolagents framework adapter
├── coding_tools.py            # CodingTool abstract + implementations
├── factory.py                 # ToolFactory for easy creation
├── agent.py                   # ToolAgent with Rich output formatting
├── system_prompt.py           # Dynamic system prompt generation
└── system_message.txt         # System prompt template
```

## Layer Details

### Output Layer (`outputs/`)

#### Models (`outputs/models.py`)

Pydantic models for tool outputs - pure data structures:

- `TextOutputModel`: Simple text content
- `CodeOutputModel`: Code with language and line numbers
- `FileListOutputModel`: List of files/directories
- `TableOutputModel`: Tabular data
- `ErrorOutputModel`: Error information

All models:
- Inherit from `BaseOutputModel`
- Can be serialized to JSON
- Have optional metadata fields
- Implement `__str__()` for string representation

#### Renderers (`outputs/renderers.py`)

Different renderers for different contexts:

- **ConsoleRenderer**: Rich console output with styling (uses Rich library)
- **FileRenderer**: Save outputs to files (markdown, CSV, etc.)
- **APIRenderer**: Convert to JSON for FastAPI responses

Example:
```python
from prompttodraft.tools.outputs.renderers import ConsoleRenderer, APIRenderer

renderer = ConsoleRenderer()
renderer.render_text(text_output)  # Pretty console display

api_renderer = APIRenderer()
json_str = api_renderer.render_text(text_output)  # JSON string
```

### Execution Backend Layer (`backends/`)

#### Abstract Interface (`backends/execution_backend.py`)

Defines the contract for all backends with primitive operations:

```python
class ExecutionBackend(ABC):
    @abstractmethod
    def execute_command(self, command: str, timeout: int | None) -> tuple[str, bool]:
        """Execute a bash command."""
        pass

    @abstractmethod
    def read_file(self, file_path: str, offset: int, limit: int | None) -> str:
        """Read a file from the filesystem."""
        pass

    # ... other primitive operations
```

#### Local Backend (`backends/local_backend.py`)

Implements all primitives using standard Python:

- Uses `subprocess` for command execution
- Uses `open()` for file operations
- Uses `os.walk()` for directory traversal
- Uses `glob` for pattern matching
- Uses `re` for regex searching

All the low-level implementation details are isolated here.

### Core Tool Layer (`core/`)

#### Metadata (`core/metadata.py`)

Framework-agnostic metadata definition:

```python
@dataclass
class ToolMetadata:
    name: str
    description: str
    inputs: dict[str, dict[str, str | bool | None]]
    output_type: str
```

Metadata can be transformed to different framework formats:
- `to_smolagents_format()`: For smolagents
- `to_openai_format()`: For OpenAI function calling

#### Core Tools

Each core tool (e.g., `BashToolCore`):

1. **Stores metadata** as a class attribute
2. **Contains business logic**: validation, formatting, error handling
3. **Delegates primitive operations** to the backend
4. **Returns output models** (not strings)

Example structure:
```python
class BashToolCore:
    # Metadata stored here
    metadata = ToolMetadata(
        name="Bash",
        description="...",
        inputs={...},
        output_type="string"
    )

    def __init__(self, backend: ExecutionBackend):
        self.backend = backend

    def execute(self, command: str, timeout: int | None) -> ToolOutputModel:
        # 1. Validation
        if self._is_banned_command(command):
            return ErrorOutputModel(error="Banned command")

        # 2. Delegate to backend
        output, is_error = self.backend.execute_command(command, timeout)

        # 3. Format output
        if self._is_code_command(command):
            return CodeOutputModel(output, language=self._guess_language(command))
        return TextOutputModel(output)

    # Helper methods (validation, formatting)
    def _is_banned_command(self, command: str) -> bool: ...
    def _is_code_command(self, command: str) -> bool: ...
```

### Framework Adapter Layer (`adapters/`)

#### Smolagents Adapter (`adapters/smolagents_adapter.py`)

Wraps core tools for smolagents framework:

```python
class SmolagentsBashTool(Tool):
    def __init__(self, core: BashToolCore):
        super().__init__()
        self.core = core
        # Copy metadata
        self.name = core.metadata.name
        self.description = core.metadata.description
        self.inputs = core.metadata.inputs
        self.output_type = core.metadata.output_type

    def forward(self, command: str, timeout: int | None = None):
        # Execute and convert to string
        return str(self.core.execute(command=command, timeout=timeout))
```

### Integration Layer

#### CodingTool (`coding_tools.py`)

High-level interface that bundles all 8 tools:

```python
class CodingToolLocal(CodingTool):
    def __init__(self):
        backend = LocalBackend()
        self._bash = BashToolCore(backend)
        self._edit = EditToolCore(backend)
        # ... all 8 tools

    def bash_tool(self, command: str, timeout: int | None = None):
        return self._bash.execute(command=command, timeout=timeout)
```

#### ToolFactory (`factory.py`)

Convenient factory for creating framework-specific tools:

```python
from prompttodraft.tools.factory import ToolFactory

# Create smolagents tools for local execution
tools = ToolFactory.create_smolagents_tools(environment="local")
```

## Usage Examples

### Basic Usage with CodingToolLocal

```python
from prompttodraft.tools.coding_tools import CodingToolLocal

# Create coding tool
coding_tool = CodingToolLocal()

# Execute bash command
result = coding_tool.bash_tool(command="echo 'Hello World'")
print(result.content)  # Access the content

# Read a file
result = coding_tool.view_tool(file_path="/path/to/file.py")
if isinstance(result, CodeOutputModel):
    print(f"Language: {result.language}")
    print(result.content)

# Edit a file
result = coding_tool.edit_tool(
    file_path="/path/to/file.py",
    old_string="old code\n",
    new_string="new code\n"
)
```

### Using with Smolagents

```python
from prompttodraft.tools.factory import ToolFactory

# Create smolagents tools
tools = ToolFactory.create_smolagents_tools(environment="local")

# Use with smolagents agent
from smolagents import CodeAgent

agent = CodeAgent(tools=tools, model=...)
agent.run("List all Python files in the current directory")
```

### Custom Rendering

```python
from prompttodraft.tools.coding_tools import CodingToolLocal
from prompttodraft.tools.outputs.renderers import ConsoleRenderer, APIRenderer

coding_tool = CodingToolLocal()
result = coding_tool.bash_tool(command="ls -la")

# Render to console
console_renderer = ConsoleRenderer()
console_renderer.render(result)

# Convert to JSON for API
api_renderer = APIRenderer()
json_data = api_renderer.render(result)
```

## Benefits of This Architecture

### 1. Minimal Code Duplication

- Business logic written **once** in core tools
- Execution logic written **once** in backends
- Framework integration **thin adapters only**

### 2. Easy to Extend

#### Adding a new execution environment:

1. Implement `ExecutionBackend` interface
2. Create `CodingToolDocker` or `CodingToolE2B`
3. Done! All 8 tools work automatically

#### Adding a new framework:

1. Create adapter (e.g., `OpenAIBashTool`)
2. Read metadata from core tool
3. Transform to framework format
4. Done!

#### Adding a new tool:

1. Create core tool (e.g., `FileSearchToolCore`)
2. Create smolagents adapter
3. Add to `CodingTool` interface
4. Update implementations

### 3. Easy to Test

```python
# Mock the backend for unit testing
class MockBackend(ExecutionBackend):
    def execute_command(self, command, timeout):
        return "mocked output", False

# Test core tool independently
bash_tool = BashToolCore(backend=MockBackend())
result = bash_tool.execute(command="echo test")
assert result.content == "mocked output"
```

### 4. Type-Safe

- Full typing throughout
- Pydantic models for outputs
- Abstract protocols for interfaces

### 5. Framework-Agnostic Core

- Core tools have **zero** framework dependencies
- Can be used with any framework
- Business logic is portable

## Future Extensions

### Add Docker Backend

```python
class DockerBackend(ExecutionBackend):
    def __init__(self, container_id: str):
        self.container = docker.from_env().containers.get(container_id)

    def execute_command(self, command, timeout):
        result = self.container.exec_run(command, timeout=timeout)
        return result.output.decode(), result.exit_code != 0

    # ... implement other methods
```

### Add OpenAI Adapter

```python
class OpenAIBashTool:
    def __init__(self, core: BashToolCore):
        self.core = core
        self.function_definition = core.metadata.to_openai_format()

    def execute(self, **kwargs):
        return self.core.execute(**kwargs)
```

### Add Web Renderer

```python
class WebRenderer(BaseRenderer):
    def render_code(self, output: CodeOutputModel) -> str:
        return f'<pre><code class="language-{output.language}">{output.content}</code></pre>'
```

## Testing

Run E2E tests:

```bash
pytest tests/test_tools_e2e.py -v
```

The tests verify:
- ✅ Output models work correctly
- ✅ LocalBackend executes primitive operations
- ✅ Core tools combine backend + business logic
- ✅ Smolagents adapters work correctly
- ✅ ToolFactory creates tools properly
- ✅ CodingToolLocal integrates everything
- ✅ Error handling works as expected
- ✅ Output serialization works

## Migration from `/smolcc`

The `/smolcc` directory contains the old monolithic implementation. This new architecture:

1. **Extracts** primitive operations → `backends/local_backend.py`
2. **Extracts** business logic → `core/*_tool_core.py`
3. **Separates** output data → `outputs/models.py`
4. **Separates** output rendering → `outputs/renderers.py`
5. **Adds** framework adapters → `adapters/smolagents_adapter.py`

All functionality is preserved, but now with:
- Better separation of concerns
- Easier to test
- Easier to extend
- Framework-agnostic core
- Reusable across execution environments

## Agent Integration

### ToolAgent (`agent.py`)

The `ToolAgent` class provides a complete agent implementation using smolagents with the 3-layer architecture:

```python
from prompttodraft.tools.agent import create_agent

# Create an agent with all tools
agent = create_agent(cwd="/path/to/project", log_file="agent.log")

# Run a query
result = agent.run("What files are in the current directory?")
```

#### Features

- **Rich Terminal Output**: Uses Rich library for beautiful terminal formatting
- **Tool Call Display**: Shows tool calls with parameters
- **Smart Output Formatting**: Automatically formats outputs based on type (code, files, tables, text)
- **Thinking Spinner**: Shows visual feedback during LLM processing
- **Execution Timing**: Displays execution time for slow operations
- **Error Handling**: Prominently displays errors

#### System Prompt Generation (`system_prompt.py`)

The agent uses dynamic system prompts that include:

- Current working directory
- Directory structure (with smart filtering)
- Git repository status (if applicable)
- Platform information
- Current date

```python
from prompttodraft.tools.system_prompt import get_system_prompt

# Generate a system prompt for a specific directory
prompt = get_system_prompt(cwd="/path/to/project")
```

#### Custom Logger

The `RichConsoleLogger` provides:

- Suppression of default smolagents output
- Rich console integration
- Optional file logging
- Formatted error display

#### Display System

The agent automatically formats different output types:

- **TextOutputModel**: Simple text with line count for multiline
- **CodeOutputModel**: Syntax-highlighted code with line numbers
- **FileListOutputModel**: Tables with file names, types, and sizes
- **ErrorOutputModel**: Prominently styled error messages
- **TableOutputModel**: Formatted tables with headers

## Design Patterns Used

1. **Strategy Pattern**: Different backends (Local, Docker, E2B)
2. **Adapter Pattern**: Framework adapters (Smolagents, OpenAI, etc.)
3. **Factory Pattern**: ToolFactory for convenient creation
4. **Template Method**: Core tools define algorithm, backends fill in steps
5. **Separation of Concerns**: Data (models) vs. Presentation (renderers)

## Conclusion

This architecture provides:

- **Maximum flexibility**: Mix and match environments + frameworks
- **Minimal duplication**: Write once, use anywhere
- **Clean separation**: Each layer has one responsibility
- **Easy testing**: Mock any layer independently
- **Future-proof**: Easy to add new environments, frameworks, or tools

The key insight: **Separate what varies from what stays the same**. Execution varies (local/docker/e2b), frameworks vary (smolagents/openai), but business logic stays constant.
