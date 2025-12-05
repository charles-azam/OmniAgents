"""
Task: Generate Comprehensive Tests

Scenario: Generate pytest tests for a module with utility functions
Difficulty: Easy-Medium
Exercises: read_file, write_file, run_shell_command, search_file_content
"""
from pathlib import Path
import subprocess
import re

from anyagent.benchmark.base_task import BenchmarkTask, TaskSetup, TaskEvaluation
from anyagent.benchmark.fixture_utils import copy_fixture_dir


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
        # Copy all files from the test_generation fixture
        copy_fixture_dir("test_generation", self.workspace_dir)

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
