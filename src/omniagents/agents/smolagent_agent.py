"""
Smolagents-based coding agent implementation.
"""
from smolagents import ToolCallingAgent, OpenAIModel, InferenceClientModel
from smolagents.tools import Tool as SmolagentsTool

from omniagents.agents.base import AgentFactory
from omniagents.tools.base_tool import CoreBackendTool
from omniagents.backends.execution_backend import ExecutionBackend
from omniagents.presets.base import Preset


def get_smolagents_model_example(model_name: str = "openai/gpt-oss-120b") -> OpenAIModel | InferenceClientModel:
    if "gpt-5" in model_name:
        return OpenAIModel(model_id=model_name)
    elif "gpt-oss-120b" in model_name:
        return InferenceClientModel(model_id=model_name, provider="cerebras")
    else:
        raise ValueError(f"Invalid model name: {model_name}")


class SmolagentsAgent(AgentFactory[OpenAIModel | InferenceClientModel, SmolagentsTool]):
    """
    Smolagents-based coding agent.

    Example:
        from omniagents.backends.local_backend import LocalBackend
        from omniagents.backends.state_manager import NoOpStateManager
        from omniagents.presets.python import PythonUVPreset

        backend = LocalBackend(project_id="my-app", state_manager=NoOpStateManager())
        model = InferenceClientModel(model_id="openai/gpt-oss-120b", provider="cerebras")

        agent = SmolagentsAgent(
            backend=backend,
            model=model,
            preset=PythonUVPreset(),
            max_steps=30,
        )
        result = agent.run("Create a FastAPI server")
    """

    def __init__(
        self,
        backend: ExecutionBackend,
        model: OpenAIModel | InferenceClientModel,
        preset: Preset | None = None,
        extra_tool_classes: list[type[CoreBackendTool]] | None = None,
        native_tools: list[SmolagentsTool] | None = None,
        max_steps: int = 30,
    ) -> None:
        self.max_steps = max_steps
        super().__init__(
            backend=backend,
            model=model,
            preset=preset,
            extra_tool_classes=extra_tool_classes,
            native_tools=native_tools,
        )

    def _convert_tool(self, tool: CoreBackendTool) -> SmolagentsTool:
        return tool.to_smolagents_tool()

    def _run_agent(self, task: str) -> str:
        from omniagents.prompts.system_prompt import get_system_prompt

        instructions = get_system_prompt(backend=self.backend, model_id="smolagents")

        agent = ToolCallingAgent(
            tools=self.tools,
            model=self.model,
            max_steps=self.max_steps,
            instructions=instructions,
        )

        result = agent.run(task=task)
        return result
