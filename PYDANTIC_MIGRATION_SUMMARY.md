# Pydantic Migration Summary

## What Was Done

This document summarizes a major refactoring of the prompttodraft codebase to use Pydantic models for tool input validation instead of manual metadata dictionaries.

## Goal

**Replace manual metadata dictionaries with Pydantic models for automatic validation and schema generation.**

### Before (Manual Approach)
```python
class WriteFileTool(CoreTool):
    metadata = ToolMetadata(
        name="write_file",
        description="Writes content to a file...",
        inputs={
            "file_path": {
                "type": "string",
                "description": "The absolute path...",
                "nullable": False,
            },
            "content": {
                "type": "string",
                "description": "The content...",
                "nullable": False,
            },
        },
        output_type="string",
    )

    def execute(self, file_path: str, content: str) -> ToolOutputModel:
        # No automatic validation
        self.backend.write_file(file_path, content)
```

### After (Pydantic Approach)
```python
class WriteFileTool(CoreTool):
    name = "write_file"
    description = "Writes content to a file..."

    class InputModel(BaseModel):
        file_path: str = Field(description="The absolute path...")
        content: str = Field(description="The content...")

    def execute(self, inputs: InputModel) -> ToolOutputModel:
        # Inputs are automatically validated by Pydantic!
        self.backend.write_file(inputs.file_path, inputs.content)
```

## Benefits

1. **Automatic Validation** - Pydantic validates inputs before execution
2. **Single Source of Truth** - `InputModel` IS the schema
3. **Better IDE Support** - Autocomplete for `inputs.file_path`
4. **Consistency** - Inputs and outputs both use Pydantic
5. **Less Boilerplate** - No manual dict writing
6. **JSON Schema Generation** - Use `InputModel.model_json_schema()` directly

## What Was Changed

### 1. Base Tool (`src/prompttodraft/tools/base_tool.py`)
- Removed `metadata: ToolMetadata` attribute
- Added `name: ClassVar[str]`, `description: ClassVar[str]`, `InputModel: ClassVar[type[BaseModel]]`
- Changed `execute(**kwargs)` to `execute(inputs: BaseModel)`
- Added `get_json_schema()` classmethod that returns `InputModel.model_json_schema()`

### 2. Adapter Generators (`src/prompttodraft/adapters/generator.py`)
- Removed dependency on `ToolMetadata`
- Added `extract_parameter_info_from_schema()` function that reads from Pydantic JSON Schema
- Updated `generate_smolagents_tool()` to use `tool_class.get_json_schema()`
- Updated `generate_langchain_tool()` to use `tool_class.get_json_schema()`
- Updated `generate_pydantic_ai_tool()` to use `tool_class.get_json_schema()`
- All generators now validate inputs using the Pydantic `InputModel` before calling `execute()`

### 3. All 10 Core Tools
Updated every tool to use the new Pydantic-based approach:

1. ✅ **WriteFileTool** - Simple required parameters
2. ✅ **ReadFileTool** - Optional parameters (`offset: int | None`, `limit: int | None`)
3. ✅ **ListDirectoryTool** - Array and boolean parameters
4. ✅ **GlobTool** - Multiple optional parameters
5. ✅ **SearchFileContentTool** - String patterns with optionals
6. ✅ **ReplaceTool** - Default values (`expected_replacements: int = 1`)
7. ✅ **RunShellCommandTool** - Optional directory parameter
8. ✅ **ReadManyFilesTool** - Complex with arrays and multiple booleans
9. ✅ **SaveMemoryTool** - Single required parameter
10. ✅ **UVTool** - Command with optional description

## Current Status

### ✅ Completed
- Base tool refactored
- All 3 adapter generators updated (smolagents, LangChain, Pydantic-AI)
- All 10 core tools converted to Pydantic

### ⚠️ In Progress
- Running tests encountered an environment variable issue: `BUCKET_PROMPT_TO_DRAFT` not set
- Tests need to run successfully to verify the migration

## Next Steps

1. **Fix test environment** - Set required environment variables or mock them in tests
2. **Run full test suite** - Verify all adapters and tools work correctly
3. **Update documentation** - Document the new Pydantic-based tool creation pattern
4. **Test with real agents** - Verify smolagents, LangChain, and Pydantic-AI agents work

## Architecture

```
CoreTool (base class)
├── name: ClassVar[str]
├── description: ClassVar[str]
├── InputModel: ClassVar[type[BaseModel]]  ← Pydantic model
├── __init__(backend: ExecutionBackend)
├── execute(inputs: BaseModel) → ToolOutputModel
└── get_json_schema() → dict

Adapter Generators
├── Read tool_class.get_json_schema()
├── Extract parameter info from JSON Schema
├── Generate framework-specific wrapper
└── Call tool_class.InputModel(**kwargs) for validation
```

## Testing Command

```bash
# Run adapter tests
uv run pytest tests/test_adapters/test_generator.py -v

# Note: May need to set BUCKET_PROMPT_TO_DRAFT env var or mock storage
```

## Files Modified

### Core
- `src/prompttodraft/tools/base_tool.py`
- `src/prompttodraft/adapters/generator.py`

### Tools (all 10)
- `src/prompttodraft/tools/write_file_tool.py`
- `src/prompttodraft/tools/read_file_tool.py`
- `src/prompttodraft/tools/list_directory_tool.py`
- `src/prompttodraft/tools/glob_tool.py`
- `src/prompttodraft/tools/search_file_content_tool.py`
- `src/prompttodraft/tools/replace_tool.py`
- `src/prompttodraft/tools/run_shell_command_tool.py`
- `src/prompttodraft/tools/read_many_files_tool.py`
- `src/prompttodraft/tools/save_memory_tool.py`
- `src/prompttodraft/tools/uv_tool.py`

## Key Design Decisions

1. **Used ClassVar** - To indicate that `name`, `description`, and `InputModel` are class attributes, not instance attributes
2. **Kept adapters using exec()** - Still dynamically generate wrapper code, but now validate with Pydantic first
3. **Backward compatible schemas** - Pydantic's `model_json_schema()` produces JSON Schema that works with all frameworks
4. **Optional parameters** - Use `Field(default=None)` or `Field(default=value)` for optional/default parameters

## Example: Creating a New Tool

```python
from pydantic import BaseModel, Field
from prompttodraft.tools.base_tool import CoreTool
from prompttodraft.outputs.outputs import ToolOutputModel, TextOutputModel

class MyNewTool(CoreTool):
    name = "my_tool"
    description = "Does something cool"

    class InputModel(BaseModel):
        required_param: str = Field(description="This is required")
        optional_param: int | None = Field(default=None, description="This is optional")
        with_default: bool = Field(default=True, description="Has a default")

    def execute(self, inputs: InputModel) -> ToolOutputModel:
        # inputs.required_param is validated automatically!
        # inputs.optional_param can be None
        # inputs.with_default is True by default
        return TextOutputModel(content=f"Processed: {inputs.required_param}")
```

That's it! The adapter generators will automatically create smolagents, LangChain, and Pydantic-AI wrappers.
