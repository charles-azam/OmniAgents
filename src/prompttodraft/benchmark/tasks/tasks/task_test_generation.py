"""
Task: Generate Comprehensive Tests

Scenario: Generate pytest tests for a module with utility functions
Difficulty: Easy-Medium
Exercises: read_file, write_file, run_shell_command, search_file_content
"""
from pathlib import Path
import subprocess
import re

from prompttodraft.benchmark.tasks.base_task import BenchmarkTask, TaskSetup, TaskEvaluation


class TestGenerationTask(BenchmarkTask):
    """
    Test generation benchmark task.

    The agent must generate comprehensive pytest tests for a given module
    and achieve >80% code coverage.
    """

    def get_task_config(self) -> TaskSetup:
        """Get task configuration."""
        return TaskSetup(
            task_name="test_generation",
            description="Generate comprehensive pytest tests for utils module with >80% coverage",
            difficulty="easy-medium",
            workspace_dir=self.workspace_dir,
            initial_prompt="""Generate comprehensive pytest tests for the utils.py module.

Requirements:
1. Create tests/test_utils.py with pytest tests
2. Test all functions in utils.py
3. Include edge cases (empty inputs, negative numbers, zero, etc.)
4. Achieve >80% code coverage
5. All tests must pass

Run `python -m pytest --cov=utils --cov-report=term-missing -v` to check coverage.

Make sure to test:
- Normal cases
- Edge cases
- Error handling

Install pytest-cov if needed: `uv pip install pytest pytest-cov`""",
            max_iterations=25,
            timeout=300  # 5 minutes
        )

    def setup(self) -> None:
        """Set up the workspace with a module to test."""
        # Create utils module with various functions
        utils_code = '''"""Utility functions for mathematical operations and string processing."""


def add_numbers(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


def multiply_numbers(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


def divide_numbers(a: float, b: float) -> float:
    """
    Divide two numbers.

    Raises:
        ValueError: If b is zero
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def reverse_string(text: str) -> str:
    """Reverse a string."""
    return text[::-1]


def count_vowels(text: str) -> int:
    """Count vowels in a string."""
    if not text:
        return 0
    vowels = "aeiouAEIOU"
    return sum(1 for char in text if char in vowels)


def is_palindrome(text: str) -> bool:
    """Check if a string is a palindrome (ignoring spaces and case)."""
    cleaned = "".join(text.split()).lower()
    return cleaned == cleaned[::-1]


def factorial(n: int) -> int:
    """
    Calculate factorial of n.

    Raises:
        ValueError: If n is negative
    """
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def find_max(numbers: list[float]) -> float:
    """
    Find maximum number in a list.

    Raises:
        ValueError: If list is empty
    """
    if not numbers:
        raise ValueError("Cannot find max of empty list")
    return max(numbers)
'''

        # Write utils module
        (self.workspace_dir / "utils.py").write_text(utils_code)

        # Create tests directory
        tests_dir = self.workspace_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "__init__.py").write_text("")

        # Create pytest.ini
        pytest_ini = """[pytest]
python_files = test_*.py
python_functions = test_*
testpaths = tests
"""
        (self.workspace_dir / "pytest.ini").write_text(pytest_ini)

        # Create pyproject.toml for dependencies
        pyproject_toml = '''[project]
name = "test-generation"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = []
'''
        (self.workspace_dir / "pyproject.toml").write_text(pyproject_toml)

        # Create README
        readme = """# Test Generation Task

Generate comprehensive tests for the utils.py module.

## Module Functions
- add_numbers(a, b) - Add two numbers
- multiply_numbers(a, b) - Multiply two numbers
- divide_numbers(a, b) - Divide (raises ValueError on division by zero)
- reverse_string(text) - Reverse a string
- count_vowels(text) - Count vowels
- is_palindrome(text) - Check if palindrome
- factorial(n) - Calculate factorial (raises ValueError for negative)
- find_max(numbers) - Find max (raises ValueError for empty list)

## Testing Requirements
- Test all functions
- Include edge cases
- Test error handling
- Achieve >80% coverage
"""
        (self.workspace_dir / "README.md").write_text(readme)

    def get_initial_prompt(self) -> str:
        """Get the initial prompt."""
        return self.task_config.initial_prompt

    def evaluate(self) -> TaskEvaluation:
        """
        Evaluate the solution.

        Checks:
        1. Test file exists
        2. Tests pass
        3. Code coverage is >80%
        4. Tests cover edge cases
        5. Tests check error handling
        """
        errors = []
        warnings = []
        details = {}

        test_file = self.workspace_dir / "tests" / "test_utils.py"

        # Check 1: Test file exists
        if not test_file.exists():
            errors.append("tests/test_utils.py not found")
            return TaskEvaluation(
                success=False,
                test_pass_rate=0.0,
                correctness_score=0.0,
                code_quality_score=0.0,
                errors=errors,
                warnings=warnings,
                details=details
            )

        # Check 2: Read test file and analyze
        try:
            test_content = test_file.read_text()

            # Check for test functions
            test_functions = re.findall(r'def (test_\w+)\(', test_content)
            num_tests = len(test_functions)
            details["num_tests"] = num_tests

            if num_tests < 8:
                warnings.append(f"Only {num_tests} test functions found, expected at least 8 (one per function)")

            # Check for edge case testing
            has_edge_cases = any(keyword in test_content.lower() for keyword in
                                ["empty", "zero", "negative", "none"])
            details["has_edge_cases"] = has_edge_cases

            if not has_edge_cases:
                warnings.append("No obvious edge case testing found")

            # Check for error testing (pytest.raises)
            has_error_tests = "pytest.raises" in test_content or "with raises" in test_content
            details["has_error_tests"] = has_error_tests

            if not has_error_tests:
                warnings.append("No error handling tests found (should test ValueError cases)")

        except Exception as e:
            errors.append(f"Error reading test file: {str(e)}")

        # Check 3: Install dependencies
        try:
            subprocess.run(
                ["uv", "pip", "install", "pytest", "pytest-cov"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
        except Exception as e:
            errors.append(f"Failed to install dependencies: {str(e)}")

        # Check 4: Run tests
        test_passed = False
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

            if not test_passed:
                errors.append("Tests failed")

        except subprocess.TimeoutExpired:
            errors.append("Tests timed out")
        except Exception as e:
            errors.append(f"Error running tests: {str(e)}")

        # Check 5: Run coverage analysis
        coverage_percent = 0.0
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--cov=utils", "--cov-report=term-missing"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Parse coverage output
            output = result.stdout + result.stderr
            details["coverage_output"] = output

            # Look for coverage percentage in output
            # Format: "utils.py      50      10      80%"
            coverage_match = re.search(r'utils\.py\s+\d+\s+\d+\s+(\d+)%', output)
            if coverage_match:
                coverage_percent = float(coverage_match.group(1))
            else:
                # Try alternate format: "TOTAL      100      20      80%"
                coverage_match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', output)
                if coverage_match:
                    coverage_percent = float(coverage_match.group(1))

            details["coverage_percent"] = coverage_percent

            if coverage_percent < 80:
                errors.append(f"Coverage is {coverage_percent}%, need >80%")

        except subprocess.TimeoutExpired:
            errors.append("Coverage analysis timed out")
        except Exception as e:
            warnings.append(f"Error running coverage: {str(e)}")

        # Calculate scores
        test_pass_rate = 1.0 if test_passed else 0.0

        # Correctness: based on coverage and tests passing
        if test_passed and coverage_percent >= 80:
            correctness_score = 1.0
        elif test_passed and coverage_percent >= 60:
            correctness_score = 0.7
        elif test_passed:
            correctness_score = 0.5
        else:
            correctness_score = 0.0

        # Code quality: test file structure
        code_quality_score = 1.0
        if num_tests < 8:
            code_quality_score -= 0.2
        if not has_edge_cases:
            code_quality_score -= 0.2
        if not has_error_tests:
            code_quality_score -= 0.2
        code_quality_score = max(0.0, code_quality_score)

        success = test_passed and coverage_percent >= 80

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
        return ["read_file", "write_file", "run_shell_command", "search_file_content", "uv"]
