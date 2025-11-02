"""
Example script for running benchmarks.

This script demonstrates how to run benchmark tasks and collect results.
"""
import tempfile
import json
from pathlib import Path

from prompttodraft.benchmark.tasks.runner import BenchmarkRunner
from prompttodraft.benchmark.tasks.tasks.task_search_replace import SearchReplaceTask
from prompttodraft.benchmark.tasks.metrics import AggregateResults


def main():
    """Run benchmark example."""
    print("="*60)
    print("Benchmark Runner Example")
    print("="*60)

    # Create temporary workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "workspace"
        workspace.mkdir()

        # Create task
        task = SearchReplaceTask(workspace_dir=workspace)

        # Create runner
        runner = BenchmarkRunner(model_id="Qwen/Qwen2.5-72B-Instruct")

        # Run task
        result = runner.run_task(
            task=task,
            framework="smolagents",
            environment="local",
            verbose=True
        )

        # Print detailed results
        print("\n" + "="*60)
        print("DETAILED RESULTS")
        print("="*60)
        print(f"\nTask: {result.task_name}")
        print(f"Framework: {result.framework}")
        print(f"Environment: {result.environment}")
        print(f"Model: {result.model}")
        print(f"\nMetrics:")
        print(f"  Success: {result.success}")
        print(f"  Execution time: {result.execution_time:.2f}s")
        print(f"  Tool calls: {result.tool_calls_total}")
        print(f"  Test pass rate: {result.test_pass_rate:.1%}")
        print(f"  Correctness: {result.correctness_score:.1%}")
        print(f"  Code quality: {result.code_quality_score:.1%}")

        print(f"\nTool usage:")
        for tool, count in sorted(result.tool_calls_by_type.items(), key=lambda x: x[1], reverse=True):
            print(f"  {tool}: {count}")

        if result.errors:
            print(f"\nErrors:")
            for error in result.errors:
                print(f"  - {error}")

        if result.warnings:
            print(f"\nWarnings:")
            for warning in result.warnings:
                print(f"  - {warning}")

        # Save results to JSON
        output_file = "benchmark_results.json"
        with open(output_file, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\nResults saved to: {output_file}")


def run_multiple_tasks():
    """Run multiple tasks and generate aggregate results."""
    print("="*60)
    print("Running Multiple Tasks")
    print("="*60)

    results = []

    # Run same task multiple times for demonstration
    for i in range(2):
        print(f"\n\nRun {i+1}/2")
        print("-"*60)

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir()

            task = SearchReplaceTask(workspace_dir=workspace)
            runner = BenchmarkRunner(model_id="Qwen/Qwen2.5-72B-Instruct")

            result = runner.run_task(
                task=task,
                framework="smolagents",
                environment="local",
                verbose=False  # Less verbose for multiple runs
            )
            results.append(result)

            print(f"Result: {'✓ Success' if result.success else '✗ Failed'}")
            print(f"Time: {result.execution_time:.1f}s, Tools: {result.tool_calls_total}")

    # Generate aggregate results
    aggregate = AggregateResults.from_results(
        results=results,
        framework="smolagents",
        environment="local",
        model="Qwen/Qwen2.5-72B-Instruct"
    )

    print("\n" + "="*60)
    print("AGGREGATE RESULTS")
    print("="*60)
    print(f"\nTasks completed: {aggregate.num_tasks}")
    print(f"Success rate: {aggregate.task_success_rate:.1%}")
    print(f"\nAverages:")
    print(f"  Execution time: {aggregate.avg_execution_time:.2f}s")
    print(f"  Tool calls: {aggregate.avg_tool_calls:.1f}")
    print(f"  Correctness: {aggregate.avg_correctness:.1%}")
    print(f"  Code quality: {aggregate.avg_code_quality:.1%}")

    print(f"\nMost used tools:")
    for tool, count in aggregate.most_used_tools[:5]:
        print(f"  {tool}: {count}")

    # Save aggregate results
    output_file = "aggregate_results.json"
    with open(output_file, "w") as f:
        json.dump(aggregate.to_dict(), f, indent=2)
    print(f"\nAggregate results saved to: {output_file}")


if __name__ == "__main__":
    # Run single task
    main()

    # Uncomment to run multiple tasks
    # run_multiple_tasks()
