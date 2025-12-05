"""
Base benchmark task interface.

This module defines the abstract base class for all benchmark tasks.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass


@dataclass
class TaskSetup:
    """Configuration for setting up a benchmark task."""

    task_name: str
    description: str
    difficulty: str  # "easy", "medium", "hard"
    workspace_dir: Path
    initial_prompt: str
    max_iterations: int = 50
    timeout: int = 600  # seconds


@dataclass
class TaskEvaluation:
    """Evaluation results for a benchmark task."""

    success: bool
    test_pass_rate: float  # 0.0 to 1.0
    correctness_score: float  # 0.0 to 1.0
    code_quality_score: float  # 0.0 to 1.0
    errors: list[str]
    warnings: list[str]
    details: dict[str, str | int | float | bool]


class BenchmarkTask(ABC):
    """
    Abstract base class for benchmark tasks.

    Each benchmark task must implement:
    1. setup() - Create the initial workspace
    2. get_initial_prompt() - Return the prompt for the agent
    3. evaluate() - Score the agent's solution
    4. cleanup() - Clean up resources
    """

    def __init__(self, workspace_dir: Path):
        """
        Initialize the benchmark task.

        Args:
            workspace_dir: Directory where the task will be set up
        """
        self.workspace_dir = workspace_dir
        self.task_config = self.get_task_config()

    @abstractmethod
    def get_task_config(self) -> TaskSetup:
        """
        Get the task configuration.

        Returns:
            TaskSetup with task metadata
        """
        pass

    @abstractmethod
    def setup(self) -> None:
        """
        Set up the initial workspace for the task.

        This should create all necessary files, install dependencies, etc.
        """
        pass

    @abstractmethod
    def get_initial_prompt(self) -> str:
        """
        Get the initial prompt to give to the agent.

        Returns:
            The prompt string
        """
        pass

    @abstractmethod
    def evaluate(self) -> TaskEvaluation:
        """
        Evaluate the agent's solution.

        This should:
        1. Run tests
        2. Check correctness
        3. Assess code quality
        4. Return evaluation results

        Returns:
            TaskEvaluation with scores and details
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up resources after the task.

        This should remove temporary files, stop processes, etc.
        """
        pass

    def get_expected_tools(self) -> list[str]:
        """
        Get the list of tools expected to be used in this task.

        Returns:
            List of tool names (e.g., ["bash", "view", "edit"])
        """
        return []  # Override in subclasses if needed
