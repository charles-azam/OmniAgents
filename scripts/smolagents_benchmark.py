#!/usr/bin/env python3
"""Smolagents benchmark for shopping cart optimizer."""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path to import prompttodraft
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from smolagents import CodeAgent
from smolagents import HfApiModel
from smolagents import tool

from prompttodraft.benchmark.metrics import MetricsTracker
from prompttodraft.benchmark.session import ShoppingSession


def create_smolagents_tools(session: ShoppingSession) -> list:
    """
    Create smolagents-compatible tools for a shopping session.

    Args:
        session: The shopping session instance.

    Returns:
        List of smolagents tool objects.
    """

    @tool
    def list_categories_tool() -> list[str]:
        """
        Get a list of all available shopping categories.

        Returns:
            List of category names.
        """
        return session.list_categories()

    @tool
    def search_item_tool(category: str) -> list[dict]:
        """
        Search for items in a specific category.
        Available categories: electronics, books, clothing, food, toys.

        Args:
            category: The category to search in.

        Returns:
            List of items with name, price, and description.
        """
        return session.search_item(category=category)

    @tool
    def get_price_tool(item_name: str) -> float | str:
        """
        Get the price of a specific item by name.

        Args:
            item_name: The name of the item.

        Returns:
            The price of the item or error message.
        """
        return session.get_price(item_name=item_name)

    @tool
    def add_to_cart_tool(item_name: str) -> str:
        """
        Add an item to the shopping cart.

        Args:
            item_name: The name of the item to add.

        Returns:
            Success message with updated cart total.
        """
        return session.add_to_cart(item_name=item_name)

    @tool
    def remove_from_cart_tool(item_name: str) -> str:
        """
        Remove an item from the shopping cart.

        Args:
            item_name: The name of the item to remove.

        Returns:
            Success message with updated cart total.
        """
        return session.remove_from_cart(item_name=item_name)

    @tool
    def get_cart_total_tool() -> float:
        """
        Get the current total price of all items in the cart.

        Returns:
            The total price of items in the cart.
        """
        return session.get_cart_total()

    @tool
    def checkout_tool() -> dict:
        """
        Finalize the purchase and complete the shopping task.
        Call this when you are satisfied with your cart selection.

        Returns:
            Summary of the cart including total, item count, and items.
        """
        result = session.checkout()
        return result.model_dump()

    return [
        list_categories_tool,
        search_item_tool,
        get_price_tool,
        add_to_cart_tool,
        remove_from_cart_tool,
        get_cart_total_tool,
        checkout_tool,
    ]


class ToolCallTracker:
    """Tracks tool calls for smolagents."""

    def __init__(self, metrics_tracker: MetricsTracker):
        """Initialize with a metrics tracker."""
        self.metrics_tracker = metrics_tracker
        self.original_tools = {}

    def wrap_tool(self, tool_obj):
        """Wrap a tool to track its calls."""
        original_forward = tool_obj.forward

        def tracked_forward(*args, **kwargs):
            self.metrics_tracker.record_tool_call(tool_name=tool_obj.name)
            return original_forward(*args, **kwargs)

        tool_obj.forward = tracked_forward
        return tool_obj


def run_benchmark() -> None:
    """Run the smolagents shopping cart benchmark."""
    # Check for HuggingFace API token
    if not os.getenv("HF_TOKEN"):
        print("Error: HF_TOKEN environment variable not set")
        sys.exit(1)

    # Create new shopping session and initialize metrics tracker
    session = ShoppingSession()
    metrics_tracker = MetricsTracker(target_budget=100.0)

    # Create tool tracker
    tool_tracker = ToolCallTracker(metrics_tracker=metrics_tracker)

    # Create tools for this session
    tools = create_smolagents_tools(session=session)

    # Wrap tools for tracking
    tracked_tools = [tool_tracker.wrap_tool(tool_obj=t) for t in tools]

    # Initialize smolagents model
    model = HfApiModel(model_id="Qwen/Qwen2.5-Coder-32B-Instruct")

    # Create agent
    agent = CodeAgent(
        tools=tracked_tools,
        model=model,
        max_steps=30,
    )

    # Start metrics tracking
    metrics_tracker.start_timer()

    # Run the agent
    print("=" * 60)
    print("Starting Smolagents Shopping Cart Benchmark")
    print("=" * 60)
    print()

    agent.run(
        task="""Fill the shopping cart to be as close to $100 as possible WITHOUT going over the budget.

Strategy:
1. First, explore the available categories to understand what's available
2. Search items in different categories to see prices
3. Add items strategically to get close to $100
4. You can remove items and add different ones to optimize
5. When satisfied with your cart (close to $100 but not over), call checkout

Important: You must call the checkout tool when you're done selecting items."""
    )

    # Stop metrics tracking
    metrics_tracker.stop_timer()

    # Build and display results
    benchmark_result = metrics_tracker.build_result(
        framework="Smolagents",
        model="Qwen/Qwen2.5-Coder-32B-Instruct",
        task_description="Fill shopping cart to $100 without going over",
        cart=session.cart,
    )

    # Calculate estimated cost (rough estimate based on HuggingFace API pricing)
    # Note: Pricing varies, this is an estimate
    metrics_tracker.calculate_cost(
        prompt_cost_per_1k=0.001,
        completion_cost_per_1k=0.002
    )

    print("\n" + "=" * 60)
    print(benchmark_result.to_summary())
    print("=" * 60)

    # Save results to JSON
    output_dir = Path(__file__).parent.parent / "benchmark_results"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "smolagents_result.json"
    with open(output_file, "w") as f:
        json.dump(benchmark_result.model_dump(), f, indent=2)

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    run_benchmark()
