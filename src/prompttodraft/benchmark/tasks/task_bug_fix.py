"""
Task: Fix Bugs in Code

Scenario: Find and fix 3 bugs in a calculator module
Difficulty: Medium
Exercises: read_file, search_file_content, replace, run_shell_command
"""
from pathlib import Path
import subprocess

from prompttodraft.benchmark.base_task import BenchmarkTask, TaskSetup, TaskEvaluation
from prompttodraft.benchmark.fixture_utils import copy_fixture_dir


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
        # Copy all files from the bug_fix fixture
        copy_fixture_dir("bug_fix", self.workspace_dir)

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
