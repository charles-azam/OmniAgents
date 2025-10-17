#!/usr/bin/env python3
"""LangChain benchmark for shopping cart optimizer."""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add parent directory to path to import prompttodraft
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain.agents import AgentExecutor
from langchain.agents import create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from prompttodraft.benchmark.metrics import MetricsTracker
from prompttodraft.benchmark.tools import add_to_cart
from prompttodraft.benchmark.tools import checkout
from prompttodraft.benchmark.tools import get_cart
from prompttodraft.benchmark.tools import get_cart_total
from prompttodraft.benchmark.tools import get_price
from prompttodraft.benchmark.tools import list_categories
from prompttodraft.benchmark.tools import remove_from_cart
from prompttodraft.benchmark.tools import reset_cart
from prompttodraft.benchmark.tools import search_item


# Create LangChain-compatible tools
@tool
def search_item_tool(category: str) -> list[dict[str, str | float]]:
    """
    Search for items in a specific category.
    Available categories: electronics, books, clothing, food, toys.

    Args:
        category: The category to search in.

    Returns:
        List of items with name, price, and description.
    """
    return search_item(category=category)


@tool
def get_price_tool(item_name: str) -> float | str:
    """
    Get the price of a specific item by name.

    Args:
        item_name: The name of the item.

    Returns:
        The price of the item or error message.
    """
    return get_price(item_name=item_name)


@tool
def add_to_cart_tool(item_name: str) -> str:
    """
    Add an item to the shopping cart.

    Args:
        item_name: The name of the item to add.

    Returns:
        Success message with updated cart total.
    """
    return add_to_cart(item_name=item_name)


@tool
def remove_from_cart_tool(item_name: str) -> str:
    """
    Remove an item from the shopping cart.

    Args:
        item_name: The name of the item to remove.

    Returns:
        Success message with updated cart total.
    """
    return remove_from_cart(item_name=item_name)


@tool
def get_cart_total_tool() -> float:
    """
    Get the current total price of all items in the cart.

    Returns:
        The total price of items in the cart.
    """
    return get_cart_total()


@tool
def checkout_tool() -> dict:
    """
    Finalize the purchase and complete the shopping task.
    Call this when you are satisfied with your cart selection.

    Returns:
        Summary of the cart including total, item count, and items.
    """
    result = checkout()
    return result.model_dump()


@tool
def list_categories_tool() -> list[str]:
    """
    Get a list of all available shopping categories.

    Returns:
        List of category names.
    """
    return list_categories()


# Custom callback to track tool calls
class ToolCallTracker:
    """Tracks tool calls for metrics."""

    def __init__(self, metrics_tracker: MetricsTracker):
        """Initialize with a metrics tracker."""
        self.metrics_tracker = metrics_tracker

    def on_tool_start(self, tool_name: str) -> None:
        """Record when a tool is called."""
        self.metrics_tracker.record_tool_call(tool_name=tool_name)


async def run_benchmark() -> None:
    """Run the LangChain shopping cart benchmark."""
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    # Reset cart and initialize metrics tracker
    reset_cart()
    metrics_tracker = MetricsTracker(target_budget=100.0)

    # Initialize LangChain components
    model = ChatOpenAI(model="gpt-4o", temperature=0)

    tools = [
        list_categories_tool,
        search_item_tool,
        get_price_tool,
        add_to_cart_tool,
        remove_from_cart_tool,
        get_cart_total_tool,
        checkout_tool,
    ]

    # Create the prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a shopping assistant. Your goal is to fill a shopping cart
to be as close to $100 as possible WITHOUT going over the budget.

Strategy suggestions:
1. First, explore the available categories to understand what's available
2. Search items in different categories to see prices
3. Add items strategically to get close to $100
4. You can remove items and add different ones to optimize
5. When satisfied with your cart (close to $100 but not over), call checkout

Important: You must call the checkout tool when you're done selecting items.""",
            ),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    # Create agent
    agent = create_tool_calling_agent(llm=model, tools=tools, prompt=prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    # Start metrics tracking
    metrics_tracker.start()

    # Run the agent
    print("=" * 60)
    print("Starting LangChain Shopping Cart Benchmark")
    print("=" * 60)
    print()

    # Track tool calls by wrapping the agent executor
    original_invoke = agent_executor.invoke

    def tracked_invoke(*args, **kwargs):
        result = original_invoke(*args, **kwargs)
        # Extract tool calls from intermediate steps
        if "intermediate_steps" in result:
            for action, _ in result["intermediate_steps"]:
                tool_name = action.tool
                metrics_tracker.record_tool_call(tool_name=tool_name)
        return result

    agent_executor.invoke = tracked_invoke

    agent_executor.invoke(
        {"input": "Fill the shopping cart to be as close to $100 as possible without going over."}
    )

    # Stop metrics tracking
    metrics_tracker.stop()

    # Build and display results
    cart = get_cart()
    benchmark_result = metrics_tracker.build_result(
        framework="LangChain",
        model="gpt-5-mini",
        task_description="Fill shopping cart to $100 without going over",
        cart=cart,
    )

    # Calculate estimated cost (rough estimate based on GPT-4 pricing)
    # Note: Without proper callback tracking, this is approximate
    metrics_tracker.calculate_cost(
        prompt_cost_per_1k=0.003,
        completion_cost_per_1k=0.015
    )

    print("\n" + "=" * 60)
    print(benchmark_result.to_summary())
    print("=" * 60)

    # Save results to JSON
    output_dir = Path(__file__).parent.parent / "benchmark_results"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "langchain_result.json"
    with open(output_file, "w") as f:
        json.dump(benchmark_result.model_dump(), f, indent=2)

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
