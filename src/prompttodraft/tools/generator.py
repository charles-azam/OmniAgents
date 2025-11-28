from prompttodraft.tools.base_tool import CoreTool
from prompttodraft.tools.write_file_tool import WriteFileTool
from prompttodraft.agents.pydantic_ai_agent import WriteFileTool

def generate_tools(backend: ExecutionBackend) -> list[CoreTool]: