"""
UserInputToolCore - Framework-agnostic user input tool.

Extracted from smolcc/tools/user_input_tool.py with business logic separated from execution.
"""
from prompttodraft.tools.core.metadata import ToolMetadata
from prompttodraft.tools.backends.execution_backend import ExecutionBackend
from prompttodraft.tools.outputs.models import (
    TextOutputModel,
    ToolOutputModel,
)


class UserInputToolCore:
    """
    Framework-agnostic user input tool.

    Extracted from smolcc/tools/user_input_tool.py:10-37
    """

    # Metadata (from user_input_tool.py:15-20)
    metadata = ToolMetadata(
        name="UserInput",
        description="Ask the user a question and get their response. Use this when you need information from the user to proceed.",
        inputs={
            "question": {
                "type": "string",
                "description": "The question to ask the user"
            }
        },
        output_type="string"
    )

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize UserInputToolCore with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    def execute(
        self,
        question: str
    ) -> ToolOutputModel:
        """
        Ask the user a question and return their response (from user_input_tool.py:22-33).

        Args:
            question: The question to ask the user

        Returns:
            A TextOutputModel with the user's response
        """
        user_input = input(f"\n[USER INPUT REQUESTED] {question}\n> ")
        return TextOutputModel(content=user_input)
