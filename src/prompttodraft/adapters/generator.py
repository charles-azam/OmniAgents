"""
Automatic adapter generation for AI frameworks.

This module provides functions to automatically generate framework-specific
tool wrappers from core tools, eliminating manual boilerplate.

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
from typing import Callable
from prompttodraft.backends.execution_backend import ExecutionBackend
from prompttodraft.tools.base_tool import CoreTool
from prompttodraft.tools.metadata import ToolMetadata


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


def extract_parameter_info(metadata: ToolMetadata) -> list[tuple[str, type, object]]:
    """
    Extract parameter information from tool metadata.

    Args:
        metadata: Tool metadata with inputs specification.

    Returns:
        List of (name, type, default) tuples, sorted with required params first.
    """
    params = []

    for param_name, input_spec in metadata.inputs.items():
        python_type = get_python_type_for_input(input_spec)
        default = get_default_for_input(input_spec)
        params.append((param_name, python_type, default))

    # Sort: required parameters (default=...) first, then optional ones
    params.sort(key=lambda p: (p[2] is not ..., p[0]))

    return params


# =============================================================================
# smolagents Adapter Generator
# =============================================================================

def generate_smolagents_tool(
    tool_class: type[CoreTool],
    backend: ExecutionBackend,
):
    """
    Generate a smolagents Tool class for a single core tool.

    Args:
        tool_class: The CoreTool subclass to wrap.
        backend: The execution backend instance.

    Returns:
        An instance of a dynamically created smolagents Tool class.
    """
    from smolagents import Tool

    # Create an instance to get metadata
    core_tool = tool_class(backend=backend)
    metadata = core_tool.metadata

    # Build inputs dict for smolagents format
    smolagents_inputs = {}
    for param_name, input_spec in metadata.inputs.items():
        smolagents_input = {
            "type": input_spec.get("type", "string"),
            "description": input_spec.get("description", ""),
        }
        if input_spec.get("nullable", False):
            smolagents_input["nullable"] = True
        if "items" in input_spec:
            smolagents_input["items"] = input_spec["items"]
        smolagents_inputs[param_name] = smolagents_input

    # Extract parameter info for forward method signature
    params = extract_parameter_info(metadata)

    # Build forward method signature dynamically
    # smolagents requires exact parameter names matching inputs
    param_strs = []
    for param_name, param_type, default in params:
        type_str = _type_to_str(param_type)
        if default is ...:
            param_strs.append(f"{param_name}: {type_str}")
        elif default is None:
            param_strs.append(f"{param_name}: {type_str} = None")
        else:
            param_strs.append(f"{param_name}: {type_str} = {repr(default)}")

    params_str = ", ".join(param_strs)
    param_names = [p[0] for p in params]
    kwargs_str = ", ".join(f"{name}={name}" for name in param_names)

    # Create the forward method code
    forward_code = f'''
def forward(self, {params_str}) -> str:
    result = self._core_tool.execute({kwargs_str})
    return str(result)
'''

    # Create __init__ method
    init_code = '''
def __init__(self):
    super(self.__class__, self).__init__()
'''

    # Execute to create the methods
    namespace = {"_core_tool": core_tool}
    exec(init_code, namespace)
    exec(forward_code, namespace)

    # Create the Tool subclass dynamically
    class_dict = {
        "name": metadata.name,
        "description": metadata.description,
        "inputs": smolagents_inputs,
        "output_type": metadata.output_type,
        "_core_tool": core_tool,
        "__init__": namespace["__init__"],
        "forward": namespace["forward"],
    }

    # Create the class
    tool_class_name = f"{metadata.name.title().replace('_', '')}SmolagentsTool"
    SmolagentsTool = type(tool_class_name, (Tool,), class_dict)

    return SmolagentsTool()


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

def generate_langchain_tool(
    tool_class: type[CoreTool],
    backend: ExecutionBackend,
) -> Callable:
    """
    Generate a LangChain tool function for a single core tool.

    Args:
        tool_class: The CoreTool subclass to wrap.
        backend: The execution backend instance.

    Returns:
        A LangChain-decorated tool function.
    """
    from langchain_core.tools import tool

    # Create instance to get metadata
    core_tool = tool_class(backend=backend)
    metadata = core_tool.metadata

    # Extract parameter info
    params = extract_parameter_info(metadata)

    # Build the function signature dynamically using exec
    # This is necessary to get proper type hints that LangChain can inspect
    param_strs = []
    for param_name, param_type, default in params:
        type_str = _type_to_str(param_type)
        if default is ...:
            param_strs.append(f"{param_name}: {type_str}")
        elif default is None:
            param_strs.append(f"{param_name}: {type_str} = None")
        else:
            param_strs.append(f"{param_name}: {type_str} = {repr(default)}")

    params_str = ", ".join(param_strs)
    param_names = [p[0] for p in params]
    kwargs_str = ", ".join(f"{name}={name}" for name in param_names)

    # Create the function code
    func_code = f'''
def {metadata.name}({params_str}) -> str:
    """
    {metadata.description}
    """
    result = _core_tool.execute({kwargs_str})
    return str(result)
'''

    # Execute in a namespace with access to core_tool
    namespace = {"_core_tool": core_tool}
    exec(func_code, namespace)

    # Get the function and decorate it
    func = namespace[metadata.name]
    decorated_func = tool(description=metadata.description)(func)

    return decorated_func


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

def generate_pydantic_ai_tool(
    tool_class: type[CoreTool],
    deps_type: type,
    backend_attr: str = "backend",
):
    """
    Generate a Pydantic-AI Tool for a single core tool.

    Args:
        tool_class: The CoreTool subclass to wrap.
        deps_type: The dependencies dataclass type (e.g., AgentDependencies).
        backend_attr: Attribute name on deps that holds the backend.

    Returns:
        A Pydantic-AI Tool instance.
    """
    from pydantic_ai import Tool, RunContext

    # Create a dummy instance to get metadata
    class _DummyBackend:
        pass

    dummy_tool = tool_class(backend=_DummyBackend())  # type: ignore
    metadata = dummy_tool.metadata

    # Extract parameter info
    params = extract_parameter_info(metadata)

    # Build the function dynamically
    param_strs = ["ctx: RunContext"]
    for param_name, param_type, default in params:
        type_str = _type_to_str(param_type)
        if default is ...:
            param_strs.append(f"{param_name}: {type_str}")
        elif default is None:
            param_strs.append(f"{param_name}: {type_str} = None")
        else:
            param_strs.append(f"{param_name}: {type_str} = {repr(default)}")

    params_str = ", ".join(param_strs)
    param_names = [p[0] for p in params]
    kwargs_str = ", ".join(f"{name}={name}" for name in param_names)

    func_code = f'''
def {metadata.name}({params_str}) -> str:
    """
    {metadata.description}
    """
    backend = getattr(ctx.deps, "{backend_attr}")
    core_tool = _tool_class(backend=backend)
    result = core_tool.execute({kwargs_str})
    return str(result)
'''

    namespace = {
        "_tool_class": tool_class,
        "RunContext": RunContext,
    }
    exec(func_code, namespace)

    func = namespace[metadata.name]

    return Tool(
        function=func,
        takes_ctx=True,
        name=metadata.name,
        description=metadata.description,
    )


def generate_pydantic_ai_tools(
    deps_type: type,
    backend_attr: str = "backend",
    tool_classes: list[type[CoreTool]] | None = None,
) -> list:
    """
    Generate Pydantic-AI Tool instances for all core tools.

    Args:
        deps_type: The dependencies dataclass type that will be passed via RunContext.
                  Must have an attribute containing the ExecutionBackend.
        backend_attr: Name of the attribute on deps_type that holds the backend.
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

        tools = generate_pydantic_ai_tools(
            deps_type=AgentDependencies,
            backend_attr="backend",
        )

        # Use with Pydantic-AI agent:
        agent = Agent(model=model, deps_type=AgentDependencies, tools=tools)
    """
    if tool_classes is None:
        tool_classes = get_all_core_tool_classes()

    return [
        generate_pydantic_ai_tool(
            tool_class=tc,
            deps_type=deps_type,
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
