"""Tests for the benchmark package."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from prompttodraft.benchmark.tools import add_to_cart
from prompttodraft.benchmark.tools import checkout
from prompttodraft.benchmark.tools import get_cart_total
from prompttodraft.benchmark.tools import get_price
from prompttodraft.benchmark.tools import list_categories
from prompttodraft.benchmark.tools import reset_cart
from prompttodraft.benchmark.tools import search_item
from prompttodraft.benchmark.metrics import MetricsTracker


def test_list_categories():
    """Test listing categories."""
    categories = list_categories()
    assert isinstance(categories, list)
    assert len(categories) == 5
    assert "electronics" in categories
    assert "books" in categories
    print("✓ test_list_categories passed")


def test_search_item():
    """Test searching items in a category."""
    items = search_item(category="electronics")
    assert isinstance(items, list)
    assert len(items) > 0
    assert "name" in items[0]
    assert "price" in items[0]
    print("✓ test_search_item passed")


def test_get_price():
    """Test getting item price."""
    price = get_price(item_name="Wireless Mouse")
    assert isinstance(price, float)
    assert price > 0
    print("✓ test_get_price passed")


def test_shopping_flow():
    """Test complete shopping flow."""
    # Reset cart
    reset_cart()

    # Add items
    result = add_to_cart(item_name="Wireless Mouse")
    assert "Added" in result

    # Get total
    total = get_cart_total()
    assert total > 0

    # Add another item
    add_to_cart(item_name="USB Cable")
    new_total = get_cart_total()
    assert new_total > total

    # Checkout
    summary = checkout()
    assert summary.total > 0
    assert summary.item_count == 2
    assert len(summary.items) == 2
    assert "Wireless Mouse" in summary.items
    assert summary.message == "Checkout complete! Thank you for shopping."

    print("✓ test_shopping_flow passed")


def test_metrics_tracker():
    """Test metrics tracker."""
    tracker = MetricsTracker(target_budget=100.0)

    # Start tracking
    tracker.start()

    # Record some tool calls
    tracker.record_tool_call(tool_name="search_item")
    tracker.record_tool_call(tool_name="add_to_cart")
    tracker.record_tool_call(tool_name="add_to_cart")

    # Stop tracking
    tracker.stop()

    # Verify metrics
    assert tracker.get_execution_time() > 0
    assert tracker.tool_calls["search_item"] == 1
    assert tracker.tool_calls["add_to_cart"] == 2

    print("✓ test_metrics_tracker passed")


if __name__ == "__main__":
    test_list_categories()
    test_search_item()
    test_get_price()
    test_shopping_flow()
    test_metrics_tracker()
    print("\n✓ All tests passed!")
