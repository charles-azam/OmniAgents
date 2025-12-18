# Creating Custom Tools

This guide shows how to create your own tools that work with all backends and frameworks.

## Basic Tool Structure

Every tool follows this pattern:

```python
from omniagents.tools.base_tool import CoreBackendTool
from omniagents.outputs.outputs import TextOutputModel
from pydantic import BaseModel, Field

# 1. Define input schema
class MyToolInput(BaseModel):
    param1: str = Field(description="First parameter")
    param2: int = Field(default=10, description="Optional parameter")

# 2. Create tool class
class MyTool(CoreBackendTool[MyToolInput, TextOutputModel]):
    name = "my_tool"
    description = "Does something useful"

    def execute(self, inputs: MyToolInput) -> TextOutputModel:
        # 3. Implement logic using self.backend
        result = self.backend.execute_command(f"echo {inputs.param1}")
        return TextOutputModel(content=result.output)
```

## Step-by-Step Example: GitTool

Let's create a tool for Git operations.

### 1. Define the Input Schema

```python
from pydantic import BaseModel, Field

class GitToolInput(BaseModel):
    command: str = Field(
        description="Git command to execute (e.g., 'status', 'add .', 'commit -m \"message\"')"
    )
```

### 2. Create the Tool Class

```python
from omniagents.tools.base_tool import CoreBackendTool
from omniagents.outputs.outputs import TextOutputModel, ErrorOutputModel

class GitTool(CoreBackendTool[GitToolInput, TextOutputModel]):
    name = "git"
    description = "Execute git commands. Examples: 'status', 'add .', 'commit -m \"message\"', 'log --oneline -5'"

    def execute(self, inputs: GitToolInput) -> TextOutputModel | ErrorOutputModel:
        # Validate command doesn't contain dangerous operations
        dangerous = ["push --force", "reset --hard", "clean -fd"]
        if any(d in inputs.command for d in dangerous):
            return ErrorOutputModel(
                error_type="DangerousCommand",
                message=f"Command '{inputs.command}' is potentially dangerous"
            )

        # Execute git command
        result = self.backend.execute_command(f"git {inputs.command}")

        if result.exit_code != 0:
            return ErrorOutputModel(
                error_type="GitError",
                message=result.output
            )

        return TextOutputModel(content=result.output)
```

### 3. Use the Tool

```python
from omniagents.agents.langchain_agent import LangChainAgent

agent = LangChainAgent(
    backend=backend,
    model=model,
    preset=preset,
    extra_tool_classes=[GitTool],  # Add your tool
)

result = agent.run("Initialize a git repo and make the first commit")
```

## Advanced Example: Database Tool

A tool that queries a SQLite database.

```python
from omniagents.tools.base_tool import CoreBackendTool
from omniagents.outputs.outputs import TableOutputModel, ErrorOutputModel
from pydantic import BaseModel, Field
import json

class SQLQueryInput(BaseModel):
    query: str = Field(description="SQL SELECT query to execute")
    database: str = Field(default="app.db", description="Database file path")

class SQLQueryTool(CoreBackendTool[SQLQueryInput, TableOutputModel]):
    name = "sql_query"
    description = "Execute read-only SQL queries on SQLite databases"

    def execute(self, inputs: SQLQueryInput) -> TableOutputModel | ErrorOutputModel:
        # Only allow SELECT queries
        if not inputs.query.strip().upper().startswith("SELECT"):
            return ErrorOutputModel(
                error_type="InvalidQuery",
                message="Only SELECT queries are allowed"
            )

        # Execute query and get JSON output
        cmd = f'''sqlite3 -json {inputs.database} "{inputs.query}"'''
        result = self.backend.execute_command(cmd)

        if result.exit_code != 0:
            return ErrorOutputModel(
                error_type="SQLError",
                message=result.output
            )

        # Parse JSON result
        rows = json.loads(result.output) if result.output else []

        if not rows:
            return TableOutputModel(headers=[], rows=[])

        headers = list(rows[0].keys())
        data = [[str(row.get(h, "")) for h in headers] for row in rows]

        return TableOutputModel(headers=headers, rows=data)
```

## Tool with File Output

A tool that generates files.

```python
from omniagents.tools.base_tool import CoreBackendTool
from omniagents.outputs.outputs import TextOutputModel, MediaOutputModel
from pydantic import BaseModel, Field
import base64

class ChartInput(BaseModel):
    data: str = Field(description="JSON data for the chart")
    chart_type: str = Field(default="bar", description="Chart type: bar, line, pie")
    output_path: str = Field(default="chart.png", description="Output file path")

class ChartTool(CoreBackendTool[ChartInput, MediaOutputModel]):
    name = "generate_chart"
    description = "Generate a chart from JSON data"

    def execute(self, inputs: ChartInput) -> MediaOutputModel | ErrorOutputModel:
        # Create Python script for chart generation
        script = f'''
import matplotlib.pyplot as plt
import json

data = json.loads('{inputs.data}')
plt.figure(figsize=(10, 6))
plt.{inputs.chart_type}(data['labels'], data['values'])
plt.savefig('{inputs.output_path}')
'''
        # Write and execute script
        self.backend.write_file("_chart_script.py", script)
        result = self.backend.execute_command("python _chart_script.py")
        self.backend.delete_file("_chart_script.py")

        if result.exit_code != 0:
            return ErrorOutputModel(error_type="ChartError", message=result.output)

        # Read generated image
        content = self.backend.read_file(inputs.output_path)
        return MediaOutputModel(
            media_type="image/png",
            base64_data=base64.b64encode(content.encode()).decode(),
            filename=inputs.output_path
        )
```

## Best Practices

### 1. Use Descriptive Field Descriptions

The LLM uses descriptions to understand parameters:

```python
# Good
query: str = Field(description="SQL SELECT query, e.g., 'SELECT * FROM users WHERE age > 21'")

# Bad
query: str = Field(description="The query")
```

### 2. Return Appropriate Output Models

Choose the right output model:

- `TextOutputModel` - General text responses
- `CodeOutputModel` - Code snippets (enables syntax highlighting)
- `TableOutputModel` - Structured data
- `FileListOutputModel` - File listings
- `MediaOutputModel` - Images, PDFs
- `ErrorOutputModel` - Errors (always handle errors!)

### 3. Validate Input

Don't trust LLM-generated input:

```python
def execute(self, inputs: MyInput) -> TextOutputModel:
    # Validate
    if ".." in inputs.path:
        return ErrorOutputModel(
            error_type="SecurityError",
            message="Path traversal not allowed"
        )
```

### 4. Use Backend Methods

Always use `self.backend` for operations:

```python
# Good - works in all backends
self.backend.write_file("output.txt", content)
self.backend.execute_command("python script.py")

# Bad - only works locally
with open("output.txt", "w") as f:
    f.write(content)
```

### 5. Handle Errors Gracefully

```python
def execute(self, inputs: MyInput) -> TextOutputModel | ErrorOutputModel:
    result = self.backend.execute_command(inputs.command)

    if result.exit_code != 0:
        return ErrorOutputModel(
            error_type="CommandFailed",
            message=result.output,
            context={"exit_code": result.exit_code}
        )

    return TextOutputModel(content=result.output)
```

## Testing Your Tool

```python
import pytest
from omniagents.backends.local_backend import LocalBackend
from omniagents.backends.state_manager import NoOpStateManager

def test_my_tool():
    backend = LocalBackend(
        project_id="test",
        state_manager=NoOpStateManager()
    )
    backend.start()

    tool = MyTool(backend=backend)
    result = tool.execute(MyToolInput(param1="test"))

    assert isinstance(result, TextOutputModel)
    assert "test" in result.content

    backend.shutdown()
```
