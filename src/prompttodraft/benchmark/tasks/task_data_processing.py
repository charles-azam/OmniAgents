"""
Task: Data Processing Script

Scenario: Process CSV data with filtering and aggregation
Difficulty: Easy
Exercises: write_file, read_file, run_shell_command
"""
from pathlib import Path
import subprocess
import csv

from prompttodraft.benchmark.base_task import BenchmarkTask, TaskSetup, TaskEvaluation
from prompttodraft.benchmark.fixture_utils import copy_fixture_dir


class DataProcessingTask(BenchmarkTask):
    """
    Data processing benchmark task.

    The agent must create a Python script that processes CSV data,
    filters rows, and outputs aggregated results.
    """

    def get_task_config(self) -> TaskSetup:
        """Get task configuration."""
        return TaskSetup(
            task_name="data_processing",
            description="Create a script to process CSV sales data with filtering and aggregation",
            difficulty="easy",
            workspace_dir=self.workspace_dir,
            initial_prompt="""Create a Python script called `process_sales.py` that processes the sales_data.csv file.

Requirements:

1. Read the sales_data.csv file (columns: date, product, quantity, price)

2. Filter the data to include only rows where:
   - quantity >= 5
   - price >= 10.0

3. Calculate and save to output.csv:
   - Total sales per product (quantity * price summed by product)
   - Sort by total sales descending
   - Columns in output: product, total_sales

4. The script should handle errors gracefully (file not found, invalid data)

5. Create tests in tests/test_process_sales.py that:
   - Test with the provided sample data
   - Test with edge cases (empty file, invalid data)
   - Verify output correctness
   - All tests must pass

6. Output format in output.csv:
   ```
   product,total_sales
   Product A,1500.50
   Product B,950.00
   ```

Run the script with: `python process_sales.py`
Run tests with: `python -m pytest -v`""",
            max_iterations=25,
            timeout=300  # 5 minutes
        )

    def setup(self) -> None:
        """Set up the workspace with sample CSV data."""
        # Copy all files from the data_processing fixture
        copy_fixture_dir("data_processing", self.workspace_dir)

    def get_initial_prompt(self) -> str:
        """Get the initial prompt."""
        return self.task_config.initial_prompt

    def evaluate(self) -> TaskEvaluation:
        """
        Evaluate the solution.

        Checks:
        1. process_sales.py exists
        2. Script runs without errors
        3. output.csv is created
        4. Output has correct format
        5. Calculations are correct
        6. Tests exist and pass
        """
        errors = []
        warnings = []
        details = {}

        script_file = self.workspace_dir / "process_sales.py"
        output_file = self.workspace_dir / "output.csv"
        test_file = self.workspace_dir / "tests" / "test_process_sales.py"

        # Check 1: Script exists
        if not script_file.exists():
            errors.append("process_sales.py not found")
            return TaskEvaluation(
                success=False,
                test_pass_rate=0.0,
                correctness_score=0.0,
                code_quality_score=0.0,
                errors=errors,
                warnings=warnings,
                details=details
            )

        if not test_file.exists():
            warnings.append("tests/test_process_sales.py not found")

        # Check 2: Run the script
        script_ran = False
        try:
            result = subprocess.run(
                ["python", "process_sales.py"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=10
            )

            script_ran = result.returncode == 0
            details["script_output"] = result.stdout + result.stderr
            details["script_returncode"] = result.returncode

            if not script_ran:
                errors.append(f"Script failed to run: {result.stderr}")

        except subprocess.TimeoutExpired:
            errors.append("Script timed out")
        except Exception as e:
            errors.append(f"Error running script: {str(e)}")

        # Check 3: Output file exists
        if not output_file.exists():
            errors.append("output.csv not created")
            return TaskEvaluation(
                success=False,
                test_pass_rate=0.0,
                correctness_score=0.0,
                code_quality_score=0.5,
                errors=errors,
                warnings=warnings,
                details=details
            )

        # Check 4: Validate output format and content
        try:
            with open(output_file, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            details["output_rows"] = len(rows)
            details["output_content"] = str(rows)

            # Check columns
            if rows:
                if 'product' not in rows[0] or 'total_sales' not in rows[0]:
                    errors.append("Output CSV missing required columns (product, total_sales)")

                # Expected results (filtered: quantity >= 5, price >= 10)
                # Laptop: (6 * 999.99) + (7 * 999.99) = 12,999.87
                # Mouse: (10 * 25.50) + (15 * 25.50) + (20 * 25.50) = 1,147.50
                # Keyboard: 8 * 75.00 = 600.00
                # Monitor: 5 * 299.99 = 1,499.95
                expected = {
                    'Laptop': 12999.87,
                    'Mouse': 1147.50,
                    'Keyboard': 600.00,
                    'Monitor': 1499.95
                }

                # Check if all products are present
                products_found = {row['product'] for row in rows}
                expected_products = set(expected.keys())

                if products_found != expected_products:
                    missing = expected_products - products_found
                    extra = products_found - expected_products
                    if missing:
                        errors.append(f"Missing products in output: {missing}")
                    if extra:
                        warnings.append(f"Extra products in output: {extra}")

                # Check calculations
                correct_calculations = 0
                for row in rows:
                    product = row['product']
                    if product in expected:
                        try:
                            total_sales = float(row['total_sales'])
                            expected_sales = expected[product]

                            # Allow small floating point differences
                            if abs(total_sales - expected_sales) < 0.02:
                                correct_calculations += 1
                            else:
                                errors.append(
                                    f"{product}: expected {expected_sales:.2f}, got {total_sales:.2f}"
                                )
                        except ValueError:
                            errors.append(f"Invalid total_sales value for {product}: {row['total_sales']}")

                details["correct_calculations"] = correct_calculations
                details["total_expected"] = len(expected)

                # Check sorting (descending by total_sales)
                if len(rows) >= 2:
                    sorted_correctly = True
                    for i in range(len(rows) - 1):
                        try:
                            current = float(rows[i]['total_sales'])
                            next_val = float(rows[i + 1]['total_sales'])
                            if current < next_val:
                                sorted_correctly = False
                                break
                        except ValueError:
                            pass

                    details["sorted_correctly"] = sorted_correctly
                    if not sorted_correctly:
                        warnings.append("Output not sorted by total_sales descending")

            else:
                errors.append("Output CSV is empty")

        except Exception as e:
            errors.append(f"Error reading output.csv: {str(e)}")

        # Check 5: Run tests if they exist
        test_passed = False
        if test_file.exists():
            try:
                # Install pytest if needed
                subprocess.run(
                    ["uv", "pip", "install", "pytest"],
                    cwd=self.workspace_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                result = subprocess.run(
                    ["python", "-m", "pytest", "-v"],
                    cwd=self.workspace_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                test_passed = result.returncode == 0
                details["test_output"] = result.stdout + result.stderr

                if not test_passed:
                    errors.append("Tests failed")

            except subprocess.TimeoutExpired:
                errors.append("Tests timed out")
            except Exception as e:
                warnings.append(f"Error running tests: {str(e)}")

        # Calculate scores
        correct_calc_ratio = details.get("correct_calculations", 0) / details.get("total_expected", 1)

        correctness_score = correct_calc_ratio if script_ran else 0.0
        test_pass_rate = 1.0 if test_passed else 0.0

        code_quality_score = 1.0
        if not script_ran:
            code_quality_score = 0.3
        elif not details.get("sorted_correctly", True):
            code_quality_score = 0.8

        success = (
            script_ran and
            output_file.exists() and
            correct_calc_ratio >= 0.95 and
            details.get("output_rows", 0) == 4
        )

        return TaskEvaluation(
            success=success,
            test_pass_rate=test_pass_rate,
            correctness_score=correctness_score,
            code_quality_score=code_quality_score,
            errors=errors,
            warnings=warnings,
            details=details
        )

    def cleanup(self) -> None:
        """Clean up workspace."""
        # Clean up output file if it exists
        output_file = self.workspace_dir / "output.csv"
        if output_file.exists():
            output_file.unlink()

    def get_expected_tools(self) -> list[str]:
        """Get expected tools for this task."""
        return ["write_file", "read_file", "run_shell_command"]
