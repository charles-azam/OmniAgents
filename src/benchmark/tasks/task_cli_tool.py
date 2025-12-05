"""
Task: Implement CLI Tool

Scenario: Create a command-line tool with argparse
Difficulty: Medium
Exercises: write_file, run_shell_command, read_file, replace
"""
from pathlib import Path
import subprocess

from prompttodraft.benchmark.base_task import BenchmarkTask, TaskSetup, TaskEvaluation
from prompttodraft.benchmark.fixture_utils import copy_fixture_dir


class CLIToolTask(BenchmarkTask):
    """
    CLI tool implementation benchmark task.

    The agent must create a command-line tool that counts words/lines/characters
    in files, similar to the `wc` command.
    """

    def get_task_config(self) -> TaskSetup:
        """Get task configuration."""
        return TaskSetup(
            task_name="cli_tool",
            description="Implement a CLI tool for counting words, lines, and characters in files",
            difficulty="medium",
            workspace_dir=self.workspace_dir,
            initial_prompt="""Create a command-line tool called `wordcount.py` that counts words, lines, and characters in text files.

Requirements:

1. Use argparse for command-line argument parsing

2. Support the following options:
   - `-l, --lines`: Count lines only
   - `-w, --words`: Count words only
   - `-c, --chars`: Count characters only
   - (no flags): Show all counts (lines, words, chars)

3. Accept one or more file paths as arguments

4. Output format: "<lines> <words> <chars> <filename>"
   - If specific flag is used, only show that count and filename
   - If multiple files, show individual counts and a total line

5. Handle errors gracefully:
   - File not found
   - Permission errors
   - Invalid arguments

6. Include a --help option with clear usage information

7. Create comprehensive tests in tests/test_wordcount.py that:
   - Test all flag combinations
   - Test multiple files
   - Test error cases
   - All tests must pass

Example usage:
```bash
python wordcount.py sample.txt
# Output: 10 50 300 sample.txt

python wordcount.py -w sample.txt
# Output: 50 sample.txt

python wordcount.py file1.txt file2.txt
# Output:
# 10 50 300 file1.txt
# 20 100 600 file2.txt
# 30 150 900 total
```

Run tests with: `python -m pytest -v`""",
            max_iterations=30,
            timeout=300  # 5 minutes
        )

    def setup(self) -> None:
        """Set up the workspace with sample files."""
        # Copy all files from the cli_tool fixture
        copy_fixture_dir("cli_tool", self.workspace_dir)

    def get_initial_prompt(self) -> str:
        """Get the initial prompt."""
        return self.task_config.initial_prompt

    def evaluate(self) -> TaskEvaluation:
        """
        Evaluate the solution.

        Checks:
        1. wordcount.py exists
        2. Uses argparse
        3. All flags work correctly
        4. Multiple files supported
        5. Error handling works
        6. Tests exist and pass
        7. Help text exists
        """
        errors: list[str] = []
        warnings: list[str] = []
        details: dict[str, str | int | float | bool] = {}

        wordcount_file = self.workspace_dir / "wordcount.py"
        test_file = self.workspace_dir / "tests" / "test_wordcount.py"

        # Check 1: Files exist
        if not wordcount_file.exists():
            errors.append("wordcount.py not found")
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
            warnings.append("tests/test_wordcount.py not found")

        # Check 2: Analyze code structure
        try:
            code_content = wordcount_file.read_text()

            has_argparse = "argparse" in code_content
            has_main = "if __name__ ==" in code_content
            has_error_handling = "try:" in code_content or "except" in code_content

            details["has_argparse"] = has_argparse
            details["has_main"] = has_main
            details["has_error_handling"] = has_error_handling

            if not has_argparse:
                errors.append("argparse not used in wordcount.py")
            if not has_main:
                warnings.append("No if __name__ == '__main__' guard found")
            if not has_error_handling:
                warnings.append("No error handling found")

        except Exception as e:
            errors.append(f"Error reading wordcount.py: {str(e)}")

        # Check 3: Test help output
        try:
            result = subprocess.run(
                ["python", "wordcount.py", "--help"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=5
            )

            has_help = result.returncode == 0 and len(result.stdout) > 0
            details["has_help"] = has_help
            details["help_output"] = result.stdout

            if not has_help:
                errors.append("--help option doesn't work")

        except Exception as e:
            errors.append(f"Error testing --help: {str(e)}")

        # Check 4: Test basic functionality (no flags)
        try:
            result = subprocess.run(
                ["python", "wordcount.py", "sample1.txt"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=5
            )

            details["basic_test_output"] = result.stdout
            details["basic_test_returncode"] = result.returncode

            # Check if output contains numbers
            import re
            numbers_found = re.findall(r'\d+', result.stdout)

            if result.returncode == 0 and len(numbers_found) >= 3:
                details["basic_test_passed"] = True
            else:
                details["basic_test_passed"] = False
                errors.append(f"Basic test failed: {result.stderr}")

        except Exception as e:
            errors.append(f"Error running basic test: {str(e)}")
            details["basic_test_passed"] = False

        # Check 5: Test -w flag
        try:
            result = subprocess.run(
                ["python", "wordcount.py", "-w", "sample1.txt"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=5
            )

            details["word_flag_output"] = result.stdout
            details["word_flag_passed"] = result.returncode == 0

            if result.returncode != 0:
                warnings.append("-w flag doesn't work correctly")

        except Exception as e:
            warnings.append(f"Error testing -w flag: {str(e)}")

        # Check 6: Test -l flag
        try:
            result = subprocess.run(
                ["python", "wordcount.py", "-l", "sample1.txt"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=5
            )

            details["line_flag_passed"] = result.returncode == 0

            if result.returncode != 0:
                warnings.append("-l flag doesn't work correctly")

        except Exception as e:
            warnings.append(f"Error testing -l flag: {str(e)}")

        # Check 7: Test multiple files
        try:
            result = subprocess.run(
                ["python", "wordcount.py", "sample1.txt", "sample2.txt"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=5
            )

            details["multiple_files_output"] = result.stdout
            details["multiple_files_passed"] = result.returncode == 0

            if result.returncode != 0:
                warnings.append("Multiple file handling doesn't work")

        except Exception as e:
            warnings.append(f"Error testing multiple files: {str(e)}")

        # Check 8: Test error handling (nonexistent file)
        try:
            result = subprocess.run(
                ["python", "wordcount.py", "nonexistent.txt"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=5
            )

            # Should either exit with error code or print error message
            handles_error = result.returncode != 0 or "error" in result.stderr.lower() or "not found" in result.stderr.lower()
            details["error_handling_passed"] = handles_error

            if not handles_error:
                warnings.append("Error handling may not work correctly")

        except Exception as e:
            warnings.append(f"Error testing error handling: {str(e)}")

        # Check 9: Run tests if they exist
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
        else:
            warnings.append("No tests provided")

        # Calculate scores
        functionality_score = sum([
            bool(details.get("basic_test_passed", False)),
            bool(details.get("word_flag_passed", False)),
            bool(details.get("line_flag_passed", False)),
            bool(details.get("multiple_files_passed", False)),
            bool(details.get("error_handling_passed", False))
        ]) / 5.0

        correctness_score = functionality_score
        test_pass_rate = 1.0 if test_passed else 0.0

        code_quality_score = 1.0
        if not has_argparse:
            code_quality_score -= 0.3
        if not has_error_handling:
            code_quality_score -= 0.2
        if not has_main:
            code_quality_score -= 0.1
        code_quality_score = max(0.0, code_quality_score)

        success = (
            bool(details.get("basic_test_passed", False)) and
            bool(details.get("word_flag_passed", False)) and
            bool(details.get("has_argparse", False)) and
            functionality_score >= 0.8
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
        pass

    def get_expected_tools(self) -> list[str]:
        """Get expected tools for this task."""
        return ["write_file", "run_shell_command", "read_file", "replace"]
