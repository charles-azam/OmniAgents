"""
Task 6: Multi-File Search and Replace

Scenario: Rename a function across multiple files
Difficulty: Easy
Exercises: grep, edit, bash (tests)
"""
from pathlib import Path
import subprocess

from prompttodraft.benchmark_tasks.base_task import BenchmarkTask, TaskSetup, TaskEvaluation


class SearchReplaceTask(BenchmarkTask):
    """
    Multi-file search and replace benchmark task.

    The agent must rename a function across multiple files and ensure tests pass.
    """

    def get_task_config(self) -> TaskSetup:
        """Get task configuration."""
        return TaskSetup(
            task_name="search_replace",
            description="Rename function 'calculate_total' to 'compute_sum' across codebase",
            difficulty="easy",
            workspace_dir=self.workspace_dir,
            initial_prompt="""Rename the function `calculate_total` to `compute_sum` across the entire codebase.

The function is used in multiple files. Make sure to:
1. Find all occurrences of the function (definition and calls)
2. Rename them consistently
3. Ensure all tests pass after renaming

Run `python -m pytest` to verify the tests pass.""",
            max_iterations=20,
            timeout=300  # 5 minutes
        )

    def setup(self) -> None:
        """Set up the workspace with files containing the function."""
        # Create main module
        main_code = '''"""Main module with calculate_total function."""

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
'''

        # Create utils module
        utils_code = '''"""Utility functions."""
from .main import calculate_total


def get_average(items: list[float]) -> float:
    """Get average of items."""
    total = calculate_total(items)
    return total / len(items) if items else 0.0


def format_total(items: list[float]) -> str:
    """Format total as string."""
    total = calculate_total(items)
    return f"${total:.2f}"
'''

        # Create tests
        test_code = '''"""Tests for the codebase."""
import pytest
from src.main import calculate_total, process_order
from src.utils import get_average, format_total


def test_calculate_total():
    """Test calculate_total function."""
    assert calculate_total([1.0, 2.0, 3.0]) == 6.0
    assert calculate_total([]) == 0.0


def test_process_order():
    """Test process_order function."""
    result = process_order([10.0, 20.0])
    assert result["subtotal"] == 30.0
    assert result["tax"] == 3.0
    assert result["total"] == 33.0


def test_get_average():
    """Test get_average function."""
    assert get_average([1.0, 2.0, 3.0]) == 2.0
    assert get_average([]) == 0.0


def test_format_total():
    """Test format_total function."""
    assert format_total([10.5, 20.3]) == "$30.80"
'''

        # Create directory structure
        src_dir = self.workspace_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        tests_dir = self.workspace_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)

        # Write files
        (src_dir / "__init__.py").write_text("")
        (src_dir / "main.py").write_text(main_code)
        (src_dir / "utils.py").write_text(utils_code)
        (tests_dir / "__init__.py").write_text("")
        (tests_dir / "test_main.py").write_text(test_code)

        # Create pytest.ini
        pytest_ini = """[pytest]
python_files = test_*.py
python_functions = test_*
testpaths = tests
"""
        (self.workspace_dir / "pytest.ini").write_text(pytest_ini)

    def get_initial_prompt(self) -> str:
        """Get the initial prompt."""
        return self.task_config.initial_prompt

    def evaluate(self) -> TaskEvaluation:
        """
        Evaluate the solution.

        Checks:
        1. All occurrences of 'calculate_total' are renamed to 'compute_sum'
        2. Tests pass
        3. Code quality (no syntax errors)
        """
        errors = []
        warnings = []
        details = {}

        # Check 1: Verify renaming
        src_dir = self.workspace_dir / "src"
        test_dir = self.workspace_dir / "tests"

        old_name_count = 0
        new_name_count = 0

        for file in list(src_dir.rglob("*.py")) + list(test_dir.rglob("*.py")):
            content = file.read_text()
            old_name_count += content.count("calculate_total")
            new_name_count += content.count("compute_sum")

        if old_name_count > 0:
            errors.append(f"Found {old_name_count} unrenamed occurrences of 'calculate_total'")
        if new_name_count == 0:
            errors.append("Function 'compute_sum' not found - renaming may not have occurred")

        details["old_name_occurrences"] = old_name_count
        details["new_name_occurrences"] = new_name_count

        # Check 2: Run tests
        try:
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
                errors.append("Tests failed after renaming")

        except subprocess.TimeoutExpired:
            errors.append("Tests timed out")
            test_passed = False
        except Exception as e:
            errors.append(f"Error running tests: {str(e)}")
            test_passed = False

        # Calculate scores
        success = old_name_count == 0 and new_name_count > 0 and test_passed
        test_pass_rate = 1.0 if test_passed else 0.0

        # Correctness: based on renaming completeness
        if old_name_count == 0 and new_name_count > 0:
            correctness_score = 1.0
        elif old_name_count > 0 and new_name_count > 0:
            correctness_score = 0.5  # Partial renaming
        else:
            correctness_score = 0.0

        # Code quality: simple check for syntax errors
        code_quality_score = 1.0  # Assume good unless we find issues
        try:
            import py_compile
            for file in src_dir.rglob("*.py"):
                py_compile.compile(str(file), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"Syntax error: {str(e)}")
            code_quality_score = 0.5

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
        # Workspace will be cleaned up by the runner
        pass

    def get_expected_tools(self) -> list[str]:
        """Get expected tools for this task."""
        return ["grep", "edit", "bash", "view"]
