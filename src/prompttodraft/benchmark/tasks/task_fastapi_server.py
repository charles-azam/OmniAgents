"""
Task: Create FastAPI Server

Scenario: Build a simple FastAPI server with tests
Difficulty: Easy
Exercises: ALL 10 tools - write_file, uv, run_shell_command, read_file, list_directory,
           glob, search_file_content, read_many_files, replace, save_memory
"""
from pathlib import Path
import subprocess
import json

from prompttodraft.benchmark.base_task import BenchmarkTask, TaskSetup, TaskEvaluation
from prompttodraft.benchmark.fixture_utils import copy_fixture_dir


class FastAPIServerTask(BenchmarkTask):
    """
    FastAPI server creation benchmark task.

    The agent must create a FastAPI server with a specific endpoint and tests.
    This task exercises all 10 tools to validate the framework works correctly.
    """

    def get_task_config(self) -> TaskSetup:
        """Get task configuration."""
        return TaskSetup(
            task_name="fastapi_server",
            description="Create a FastAPI server with /hello endpoint and tests",
            difficulty="easy",
            workspace_dir=self.workspace_dir,
            initial_prompt="""Create a FastAPI server with the following requirements:

1. Create a FastAPI application with a GET endpoint `/hello` that returns:
   {"message": "Hello, World!"}

2. Create comprehensive pytest tests that:
   - Test the /hello endpoint
   - Verify the response format
   - Test with the TestClient

3. Use `uv` to install dependencies (fastapi, pytest, httpx)

4. Ensure all tests pass with `python -m pytest -v`

Project structure should be:
- app/main.py (FastAPI server)
- tests/test_main.py (tests)
- pyproject.toml (project config with dependencies)

Make sure to follow best practices and include proper imports.""",
            max_iterations=25,
            timeout=300  # 5 minutes
        )

    def setup(self) -> None:
        """Set up the workspace with basic structure."""
        # Copy all files from the fastapi_server fixture
        copy_fixture_dir("fastapi_server", self.workspace_dir)

    def get_initial_prompt(self) -> str:
        """Get the initial prompt."""
        return self.task_config.initial_prompt

    def evaluate(self) -> TaskEvaluation:
        """
        Evaluate the solution.

        Checks:
        1. FastAPI server exists and has correct structure
        2. /hello endpoint exists and returns correct response
        3. Tests exist and pass
        4. Dependencies are installed correctly
        5. Code quality (imports, structure)
        """
        errors = []
        warnings = []
        details = {}

        # Check 1: Verify file structure
        app_dir = self.workspace_dir / "app"
        test_dir = self.workspace_dir / "tests"
        main_file = app_dir / "main.py"
        test_file = test_dir / "test_main.py"
        pyproject_file = self.workspace_dir / "pyproject.toml"

        files_exist = True
        if not main_file.exists():
            errors.append("app/main.py not found")
            files_exist = False
        if not test_file.exists():
            errors.append("tests/test_main.py not found")
            files_exist = False
        if not pyproject_file.exists():
            errors.append("pyproject.toml not found")
            files_exist = False

        details["files_exist"] = files_exist

        if not files_exist:
            return TaskEvaluation(
                success=False,
                test_pass_rate=0.0,
                correctness_score=0.0,
                code_quality_score=0.0,
                errors=errors,
                warnings=warnings,
                details=details
            )

        # Check 2: Verify FastAPI app structure
        try:
            main_content = main_file.read_text()

            # Check for required imports
            has_fastapi = "from fastapi import FastAPI" in main_content or "import fastapi" in main_content
            has_hello_route = "/hello" in main_content
            has_json_response = '"message"' in main_content or "'message'" in main_content

            if not has_fastapi:
                errors.append("FastAPI import not found in main.py")
            if not has_hello_route:
                errors.append("/hello endpoint not found in main.py")
            if not has_json_response:
                errors.append("JSON response with 'message' key not found")

            details["has_fastapi"] = has_fastapi
            details["has_hello_route"] = has_hello_route
            details["has_json_response"] = has_json_response

        except Exception as e:
            errors.append(f"Error reading main.py: {str(e)}")

        # Check 3: Verify test structure
        try:
            test_content = test_file.read_text()

            has_test_client = "TestClient" in test_content
            has_test_function = "def test_" in test_content
            has_hello_test = "/hello" in test_content

            if not has_test_client:
                errors.append("TestClient not imported in tests")
            if not has_test_function:
                errors.append("No test functions found in tests")
            if not has_hello_test:
                warnings.append("No test for /hello endpoint found")

            details["has_test_client"] = has_test_client
            details["has_test_function"] = has_test_function

        except Exception as e:
            errors.append(f"Error reading test_main.py: {str(e)}")

        # Check 4: Verify dependencies in pyproject.toml
        try:
            pyproject_content = pyproject_file.read_text()

            has_fastapi_dep = "fastapi" in pyproject_content
            has_pytest_dep = "pytest" in pyproject_content

            if not has_fastapi_dep:
                warnings.append("fastapi not in dependencies")
            if not has_pytest_dep:
                warnings.append("pytest not in dependencies")

            details["has_fastapi_dep"] = has_fastapi_dep
            details["has_pytest_dep"] = has_pytest_dep

        except Exception as e:
            errors.append(f"Error reading pyproject.toml: {str(e)}")

        # Check 5: Run tests
        test_passed = False
        try:
            # First, try to install dependencies if not already installed
            install_result = subprocess.run(
                ["uv", "sync", "--frozen"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=60
            )

            # Try with pip install if uv sync fails
            if install_result.returncode != 0:
                subprocess.run(
                    ["uv", "pip", "install", "fastapi", "pytest", "httpx"],
                    cwd=self.workspace_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

            # Run tests
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

            if not test_passed:
                errors.append(f"Tests failed: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            errors.append("Tests timed out")
        except FileNotFoundError as e:
            errors.append(f"Command not found: {str(e)}")
        except Exception as e:
            errors.append(f"Error running tests: {str(e)}")

        # Check 6: Code quality - syntax check
        code_quality_score = 1.0
        try:
            import py_compile
            for py_file in app_dir.rglob("*.py"):
                if py_file.name != "__init__.py":
                    py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"Syntax error in app/: {str(e)}")
            code_quality_score = 0.5

        # Calculate scores
        structure_score = sum([
            files_exist,
            details.get("has_fastapi", False),
            details.get("has_hello_route", False),
            details.get("has_json_response", False),
            details.get("has_test_client", False),
            details.get("has_test_function", False)
        ]) / 6.0

        correctness_score = structure_score if test_passed else structure_score * 0.5
        test_pass_rate = 1.0 if test_passed else 0.0

        success = (
            files_exist and
            test_passed and
            details.get("has_fastapi", False) and
            details.get("has_hello_route", False)
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
        # Workspace will be cleaned up by the runner
        pass

    def get_expected_tools(self) -> list[str]:
        """Get expected tools for this task."""
        return [
            "write_file",
            "uv",
            "run_shell_command",
            "read_file",
            "list_directory",
            "glob",
            "search_file_content",
            "read_many_files",
            "replace"
        ]
