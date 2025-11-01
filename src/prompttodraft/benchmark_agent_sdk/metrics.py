"""Metrics tracking for benchmark execution."""

import time
from prompttodraft.benchmark_agent_sdk.types import BenchmarkMetrics
from prompttodraft.benchmark_agent_sdk.types import BenchmarkResult
from prompttodraft.benchmark_agent_sdk.types import ShoppingCart


class MetricsTracker:
    """Tracks metrics during benchmark execution."""

    def __init__(self, target_budget: float = 100.0):
        """
        Initialize metrics tracker.

        Args:
            target_budget: The target budget for the shopping cart.
        """
        self.target_budget = target_budget
        self.start_time: float | None = None
        self.end_time: float | None = None
        self.tool_calls: dict[str, int] = {}
        self.token_usage: dict[str, int] = {}
        self.total_tokens: int = 0
        self.estimated_cost: float = 0.0

    def start_timer(self) -> None:
        """Start tracking time."""
        self.start_time = time.time()

    def stop_timer(self) -> None:
        """Stop tracking time."""
        self.end_time = time.time()

    def record_tool_call(self, tool_name: str) -> None:
        """
        Record a tool call.

        Args:
            tool_name: Name of the tool that was called.
        """
        self.tool_calls[tool_name] = self.tool_calls.get(tool_name, 0) + 1

    def record_token_usage(
        self,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0
    ) -> None:
        """
        Record token usage.

        Args:
            prompt_tokens: Number of prompt tokens used.
            completion_tokens: Number of completion tokens used.
            total_tokens: Total tokens used.
        """
        self.token_usage["prompt"] = self.token_usage.get("prompt", 0) + prompt_tokens
        self.token_usage["completion"] = (
            self.token_usage.get("completion", 0) + completion_tokens
        )
        self.token_usage["total"] = self.token_usage.get("total", 0) + total_tokens
        self.total_tokens += total_tokens

    def calculate_cost(
        self,
        prompt_cost_per_1k: float = 0.003,
        completion_cost_per_1k: float = 0.015
    ) -> None:
        """
        Calculate estimated cost based on token usage.

        Args:
            prompt_cost_per_1k: Cost per 1000 prompt tokens (default for GPT-4).
            completion_cost_per_1k: Cost per 1000 completion tokens (default for GPT-4).
        """
        prompt_tokens = self.token_usage.get("prompt", 0)
        completion_tokens = self.token_usage.get("completion", 0)

        prompt_cost = (prompt_tokens / 1000) * prompt_cost_per_1k
        completion_cost = (completion_tokens / 1000) * completion_cost_per_1k

        self.estimated_cost = prompt_cost + completion_cost

    def get_execution_time(self) -> float:
        """Get execution time in seconds."""
        if self.start_time is None:
            return 0.0
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    def build_metrics(self, cart: ShoppingCart) -> BenchmarkMetrics:
        """
        Build the BenchmarkMetrics object.

        Args:
            cart: The final shopping cart.

        Returns:
            BenchmarkMetrics object with all collected metrics.
        """
        final_total = round(cart.total, 2)
        distance = abs(self.target_budget - final_total)

        # Success criteria: cart total between target-5 and target (e.g., $95-$100)
        success = (self.target_budget - 5.0) <= final_total <= self.target_budget

        return BenchmarkMetrics(
            tool_call_count=sum(self.tool_calls.values()),
            tool_call_breakdown=self.tool_calls.copy(),
            execution_time_seconds=round(self.get_execution_time(), 2),
            token_usage=self.token_usage.copy(),
            estimated_cost=self.estimated_cost,
            success=success,
            final_cart_total=final_total,
            distance_from_target=round(distance, 2),
            target_budget=self.target_budget,
        )

    def build_result(
        self,
        framework: str,
        model: str,
        task_description: str,
        cart: ShoppingCart
    ) -> BenchmarkResult:
        """
        Build the complete BenchmarkResult object.

        Args:
            framework: Name of the framework being tested.
            model: Model identifier.
            task_description: Description of the task.
            cart: The final shopping cart.

        Returns:
            Complete BenchmarkResult object.
        """
        metrics = self.build_metrics(cart=cart)
        cart_summary = cart.get_summary()

        return BenchmarkResult(
            framework=framework,
            metrics=metrics,
            cart_summary=cart_summary,
            task_description=task_description,
            model=model,
        )
