"""
Base class for all core tools.

This module defines the abstract base classes that all core tools inherit from.
Tools use Pydantic models for automatic validation and schema generation.

- CoreTool: Base class for pure computation tools (no backend required)
- CoreBackendTool: Base class for tools that need filesystem/command access
"""
from abc import ABC, abstractmethod
from typing import ClassVar, TypeVar, Generic, get_args, get_origin, Any

from pydantic import BaseModel

from prompttodraft.backends.execution_backend import ExecutionBackend
from prompttodraft.outputs.outputs import ToolOutputModel
from smolagents.tools import Tool as SmolagentsTool
from langchain_core.tools import Tool as LangChainTool
from pydantic_ai import Tool as PydanticAITool

TInput = TypeVar('TInput', bound=BaseModel)
TOutput = TypeVar('TOutput', bound=ToolOutputModel | BaseModel)


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

    @abstractmethod
    def execute(self, inputs: TInput) -> TOutput:
        ...

    def execute_unpacked(self, **kwargs: Any) -> TOutput:
        input_model = self.get_input_model()
        pydantic_inputs = input_model.model_validate(kwargs)
        return self.execute(inputs=pydantic_inputs)
    
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
        
    def to_smolagents_tool(main_class_self, use_string_outputs: bool = True) -> type[SmolagentsTool]:
        """
        Convert the tool to a smolagents Tool.

        Returns:
            A smolagents Tool instance.
        """

        # Convert JSON schema to smolagents format
        input_schema = main_class_self.get_input_schema()
        smolagents_inputs = {}

        if "properties" in input_schema:
            for param_name, param_schema in input_schema["properties"].items():
                smolagents_inputs[param_name] = {
                    "type": param_schema.get("type", "string"),
                    "description": param_schema.get("description", f"Parameter {param_name}")
                }

        class CustomSmolagentsTool(SmolagentsTool):
            name = main_class_self.name
            description = main_class_self.description
            inputs = smolagents_inputs
            output_type = "string" if use_string_outputs else "any"
            skip_forward_signature_validation = True

            def forward(self, **kwargs: Any) -> str | Any:
                return main_class_self.execute_unpacked(**kwargs)

        return CustomSmolagentsTool
        
    def to_langchain_tool(self) -> LangChainTool:
        """
        Convert the tool to a LangChain tool.

        Returns:
            A LangChain tool instance.
        """
        return LangChainTool(
            name=self.name,
            description=self.description,
            inputs=self.get_input_schema(),
            outputs=self.get_output_schema(),
        )
    def to_pydantic_ai_tool(self) -> PydanticAITool:
        """
        Convert the tool to a Pydantic-AI tool.

        Returns:
            A Pydantic-AI tool instance.
        """
        return PydanticAITool(
            name=self.name,)


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

    def to_smolagents_tool(self, use_string_outputs: bool = True) -> type[SmolagentsTool]:
        CustomSmolagentsTool = super().to_smolagents_tool(use_string_outputs)
        class BackendCustomSmolagentsTool(CustomSmolagentsTool):
            def __init__(self, backend: ExecutionBackend):
                self.backend = backend
            
        return BackendCustomSmolagentsTool