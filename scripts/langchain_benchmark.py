#!/usr/bin/env python3
"""LangChain benchmark for shopping cart optimizer."""

import json
import os
from pathlib import Path

from langchain.agents import AgentExecutor
from langchain.agents import create_tool_calling_agent, create_openai_functions_agent
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from prompttodraft.benchmark_agent_sdk.metrics import MetricsTracker
from prompttodraft.benchmark_agent_sdk.session import ShoppingSession
from prompttodraft.benchmark_agent_sdk.config import SYSTEM_PROMPT, TASK_DESCRIPTION, TARGET_BUDGET, MODEL_CONFIGS, REQUIRED_API_KEYS
from prompttodraft.benchmark_agent_sdk.config import get_pricing_for_provider


def create_langchain_tools(session: ShoppingSession) -> list:
    """
    Create LangChain-compatible tools for a shopping session.

    Args:
        session: The shopping session instance.

    Returns:
        List of LangChain tool objects.
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
    def search_item_tool(category: str) -> list[dict[str, str | float]]:
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


class ToolCallbackHandler(BaseCallbackHandler):
    """Custom callback handler to track tool calls."""

    def __init__(self, metrics_tracker: MetricsTracker):
        """Initialize with a metrics tracker."""
        super().__init__()
        self.metrics_tracker = metrics_tracker

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs) -> None:
        """Record when a tool is called."""
        tool_name = serialized.get("name", "unknown")
        self.metrics_tracker.record_tool_call(tool_name=tool_name)


def create_model(provider: str, model_id: str):
    """
    Create a LangChain model from provider and model_id.

    Args:
        provider: Provider name (openai, huggingface, xai).
        model_id: Model identifier.

    Returns:
        Configured LangChain model.
    """
    if provider == "openai":
        return ChatOpenAI(
            model=model_id,
            temperature=0,
        )
    elif provider == "huggingface":
        from langchain_huggingface import ChatHuggingFace
        from langchain_huggingface import HuggingFaceEndpoint

        llm = HuggingFaceEndpoint(
            repo_id=model_id,
            task="text-generation",
            temperature=0,
        )
        return ChatHuggingFace(llm=llm)
    elif provider == "xai":
        from langchain_xai import ChatXAI

        return ChatXAI(
            model=model_id,
            temperature=0,
        )
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

    # Create new shopping session and initialize metrics tracker
    session = ShoppingSession()
    metrics_tracker = MetricsTracker(target_budget=TARGET_BUDGET)

    # Initialize model
    model = create_model(provider=provider, model_id=model_id)

    # Create tools for this session
    tools = create_langchain_tools(session=session)

    # Create the prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    # Create callback handler for tracking tool calls
    callback_handler = ToolCallbackHandler(metrics_tracker=metrics_tracker)

    # Create agent
    agent = create_tool_calling_agent(llm=model, tools=tools, prompt=prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    # Start metrics tracking
    metrics_tracker.start_timer()

    agent_executor.invoke(
        input={"input": TASK_DESCRIPTION},
        config={"callbacks": [callback_handler]}
    )

    # Stop metrics tracking
    metrics_tracker.stop_timer()

    # Build and display results
    benchmark_result = metrics_tracker.build_result(
        framework=f"LangChain ({provider})",
        model=display_name,
        task_description=TASK_DESCRIPTION,
        cart=session.cart,
    )

    # Calculate estimated cost based on provider
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
    output_file = output_dir / f"langchain_{safe_filename}_result.json"
    with open(output_file, "w") as f:
        json.dump(benchmark_result.model_dump(), f, indent=2)

    print(f"\nResults saved to: {output_file}")


def run_benchmark() -> None:
    """Run the LangChain shopping cart benchmark with multiple models."""
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

        run_single_benchmark(
            provider=provider,
            model_id=model_config["model_id"],
            display_name=model_config["display_name"]
        )
        completed_count += 1

    print("\n" + "=" * 60)
    print(f"Completed {completed_count} benchmark(s)!")
    print("=" * 60)


if __name__ == "__main__":
    run_benchmark()
