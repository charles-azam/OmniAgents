"""
Base class for all core tools.

This module defines the abstract base classes that all core tools inherit from.
Tools use Pydantic models for automatic validation and schema generation.

- CoreTool: Base class for pure computation tools (no backend required)
- CoreBackendTool: Base class for tools that need filesystem/command access
"""
from abc import ABC, abstractmethod
from typing import ClassVar, TypeVar, Generic, get_args, get_origin

from pydantic import BaseModel

from prompttodraft.backends.execution_backend import ExecutionBackend
from prompttodraft.outputs.outputs import ToolOutputModel


TInput = TypeVar('TInput', bound=BaseModel)
TOutput = TypeVar('TOutput', bound=ToolOutputModel)


class CoreTool(ABC, Generic[TInput, TOutput]):
    """
    Abstract base class for all tools with strong typing.

    All tools must:
    - Inherit with Generic parameters: CoreTool[InputModel, OutputModel]
    - Define name: Tool name (string)
    - Define description: Tool description (string)
    - Implement execute: Method to execute the tool

    Input and output models are extracted from Generic parameters using
    helper methods, providing type safety without runtime magic.

    Example:
        class MyInput(BaseModel):
            path: str

        class MyTool(CoreBackendTool[MyInput, TextOutputModel]):
            name = "my_tool"
            description = "Does something"

            def execute(self, inputs: MyInput) -> TextOutputModel:
                # Full type safety here!
                return TextOutputModel(content=inputs.path)
    """

    name: ClassVar[str]
    description: ClassVar[str]

    @classmethod
    def get_input_model(cls) -> type[BaseModel]:
        """
        Extract InputModel from Generic parameters.

        Returns:
            The input model class (TInput from Generic parameters)

        Raises:
            TypeError: If Generic parameters are not specified
        """
        if hasattr(cls, '__orig_bases__'):
            for base in cls.__orig_bases__:
                origin = get_origin(base)
                # Check if this base is CoreTool or CoreBackendTool
                if origin is CoreTool or (origin is not None and issubclass(origin, CoreTool)):
                    args = get_args(base)
                    if args and len(args) >= 1:
                        return args[0]
        raise TypeError(f"{cls.__name__} must specify Generic parameters: CoreTool[InputModel, OutputModel]")

    @classmethod
    def get_output_model(cls) -> type[ToolOutputModel]:
        """
        Extract OutputModel from Generic parameters.

        Returns:
            The output model class (TOutput from Generic parameters)

        Raises:
            TypeError: If Generic parameters are not specified
        """
        if hasattr(cls, '__orig_bases__'):
            for base in cls.__orig_bases__:
                origin = get_origin(base)
                # Check if this base is CoreTool or CoreBackendTool
                if origin is CoreTool or (origin is not None and issubclass(origin, CoreTool)):
                    args = get_args(base)
                    if args and len(args) >= 2:
                        return args[1]
        raise TypeError(f"{cls.__name__} must specify Generic parameters: CoreTool[InputModel, OutputModel]")

    @abstractmethod
    def execute(self, inputs: TInput) -> TOutput:
        """
        Execute the tool with validated Pydantic inputs.

        Args:
            inputs: Validated input model instance (type matches TInput from Generic parameters)

        Returns:
            ToolOutputModel instance (type matches TOutput from Generic parameters)
        """
        ...

    @classmethod
    def get_input_schema(cls) -> dict:
        """
        Get JSON Schema for this tool's inputs.

        Returns:
            JSON Schema dict generated from InputModel
        """
        return cls.get_input_model().model_json_schema()

    @classmethod
    def get_output_schema(cls) -> dict:
        """
        Get JSON Schema for this tool's outputs.

        Returns:
            JSON Schema dict generated from OutputModel
        """
        return cls.get_output_model().model_json_schema()

    @classmethod
    def get_tool_definition(cls) -> dict:
        """
        Get complete tool definition for adapter generation.

        Returns:
            Dict with name, description, input_schema, and output_schema
        """
        return {
            "name": cls.name,
            "description": cls.description,
            "input_schema": cls.get_input_schema(),
            "output_schema": cls.get_output_schema(),
        }


class CoreBackendTool(CoreTool[TInput, TOutput]):
    """
    Abstract base class for tools that require an execution backend.

    Use this for tools that need filesystem operations, command execution,
    or other backend capabilities (local, docker, e2b).

    Inherits the Generic typing from CoreTool, so tools should use:
        CoreBackendTool[InputModel, OutputModel]
    """

    def __init__(self, backend: ExecutionBackend):
        """
        Initialize the tool with an execution backend.

        Args:
            backend: The execution backend to use (local, docker, e2b)
        """
        self.backend = backend
