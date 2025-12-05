"""
Benchmark metrics and result dataclasses.

This module defines the data structures for collecting and storing benchmark results.
"""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BenchmarkResult:
    """Results from a single benchmark task execution."""

    # Task identification
    task_name: str
    framework: str  # "smolagents", "openai", "pydantic-ai", "autogen"
    environment: str  # "local", "docker", "e2b"
    model: str  # "claude-3-5-sonnet", "gpt-4", etc.
    timestamp: datetime = field(default_factory=datetime.now)

    # Performance metrics
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost: float = 0.0  # USD
    execution_time: float = 0.0  # seconds

    # Tool usage metrics
    tool_calls_total: int = 0
    tool_calls_by_type: dict[str, int] = field(default_factory=dict)
    tool_success_rate: float = 0.0  # 0.0 to 1.0

    # Quality metrics
    success: bool = False
    test_pass_rate: float = 0.0  # 0.0 to 1.0
    correctness_score: float = 0.0  # Task-specific, 0.0 to 1.0
    code_quality_score: float = 0.0  # Linting/formatting, 0.0 to 1.0

    # Error tracking
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Additional metadata
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "task_name": self.task_name,
            "framework": self.framework,
            "environment": self.environment,
            "model": self.model,
            "timestamp": self.timestamp.isoformat(),
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "estimated_cost": self.estimated_cost,
            "execution_time": self.execution_time,
            "tool_calls_total": self.tool_calls_total,
            "tool_calls_by_type": self.tool_calls_by_type,
            "tool_success_rate": self.tool_success_rate,
            "success": self.success,
            "test_pass_rate": self.test_pass_rate,
            "correctness_score": self.correctness_score,
            "code_quality_score": self.code_quality_score,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


@dataclass
class AggregateResults:
    """Aggregate results across multiple benchmark tasks."""

    framework: str
    environment: str
    model: str
    num_tasks: int
    timestamp: datetime = field(default_factory=datetime.now)

    # Averages across all tasks
    avg_tokens: float = 0.0
    avg_cost: float = 0.0
    avg_execution_time: float = 0.0
    avg_tool_calls: float = 0.0

    # Success rates
    task_success_rate: float = 0.0  # % of tasks completed successfully
    avg_test_pass_rate: float = 0.0
    avg_correctness: float = 0.0
    avg_code_quality: float = 0.0

    # Efficiency (for successful tasks only)
    tokens_per_successful_task: float = 0.0
    time_per_successful_task: float = 0.0
    cost_per_successful_task: float = 0.0

    # Tool usage patterns
    most_used_tools: list[tuple[str, int]] = field(default_factory=list)
    total_tool_calls: int = 0

    # Individual task results
    task_results: list[BenchmarkResult] = field(default_factory=list)

    @staticmethod
    def from_results(
        results: list[BenchmarkResult],
        framework: str,
        environment: str,
        model: str
    ) -> "AggregateResults":
        """
        Create aggregate results from a list of benchmark results.

        Args:
            results: List of BenchmarkResult objects
            framework: Framework name
            environment: Environment name
            model: Model name

        Returns:
            AggregateResults object with computed metrics
        """
        if not results:
            return AggregateResults(
                framework=framework,
                environment=environment,
                model=model,
                num_tasks=0
            )

        num_tasks = len(results)
        successful_results = [r for r in results if r.success]
        num_successful = len(successful_results)

        # Calculate averages
        avg_tokens = sum(r.total_tokens for r in results) / num_tasks
        avg_cost = sum(r.estimated_cost for r in results) / num_tasks
        avg_execution_time = sum(r.execution_time for r in results) / num_tasks
        avg_tool_calls = sum(r.tool_calls_total for r in results) / num_tasks

        # Success rates
        task_success_rate = num_successful / num_tasks if num_tasks > 0 else 0.0
        avg_test_pass_rate = sum(r.test_pass_rate for r in results) / num_tasks
        avg_correctness = sum(r.correctness_score for r in results) / num_tasks
        avg_code_quality = sum(r.code_quality_score for r in results) / num_tasks

        # Efficiency for successful tasks
        if num_successful > 0:
            tokens_per_successful = sum(r.total_tokens for r in successful_results) / num_successful
            time_per_successful = sum(r.execution_time for r in successful_results) / num_successful
            cost_per_successful = sum(r.estimated_cost for r in successful_results) / num_successful
        else:
            tokens_per_successful = 0.0
            time_per_successful = 0.0
            cost_per_successful = 0.0

        # Tool usage patterns
        tool_usage: dict[str, int] = {}
        for r in results:
            for tool, count in r.tool_calls_by_type.items():
                tool_usage[tool] = tool_usage.get(tool, 0) + count

        most_used_tools = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)
        total_tool_calls = sum(tool_usage.values())

        return AggregateResults(
            framework=framework,
            environment=environment,
            model=model,
            num_tasks=num_tasks,
            avg_tokens=avg_tokens,
            avg_cost=avg_cost,
            avg_execution_time=avg_execution_time,
            avg_tool_calls=avg_tool_calls,
            task_success_rate=task_success_rate,
            avg_test_pass_rate=avg_test_pass_rate,
            avg_correctness=avg_correctness,
            avg_code_quality=avg_code_quality,
            tokens_per_successful_task=tokens_per_successful,
            time_per_successful_task=time_per_successful,
            cost_per_successful_task=cost_per_successful,
            most_used_tools=most_used_tools,
            total_tool_calls=total_tool_calls,
            task_results=results
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "framework": self.framework,
            "environment": self.environment,
            "model": self.model,
            "num_tasks": self.num_tasks,
            "timestamp": self.timestamp.isoformat(),
            "avg_tokens": self.avg_tokens,
            "avg_cost": self.avg_cost,
            "avg_execution_time": self.avg_execution_time,
            "avg_tool_calls": self.avg_tool_calls,
            "task_success_rate": self.task_success_rate,
            "avg_test_pass_rate": self.avg_test_pass_rate,
            "avg_correctness": self.avg_correctness,
            "avg_code_quality": self.avg_code_quality,
            "tokens_per_successful_task": self.tokens_per_successful_task,
            "time_per_successful_task": self.time_per_successful_task,
            "cost_per_successful_task": self.cost_per_successful_task,
            "most_used_tools": self.most_used_tools,
            "total_tool_calls": self.total_tool_calls,
            "task_results": [r.to_dict() for r in self.task_results],
        }
