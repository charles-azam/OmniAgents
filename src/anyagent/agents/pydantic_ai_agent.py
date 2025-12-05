"""
Pydantic-AI based coding agent implementation.
"""
import os

from pydantic_ai import Agent, Tool as PydanticAITool
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from openai import AsyncOpenAI

from anyagent.agents.base import AgentFactory
from anyagent.tools.base_tool import CoreBackendTool
from anyagent.backends.execution_backend import ExecutionBackend
from anyagent.presets.base import Preset


def get_pydantic_ai_model_example(model_name: str = "openai/gpt-oss-120b:cerebras") -> OpenAIChatModel:
    if "gpt-5" in model_name:
        return OpenAIChatModel(model_name=model_name)
    elif "gpt-oss-120b" in model_name:
        hf_client = AsyncOpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=os.getenv("HF_TOKEN"),
        )
        hf_provider = OpenAIProvider(openai_client=hf_client)
        return OpenAIChatModel(model_name=model_name, provider=hf_provider)
    else:
        raise ValueError(f"Invalid model name: {model_name}")


class PydanticAIAgent(AgentFactory[OpenAIChatModel, PydanticAITool]):
    """
    Pydantic-AI based coding agent.

    Example:
        from anyagent.backends.local_backend import LocalBackend
        from anyagent.backends.state_manager import NoOpStateManager
        from anyagent.presets.python import PythonUVPreset

        backend = LocalBackend(project_id="my-app", state_manager=NoOpStateManager())
        model = get_pydantic_ai_model_example()

        agent = PydanticAIAgent(
            backend=backend,
            model=model,
            preset=PythonUVPreset(),
        )
        result = agent.run("Create a FastAPI server")
    """

    def __init__(
        self,
        backend: ExecutionBackend,
        model: OpenAIChatModel,
        preset: Preset | None = None,
        extra_tool_classes: list[type[CoreBackendTool]] | None = None,
        native_tools: list[PydanticAITool] | None = None,
        enable_logfire: bool = False,
    ) -> None:
        self._enable_logfire = enable_logfire
        super().__init__(
            backend=backend,
            model=model,
            preset=preset,
            extra_tool_classes=extra_tool_classes,
            native_tools=native_tools,
        )

    def _convert_tool(self, tool: CoreBackendTool) -> PydanticAITool:
        return tool.to_pydantic_ai_tool()

    def _run_agent(self, task: str) -> str:
        from anyagent.prompts.system_prompt import get_system_prompt

        if self._enable_logfire:
            import logfire
            logfire.configure(console=logfire.ConsoleOptions(verbose=True, colors="auto"))
            logfire.instrument_pydantic_ai()

        system_prompt = get_system_prompt(backend=self.backend, model_id="pydantic_ai")

        agent = Agent[str](
            model=self.model,
            system_prompt=system_prompt,
            tools=self.tools,
        )

        result = agent.run_sync(user_prompt=task)
        return result.output
