"""
Benchmark runner for executing and evaluating tasks.

This module provides the main BenchmarkRunner class that executes benchmark tasks
with different frameworks and collects metrics.
"""
import time
import tempfile
import shutil
from pathlib import Path
from typing import Literal

from smolagents import CodeAgent, ApiModel

from prompttodraft.benchmark_tasks.base_task import BenchmarkTask
from prompttodraft.benchmark_tasks.metrics import BenchmarkResult
from prompttodraft.tools.factory import ToolFactory


class AgentExecutionError(Exception):
    """Raised when agent execution fails."""
    pass


class BenchmarkRunner:
    """
    Runs benchmark tasks with different frameworks and collects metrics.
    """

    def __init__(self, model_id: str = "Qwen/Qwen2.5-72B-Instruct"):
        """
        Initialize the benchmark runner.

        Args:
            model_id: The model to use for benchmarks
        """
        self.model_id = model_id

    def run_task(
        self,
        task: BenchmarkTask,
        framework: Literal["smolagents"] = "smolagents",
        environment: Literal["local"] = "local",
        verbose: bool = True
    ) -> BenchmarkResult:
        """
        Run a single benchmark task.

        Args:
            task: The benchmark task to run
            framework: Framework to use ("smolagents" for now)
            environment: Execution environment ("local" for now)
            verbose: Whether to print progress

        Returns:
            BenchmarkResult with collected metrics
        """
        if verbose:
            print(f"\n{'='*60}")
            print(f"Running task: {task.task_config.task_name}")
            print(f"Framework: {framework}, Environment: {environment}")
            print(f"{'='*60}\n")

        # Create result object
        result = BenchmarkResult(
            task_name=task.task_config.task_name,
            framework=framework,
            environment=environment,
            model=self.model_id
        )

        # Set up workspace
        try:
            if verbose:
                print("Setting up workspace...")
            task.setup()

            # Get initial prompt
            initial_prompt = task.get_initial_prompt()

            # Run agent
            if verbose:
                print("Running agent...")

            start_time = time.time()
            agent_metrics = self._run_agent(
                framework=framework,
                environment=environment,
                initial_prompt=initial_prompt,
                workspace_dir=task.workspace_dir,
                max_iterations=task.task_config.max_iterations,
                timeout=task.task_config.timeout,
                verbose=verbose
            )
            execution_time = time.time() - start_time

            # Update result with agent metrics
            result.execution_time = execution_time
            result.tool_calls_total = agent_metrics["tool_calls_total"]
            result.tool_calls_by_type = agent_metrics["tool_calls_by_type"]

            # Evaluate solution
            if verbose:
                print("\nEvaluating solution...")
            evaluation = task.evaluate()

            # Update result with evaluation
            result.success = evaluation.success
            result.test_pass_rate = evaluation.test_pass_rate
            result.correctness_score = evaluation.correctness_score
            result.code_quality_score = evaluation.code_quality_score
            result.errors = evaluation.errors
            result.warnings = evaluation.warnings
            result.metadata = evaluation.details

            if verbose:
                print(f"\nTask completed:")
                print(f"  Success: {result.success}")
                print(f"  Test pass rate: {result.test_pass_rate:.1%}")
                print(f"  Correctness: {result.correctness_score:.1%}")
                print(f"  Code quality: {result.code_quality_score:.1%}")
                print(f"  Tool calls: {result.tool_calls_total}")
                print(f"  Time: {result.execution_time:.1f}s")

                if result.errors:
                    print(f"\n  Errors: {len(result.errors)}")
                    for error in result.errors[:3]:  # Show first 3
                        print(f"    - {error}")

        except Exception as e:
            result.success = False
            result.errors.append(f"Execution error: {str(e)}")
            if verbose:
                print(f"\nTask failed with error: {str(e)}")

        finally:
            # Cleanup
            try:
                task.cleanup()
            except Exception as e:
                result.warnings.append(f"Cleanup error: {str(e)}")

        return result

    def _run_agent(
        self,
        framework: str,
        environment: str,
        initial_prompt: str,
        workspace_dir: Path,
        max_iterations: int,
        timeout: int,
        verbose: bool
    ) -> dict:
        """
        Run the agent with the given framework and environment.

        Args:
            framework: Framework to use
            environment: Execution environment
            initial_prompt: Initial prompt for the agent
            workspace_dir: Working directory for the agent
            max_iterations: Maximum number of iterations
            timeout: Timeout in seconds
            verbose: Whether to print progress

        Returns:
            Dict with metrics (tool_calls_total, tool_calls_by_type)
        """
        if framework == "smolagents":
            return self._run_smolagents(
                environment=environment,
                initial_prompt=initial_prompt,
                workspace_dir=workspace_dir,
                max_iterations=max_iterations,
                timeout=timeout,
                verbose=verbose
            )
        else:
            raise ValueError(f"Unsupported framework: {framework}")

    def _run_smolagents(
        self,
        environment: str,
        initial_prompt: str,
        workspace_dir: Path,
        max_iterations: int,
        timeout: int,
        verbose: bool
    ) -> dict:
        """
        Run the agent using smolagents framework.

        Args:
            environment: Execution environment
            initial_prompt: Initial prompt
            workspace_dir: Working directory
            max_iterations: Max iterations
            timeout: Timeout in seconds
            verbose: Print progress

        Returns:
            Dict with metrics
        """
        # Create backend and tools
        backend = ToolFactory.create_backend(environment=environment)
        tools = ToolFactory.create_smolagents_tools(backend=backend)

        # Create model
        model = ApiModel(model_id=self.model_id)

        # Create agent
        agent = CodeAgent(
            tools=tools,
            model=model,
            max_steps=max_iterations,
            verbosity_level=2 if verbose else 0
        )

        # Track tool calls
        tool_calls_by_type: dict[str, int] = {}
        tool_calls_total = 0

        # Monkey-patch tool execution to track calls
        original_forward = None

        def track_tool_call(tool_name: str):
            nonlocal tool_calls_total, tool_calls_by_type
            tool_calls_total += 1
            tool_calls_by_type[tool_name] = tool_calls_by_type.get(tool_name, 0) + 1

        # Wrap each tool's forward method
        for tool in tools:
            original = tool.forward
            def wrapped_forward(*args, _original=original, _tool_name=tool.name, **kwargs):
                track_tool_call(_tool_name)
                return _original(*args, **kwargs)
            tool.forward = wrapped_forward

        # Run agent
        try:
            # Change to workspace directory
            import os
            original_cwd = os.getcwd()
            os.chdir(workspace_dir)

            try:
                result = agent.run(initial_prompt)
                if verbose:
                    print(f"\nAgent result: {result}")
            finally:
                os.chdir(original_cwd)

        except Exception as e:
            raise AgentExecutionError(f"Agent execution failed: {str(e)}")

        return {
            "tool_calls_total": tool_calls_total,
            "tool_calls_by_type": tool_calls_by_type
        }

    def run_suite(
        self,
        tasks: list[BenchmarkTask],
        framework: Literal["smolagents"] = "smolagents",
        environment: Literal["local"] = "local",
        verbose: bool = True
    ) -> list[BenchmarkResult]:
        """
        Run a suite of benchmark tasks.

        Args:
            tasks: List of tasks to run
            framework: Framework to use
            environment: Execution environment
            verbose: Print progress

        Returns:
            List of BenchmarkResult objects
        """
        results = []

        for i, task in enumerate(tasks):
            if verbose:
                print(f"\n\n{'#'*60}")
                print(f"# Task {i+1}/{len(tasks)}")
                print(f"{'#'*60}")

            result = self.run_task(
                task=task,
                framework=framework,
                environment=environment,
                verbose=verbose
            )
            results.append(result)

        return results
