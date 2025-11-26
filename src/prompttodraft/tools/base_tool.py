"""
Base class for all core tools.

This module defines the abstract base class that all core tools inherit from.
Tools use Pydantic models for automatic validation and schema generation.
"""
from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel

from prompttodraft.backends.execution_backend import ExecutionBackend


class CoreTool(ABC):
    """
    Abstract base class for all core tools.

    All tools must define:
    - name: Tool name (string)
    - description: Tool description (string)
    - InputModel: Pydantic model defining input parameters
    - OutputModel: Pydantic model defining output structure
    - execute: Method to execute the tool

    This base class ensures consistency across all tools and enables
    automatic adapter generation using Pydantic's model_json_schema().
    """

    name: ClassVar[str]
    description: ClassVar[str]
    InputModel: ClassVar[type[BaseModel]]
    OutputModel: ClassVar[type[BaseModel]]

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize the tool with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend

    @abstractmethod
    def execute(self, inputs: BaseModel) -> BaseModel:
        """
        Execute the tool with validated Pydantic inputs.

        Args:
            inputs: Validated input model instance (type matches self.InputModel)

        Returns:
            Pydantic BaseModel with the tool's output (type matches self.OutputModel)
        """
        pass

    @classmethod
    def get_input_schema(cls) -> dict:
        """
        Get JSON Schema for this tool's inputs.

        Returns:
            JSON Schema dict generated from InputModel
        """
        return cls.InputModel.model_json_schema()

    @classmethod
    def get_output_schema(cls) -> dict:
        """
        Get JSON Schema for this tool's outputs.

        Returns:
            JSON Schema dict generated from OutputModel
        """
        return cls.OutputModel.model_json_schema()

    @classmethod
    def get_json_schema(cls) -> dict:
        """
        Get JSON Schema for this tool's inputs (for backward compatibility).

        Returns:
            JSON Schema dict generated from InputModel
        """
        return cls.get_input_schema()
