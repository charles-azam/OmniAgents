"""Tests for benchmark tasks."""
import tempfile
from pathlib import Path
import pytest

from anyagents.benchmark.tasks import (
    SearchReplaceTask,
    FastAPIServerTask,
    TestGenerationTask,
    CLIToolTask,
    DataProcessingTask,
    BugFixTask,
)


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestTaskSetup:
    """Test that all tasks can be set up correctly."""

    def test_search_replace_task_setup(self, temp_workspace):
        """Test SearchReplaceTask setup."""
        task = SearchReplaceTask(workspace_dir=temp_workspace)
        task.setup()

        # Verify files were created
        assert (temp_workspace / "src" / "main.py").exists()
        assert (temp_workspace / "src" / "utils.py").exists()
        assert (temp_workspace / "tests" / "test_main.py").exists()
        assert (temp_workspace / "pytest.ini").exists()

        # Verify task config
        config = task.get_task_config()
        assert config.task_name == "search_replace"
        assert config.difficulty == "easy"
        assert "calculate_total" in config.initial_prompt

    def test_fastapi_server_task_setup(self, temp_workspace):
        """Test FastAPIServerTask setup."""
        task = FastAPIServerTask(workspace_dir=temp_workspace)
        task.setup()

        # Verify structure was created
        assert (temp_workspace / "app").exists()
        assert (temp_workspace / "tests").exists()
        assert (temp_workspace / "pyproject.toml").exists()
        assert (temp_workspace / "pytest.ini").exists()

        # Verify task config
        config = task.get_task_config()
        assert config.task_name == "fastapi_server"
        assert config.difficulty == "easy"
        assert "FastAPI" in config.initial_prompt

        # Verify expected tools
        expected_tools = task.get_expected_tools()
        assert "write_file" in expected_tools
        assert "uv" in expected_tools

    def test_test_generation_task_setup(self, temp_workspace):
        """Test TestGenerationTask setup."""
        task = TestGenerationTask(workspace_dir=temp_workspace)
        task.setup()

        # Verify files were created
        assert (temp_workspace / "utils.py").exists()
        assert (temp_workspace / "tests").exists()
        assert (temp_workspace / "pytest.ini").exists()

        # Verify utils.py has functions to test
        utils_content = (temp_workspace / "utils.py").read_text()
        assert "def add_numbers" in utils_content
        assert "def factorial" in utils_content

        # Verify task config
        config = task.get_task_config()
        assert config.task_name == "test_generation"
        assert config.difficulty == "easy-medium"

    def test_cli_tool_task_setup(self, temp_workspace):
        """Test CLIToolTask setup."""
        task = CLIToolTask(workspace_dir=temp_workspace)
        task.setup()

        # Verify sample files were created
        assert (temp_workspace / "sample1.txt").exists()
        assert (temp_workspace / "sample2.txt").exists()
        assert (temp_workspace / "tests").exists()

        # Verify task config
        config = task.get_task_config()
        assert config.task_name == "cli_tool"
        assert config.difficulty == "medium"
        assert "argparse" in config.initial_prompt

    def test_data_processing_task_setup(self, temp_workspace):
        """Test DataProcessingTask setup."""
        task = DataProcessingTask(workspace_dir=temp_workspace)
        task.setup()

        # Verify files were created
        assert (temp_workspace / "sales_data.csv").exists()
        assert (temp_workspace / "tests").exists()

        # Verify CSV has data
        csv_content = (temp_workspace / "sales_data.csv").read_text()
        assert "date,product,quantity,price" in csv_content
        assert "Laptop" in csv_content

        # Verify task config
        config = task.get_task_config()
        assert config.task_name == "data_processing"
        assert config.difficulty == "easy"

    def test_bug_fix_task_setup(self, temp_workspace):
        """Test BugFixTask setup."""
        task = BugFixTask(workspace_dir=temp_workspace)
        task.setup()

        # Verify files were created
        assert (temp_workspace / "calculator.py").exists()
        assert (temp_workspace / "tests" / "test_calculator.py").exists()

        # Verify bugs are present in code
        calculator_content = (temp_workspace / "calculator.py").read_text()
        assert "range(exponent - 1)" in calculator_content  # Bug 1
        assert "n % 2 == 1" in calculator_content  # Bug 2

        # Verify task config
        config = task.get_task_config()
        assert config.task_name == "bug_fix"
        assert config.difficulty == "medium"


class TestTaskConfiguration:
    """Test task configuration and metadata."""

    def test_all_tasks_have_valid_config(self, temp_workspace):
        """Test that all tasks have valid configuration."""
        tasks = [
            SearchReplaceTask(temp_workspace),
            FastAPIServerTask(temp_workspace),
            TestGenerationTask(temp_workspace),
            CLIToolTask(temp_workspace),
            DataProcessingTask(temp_workspace),
            BugFixTask(temp_workspace),
        ]

        for task in tasks:
            config = task.get_task_config()

            # Check required fields
            assert config.task_name
            assert config.description
            assert config.difficulty in ["easy", "easy-medium", "medium", "hard"]
            assert config.initial_prompt
            assert config.max_iterations > 0
            assert config.timeout > 0

            # Check initial prompt method
            prompt = task.get_initial_prompt()
            assert prompt == config.initial_prompt

    def test_all_tasks_have_expected_tools(self, temp_workspace):
        """Test that all tasks define expected tools."""
        tasks = [
            SearchReplaceTask(temp_workspace),
            FastAPIServerTask(temp_workspace),
            TestGenerationTask(temp_workspace),
            CLIToolTask(temp_workspace),
            DataProcessingTask(temp_workspace),
            BugFixTask(temp_workspace),
        ]

        for task in tasks:
            expected_tools = task.get_expected_tools()
            assert isinstance(expected_tools, list)
            assert len(expected_tools) > 0
            for tool in expected_tools:
                assert isinstance(tool, str)


class TestTaskEvaluation:
    """Test task evaluation without running agents."""

    def test_fastapi_task_evaluation_fails_without_solution(self, temp_workspace):
        """Test that FastAPIServerTask evaluation fails when no solution exists."""
        task = FastAPIServerTask(workspace_dir=temp_workspace)
        task.setup()

        evaluation = task.evaluate()

        # Should fail because no solution was created
        assert evaluation.success is False
        assert evaluation.correctness_score < 1.0
        assert len(evaluation.errors) > 0

    def test_bug_fix_task_evaluation_fails_with_bugs(self, temp_workspace):
        """Test that BugFixTask evaluation fails when bugs are not fixed."""
        task = BugFixTask(workspace_dir=temp_workspace)
        task.setup()

        evaluation = task.evaluate()

        # Should fail because bugs are still present
        assert evaluation.success is False
        assert evaluation.correctness_score < 1.0
        # Should detect unfixed bugs
        assert any("Bug" in str(error) or "bug" in str(error) for error in evaluation.errors)

    def test_data_processing_task_evaluation_fails_without_output(self, temp_workspace):
        """Test that DataProcessingTask evaluation fails without script file."""
        task = DataProcessingTask(workspace_dir=temp_workspace)
        task.setup()

        evaluation = task.evaluate()

        # Should fail because no solution script was created
        assert evaluation.success is False
        assert "process_sales.py" in str(evaluation.errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
