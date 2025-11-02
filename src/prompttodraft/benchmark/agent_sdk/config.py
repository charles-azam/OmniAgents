"""Shared configuration for benchmarks."""

# System prompt for shopping cart task
SYSTEM_PROMPT = """You are a shopping assistant. Your goal is to fill a shopping cart
to be as close to $100 as possible WITHOUT going over the budget.

Strategy suggestions:
1. First, explore the available categories to understand what's available
2. Search items in different categories to see prices
3. Add items strategically to get close to $100
4. You can remove items and add different ones to optimize
5. When satisfied with your cart (close to $100 but not over), call checkout

Important: You must call the checkout tool when you're done selecting items."""

# Task description
TASK_DESCRIPTION = "Fill shopping cart to $100 without going over"

# Target budget
TARGET_BUDGET = 100.0

# Model configurations
MODEL_CONFIGS = [
    {
        "provider": "openai",
        "model_id": "gpt-5-mini",
        "display_name": "GPT-5 Mini (OpenAI)",
    },
    {
        "provider": "huggingface",
        "model_id": "openai/gpt-oss-120b",
        "display_name": "GPT OSS 120B (HuggingFace)",
    },
    {
        "provider": "xai",
        "model_id": "grok-4-fast-reasoning",
        "display_name": "Grok 4 Fast Reasoning (X.AI)",
    },
    {
        "provider": "xai",
        "model_id": "grok-4-fast-non-reasoning",
        "display_name": "Grok 4 Fast Non-Reasoning (X.AI)",
    },
]

MODEL_CONFIGS_NO_XAI = [
    {
        "provider": "openai",
        "model_id": "gpt-5-mini",
        "display_name": "GPT-5 Mini (OpenAI)",
    },
    {
        "provider": "huggingface",
        "model_id": "openai/gpt-oss-120b",
        "display_name": "GPT OSS 120B (HuggingFace)",
    },
]

# API key requirements per provider
REQUIRED_API_KEYS = {
    "openai": "OPENAI_API_KEY",
    "huggingface": "HF_TOKEN",
    "xai": "XAI_API_KEY",
}

# Pricing per provider (per 1M tokens)
PRICING = {
    "openai": {
        "input": 0.25,
        "output": 2.00,
    },
    "xai": {
        "input": 0.20,
        "output": 0.50,
    },
    "huggingface": {
        "input": 0.15,
        "output": 0.60,
    },
}


def get_pricing_for_provider(provider: str) -> tuple[float, float]:
    """
    Get pricing for a provider converted to per 1K tokens.

    Args:
        provider: Provider name.

    Returns:
        Tuple of (input_cost_per_1k, output_cost_per_1k).
    """
    pricing = PRICING.get(provider, PRICING["huggingface"])
    return pricing["input"] / 1000, pricing["output"] / 1000
