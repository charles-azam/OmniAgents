"""Smolagents benchmark runner for shopping cart optimizer."""

import json
import os
from pathlib import Path

from smolagents import ToolCallingAgent
from smolagents import InferenceClientModel
from smolagents import OpenAIModel
from smolagents import tool

from prompttodraft.benchmark.agent_sdk.config import MODEL_CONFIGS_NO_XAI, REQUIRED_API_KEYS, SYSTEM_PROMPT, TARGET_BUDGET, TASK_DESCRIPTION, get_pricing_for_provider
from prompttodraft.benchmark.agent_sdk.metrics import MetricsTracker
from prompttodraft.benchmark.agent_sdk.session import ShoppingSession

from phoenix.otel import register
from openinference.instrumentation.smolagents import SmolagentsInstrumentor


def initialize_instrumentation() -> None:
    """Initialize Phoenix instrumentation for Smolagents."""
    register()
    SmolagentsInstrumentor().instrument()


def create_smolagents_tools(session: ShoppingSession, metrics_tracker: MetricsTracker) -> list:
    """
    Create smolagents-compatible tools for a shopping session.

    Args:
        session: The shopping session instance.
        metrics_tracker: Metrics tracker to record tool calls.

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
        metrics_tracker.record_tool_call(tool_name="list_categories")
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
        metrics_tracker.record_tool_call(tool_name="search_item")
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
        metrics_tracker.record_tool_call(tool_name="get_price")
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
        metrics_tracker.record_tool_call(tool_name="add_to_cart")
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
        metrics_tracker.record_tool_call(tool_name="remove_from_cart")
        return session.remove_from_cart(item_name=item_name)

    @tool
    def get_cart_total_tool() -> float:
        """
        Get the current total price of all items in the cart.

        Returns:
            The total price of items in the cart.
        """
        metrics_tracker.record_tool_call(tool_name="get_cart_total")
        return session.get_cart_total()

    @tool
    def checkout_tool() -> dict:
        """
        Finalize the purchase and complete the shopping task.
        Call this when you are satisfied with your cart selection.

        Returns:
            Summary of the cart including total, item count, and items.
        """
        metrics_tracker.record_tool_call(tool_name="checkout")
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


def create_model(provider: str, model_id: str):
    """
    Create a smolagents model from provider and model_id.

    Args:
        provider: Provider name (openai, huggingface, xai).
        model_id: Model identifier.

    Returns:
        Configured smolagents model.
    """
    if provider == "openai":
        return OpenAIModel(model_id=model_id)
    elif provider == "huggingface":
        return InferenceClientModel(model_id=model_id)
    elif provider == "xai":
        return OpenAIModel(
            model_id=model_id,
            api_key=os.getenv("XAI_API_KEY"),
            api_base="https://api.x.ai/v1"
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def run_single_benchmark(provider: str, model_id: str, display_name: str, output_dir: Path) -> dict:
    """
    Run a single benchmark with smolagents.

    Args:
        provider: Provider name.
        model_id: Model identifier.
        display_name: Display name for results.
        output_dir: Directory to save results.

    Returns:
        Dictionary containing benchmark results.
    """
    print("\n" + "=" * 60)
    print(f"Testing: {display_name}")
    print("=" * 60)

    # Create new shopping session and initialize metrics tracker
    session = ShoppingSession()
    metrics_tracker = MetricsTracker(target_budget=TARGET_BUDGET)

    # Create tools for this session
    tools = create_smolagents_tools(session=session, metrics_tracker=metrics_tracker)

    # Initialize smolagents model
    model = create_model(provider=provider, model_id=model_id)

    # Create agent
    agent = ToolCallingAgent(
        tools=tools,
        model=model,
        max_steps=10,
    )

    # Start metrics tracking
    metrics_tracker.start_timer()

    # Run the agent
    agent.run(task=TASK_DESCRIPTION)

    # Stop metrics tracking
    metrics_tracker.stop_timer()

    # Build and display results
    benchmark_result = metrics_tracker.build_result(
        framework=f"Smolagents ({provider})",
        model=display_name,
        task_description=TASK_DESCRIPTION,
        cart=session.cart,
    )

    # Calculate estimated cost
    prompt_cost, completion_cost = get_pricing_for_provider(provider=provider)
    metrics_tracker.calculate_cost(
        prompt_cost_per_1k=prompt_cost,
        completion_cost_per_1k=completion_cost
    )

    print("\n" + "=" * 60)
    print(benchmark_result.to_summary())
    print("=" * 60)

    # Save results to JSON
    output_dir.mkdir(exist_ok=True)

    # Create safe filename from model display name
    safe_filename = display_name.replace("/", "_").replace(" ", "_").replace("(", "").replace(")", "").lower()
    output_file = output_dir / f"smolagents_{safe_filename}_result.json"
    with open(output_file, "w") as f:
        json.dump(benchmark_result.model_dump(), f, indent=2)

    print(f"\nResults saved to: {output_file}")

    return benchmark_result.model_dump()


def main() -> list[dict]:
    """
    Run the smolagents shopping cart benchmark with multiple models.

    Returns:
        List of benchmark results dictionaries.
    """
    initialize_instrumentation()

    missing_keys = []
    for model_config in MODEL_CONFIGS_NO_XAI:
        provider = model_config["provider"]
        key = REQUIRED_API_KEYS[provider]
        if not os.getenv(key):
            missing_keys.append(f"{key} (for {model_config['display_name']})")

    if missing_keys:
        print("Warning: Missing API keys for some models:")
        for key in missing_keys:
            print(f"  - {key}")
        print("\nSkipping models with missing keys...\n")

    # Determine output directory
    output_dir = Path.cwd() / "benchmark_results"

    # Run benchmarks for each model
    completed_count = 0
    results = []
    for model_config in MODEL_CONFIGS_NO_XAI:
        provider = model_config["provider"]
        key = REQUIRED_API_KEYS[provider]

        if not os.getenv(key):
            print(f"\nSkipping {model_config['display_name']} (missing {key})")
            continue

        result = run_single_benchmark(
            provider=provider,
            model_id=model_config["model_id"],
            display_name=model_config["display_name"],
            output_dir=output_dir
        )
        results.append(result)
        completed_count += 1

    print("\n" + "=" * 60)
    print(f"Completed {completed_count} Smolagents benchmark(s)!")
    print("=" * 60)

    return results
