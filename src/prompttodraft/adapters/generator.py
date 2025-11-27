"""
Automatic adapter generation for AI frameworks.

This module provides functions to automatically generate framework-specific
tool wrappers from core tools, eliminating manual boilerplate.

Uses Pydantic's model_json_schema() for automatic schema generation.

Supported frameworks:
- smolagents: generate_smolagents_tools()
- LangChain: generate_langchain_tools()
- Pydantic-AI: generate_pydantic_ai_tools()

Usage:
    from prompttodraft.adapters.generator import (
        generate_smolagents_tools,
        generate_langchain_tools,
        generate_pydantic_ai_tools,
        get_all_core_tools,
    )

    # Get all tools for a backend
    tools = generate_langchain_tools(backend)

    # Or specify which tools to include
    from prompttodraft.tools.write_file_tool import WriteFileTool
    tools = generate_langchain_tools(backend, tool_classes=[WriteFileTool])
"""
from prompttodraft.backends.execution_backend import ExecutionBackend
from prompttodraft.tools.base_tool import CoreTool


# Type mapping from metadata types to Python types
METADATA_TYPE_TO_PYTHON = {
    "string": str,
    "number": int,
    "integer": int,
    "float": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def get_all_core_tool_classes() -> list[type[CoreTool]]:
    """
    Get all available core tool classes.

    Returns:
        List of all CoreTool subclasses.
    """
    from prompttodraft.tools.write_file_tool import WriteFileTool
    from prompttodraft.tools.read_file_tool import ReadFileTool
    from prompttodraft.tools.list_directory_tool import ListDirectoryTool
    from prompttodraft.tools.glob_tool import GlobTool
    from prompttodraft.tools.search_file_content_tool import SearchFileContentTool
    from prompttodraft.tools.replace_tool import ReplaceTool
    from prompttodraft.tools.run_shell_command_tool import RunShellCommandTool
    from prompttodraft.tools.read_many_files_tool import ReadManyFilesTool
    from prompttodraft.tools.save_memory_tool import SaveMemoryTool
    from prompttodraft.tools.uv_tool import UVTool

    return [
        WriteFileTool,
        ReadFileTool,
        ListDirectoryTool,
        GlobTool,
        SearchFileContentTool,
        ReplaceTool,
        RunShellCommandTool,
        ReadManyFilesTool,
        SaveMemoryTool,
        UVTool,
    ]


def get_python_type_for_input(input_spec: dict) -> type:
    """
    Convert metadata input spec to Python type.

    Args:
        input_spec: Dictionary with 'type', 'nullable', etc.

    Returns:
        Python type or union type.
    """
    base_type = METADATA_TYPE_TO_PYTHON.get(input_spec.get("type", "string"), str)

    # Handle array item types
    if input_spec.get("type") == "array" and "items" in input_spec:
        item_type = input_spec["items"].get("type", "string")
        item_python_type = METADATA_TYPE_TO_PYTHON.get(item_type, str)
        base_type = list[item_python_type]

    # Handle nullable
    if input_spec.get("nullable", False):
        return base_type | None

    return base_type


def get_default_for_input(input_spec: dict):
    """
    Get default value for an input parameter.

    Args:
        input_spec: Dictionary with 'type', 'nullable', 'default', etc.

    Returns:
        Default value or None if no default.
    """
    if "default" in input_spec:
        return input_spec["default"]

    if input_spec.get("nullable", False):
        return None

    # No default for required parameters
    return ...


def extract_parameter_info_from_schema(schema: dict) -> list[tuple[str, type, object]]:
    """
    Extract parameter information from Pydantic JSON Schema.

    Args:
        schema: JSON Schema dict from model_json_schema()

    Returns:
        List of (name, type, default) tuples, sorted with required params first.
    """
    params = []
    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))

    for param_name, prop_spec in properties.items():
        python_type = get_python_type_for_input(prop_spec)

        # Check if field has a default value
        if "default" in prop_spec:
            default = prop_spec["default"]
        elif param_name not in required_fields:
            # Optional field without explicit default
            default = None
        else:
            # Required field
            default = ...

        params.append((param_name, python_type, default))

    # Sort: required parameters (default=...) first, then optional ones
    params.sort(key=lambda p: (p[2] is not ..., p[0]))

    return params


# =============================================================================
# smolagents Adapter Generator
# =============================================================================


def _build_smolagents_inputs(schema: dict) -> dict[str, dict[str, str | bool]]:
    """
    Build smolagents-compatible inputs dict from JSON Schema.

    Args:
        schema: JSON Schema dict from Pydantic model_json_schema()

    Returns:
        Dictionary in smolagents inputs format.
    """
    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))
    smolagents_inputs: dict[str, dict[str, str | bool]] = {}

    for param_name, prop_spec in properties.items():
        smolagents_input: dict[str, str | bool] = {
            "type": prop_spec.get("type", "string"),
            "description": prop_spec.get("description", ""),
        }
        # Handle anyOf (for optional types like str | None)
        if "anyOf" in prop_spec:
            smolagents_input["nullable"] = True
            # Get the non-null type
            for type_spec in prop_spec["anyOf"]:
                if type_spec.get("type") != "null":
                    smolagents_input["type"] = type_spec.get("type", "string")
                    if "items" in type_spec:
                        smolagents_input["items"] = type_spec["items"]
                    break
        # Mark as nullable if it has a default value or is not required
        elif "default" in prop_spec or param_name not in required_fields:
            smolagents_input["nullable"] = True
        if "items" in prop_spec:
            smolagents_input["items"] = prop_spec["items"]
        smolagents_inputs[param_name] = smolagents_input

    return smolagents_inputs


class SmolagentsToolAdapter:
    """
    Adapter that wraps a CoreTool to be compatible with smolagents Tool interface.

    This class avoids using exec() by leveraging smolagents' skip_forward_signature_validation
    feature, allowing forward() to accept **kwargs instead of explicit parameters.

    Usage:
        from prompttodraft.adapters.generator import SmolagentsToolAdapter
        from prompttodraft.tools.write_file_tool import WriteFileTool

        tool = SmolagentsToolAdapter(
            tool_class=WriteFileTool,
            backend=backend,
        )
    """

    # Skip signature validation - allows forward(**kwargs) pattern
    skip_forward_signature_validation = True

    def __init__(
        self,
        tool_class: type[CoreTool],
        backend: ExecutionBackend,
    ):
        """
        Initialize the smolagents tool adapter.

        Args:
            tool_class: The CoreTool subclass to wrap.
            backend: The execution backend instance.
        """
        self._tool_class = tool_class
        self._core_tool = tool_class(backend=backend)
        self._input_model = tool_class.InputModel

        # Set smolagents required attributes
        self.name = tool_class.name
        self.description = tool_class.description
        self.output_type = "string"

        # Build inputs from schema
        schema = tool_class.get_json_schema()
        self.inputs = _build_smolagents_inputs(schema=schema)

        self.is_initialized = True

    def forward(self, **kwargs) -> str:
        """
        Execute the tool with the given keyword arguments.

        Args:
            **kwargs: Tool input parameters matching the InputModel fields.

        Returns:
            String representation of the tool output.
        """
        # Validate and create inputs using Pydantic model
        validated_inputs = self._input_model(**kwargs)
        result = self._core_tool.execute(inputs=validated_inputs)
        return str(result)

    def __call__(self, *args, **kwargs) -> str:
        """
        Call the tool, converting positional args to kwargs if needed.

        Args:
            *args: Positional arguments (converted to kwargs based on input order).
            **kwargs: Keyword arguments for the tool.

        Returns:
            String representation of the tool output.
        """
        # Handle positional arguments by mapping to input names
        if args:
            input_names = list(self.inputs.keys())
            for i, arg in enumerate(args):
                if i < len(input_names):
                    kwargs[input_names[i]] = arg
        return self.forward(**kwargs)


def generate_smolagents_tool(
    tool_class: type[CoreTool],
    backend: ExecutionBackend,
):
    """
    Generate a smolagents-compatible tool for a single core tool.

    Args:
        tool_class: The CoreTool subclass to wrap.
        backend: The execution backend instance.

    Returns:
        A SmolagentsToolAdapter instance that can be used with smolagents.
    """
    from smolagents import Tool

    # Create the adapter
    adapter = SmolagentsToolAdapter(
        tool_class=tool_class,
        backend=backend,
    )

    # Create a proper Tool subclass dynamically (without exec)
    # that inherits from smolagents.Tool for full compatibility
    class WrappedTool(Tool):
        skip_forward_signature_validation = True

        def __init__(self, _adapter: SmolagentsToolAdapter):
            self._adapter = _adapter
            self.name = _adapter.name
            self.description = _adapter.description
            self.inputs = _adapter.inputs
            self.output_type = _adapter.output_type
            self.is_initialized = True

        def forward(self, **kwargs) -> str:
            return self._adapter.forward(**kwargs)

    return WrappedTool(_adapter=adapter)


def generate_smolagents_tools(
    backend: ExecutionBackend,
    tool_classes: list[type[CoreTool]] | None = None,
) -> list:
    """
    Generate smolagents Tool instances for all core tools.

    Args:
        backend: The execution backend instance.
        tool_classes: Optional list of specific tool classes to generate.
                     If None, generates all available tools.

    Returns:
        List of smolagents Tool instances.

    Example:
        from prompttodraft.adapters.generator import generate_smolagents_tools
        from prompttodraft.backends.local_backend import LocalBackend

        backend = LocalBackend(project_id="my-project", state_manager=...)
        tools = generate_smolagents_tools(backend)

        # Or specific tools only:
        from prompttodraft.tools.write_file_tool import WriteFileTool
        tools = generate_smolagents_tools(backend, tool_classes=[WriteFileTool])
    """
    if tool_classes is None:
        tool_classes = get_all_core_tool_classes()

    return [
        generate_smolagents_tool(tool_class=tc, backend=backend)
        for tc in tool_classes
    ]


# =============================================================================
# LangChain Adapter Generator
# =============================================================================


class LangChainToolAdapter:
    """
    Adapter that wraps a CoreTool to be compatible with LangChain's tool interface.

    This class avoids using exec() by using LangChain's StructuredTool which
    accepts a Pydantic model for args_schema directly.

    Usage:
        from prompttodraft.adapters.generator import LangChainToolAdapter
        from prompttodraft.tools.write_file_tool import WriteFileTool

        adapter = LangChainToolAdapter(
            tool_class=WriteFileTool,
            backend=backend,
        )
        langchain_tool = adapter.to_langchain_tool()
    """

    def __init__(
        self,
        tool_class: type[CoreTool],
        backend: ExecutionBackend,
    ):
        """
        Initialize the LangChain tool adapter.

        Args:
            tool_class: The CoreTool subclass to wrap.
            backend: The execution backend instance.
        """
        self._tool_class = tool_class
        self._core_tool = tool_class(backend=backend)
        self._input_model = tool_class.InputModel
        self.name = tool_class.name
        self.description = tool_class.description

    def _invoke(self, **kwargs) -> str:
        """
        Execute the tool with the given keyword arguments.

        Args:
            **kwargs: Tool input parameters matching the InputModel fields.

        Returns:
            String representation of the tool output.
        """
        validated_inputs = self._input_model(**kwargs)
        result = self._core_tool.execute(inputs=validated_inputs)
        return str(result)

    def to_langchain_tool(self):
        """
        Create a LangChain StructuredTool from this adapter.

        Returns:
            A LangChain StructuredTool instance.
        """
        from langchain_core.tools import StructuredTool

        return StructuredTool.from_function(
            func=self._invoke,
            name=self.name,
            description=self.description,
            args_schema=self._input_model,
        )


def generate_langchain_tool(
    tool_class: type[CoreTool],
    backend: ExecutionBackend,
):
    """
    Generate a LangChain tool for a single core tool.

    Args:
        tool_class: The CoreTool subclass to wrap.
        backend: The execution backend instance.

    Returns:
        A LangChain StructuredTool instance.
    """
    adapter = LangChainToolAdapter(
        tool_class=tool_class,
        backend=backend,
    )
    return adapter.to_langchain_tool()


def generate_langchain_tools(
    backend: ExecutionBackend,
    tool_classes: list[type[CoreTool]] | None = None,
) -> list:
    """
    Generate LangChain tool functions for all core tools.

    Args:
        backend: The execution backend instance.
        tool_classes: Optional list of specific tool classes to generate.
                     If None, generates all available tools.

    Returns:
        List of LangChain tool functions.

    Example:
        from prompttodraft.adapters.generator import generate_langchain_tools
        from prompttodraft.backends.local_backend import LocalBackend

        backend = LocalBackend(project_id="my-project", state_manager=...)
        tools = generate_langchain_tools(backend)

        # Use with LangChain agent:
        from langchain.agents import create_agent
        agent = create_agent(model=model, tools=tools)
    """
    if tool_classes is None:
        tool_classes = get_all_core_tool_classes()

    return [
        generate_langchain_tool(tool_class=tc, backend=backend)
        for tc in tool_classes
    ]


# =============================================================================
# Pydantic-AI Adapter Generator
# =============================================================================


class PydanticAIToolAdapter:
    """
    Adapter that wraps a CoreTool to be compatible with Pydantic-AI's tool interface.

    This class avoids using exec() by creating a closure-based wrapper function.

    Usage:
        from prompttodraft.adapters.generator import PydanticAIToolAdapter
        from prompttodraft.tools.write_file_tool import WriteFileTool

        adapter = PydanticAIToolAdapter(
            tool_class=WriteFileTool,
            backend_attr="backend",
        )
        pydantic_ai_tool = adapter.to_pydantic_ai_tool()
    """

    def __init__(
        self,
        tool_class: type[CoreTool],
        backend_attr: str = "backend",
    ):
        """
        Initialize the Pydantic-AI tool adapter.

        Args:
            tool_class: The CoreTool subclass to wrap.
            backend_attr: Attribute name on deps that holds the backend.
        """
        self._tool_class = tool_class
        self._input_model = tool_class.InputModel
        self._backend_attr = backend_attr
        self.name = tool_class.name
        self.description = tool_class.description

    def _create_tool_function(self):
        """
        Create a tool function that accepts RunContext and **kwargs.

        Returns:
            A function compatible with Pydantic-AI Tool.
        """
        # Capture references in closure
        tool_class = self._tool_class
        input_model = self._input_model
        backend_attr = self._backend_attr

        def tool_function(ctx, **kwargs) -> str:
            """Execute the tool with context and keyword arguments."""
            backend = getattr(ctx.deps, backend_attr)
            core_tool = tool_class(backend=backend)
            validated_inputs = input_model(**kwargs)
            result = core_tool.execute(inputs=validated_inputs)
            return str(result)

        # Set function metadata
        tool_function.__name__ = self.name
        tool_function.__doc__ = self.description

        return tool_function

    def to_pydantic_ai_tool(self):
        """
        Create a Pydantic-AI Tool from this adapter.

        Returns:
            A Pydantic-AI Tool instance.
        """
        from pydantic_ai import Tool

        return Tool(
            function=self._create_tool_function(),
            takes_ctx=True,
            name=self.name,
            description=self.description,
        )


def generate_pydantic_ai_tool(
    tool_class: type[CoreTool],
    backend_attr: str = "backend",
):
    """
    Generate a Pydantic-AI Tool for a single core tool.

    Args:
        tool_class: The CoreTool subclass to wrap.
        backend_attr: Attribute name on deps that holds the backend.

    Returns:
        A Pydantic-AI Tool instance.
    """
    adapter = PydanticAIToolAdapter(
        tool_class=tool_class,
        backend_attr=backend_attr,
    )
    return adapter.to_pydantic_ai_tool()


def generate_pydantic_ai_tools(
    backend_attr: str = "backend",
    tool_classes: list[type[CoreTool]] | None = None,
) -> list:
    """
    Generate Pydantic-AI Tool instances for all core tools.

    Args:
        backend_attr: Name of the attribute on deps that holds the backend.
                     Defaults to "backend".
        tool_classes: Optional list of specific tool classes to generate.
                     If None, generates all available tools.

    Returns:
        List of Pydantic-AI Tool instances.

    Example:
        from dataclasses import dataclass
        from prompttodraft.adapters.generator import generate_pydantic_ai_tools
        from prompttodraft.backends.execution_backend import ExecutionBackend

        @dataclass
        class AgentDependencies:
            backend: ExecutionBackend

        tools = generate_pydantic_ai_tools(backend_attr="backend")

        # Use with Pydantic-AI agent:
        agent = Agent(model=model, deps_type=AgentDependencies, tools=tools)
    """
    if tool_classes is None:
        tool_classes = get_all_core_tool_classes()

    return [
        generate_pydantic_ai_tool(
            tool_class=tc,
            backend_attr=backend_attr,
        )
        for tc in tool_classes
    ]


# =============================================================================
# Utility Functions
# =============================================================================

def _type_to_str(t: type) -> str:
    """
    Convert a Python type to its string representation for code generation.

    Args:
        t: Python type or generic type.

    Returns:
        String representation suitable for code generation.
    """
    import types
    from typing import Union, get_origin, get_args

    # Handle None type
    if t is type(None):
        return "None"

    # Handle union types (e.g., str | None) - Python 3.10+ UnionType
    if isinstance(t, types.UnionType):
        args = get_args(t)
        return " | ".join(_type_to_str(arg) for arg in args)

    # Handle typing.Union types
    origin = get_origin(t)

    if origin is Union:
        args = get_args(t)
        return " | ".join(_type_to_str(arg) for arg in args)

    # Handle list[T]
    if origin is list:
        args = get_args(t)
        if args:
            return f"list[{_type_to_str(args[0])}]"
        return "list"

    # Handle dict[K, V]
    if origin is dict:
        args = get_args(t)
        if len(args) == 2:
            return f"dict[{_type_to_str(args[0])}, {_type_to_str(args[1])}]"
        return "dict"

    # Basic types - check for __name__ attribute
    if hasattr(t, "__name__"):
        return t.__name__

    # Fallback for other types
    return str(t)
