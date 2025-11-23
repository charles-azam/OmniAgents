"""Utility functions."""
from .main import calculate_total


def get_average(items: list[float]) -> float:
    """Get average of items."""
    total = calculate_total(items)
    return total / len(items) if items else 0.0


def format_total(items: list[float]) -> str:
    """Format total as string."""
    total = calculate_total(items)
    return f"${total:.2f}"
