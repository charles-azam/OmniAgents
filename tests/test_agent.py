"""
Test the new Gemini-style agent implementation.

This test verifies that the agent can be created with different backends
and has access to all 9 tools.
"""
import os
from prompttodraft.tools.agent import create_agent
from prompttodraft.tools.factory import ToolFactory
from prompttodraft.tools.backends.local_backend import LocalBackend


def test_agent_creation():
    """Test that the agent can be created with default settings."""
    print("Testing agent creation...")

    # Create agent with defaults (LocalBackend, Groq model)
    agent = create_agent(cwd=os.getcwd(), log_file=None)

    # Verify agent has tools (9 custom tools + 1 built-in final_answer tool)
    assert len(agent.tools) == 10, f"Expected 10 tools, got {len(agent.tools)}"

    # Verify tool names (including smolagents' built-in final_answer tool)
    expected_tool_names = {
        "write_file",
        "read_file",
        "list_directory",
        "glob",
        "search_file_content",
        "replace",
        "run_shell_command",
        "read_many_files",
        "save_memory",
        "final_answer",  # Built-in smolagents tool
    }

    actual_tool_names = set(agent.tools.keys())
    assert actual_tool_names == expected_tool_names, f"Tool names mismatch: {actual_tool_names}"

    print(f"✓ Agent created successfully with {len(agent.tools)} tools")
    print(f"  Custom Tools: {', '.join(sorted([t for t in agent.tools.keys() if t != 'final_answer']))}")


def test_agent_with_custom_backend():
    """Test that the agent can be created with a custom backend."""
    print("\nTesting agent with custom backend...")

    # Create a LocalBackend
    backend = LocalBackend(project_id="test_agent")
    backend.start()

    # Create agent with custom backend
    agent = create_agent(cwd=os.getcwd(), backend=backend, log_file=None)

    # Verify agent has tools (9 custom tools + 1 built-in final_answer tool)
    assert len(agent.tools) == 10

    print("✓ Agent created successfully with custom backend")

    # Cleanup
    backend.shutdown()


def test_system_prompt_generation():
    """Test that system prompt is generated correctly."""
    print("\nTesting system prompt generation...")

    from prompttodraft.tools.system_prompt import get_system_prompt

    # Generate system prompt
    system_prompt = get_system_prompt(cwd=os.getcwd())

    # Verify prompt contains key sections
    assert "Core Mandates" in system_prompt
    assert "Primary Workflows" in system_prompt
    assert "Operational Guidelines" in system_prompt
    assert "Memory" in system_prompt
    assert "directoryStructure" in system_prompt

    # Verify placeholders are replaced
    assert "{working_directory}" not in system_prompt
    assert "{is_git_repo}" not in system_prompt
    assert "{platform}" not in system_prompt
    assert "{date}" not in system_prompt
    assert "{model}" not in system_prompt

    print("✓ System prompt generated correctly")
    print(f"  Prompt length: {len(system_prompt)} characters")


def test_tool_factory():
    """Test that ToolFactory creates tools correctly."""
    print("\nTesting ToolFactory...")

    # Create backend
    backend = LocalBackend(project_id="test_factory")
    backend.start()

    # Create tools
    tools = ToolFactory.create_smolagents_tools(backend=backend)

    # Verify we created 9 custom tools (final_answer is added by smolagents when creating the agent)
    assert len(tools) == 9

    # Verify each tool has correct attributes
    for tool in tools:
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert hasattr(tool, "forward")

    print(f"✓ ToolFactory created {len(tools)} tools successfully")

    # Cleanup
    backend.shutdown()


if __name__ == "__main__":
    print("="*80)
    print("Testing Gemini-style Agent Implementation")
    print("="*80)

    test_agent_creation()
    test_agent_with_custom_backend()
    test_system_prompt_generation()
    test_tool_factory()

    print("\n" + "="*80)
    print("✅ ALL AGENT TESTS PASSED!")
    print("="*80)
