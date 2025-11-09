"""Main module with calculate_total function."""

def calculate_total(items: list[float]) -> float:
    """Calculate the total sum of items."""
    return sum(items)


def process_order(prices: list[float]) -> dict[str, float]:
    """Process an order and return summary."""
    total = calculate_total(prices)
    tax = total * 0.1
    return {
        "subtotal": total,
        "tax": tax,
        "total": total + tax
    }
