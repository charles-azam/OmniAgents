"""Item catalog for shopping cart benchmark."""

from prompttodraft.benchmark_agent_sdk.types import Item

# Define the catalog with ~30 items across 5 categories
# Prices range from $5 to $40 to allow for interesting optimization problems
_CATALOG: list[Item] = [
    # Electronics (5 items)
    Item(
        name="Wireless Mouse",
        category="electronics",
        price=15.99,
        description="Ergonomic wireless mouse with USB receiver",
    ),
    Item(
        name="USB Cable",
        category="electronics",
        price=8.50,
        description="6ft USB-C to USB-A cable",
    ),
    Item(
        name="Phone Stand",
        category="electronics",
        price=12.99,
        description="Adjustable phone stand for desk",
    ),
    Item(
        name="Bluetooth Speaker",
        category="electronics",
        price=35.00,
        description="Portable Bluetooth speaker with 8-hour battery",
    ),
    Item(
        name="Screen Cleaner",
        category="electronics",
        price=6.99,
        description="Screen cleaning kit with microfiber cloth",
    ),
    Item(
        name="Webcam Cover",
        category="electronics",
        price=5.49,
        description="Privacy webcam cover slider",
    ),
    # Books (6 items)
    Item(
        name="Python Programming Guide",
        category="books",
        price=24.99,
        description="Comprehensive guide to Python programming",
    ),
    Item(
        name="Science Fiction Novel",
        category="books",
        price=14.50,
        description="Bestselling sci-fi adventure novel",
    ),
    Item(
        name="Cookbook",
        category="books",
        price=19.99,
        description="Quick and easy recipes for beginners",
    ),
    Item(
        name="Mystery Thriller",
        category="books",
        price=12.99,
        description="Page-turning mystery thriller",
    ),
    Item(
        name="Self-Help Book",
        category="books",
        price=16.50,
        description="Guide to personal development",
    ),
    Item(
        name="Children's Picture Book",
        category="books",
        price=9.99,
        description="Colorful illustrated children's book",
    ),
    # Clothing (6 items)
    Item(
        name="Cotton T-Shirt",
        category="clothing",
        price=18.99,
        description="100% cotton crew neck t-shirt",
    ),
    Item(
        name="Socks (3-pack)",
        category="clothing",
        price=11.99,
        description="Athletic socks 3-pack",
    ),
    Item(
        name="Baseball Cap",
        category="clothing",
        price=15.50,
        description="Adjustable baseball cap",
    ),
    Item(
        name="Scarf",
        category="clothing",
        price=22.00,
        description="Warm winter scarf",
    ),
    Item(
        name="Gloves",
        category="clothing",
        price=13.99,
        description="Touchscreen-compatible gloves",
    ),
    Item(
        name="Belt",
        category="clothing",
        price=19.50,
        description="Leather belt with metal buckle",
    ),
    # Food (6 items)
    Item(
        name="Coffee Beans (1lb)",
        category="food",
        price=14.99,
        description="Premium arabica coffee beans",
    ),
    Item(
        name="Tea Sampler",
        category="food",
        price=16.99,
        description="Assorted tea bags sampler pack",
    ),
    Item(
        name="Chocolate Bar",
        category="food",
        price=5.99,
        description="Artisan dark chocolate bar",
    ),
    Item(
        name="Trail Mix",
        category="food",
        price=8.50,
        description="Mixed nuts and dried fruit",
    ),
    Item(
        name="Honey Jar",
        category="food",
        price=12.50,
        description="Raw organic honey 12oz",
    ),
    Item(
        name="Olive Oil",
        category="food",
        price=18.99,
        description="Extra virgin olive oil 500ml",
    ),
    # Toys (6 items)
    Item(
        name="Puzzle (1000 pieces)",
        category="toys",
        price=17.99,
        description="Challenging 1000-piece jigsaw puzzle",
    ),
    Item(
        name="Board Game",
        category="toys",
        price=29.99,
        description="Classic family board game",
    ),
    Item(
        name="Playing Cards",
        category="toys",
        price=6.50,
        description="Standard deck of playing cards",
    ),
    Item(
        name="Toy Car",
        category="toys",
        price=11.99,
        description="Die-cast metal toy car",
    ),
    Item(
        name="Coloring Book Set",
        category="toys",
        price=13.50,
        description="Adult coloring book with colored pencils",
    ),
    Item(
        name="Fidget Toy",
        category="toys",
        price=7.99,
        description="Stress-relief fidget toy",
    ),
]

# Create a lookup dictionary for quick access
_CATALOG_DICT: dict[str, Item] = {item.name.lower(): item for item in _CATALOG}


def get_catalog() -> list[Item]:
    """Get the complete item catalog."""
    return _CATALOG.copy()


def get_categories() -> list[str]:
    """Get list of all available categories."""
    return ["electronics", "books", "clothing", "food", "toys"]


def get_items_by_category(category: str) -> list[Item]:
    """Get all items in a specific category."""
    category_lower = category.lower()
    return [item for item in _CATALOG if item.category.lower() == category_lower]


def get_item_by_name(name: str) -> Item | None:
    """Get an item by its name (case-insensitive)."""
    return _CATALOG_DICT.get(name.lower())
