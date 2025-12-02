# Bug Report: HuggingFace adapter loses tool call `arguments` during message history serialization

## Description

When using the HuggingFace model adapter with tool calling, the `arguments` field is lost when serializing tool call history to send back to the model. This causes API errors like:

```
'messages.2.tool_calls.0.function.arguments' : property 'arguments' is missing
```

## Root Cause

In `pydantic_ai/models/huggingface.py`, the `_map_tool_call` method uses `ChatCompletionInputToolCall` which contains `ChatCompletionInputFunctionDefinition`:

```python
@staticmethod
def _map_tool_call(t: ToolCallPart) -> ChatCompletionInputToolCall:
    return ChatCompletionInputToolCall.parse_obj_as_instance(
        {
            'id': _guard_tool_call_id(t=t),
            'type': 'function',
            'function': {
                'name': t.tool_name,
                'arguments': t.args_as_json_str(),
            },
        }
    )
```

The problem is that `ChatCompletionInputFunctionDefinition` (from `huggingface_hub`) is a dataclass with these fields:

- `name`
- `parameters`
- `description`

It does **NOT** have an `arguments` field. When `parse_obj_as_instance` is called, it adds `arguments` as a dynamic attribute, but when the message is serialized (via `dataclasses.asdict()`), the `arguments` field is lost because it's not a dataclass field.

The correct class to use is `ChatCompletionOutputToolCall` which contains `ChatCompletionOutputFunctionDefinition` - this class **does** have an `arguments` field.

## Minimal Reproducible Example

```python
import os
from pydantic_ai import Agent, Tool
from pydantic_ai.models.huggingface import HuggingFaceModel
from pydantic_ai.providers.huggingface import HuggingFaceProvider


def calculator(*, operation: str, a: float, b: float) -> str:
    """Performs arithmetic.

    Args:
        operation: The operation (multiply, add, etc.)
        a: First number
        b: Second number
    """
    if operation == "multiply":
        return str(a * b)
    return str(a + b)


model = HuggingFaceModel(
    model_name="openai/gpt-oss-120b",
    provider=HuggingFaceProvider(
        api_key=os.environ["HF_TOKEN"],
        provider_name="groq",
    ),
)

agent = Agent(
    model=model,
    tools=[Tool(function=calculator, name="calculator", description="Calculator")],
    system_prompt="Use the calculator tool to answer math questions.",
)

# This fails with: 'messages.2.tool_calls.0.function.arguments' : property 'arguments' is missing
result = agent.run_sync("What is 15 multiplied by 3? Use the calculator tool.")
print(result.output)
```

## Expected Behavior

The tool call should work and return "45".

## Actual Behavior

```
pydantic_ai.exceptions.ModelHTTPError: status_code: 400, model_name: openai/gpt-oss-120b,
body: {'error': {'message': "'messages.2' : for 'role:assistant' the following must be
satisfied[('messages.2.tool_calls.0.function.arguments' : property 'arguments' is missing)]",
'type': 'invalid_request_error'}}
```

## Suggested Fix

Change `_map_tool_call` to use `ChatCompletionOutputToolCall` and `ChatCompletionOutputFunctionDefinition`:

```python
from huggingface_hub.inference._generated.types.chat_completion import (
    ChatCompletionOutputToolCall,
    ChatCompletionOutputFunctionDefinition,
)

@staticmethod
def _map_tool_call(t: ToolCallPart) -> ChatCompletionOutputToolCall:
    return ChatCompletionOutputToolCall(
        id=_guard_tool_call_id(t=t),
        type="function",
        function=ChatCompletionOutputFunctionDefinition(
            name=t.tool_name,
            arguments=t.args_as_json_str(),
        ),
    )
```

## Proof that fix works

```python
# Verify the classes have different fields
import dataclasses
from huggingface_hub.inference._generated.types.chat_completion import (
    ChatCompletionInputFunctionDefinition,
    ChatCompletionOutputFunctionDefinition,
)

print("Input (current - broken):", [f.name for f in dataclasses.fields(ChatCompletionInputFunctionDefinition)])
# Output: ['name', 'parameters', 'description']  -- NO 'arguments'!

print("Output (fix):", [f.name for f in dataclasses.fields(ChatCompletionOutputFunctionDefinition)])
# Output: ['arguments', 'name', 'description']  -- HAS 'arguments'!
```

## Workaround

Until this is fixed, you can apply a monkey-patch:

```python
from pydantic_ai.models.huggingface import HuggingFaceModel
from pydantic_ai.messages import ToolCallPart
from pydantic_ai._utils import guard_tool_call_id as _guard_tool_call_id
from huggingface_hub.inference._generated.types.chat_completion import (
    ChatCompletionOutputToolCall,
    ChatCompletionOutputFunctionDefinition,
)


@staticmethod
def _map_tool_call_fixed(t: ToolCallPart) -> ChatCompletionOutputToolCall:
    return ChatCompletionOutputToolCall(
        id=_guard_tool_call_id(t=t),
        type="function",
        function=ChatCompletionOutputFunctionDefinition(
            name=t.tool_name,
            arguments=t.args_as_json_str(),
        ),
    )


HuggingFaceModel._map_tool_call = _map_tool_call_fixed
```

## Environment

- pydantic-ai version: [your version]
- huggingface-hub version: 0.36.0
- Python version: 3.13
