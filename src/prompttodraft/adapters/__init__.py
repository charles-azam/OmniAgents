"""
Automatic adapter generation for AI frameworks.

This module provides zero-boilerplate tool generation for popular AI frameworks.
Write tools once, run with any framework.

Example:
    # Generate tools for LangChain
    from prompttodraft.adapters import generate_langchain_tools
    tools = generate_langchain_tools(backend)

    # Generate tools for smolagents
    from prompttodraft.adapters import generate_smolagents_tools
    tools = generate_smolagents_tools(backend)

    # Generate tools for Pydantic-AI
    from prompttodraft.adapters import generate_pydantic_ai_tools
    tools = generate_pydantic_ai_tools(deps_type=MyDeps)
"""
from prompttodraft.adapters.generator import (
    generate_smolagents_tools,
    generate_smolagents_tool,
    generate_langchain_tools,
    generate_langchain_tool,
    generate_pydantic_ai_tools,
    generate_pydantic_ai_tool,
    get_all_core_tool_classes,
)

__all__ = [
    "generate_smolagents_tools",
    "generate_smolagents_tool",
    "generate_langchain_tools",
    "generate_langchain_tool",
    "generate_pydantic_ai_tools",
    "generate_pydantic_ai_tool",
    "get_all_core_tool_classes",
]
