#!/usr/bin/env python3
"""OpenAI Agents SDK benchmark for shopping cart optimizer."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from agents import Agent
from agents import Runner
from agents import function_tool
from agents.extensions.models.litellm_model import LitellmModel

from prompttodraft.benchmark_agent_sdk.config import MODEL_CONFIGS, REQUIRED_API_KEYS, SYSTEM_PROMPT, TARGET_BUDGET, TASK_DESCRIPTION, get_pricing_for_provider
from prompttodraft.benchmark_agent_sdk.metrics import MetricsTracker
from prompttodraft.benchmark_agent_sdk.session import ShoppingSession


def create_agent_tools(session: ShoppingSession, metrics_tracker: MetricsTracker) -> list:
    """
    Create OpenAI Agents tools for a shopping session.

    Args:
        session: The shopping session instance.
        metrics_tracker: Metrics tracker to record tool calls.

    Returns:
        List of OpenAI Agents tool objects.
    """

    @function_tool
    def list_categories() -> list[str]:
        """Get a list of all available shopping categories."""
        metrics_tracker.record_tool_call(tool_name="list_categories")
        return session.list_categories()

    @function_tool
    def search_item(category: str) -> list[dict]:
        """
        Search for items in a specific category.

        Args:
            category: The category to search in. Available: electronics, books, clothing, food, toys.
        """
        metrics_tracker.record_tool_call(tool_name="search_item")
        return session.search_item(category=category)

    @function_tool
    def get_price(item_name: str) -> float | str:
        """
        Get the price of a specific item by name.

        Args:
            item_name: The name of the item.
        """
        metrics_tracker.record_tool_call(tool_name="get_price")
        return session.get_price(item_name=item_name)

    @function_tool
    def add_to_cart(item_name: str) -> str:
        """
        Add an item to the shopping cart.

        Args:
            item_name: The name of the item to add.
        """
        metrics_tracker.record_tool_call(tool_name="add_to_cart")
        return session.add_to_cart(item_name=item_name)

    @function_tool
    def remove_from_cart(item_name: str) -> str:
        """
        Remove an item from the shopping cart.

        Args:
            item_name: The name of the item to remove.
        """
        metrics_tracker.record_tool_call(tool_name="remove_from_cart")
        return session.remove_from_cart(item_name=item_name)

    @function_tool
    def get_cart_total() -> float:
        """Get the current total price of all items in the cart."""
        metrics_tracker.record_tool_call(tool_name="get_cart_total")
        return session.get_cart_total()

    @function_tool
    def checkout() -> dict:
        """Finalize the purchase and complete the shopping task."""
        metrics_tracker.record_tool_call(tool_name="checkout")
        return session.checkout().model_dump()

    return [
        list_categories,
        search_item,
        get_price,
        add_to_cart,
        remove_from_cart,
        get_cart_total,
        checkout,
    ]


def get_litellm_model_name(provider: str, model_id: str) -> str:
    """
    Convert provider and model_id to LiteLLM format.

    Args:
        provider: Provider name.
        model_id: Model identifier.

    Returns:
        LiteLLM model string.
    """
    if provider == "openai":
        return model_id
    elif provider == "huggingface":
        return f"huggingface/{model_id}"
    elif provider == "xai":
        return f"xai/{model_id}"
    else:
        return model_id


def get_api_key_for_provider(provider: str) -> str | None:
    """
    Get API key for a provider.

    Args:
        provider: Provider name.

    Returns:
        API key value or None.
    """
    key_name = REQUIRED_API_KEYS.get(provider)
    if not key_name:
        return None
    return os.getenv(key_name)


async def run_single_benchmark(provider: str, model_id: str, display_name: str) -> None:
    """
    Run a single benchmark with OpenAI Agents SDK.

    Args:
        provider: Provider name.
        model_id: Model identifier.
        display_name: Display name for results.
    """
    print("\n" + "=" * 60)
    print(f"Testing: {display_name}")
    print("=" * 60)

    # Create new shopping session and initialize metrics tracker
    session = ShoppingSession()
    metrics_tracker = MetricsTracker(target_budget=TARGET_BUDGET)

    # Create tools for this session
    tools = create_agent_tools(session=session, metrics_tracker=metrics_tracker)

    # Create agent with appropriate model
    if provider == "openai":
        # For OpenAI, just pass model name as string (uses OPENAI_API_KEY by default)
        agent = Agent(
            name="shopping_assistant",
            instructions=SYSTEM_PROMPT,
            tools=tools,
            model=model_id,
        )
    else:
        # For other providers, use LiteLLM
        api_key = get_api_key_for_provider(provider=provider)
        litellm_model_name = get_litellm_model_name(provider=provider, model_id=model_id)
        model = LitellmModel(model=litellm_model_name, api_key=api_key)

        agent = Agent(
            name="shopping_assistant",
            instructions=SYSTEM_PROMPT,
            tools=tools,
            model=model,
        )

    # Start metrics tracking
    metrics_tracker.start_timer()

    # Run agent
    result = await Runner.run(agent, TASK_DESCRIPTION, max_turns=30)

    print(f"\nFinal output: {result.final_output}")

    # Stop metrics tracking
    metrics_tracker.stop_timer()

    # Build and display results
    benchmark_result = metrics_tracker.build_result(
        framework=f"OpenAI Agents SDK ({provider})",
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
    output_dir = Path(__file__).parent.parent / "benchmark_results"
    output_dir.mkdir(exist_ok=True)

    # Create safe filename from model display name
    safe_filename = display_name.replace("/", "_").replace(" ", "_").replace("(", "").replace(")", "").lower()
    output_file = output_dir / f"openai_agents_{safe_filename}_result.json"
    with open(output_file, "w") as f:
        json.dump(benchmark_result.model_dump(), f, indent=2)

    print(f"\nResults saved to: {output_file}")


async def run_benchmark() -> None:
    """Run the OpenAI Agents SDK shopping cart benchmark with multiple models."""
    missing_keys = []
    for model_config in MODEL_CONFIGS:
        provider = model_config["provider"]
        key = REQUIRED_API_KEYS[provider]
        if not os.getenv(key):
            missing_keys.append(f"{key} (for {model_config['display_name']})")

    if missing_keys:
        print("Warning: Missing API keys for some models:")
        for key in missing_keys:
            print(f"  - {key}")
        print("\nSkipping models with missing keys...\n")

    # Run benchmarks for each model
    completed_count = 0
    for model_config in MODEL_CONFIGS:
        provider = model_config["provider"]
        key = REQUIRED_API_KEYS[provider]

        if not os.getenv(key):
            print(f"\nSkipping {model_config['display_name']} (missing {key})")
            continue

        await run_single_benchmark(
            provider=provider,
            model_id=model_config["model_id"],
            display_name=model_config["display_name"]
        )
        completed_count += 1

    print("\n" + "=" * 60)
    print(f"Completed {completed_count} benchmark(s)!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
