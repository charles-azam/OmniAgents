"""Shopping cart tools for benchmark."""

from prompttodraft.benchmark.types import CheckoutSummary
from prompttodraft.benchmark.types import Item
from prompttodraft.benchmark.types import ShoppingCart
from prompttodraft.benchmark.catalog import get_items_by_category
from prompttodraft.benchmark.catalog import get_item_by_name
from prompttodraft.benchmark.catalog import get_categories

# Global shopping cart state (will be reset between benchmark runs)
_shopping_cart = ShoppingCart()


def reset_cart() -> None:
    """Reset the shopping cart to empty state."""
    global _shopping_cart
    _shopping_cart = ShoppingCart()


def get_cart() -> ShoppingCart:
    """Get the current shopping cart (for internal use)."""
    return _shopping_cart


def search_item(category: str) -> list[dict[str, str | float]]:
    """
    Search for items in a specific category.

    Args:
        category: The category to search in. Available categories: electronics, books, clothing, food, toys.

    Returns:
        List of items in the category with their name, price, and description.
    """
    items = get_items_by_category(category=category)
    return [
        {
            "name": item.name,
            "price": item.price,
            "description": item.description,
        }
        for item in items
    ]


def get_price(item_name: str) -> float | str:
    """
    Get the price of a specific item by name.

    Args:
        item_name: The name of the item to get the price for.

    Returns:
        The price of the item, or an error message if not found.
    """
    item = get_item_by_name(name=item_name)
    if item is None:
        return f"Error: Item '{item_name}' not found in catalog"
    return item.price


def add_to_cart(item_name: str) -> str:
    """
    Add an item to the shopping cart.

    Args:
        item_name: The name of the item to add to the cart.

    Returns:
        Success message with updated cart total, or error message if item not found.
    """
    item = get_item_by_name(name=item_name)
    if item is None:
        return f"Error: Item '{item_name}' not found in catalog"

    _shopping_cart.add_item(item=item)
    return f"Added '{item.name}' (${item.price:.2f}) to cart. Current total: ${_shopping_cart.total:.2f}"


def remove_from_cart(item_name: str) -> str:
    """
    Remove an item from the shopping cart.

    Args:
        item_name: The name of the item to remove from the cart.

    Returns:
        Success message with updated cart total, or error message if item not in cart.
    """
    success = _shopping_cart.remove_item(item_name=item_name)
    if not success:
        return f"Error: Item '{item_name}' not found in cart"

    return f"Removed '{item_name}' from cart. Current total: ${_shopping_cart.total:.2f}"


def get_cart_total() -> float:
    """
    Get the current total price of all items in the cart.

    Returns:
        The total price of all items currently in the cart.
    """
    return round(_shopping_cart.total, 2)


def checkout() -> CheckoutSummary:
    """
    Finalize the purchase and get a summary of the cart.
    This completes the shopping task.

    Returns:
        A summary of the cart including total, item count, and list of items.
    """
    summary = _shopping_cart.get_summary()
    return CheckoutSummary(
        total=summary.total,
        item_count=summary.item_count,
        items=summary.items,
        message="Checkout complete! Thank you for shopping.",
    )


def list_categories() -> list[str]:
    """
    Get a list of all available shopping categories.

    Returns:
        List of category names.
    """
    return get_categories()
