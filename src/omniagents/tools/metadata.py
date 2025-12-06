"""
Tool metadata definitions.

This module defines the metadata structure for tools, which is framework-agnostic
and can be transformed into different framework-specific formats.
"""
from dataclasses import dataclass, field


@dataclass
class ToolMetadata:
    """Metadata for a tool (name, description, inputs, outputs)."""

    name: str
    description: str
    inputs: dict[str, dict[str, str | bool | None]]
    output_type: str
    metadata: dict[str, str | int | bool] = field(default_factory=dict)

    def to_smolagents_format(self) -> dict[str, str | dict[str, dict[str, str | bool | None]]]:
        """
        Convert metadata to smolagents Tool format.

        Returns:
            Dictionary with name, description, inputs, output_type
        """
        return {
            "name": self.name,
            "description": self.description,
            "inputs": self.inputs,
            "output_type": self.output_type
        }
