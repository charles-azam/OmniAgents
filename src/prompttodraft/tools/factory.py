"""
Tool factory for creating framework-specific tools.

This module provides factory methods to create tools for different frameworks
(smolagents, openai, etc.) and execution environments (local, docker, e2b).
"""
from typing import Literal

from smolagents import Tool

from prompttodraft.tools.coding_tools import CodingToolLocal, CodingToolDocker, CodingToolE2B
from prompttodraft.tools.adapters.smolagents_adapter import (
    SmolagentsBashTool,
    SmolagentsViewTool,
    SmolagentsEditTool,
    SmolagentsReplaceTool,
    SmolagentsGlobTool,
    SmolagentsGrepTool,
    SmolagentsLSTool,
    SmolagentsUserInputTool,
)


class ToolFactory:
    """Factory for creating framework-specific tools."""

    @staticmethod
    def create_smolagents_tools(
        environment: Literal["local", "docker", "e2b"] = "local"
    ) -> list[Tool]:
        """
        Create smolagents-compatible tools for the given environment.

        Args:
            environment: The execution environment ("local", "docker", or "e2b")

        Returns:
            List of smolagents Tool instances

        Raises:
            NotImplementedError: If docker or e2b environment is requested
        """
        # Create the appropriate coding tool based on environment
        coding_tool = ToolFactory._create_coding_tool(environment=environment)

        # Wrap each core tool with smolagents adapter
        return [
            SmolagentsBashTool(core=coding_tool._bash),
            SmolagentsViewTool(core=coding_tool._view),
            SmolagentsEditTool(core=coding_tool._edit),
            SmolagentsReplaceTool(core=coding_tool._replace),
            SmolagentsGlobTool(core=coding_tool._glob),
            SmolagentsGrepTool(core=coding_tool._grep),
            SmolagentsLSTool(core=coding_tool._ls),
            SmolagentsUserInputTool(core=coding_tool._user_input),
        ]

    @staticmethod
    def _create_coding_tool(
        environment: Literal["local", "docker", "e2b"]
    ) -> CodingToolLocal | CodingToolDocker | CodingToolE2B:
        """
        Create a CodingTool instance for the given environment.

        Args:
            environment: The execution environment

        Returns:
            CodingTool instance

        Raises:
            NotImplementedError: If docker or e2b environment is requested
        """
        match environment:
            case "local":
                return CodingToolLocal()
            case "docker":
                return CodingToolDocker()
            case "e2b":
                return CodingToolE2B()
            case _:
                raise ValueError(f"Unknown environment: {environment}")
