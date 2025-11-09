"""
Task: Fix Bugs in Code

Scenario: Find and fix 3 bugs in a calculator module
Difficulty: Medium
Exercises: read_file, search_file_content, replace, run_shell_command
"""
from pathlib import Path
import subprocess

from prompttodraft.benchmark.tasks.base_task import BenchmarkTask, TaskSetup, TaskEvaluation


class BugFixTask(BenchmarkTask):
    """
    Bug fixing benchmark task.

    The agent must find and fix 3 bugs in a calculator module:
    1. Off-by-one error in power function
    2. Logic error in is_even function
    3. Division by zero not handled in average function
    """

    def get_task_config(self) -> TaskSetup:
        """Get task configuration."""
        return TaskSetup(
            task_name="bug_fix",
            description="Find and fix 3 bugs in calculator.py to make all tests pass",
            difficulty="medium",
            workspace_dir=self.workspace_dir,
            initial_prompt="""There are 3 bugs in the calculator.py module that cause tests to fail.

Your task:
1. Run the tests to see which ones fail: `python -m pytest -v`
2. Find and fix the bugs in calculator.py
3. Ensure ALL tests pass
4. Do NOT modify the test file

The bugs are subtle but important. Read the test expectations carefully.

Hints:
- Look for off-by-one errors
- Check logic conditions
- Consider edge cases like division by zero

Run tests with: `python -m pytest -v`""",
            max_iterations=25,
            timeout=300  # 5 minutes
        )

    def setup(self) -> None:
        """Set up the workspace with buggy code and tests."""
        # Create buggy calculator module
        calculator_code = '''"""Calculator module with some bugs to fix."""


def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


def divide(a: float, b: float) -> float:
    """
    Divide a by b.

    Raises:
        ValueError: If b is zero
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def power(base: float, exponent: int) -> float:
    """
    Calculate base raised to exponent.

    BUG: Off-by-one error in the loop
    """
    result = 1.0
    for _ in range(exponent - 1):  # BUG: Should be range(exponent)
        result *= base
    return result


def is_even(n: int) -> bool:
    """
    Check if a number is even.

    BUG: Logic error
    """
    return n % 2 == 1  # BUG: Should be == 0


def average(numbers: list[float]) -> float:
    """
    Calculate average of numbers.

    BUG: Doesn't handle empty list
    """
    total = sum(numbers)
    return total / len(numbers)  # BUG: Will crash on empty list


def factorial(n: int) -> int:
    """Calculate factorial (this one is correct)."""
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
'''

        # Create comprehensive tests
        test_code = '''"""Tests for calculator module."""
import pytest
from calculator import (
    add, subtract, multiply, divide, power,
    is_even, average, factorial
)


def test_add():
    """Test addition."""
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0


def test_subtract():
    """Test subtraction."""
    assert subtract(5, 3) == 2
    assert subtract(0, 5) == -5


def test_multiply():
    """Test multiplication."""
    assert multiply(3, 4) == 12
    assert multiply(0, 5) == 0


def test_divide():
    """Test division."""
    assert divide(10, 2) == 5
    assert divide(7, 2) == 3.5

    with pytest.raises(ValueError):
        divide(5, 0)


def test_power():
    """Test power function - THIS WILL FAIL DUE TO BUG."""
    assert power(2, 3) == 8  # 2^3 = 8
    assert power(5, 2) == 25  # 5^2 = 25
    assert power(3, 0) == 1  # 3^0 = 1
    assert power(10, 1) == 10  # 10^1 = 10


def test_is_even():
    """Test is_even function - THIS WILL FAIL DUE TO BUG."""
    assert is_even(2) == True
    assert is_even(4) == True
    assert is_even(0) == True
    assert is_even(1) == False
    assert is_even(3) == False
    assert is_even(7) == False


def test_average():
    """Test average function - THIS WILL FAIL DUE TO BUG."""
    assert average([1, 2, 3, 4, 5]) == 3.0
    assert average([10, 20]) == 15.0
    assert average([5]) == 5.0

    # Should handle empty list gracefully
    with pytest.raises(ValueError, match="Cannot calculate average"):
        average([])


def test_factorial():
    """Test factorial (this should pass)."""
    assert factorial(0) == 1
    assert factorial(1) == 1
    assert factorial(5) == 120
    assert factorial(3) == 6

    with pytest.raises(ValueError):
        factorial(-1)
'''

        # Write files
        (self.workspace_dir / "calculator.py").write_text(calculator_code)

        tests_dir = self.workspace_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "__init__.py").write_text("")
        (tests_dir / "test_calculator.py").write_text(test_code)

        # Create pytest.ini
        pytest_ini = """[pytest]
python_files = test_*.py
python_functions = test_*
testpaths = tests
"""
        (self.workspace_dir / "pytest.ini").write_text(pytest_ini)

        # Create pyproject.toml
        pyproject_toml = '''[project]
name = "bug-fix"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = []
'''
        (self.workspace_dir / "pyproject.toml").write_text(pyproject_toml)

        # Create README
        readme = """# Bug Fix Task

Fix 3 bugs in calculator.py to make all tests pass.

## Bugs to Find
1. **power()** - Off-by-one error in loop
2. **is_even()** - Logic error in condition
3. **average()** - Doesn't handle empty list (should raise ValueError)

## Running Tests
```bash
python -m pytest -v
```

## Expected Behavior
- power(2, 3) should return 8 (not 4)
- is_even(2) should return True (not False)
- average([]) should raise ValueError with message "Cannot calculate average"
"""
        (self.workspace_dir / "README.md").write_text(readme)

    def get_initial_prompt(self) -> str:
        """Get the initial prompt."""
        return self.task_config.initial_prompt

    def evaluate(self) -> TaskEvaluation:
        """
        Evaluate the solution.

        Checks:
        1. calculator.py still exists
        2. All 3 bugs are fixed
        3. All tests pass
        4. No new bugs introduced
        5. Tests file was not modified
        """
        errors = []
        warnings = []
        details = {}

        calculator_file = self.workspace_dir / "calculator.py"
        test_file = self.workspace_dir / "tests" / "test_calculator.py"

        # Check 1: File exists
        if not calculator_file.exists():
            errors.append("calculator.py not found")
            return TaskEvaluation(
                success=False,
                test_pass_rate=0.0,
                correctness_score=0.0,
                code_quality_score=0.0,
                errors=errors,
                warnings=warnings,
                details=details
            )

        # Check 2: Read calculator.py and verify bugs are fixed
        try:
            code_content = calculator_file.read_text()

            # Check Bug 1: power function should use range(exponent), not range(exponent - 1)
            bug1_fixed = "range(exponent)" in code_content and "range(exponent - 1)" not in code_content
            details["bug1_power_fixed"] = bug1_fixed

            # Check Bug 2: is_even should use n % 2 == 0, not n % 2 == 1
            bug2_fixed = ("n % 2 == 0" in code_content or "n%2==0" in code_content) and \
                        ("n % 2 == 1" not in code_content or "# BUG:" in code_content.split("n % 2 == 1")[0] if "n % 2 == 1" in code_content else True)
            details["bug2_is_even_fixed"] = bug2_fixed

            # Check Bug 3: average should handle empty list
            bug3_fixed = ("len(numbers) == 0" in code_content or "not numbers" in code_content) and \
                        ("ValueError" in code_content)
            details["bug3_average_fixed"] = bug3_fixed

            if not bug1_fixed:
                errors.append("Bug 1 (power function off-by-one error) not fixed")
            if not bug2_fixed:
                errors.append("Bug 2 (is_even logic error) not fixed")
            if not bug3_fixed:
                errors.append("Bug 3 (average empty list handling) not fixed")

        except Exception as e:
            errors.append(f"Error reading calculator.py: {str(e)}")

        # Check 3: Install pytest
        try:
            subprocess.run(
                ["uv", "pip", "install", "pytest"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
        except Exception as e:
            warnings.append(f"Failed to install pytest: {str(e)}")

        # Check 4: Run tests
        test_passed = False
        tests_run = 0
        tests_passed = 0

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "-v", "--tb=short"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            test_passed = result.returncode == 0
            details["test_output"] = result.stdout + result.stderr
            details["test_returncode"] = result.returncode

            # Parse test output to count passed/failed
            import re
            passed_match = re.search(r'(\d+) passed', result.stdout)
            failed_match = re.search(r'(\d+) failed', result.stdout)

            if passed_match:
                tests_passed = int(passed_match.group(1))
            if failed_match:
                tests_failed = int(failed_match.group(1))
                tests_run = tests_passed + tests_failed
            else:
                tests_run = tests_passed

            details["tests_passed"] = tests_passed
            details["tests_run"] = tests_run

            if not test_passed:
                errors.append(f"Tests failed: {tests_passed}/{tests_run} passed")

        except subprocess.TimeoutExpired:
            errors.append("Tests timed out")
        except Exception as e:
            errors.append(f"Error running tests: {str(e)}")

        # Check 5: Verify test file wasn't modified (check if it has the same structure)
        try:
            test_content = test_file.read_text()

            # Verify key test functions exist
            required_tests = ["test_power", "test_is_even", "test_average"]
            for test_name in required_tests:
                if f"def {test_name}" not in test_content:
                    warnings.append(f"Test function {test_name} missing - tests may have been modified")

        except Exception as e:
            warnings.append(f"Error reading test file: {str(e)}")

        # Calculate scores
        bugs_fixed = sum([
            details.get("bug1_power_fixed", False),
            details.get("bug2_is_even_fixed", False),
            details.get("bug3_average_fixed", False)
        ])

        correctness_score = bugs_fixed / 3.0
        test_pass_rate = tests_passed / tests_run if tests_run > 0 else 0.0

        code_quality_score = 1.0
        try:
            import py_compile
            py_compile.compile(str(calculator_file), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"Syntax error: {str(e)}")
            code_quality_score = 0.3

        success = test_passed and bugs_fixed == 3

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
        pass

    def get_expected_tools(self) -> list[str]:
        """Get expected tools for this task."""
        return ["read_file", "search_file_content", "replace", "run_shell_command"]
