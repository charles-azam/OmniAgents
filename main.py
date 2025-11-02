"""
Example usage of the ToolAgent with a moderately difficult task.

This script creates a playground environment with a buggy data processing project
and uses the agent to debug and fix it.
"""
import os
import shutil
from pathlib import Path

from prompttodraft.common import PROMPT_TO_DRAFT_REPO_PATH
from prompttodraft.agent.agent import create_agent


def reset_playground() -> Path:
    """
    Reset the playground directory by removing it and recreating it with example files.

    This creates a moderately difficult task: a data processing script with bugs
    that the agent needs to find and fix.

    Returns:
        Path to the playground directory
    """
    playground_dir = PROMPT_TO_DRAFT_REPO_PATH / "playground"

    # Remove the directory if it exists
    if playground_dir.exists():
        shutil.rmtree(path=playground_dir)

    # Create fresh playground directory
    playground_dir.mkdir(parents=True, exist_ok=True)

    # Create a buggy data processor script
    data_processor = '''"""
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
'''

    # Create sample CSV data
    csv_data = '''product,quantity,price
Laptop,10,999.99
Mouse,50,25.50
Keyboard,30,75.00
Monitor,15,350.00
Laptop,5,999.99
Mouse,100,25.50
'''

    # Create expected output file
    expected_output = '''EXPECTED OUTPUT:
Total Revenue: $54074.35
Top Product: Laptop

EXPLANATION:
- Laptop: (10 * 999.99) + (5 * 999.99) = 14999.85
- Mouse: (50 * 25.50) + (100 * 25.50) = 3825.00
- Keyboard: (30 * 75.00) = 2250.00
- Monitor: (15 * 350.00) = 5250.00
Total: 26324.85

Wait, that's wrong! The total should be 26324.85, not 54074.35
And the top product should be Laptop (14999.85), not the minimum!

BUGS TO FIX:
1. calculate_total_revenue: Uses + instead of * for quantity and price
2. find_top_product: Uses min() instead of max()
'''

    # Create task description
    task_description = '''# Data Processing Bug Hunt

## Task
This playground contains a data processing script with bugs. Your mission:

1. **Understand the code**: Read data_processor.py and sales_data.csv
2. **Run the script**: Execute it and see what output it produces
3. **Find the bugs**: There are 2 bugs in the code
4. **Fix the bugs**: Correct the issues
5. **Verify**: Run the script again and confirm it matches expected_output.txt

## Expected Behavior
The script should:
- Calculate total revenue correctly (quantity × price for each sale)
- Find the product with the HIGHEST total sales (not lowest)

## Files
- `data_processor.py`: The buggy script
- `sales_data.csv`: Sample sales data
- `expected_output.txt`: What the correct output should be
- `TASK.md`: This file

Good luck!
'''

    # Write all files
    (playground_dir / "data_processor.py").write_text(data=data_processor)
    (playground_dir / "sales_data.csv").write_text(data=csv_data)
    (playground_dir / "expected_output.txt").write_text(data=expected_output)
    (playground_dir / "TASK.md").write_text(data=task_description)

    print(f"✅ Playground reset at: {playground_dir}")
    print(f"📁 Created files:")
    print(f"   - data_processor.py (buggy script)")
    print(f"   - sales_data.csv (sample data)")
    print(f"   - expected_output.txt (correct output)")
    print(f"   - TASK.md (task description)")

    return playground_dir


def main() -> None:
    """
    Main function: Reset playground and use agent to solve the task.
    """
    # Reset the playground
    print("="*80)
    print("RESETTING PLAYGROUND")
    print("="*80 + "\n")

    playground_dir = reset_playground()

    # Create the agent
    print("\n" + "="*80)
    print("CREATING AGENT")
    print("="*80 + "\n")

    agent = create_agent(cwd=str(playground_dir), log_file="agent_playground.log")

    # Give the agent the task
    print("\n" + "="*80)
    print("AGENT TASK: DEBUG AND FIX THE DATA PROCESSOR")
    print("="*80 + "\n")

    task = """
    Read the TASK.md file to understand the task, then:
    1. Read and understand the data_processor.py code
    2. Run the script to see the current (buggy) output
    3. Find the 2 bugs in the code
    4. Fix both bugs
    5. Run the script again to verify it produces the correct output

    Be methodical and explain what you find at each step.
    """

    agent.run(user_input=task)

    print("\n" + "="*80)
    print("✅ TASK COMPLETED")
    print("="*80)
    print(f"📝 Full logs saved to: {os.path.abspath('agent_playground.log')}")


if __name__ == "__main__":
    main()
