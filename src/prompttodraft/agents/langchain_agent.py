"""
LangChain-based coding agent implementation.
"""
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool as LangChainTool
from langsmith import traceable
import os

from prompttodraft.agents.base import AgentFactory
from prompttodraft.tools.base_tool import CoreBackendTool


def get_langchain_model_example(model_name: str = "openai/gpt-oss-120b:cerebras") -> ChatOpenAI:
    if "gpt-5" in model_name:
        return ChatOpenAI(model=model_name)
    elif "gpt-oss-120b" in model_name:
        return ChatOpenAI(base_url="https://router.huggingface.co/v1", api_key=os.environ["HF_TOKEN"], model=model_name)
    else:
        raise ValueError(f"Invalid model name: {model_name}")


class LangChainAgent(AgentFactory[BaseChatModel, LangChainTool]):
    """
    LangChain-based coding agent.

    Example:
        from prompttodraft.backends.local_backend import LocalBackend
        from prompttodraft.backends.state_manager import NoOpStateManager
        from prompttodraft.presets.python import PythonUVPreset

        backend = LocalBackend(project_id="my-app", state_manager=NoOpStateManager())
        model = ChatOpenAI(model="gpt-4")

        agent = LangChainAgent(
            backend=backend,
            model=model,
            preset=PythonUVPreset(),
        )
        result = agent.run("Create a FastAPI server")
    """

    def _convert_tool(self, tool: CoreBackendTool) -> LangChainTool:
        return tool.to_langchain_tool()

    @traceable
    def _run_agent(self, task: str) -> str:
        agent_executor = create_agent(model=self.model, tools=self.tools)
        result = agent_executor.invoke(input={"messages": [("user", task)]})

        if "messages" in result:
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                return last_message.content
            return str(last_message)

        return str(result)
