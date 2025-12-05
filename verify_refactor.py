"""
Verification script for PromptToDraft refactoring.
"""
from prompttodraft.api import AgentFactory
from prompttodraft.profiles.empty_profile import EmptyProfile
from prompttodraft.profiles.python_uv_profile import PythonUVProfile

def test_api_creation():
    print("Testing AgentFactory...")
    
    # Test Python UV Agent creation
    agent_uv = AgentFactory.create_agent(
        framework="langchain",
        language="python-uv",
        project_id="test-api-uv"
    )
    assert isinstance(agent_uv.profile, PythonUVProfile)
    print("✓ Python UV Agent created successfully")
    
    # Test Empty Agent creation
    agent_empty = AgentFactory.create_agent(
        framework="langchain",
        language="empty",
        project_id="test-api-empty"
    )
    assert isinstance(agent_empty.profile, EmptyProfile)
    print("✓ Empty Agent created successfully")
    
    # Verify tools
    uv_tools = agent_uv.profile.get_tools(agent_uv.backend)
    assert len(uv_tools) == 1
    assert uv_tools[0].name == "uv"
    print("✓ Python UV Profile has uv tool")
    
    empty_tools = agent_empty.profile.get_tools(agent_empty.backend)
    assert len(empty_tools) == 0
    print("✓ Empty Profile has no tools")

if __name__ == "__main__":
    test_api_creation()
