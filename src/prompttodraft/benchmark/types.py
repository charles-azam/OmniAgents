"""Shared types for benchmark framework."""

from pydantic import BaseModel
from pydantic import Field


class CheckoutSummary(BaseModel):
    """Summary of a completed checkout."""

    total: float = Field(description="Total price of items in cart")
    item_count: int = Field(description="Number of items in cart")
    items: list[str] = Field(description="List of item names in cart")
    message: str = Field(description="Checkout confirmation message")


class Item(BaseModel):
    """Represents an item in the catalog."""

    name: str = Field(description="Name of the item")
    category: str = Field(description="Category of the item")
    price: float = Field(description="Price of the item in dollars")
    description: str = Field(description="Description of the item")


class ShoppingCart(BaseModel):
    """Represents the shopping cart state."""

    items: list[Item] = Field(default_factory=list, description="Items in the cart")
    total: float = Field(default=0.0, description="Total price of items in cart")

    def add_item(self, item: Item) -> None:
        """Add an item to the cart."""
        self.items.append(item)
        self.total += item.price

    def remove_item(self, item_name: str) -> bool:
        """Remove an item from the cart by name. Returns True if successful."""
        for i, item in enumerate(self.items):
            if item.name.lower() == item_name.lower():
                self.total -= item.price
                self.items.pop(i)
                return True
        return False

    def get_summary(self) -> CheckoutSummary:
        """Get a summary of the cart."""
        return CheckoutSummary(
            total=round(self.total, 2),
            item_count=len(self.items),
            items=[item.name for item in self.items],
            message="Cart summary retrieved",
        )


class BenchmarkMetrics(BaseModel):
    """Metrics collected during benchmark execution."""

    tool_call_count: int = Field(default=0, description="Total number of tool calls")
    tool_call_breakdown: dict[str, int] = Field(
        default_factory=dict, description="Breakdown of tool calls by tool name"
    )
    execution_time_seconds: float = Field(
        default=0.0, description="Total execution time in seconds"
    )
    token_usage: dict[str, int] = Field(
        default_factory=dict, description="Token usage breakdown (prompt, completion, total)"
    )
    estimated_cost: float = Field(default=0.0, description="Estimated cost in dollars")
    success: bool = Field(default=False, description="Whether the task was successful")
    final_cart_total: float = Field(default=0.0, description="Final cart total")
    distance_from_target: float = Field(
        default=0.0, description="Absolute distance from target budget"
    )
    target_budget: float = Field(default=100.0, description="Target budget")


class BenchmarkResult(BaseModel):
    """Complete benchmark result."""

    framework: str = Field(description="Name of the framework tested")
    metrics: BenchmarkMetrics = Field(description="Collected metrics")
    cart_summary: CheckoutSummary = Field(
        description="Final shopping cart summary"
    )
    task_description: str = Field(description="Description of the task")
    model: str = Field(description="Model used for the benchmark")

    def to_summary(self) -> str:
        """Generate a human-readable summary."""
        return f"""
=== {self.framework} Benchmark Results ===
Model: {self.model}
Task: {self.task_description}

Performance:
- Execution Time: {self.metrics.execution_time_seconds:.2f}s
- Tool Calls: {self.metrics.tool_call_count}
- Success: {'✓' if self.metrics.success else '✗'}

Cart Summary:
- Target Budget: ${self.metrics.target_budget:.2f}
- Final Total: ${self.metrics.final_cart_total:.2f}
- Distance from Target: ${self.metrics.distance_from_target:.2f}
- Items: {self.cart_summary.item_count}

Token Usage:
- Total Tokens: {self.metrics.token_usage.get('total', 'N/A')}
- Estimated Cost: ${self.metrics.estimated_cost:.4f}

Tool Call Breakdown:
{self._format_tool_breakdown()}
"""

    def _format_tool_breakdown(self) -> str:
        """Format tool call breakdown for display."""
        if not self.metrics.tool_call_breakdown:
            return "  No tool calls recorded"
        return "\n".join(
            f"  - {tool}: {count}"
            for tool, count in sorted(
                self.metrics.tool_call_breakdown.items(),
                key=lambda x: x[1],
                reverse=True
            )
        )
