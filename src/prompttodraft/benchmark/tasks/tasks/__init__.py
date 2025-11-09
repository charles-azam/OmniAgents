"""Benchmark tasks for evaluating AI coding agents."""

from .task_search_replace import SearchReplaceTask
from .task_fastapi_server import FastAPIServerTask
from .task_test_generation import TestGenerationTask
from .task_cli_tool import CLIToolTask
from .task_data_processing import DataProcessingTask
from .task_bug_fix import BugFixTask

__all__ = [
    "SearchReplaceTask",
    "FastAPIServerTask",
    "TestGenerationTask",
    "CLIToolTask",
    "DataProcessingTask",
    "BugFixTask",
]
