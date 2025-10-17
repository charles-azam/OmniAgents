#!/usr/bin/env python3
"""Pydantic AI benchmark for shopping cart optimizer."""

import json
import os
from pathlib import Path

import logfire
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from openai import AsyncOpenAI

from prompttodraft.benchmark.metrics import MetricsTracker
from prompttodraft.benchmark.session import ShoppingSession
from prompttodraft.benchmark.config import (
    SYSTEM_PROMPT,
    TASK_DESCRIPTION,
    TARGET_BUDGET,
    MODEL_CONFIGS,
    REQUIRED_API_KEYS,
)
from prompttodraft.benchmark.config import get_pricing_for_provider


def setup_logfire() -> None:
    """
    Configure Logfire for observability.

    This will enable detailed tracing of agent runs, tool calls, and model requests.
    """
    logfire.configure(
        service_name="pydantic-ai-benchmark",
        send_to_logfire=False,
        console=logfire.ConsoleOptions(
            verbose=True,
            colors="auto",
        ),
    )
    logfire.instrument_pydantic_ai()
    print("✅ Logfire instrumentation enabled\n")


def create_pydantic_ai_agent(session: ShoppingSession, model: OpenAIChatModel, metrics_tracker: MetricsTracker, verbose: bool = True) -> Agent:
    """
    Create a Pydantic AI agent with shopping tools.

    Args:
        session: The shopping session instance.
        model: The Pydantic AI model to use.
        metrics_tracker: Metrics tracker for recording tool calls.
        verbose: Whether to print tool calls and results.

    Returns:
        Configured Pydantic AI agent.
    """
    agent = Agent(model=model, system_prompt=SYSTEM_PROMPT)

    @agent.tool
    def list_categories(ctx: RunContext) -> list[str]:
        """
        Get a list of all available shopping categories.

        Args:
            ctx: The run context.

        Returns:
            List of category names.
        """
        if verbose:
            print("\n> Calling tool: list_categories")
        metrics_tracker.record_tool_call(tool_name="list_categories")
        result = session.list_categories()
        if verbose:
            print(f"< Tool result: {result}")
        return result

    @agent.tool
    def search_item(ctx: RunContext, category: str) -> list[dict[str, str | float]]:
        """
        Search for items in a specific category.
        Available categories: electronics, books, clothing, food, toys.

        Args:
            ctx: The run context.
            category: The category to search in.

        Returns:
            List of items with name, price, and description.
        """
        if verbose:
            print(f"\n> Calling tool: search_item(category='{category}')")
        metrics_tracker.record_tool_call(tool_name="search_item")
        result = session.search_item(category=category)
        if verbose:
            print(f"< Tool result: Found {len(result)} items in {category}")
        return result

    @agent.tool
    def get_price(ctx: RunContext, item_name: str) -> float | str:
        """
        Get the price of a specific item by name.

        Args:
            ctx: The run context.
            item_name: The name of the item.

        Returns:
            The price of the item or error message.
        """
        if verbose:
            print(f"\n> Calling tool: get_price(item_name='{item_name}')")
        metrics_tracker.record_tool_call(tool_name="get_price")
        result = session.get_price(item_name=item_name)
        if verbose:
            print(f"< Tool result: {result}")
        return result

    @agent.tool
    def add_to_cart(ctx: RunContext, item_name: str) -> str:
        """
        Add an item to the shopping cart.

        Args:
            ctx: The run context.
            item_name: The name of the item to add.

        Returns:
            Success message with updated cart total.
        """
        if verbose:
            print(f"\n> Calling tool: add_to_cart(item_name='{item_name}')")
        metrics_tracker.record_tool_call(tool_name="add_to_cart")
        result = session.add_to_cart(item_name=item_name)
        if verbose:
            print(f"< Tool result: {result}")
        return result

    @agent.tool
    def remove_from_cart(ctx: RunContext, item_name: str) -> str:
        """
        Remove an item from the shopping cart.

        Args:
            ctx: The run context.
            item_name: The name of the item to remove.

        Returns:
            Success message with updated cart total.
        """
        if verbose:
            print(f"\n> Calling tool: remove_from_cart(item_name='{item_name}')")
        metrics_tracker.record_tool_call(tool_name="remove_from_cart")
        result = session.remove_from_cart(item_name=item_name)
        if verbose:
            print(f"< Tool result: {result}")
        return result

    @agent.tool
    def get_cart_total(ctx: RunContext) -> float:
        """
        Get the current total price of all items in the cart.

        Args:
            ctx: The run context.

        Returns:
            The total price of items in the cart.
        """
        if verbose:
            print("\n> Calling tool: get_cart_total")
        metrics_tracker.record_tool_call(tool_name="get_cart_total")
        result = session.get_cart_total()
        if verbose:
            print(f"< Tool result: ${result:.2f}")
        return result

    @agent.tool
    def checkout(ctx: RunContext) -> dict:
        """
        Finalize the purchase and complete the shopping task.
        Call this when you are satisfied with your cart selection.

        Args:
            ctx: The run context.

        Returns:
            Summary of the cart including total, item count, and items.
        """
        if verbose:
            print("\n> Calling tool: checkout")
        metrics_tracker.record_tool_call(tool_name="checkout")
        result = session.checkout()
        result_dict = result.model_dump()
        if verbose:
            print(f"< Tool result: {result_dict}")
        return result_dict

    return agent


def create_model(provider: str, model_id: str) -> OpenAIChatModel:
    """
    Create a Pydantic AI model from provider and model_id.

    Args:
        provider: Provider name (openai, huggingface, xai).
        model_id: Model identifier.

    Returns:
        Configured Pydantic AI model.
    """
    if provider == "openai":
        return OpenAIChatModel(model_name=model_id)
    elif provider == "huggingface":
        raise NotImplementedError("HuggingFace provider not yet supported in Pydantic AI")
    elif provider == "xai":
        xai_client = AsyncOpenAI(
            base_url="https://api.x.ai/v1",
            api_key=os.getenv("XAI_API_KEY"),
        )
        xai_provider = OpenAIProvider(openai_client=xai_client)
        return OpenAIChatModel(model_name=model_id, provider=xai_provider)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def run_single_benchmark(provider: str, model_id: str, display_name: str) -> None:
    """
    Run a single benchmark with a specific model.

    Args:
        provider: Provider name.
        model_id: Model identifier.
        display_name: Display name for results.
    """
    print("\n" + "=" * 60)
    print(f"Testing: {display_name}")
    print("=" * 60)

    session = ShoppingSession()
    metrics_tracker = MetricsTracker(target_budget=TARGET_BUDGET)

    model = create_model(provider=provider, model_id=model_id)

    agent = create_pydantic_ai_agent(
        session=session, model=model, metrics_tracker=metrics_tracker, verbose=True
    )

    metrics_tracker.start_timer()

    print(f"\n🤖 Starting agent execution...")
    print(f"Task: {TASK_DESCRIPTION}\n")

    result = agent.run_sync(user_prompt=TASK_DESCRIPTION)

    print("\n✅ Agent execution completed")

    metrics_tracker.stop_timer()

    benchmark_result = metrics_tracker.build_result(
        framework=f"Pydantic AI ({provider})",
        model=display_name,
        task_description=TASK_DESCRIPTION,
        cart=session.cart,
    )

    prompt_cost, completion_cost = get_pricing_for_provider(provider=provider)
    metrics_tracker.calculate_cost(
        prompt_cost_per_1k=prompt_cost, completion_cost_per_1k=completion_cost
    )

    print("\n" + "=" * 60)
    print(benchmark_result.to_summary())
    print("=" * 60)

    output_dir = Path(__file__).parent.parent / "benchmark_results"
    output_dir.mkdir(exist_ok=True)

    safe_filename = (
        display_name.replace("/", "_")
        .replace(" ", "_")
        .replace("(", "")
        .replace(")", "")
        .lower()
    )
    output_file = output_dir / f"pydantic_ai_{safe_filename}_result.json"
    with open(output_file, "w") as f:
        json.dump(benchmark_result.model_dump(), f, indent=2)

    print(f"\nResults saved to: {output_file}")


def run_benchmark() -> None:
    """Run the Pydantic AI shopping cart benchmark with multiple models."""
    setup_logfire()

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

    completed_count = 0
    for model_config in MODEL_CONFIGS:
        provider = model_config["provider"]
        key = REQUIRED_API_KEYS[provider]

        if not os.getenv(key):
            print(f"\nSkipping {model_config['display_name']} (missing {key})")
            continue

        if provider == "huggingface":
            print(
                f"\nSkipping {model_config['display_name']} (HuggingFace not yet supported)"
            )
            continue

        run_single_benchmark(
            provider=provider,
            model_id=model_config["model_id"],
            display_name=model_config["display_name"],
        )
        completed_count += 1

    print("\n" + "=" * 60)
    print(f"Completed {completed_count} benchmark(s)!")
    print("=" * 60)


if __name__ == "__main__":
    run_benchmark()
