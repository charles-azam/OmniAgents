"""
Adapter Generator Demo

This example demonstrates the zero-boilerplate tool generation feature.
Write tools once, use them with any AI framework.

Key benefits:
- No manual wrapper classes needed
- Same core tools work with smolagents, LangChain, and Pydantic-AI
- Type-safe parameter handling
- Consistent behavior across frameworks
"""
from anyagents.adapters.generator import (
    generate_smolagents_tools,
    generate_langchain_tools,
    generate_pydantic_ai_tools,
    get_all_core_tool_classes,
)
from anyagents.backends.local_backend import LocalBackend
from anyagents.backends.state_manager import NoOpStateManager
from dataclasses import dataclass
from anyagents.backends.execution_backend import ExecutionBackend


# For Pydantic-AI, we need a dependencies class
@dataclass
class AgentDeps:
    backend: ExecutionBackend


def demo_smolagents():
    """Demo: Generate smolagents tools."""
    print("\n" + "=" * 60)
    print("SMOLAGENTS ADAPTER DEMO")
    print("=" * 60)

    backend = LocalBackend(
        project_id="demo-smolagents",
        state_manager=NoOpStateManager(),
    )

    # Generate all 10 tools with one line
    tools = generate_smolagents_tools(backend=backend)

    print(f"\nGenerated {len(tools)} smolagents tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:50]}...")

    # Or generate specific tools only
    from anyagents.tools.write_file_tool import WriteFileTool
    from anyagents.tools.read_file_tool import ReadFileTool

    subset_tools = generate_smolagents_tools(
        backend=backend,
        tool_classes=[WriteFileTool, ReadFileTool],
    )
    print(f"\nSubset generation: {len(subset_tools)} tools")


def demo_langchain():
    """Demo: Generate LangChain tools."""
    print("\n" + "=" * 60)
    print("LANGCHAIN ADAPTER DEMO")
    print("=" * 60)

    backend = LocalBackend(
        project_id="demo-langchain",
        state_manager=NoOpStateManager(),
    )

    # Generate all 10 tools with one line
    tools = generate_langchain_tools(backend=backend)

    print(f"\nGenerated {len(tools)} LangChain tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:50]}...")

    # Each tool can be used with LangChain's invoke method
    print("\nTool inspection:")
    write_tool = next(t for t in tools if t.name == "write_file")
    print(f"  Name: {write_tool.name}")
    print(f"  Has invoke: {hasattr(write_tool, 'invoke')}")


def demo_pydantic_ai():
    """Demo: Generate Pydantic-AI tools."""
    print("\n" + "=" * 60)
    print("PYDANTIC-AI ADAPTER DEMO")
    print("=" * 60)

    # Generate all 10 tools with one line
    # Note: Pydantic-AI tools use RunContext for dependency injection
    tools = generate_pydantic_ai_tools(
        deps_type=AgentDeps,
        backend_attr="backend",
    )

    print(f"\nGenerated {len(tools)} Pydantic-AI tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:50]}...")

    # Each tool takes context as first parameter
    print("\nTool properties:")
    write_tool = next(t for t in tools if t.name == "write_file")
    print(f"  Name: {write_tool.name}")
    print(f"  Takes context: {write_tool.takes_ctx}")


def show_available_tools():
    """Show all available core tools."""
    print("\n" + "=" * 60)
    print("AVAILABLE CORE TOOLS")
    print("=" * 60)

    tool_classes = get_all_core_tool_classes()

    print(f"\n{len(tool_classes)} core tools available:\n")
    for tc in tool_classes:
        print(f"  {tc.__name__}")
        print(f"    → {tc.metadata.name}")
        print(f"    → {tc.metadata.description[:60]}...")
        print()
        
def test():
    from anyagents.tools.write_file_tool import WriteFileTool
    
    write_file_tool = WriteFileTool(backend=None)
    pass


def main():
    test()
    """Run all demos."""
    print("\n" + "#" * 60)
    print("#  ANYAGENTS ADAPTER GENERATOR DEMO")
    print("#  Zero-boilerplate tool generation for AI frameworks")
    print("#" * 60)

    show_available_tools()
    demo_smolagents()
    demo_langchain()
    demo_pydantic_ai()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
Before adapter generator:
  - 280+ lines per framework for manual wrappers
  - Duplicate code across frameworks
  - Manual maintenance of parameter signatures

After adapter generator:
  - 1 line to generate all tools: generate_*_tools(backend)
  - Automatic type inference from metadata
  - Framework-specific signatures generated dynamically
  - Single source of truth for tool behavior
""")


if __name__ == "__main__":
    main()
