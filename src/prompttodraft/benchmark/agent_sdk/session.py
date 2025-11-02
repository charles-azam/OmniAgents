"""Shopping session that encapsulates cart state and operations."""

from prompttodraft.benchmark.agent_sdk.types import CheckoutSummary
from prompttodraft.benchmark.agent_sdk.types import ShoppingCart
from prompttodraft.benchmark.agent_sdk.catalog import get_categories
from prompttodraft.benchmark.agent_sdk.catalog import get_item_by_name
from prompttodraft.benchmark.agent_sdk.catalog import get_items_by_category


class ShoppingSession:
    """Encapsulates a shopping session with cart state and operations."""

    def __init__(self):
        """Initialize a new shopping session with an empty cart."""
        self.cart = ShoppingCart()

    def list_categories(self) -> list[str]:
        """
        Get a list of all available shopping categories.

        Returns:
            List of category names.
        """
        return get_categories()

    def search_item(self, category: str) -> list[dict[str, str | float]]:
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

    def get_price(self, item_name: str) -> float | str:
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

    def add_to_cart(self, item_name: str) -> str:
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

        self.cart.add_item(item=item)
        return f"Added '{item.name}' (${item.price:.2f}) to cart. Current total: ${self.cart.total:.2f}"

    def remove_from_cart(self, item_name: str) -> str:
        """
        Remove an item from the shopping cart.

        Args:
            item_name: The name of the item to remove from the cart.

        Returns:
            Success message with updated cart total, or error message if item not in cart.
        """
        success = self.cart.remove_item(item_name=item_name)
        if not success:
            return f"Error: Item '{item_name}' not found in cart"

        return f"Removed '{item_name}' from cart. Current total: ${self.cart.total:.2f}"

    def get_cart_total(self) -> float:
        """
        Get the current total price of all items in the cart.

        Returns:
            The total price of all items currently in the cart.
        """
        return round(self.cart.total, 2)

    def checkout(self) -> CheckoutSummary:
        """
        Finalize the purchase and get a summary of the cart.
        This completes the shopping task.

        Returns:
            A summary of the cart including total, item count, and list of items.
        """
        summary = self.cart.get_summary()
        return CheckoutSummary(
            total=summary.total,
            item_count=summary.item_count,
            items=summary.items,
            message="Checkout complete! Thank you for shopping.",
        )
