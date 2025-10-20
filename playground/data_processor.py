"""
Data processor for sales analysis.

This module processes sales data from CSV files and generates reports.
"""


def parse_csv_file(file_path: str) -> list[dict[str, str]]:
    """
    Parse a CSV file and return a list of dictionaries.

    Args:
        file_path: Path to the CSV file

    Returns:
        List of dictionaries representing each row
    """
    with open(file_path, "r") as f:
        lines = f.readlines()

    headers = lines[0].strip().split(",")
    data = []

    for line in lines[1:]:
        values = line.strip().split(",")
        row = {}
        for i, header in enumerate(headers):
            row[header] = values[i]
        data.append(row)

    return data


def calculate_total_revenue(sales_data: list[dict[str, str]]) -> float:
    """
    Calculate total revenue from sales data.

    Args:
        sales_data: List of sales records

    Returns:
        Total revenue
    """
    total = 0
    for sale in sales_data:
        quantity = int(sale["quantity"])
        price = float(sale["price"])
        total += quantity + price  # BUG: Should be multiplication, not addition!

    return total


def find_top_product(sales_data: list[dict[str, str]]) -> str:
    """
    Find the product with the highest total sales.

    Args:
        sales_data: List of sales records

    Returns:
        Name of the top product
    """
    product_revenues = {}

    for sale in sales_data:
        product = sale["product"]
        quantity = int(sale["quantity"])
        price = float(sale["price"])
        revenue = quantity * price

        if product in product_revenues:
            product_revenues[product] += revenue
        else:
            product_revenues[product] = revenue

    # BUG: This returns minimum, not maximum!
    top_product = min(product_revenues, key=product_revenues.get)
    return top_product


def generate_report(file_path: str) -> None:
    """
    Generate a sales report from a CSV file.

    Args:
        file_path: Path to the CSV file
    """
    sales_data = parse_csv_file(file_path=file_path)
    total_revenue = calculate_total_revenue(sales_data=sales_data)
    top_product = find_top_product(sales_data=sales_data)

    print(f"Total Revenue: ${total_revenue:.2f}")
    print(f"Top Product: {top_product}")


if __name__ == "__main__":
    generate_report(file_path="sales_data.csv")
