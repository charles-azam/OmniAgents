## Benchmark Suite

A comprehensive benchmark suite for comparing AI coding agents across different frameworks (smolagents, OpenAI, Pydantic-AI, Autogen) and execution environments (local, docker, e2b).

## Overview

This benchmark suite helps you:

- 📊 **Compare frameworks** objectively with measurable metrics
- 💰 **Track costs** (token usage, estimated API costs)
- 🛠️ **Analyze tool usage** patterns across different agents
- ✅ **Measure quality** (test pass rates, correctness, code quality)
- ⚡ **Assess efficiency** (execution time, tool calls)

## Quick Start

```python
from pathlib import Path
import tempfile
from prompttodraft.benchmark_tasks.runner import BenchmarkRunner
from prompttodraft.benchmark_tasks.tasks.task_search_replace import SearchReplaceTask
from prompttodraft.benchmark_tasks.reporting.report_generator import save_report
from prompttodraft.benchmark_tasks.metrics import AggregateResults

# Create workspace
with tempfile.TemporaryDirectory() as tmpdir:
    workspace = Path(tmpdir) / "workspace"
    workspace.mkdir()

    # Create and run task
    task = SearchReplaceTask(workspace_dir=workspace)
    runner = BenchmarkRunner(model_id="Qwen/Qwen2.5-72B-Instruct")

    result = runner.run_task(
        task=task,
        framework="smolagents",
        environment="local",
        verbose=True
    )

    # Generate report
    aggregate = AggregateResults.from_results(
        results=[result],
        framework="smolagents",
        environment="local",
        model="Qwen/Qwen2.5-72B-Instruct"
    )

    save_report(aggregate, "report.html", format="html")
```

## Architecture

```
benchmarks/
├── base_task.py              # Abstract base class for tasks
├── runner.py                 # BenchmarkRunner orchestrates execution
├── metrics.py                # Result dataclasses and metrics
├── tasks/                    # Benchmark task implementations
│   └── task_search_replace.py
└── reporting/                # Report generation
    └── report_generator.py
```

## Benchmark Tasks

### Implemented Tasks

#### Task 6: Multi-File Search and Replace (Easy)
- **Scenario**: Rename a function across multiple files
- **Exercises**: grep, edit, bash (run tests)
- **Success Criteria**: All occurrences renamed, tests pass
- **Expected Time**: ~1-2 minutes
- **Expected Tool Calls**: 8-15

### Planned Tasks

#### Task 1: Bug Hunt and Fix (Medium)
- Find and fix 3 bugs in a Python project
- Exercises: grep, view, edit, bash
- Success: All tests pass

#### Task 2: Feature Implementation (Hard)
- Implement a new feature from spec
- Exercises: All tools comprehensively
- Success: Feature works, tests pass

#### Task 3: Code Refactoring (Medium)
- Refactor code to pass linting rules
- Exercises: bash (linter), grep, edit
- Success: All rules pass, behavior preserved

#### Task 4: Test Generation (Medium)
- Generate tests for untested code
- Exercises: view, replace, bash (coverage)
- Success: 100% coverage, meaningful tests

#### Task 5: Documentation Generation (Easy)
- Add docstrings to all functions
- Exercises: view, edit, bash (build docs)
- Success: Complete docstrings, docs build

#### Task 7: Dependency Update (Hard)
- Update deprecated library to new version
- Exercises: grep, view, edit, bash
- Success: Dependency updated, tests pass

## Metrics Collected

### Performance Metrics
- **Total Tokens**: Input + output tokens
- **Estimated Cost**: Based on model pricing
- **Execution Time**: Wall-clock time for task
- **Tool Calls**: Total and per-tool breakdown

### Quality Metrics
- **Success**: Did the agent complete the task?
- **Test Pass Rate**: % of tests passing
- **Correctness Score**: Task-specific correctness (0-1)
- **Code Quality Score**: Linting, formatting, style (0-1)

### Tool Usage Metrics
- **Tool Calls by Type**: How many times each tool was used
- **Tool Success Rate**: % of successful tool calls
- **Tool Usage Patterns**: Which tools are preferred?

## Creating Custom Tasks

To create a new benchmark task:

1. **Subclass `BenchmarkTask`**:

```python
from prompttodraft.benchmark_tasks.base_task import BenchmarkTask, TaskSetup, TaskEvaluation

class MyCustomTask(BenchmarkTask):
    def get_task_config(self) -> TaskSetup:
        return TaskSetup(
            task_name="my_task",
            description="Task description",
            difficulty="medium",
            workspace_dir=self.workspace_dir,
            initial_prompt="Prompt for the agent...",
            max_iterations=30,
            timeout=300
        )

    def setup(self) -> None:
        # Create files, install dependencies, etc.
        (self.workspace_dir / "main.py").write_text("print('hello')")

    def get_initial_prompt(self) -> str:
        return self.task_config.initial_prompt

    def evaluate(self) -> TaskEvaluation:
        # Check solution quality
        success = True  # Check if task succeeded
        test_pass_rate = 1.0  # Run tests
        correctness_score = 1.0  # Check correctness
        code_quality_score = 1.0  # Check code quality

        return TaskEvaluation(
            success=success,
            test_pass_rate=test_pass_rate,
            correctness_score=correctness_score,
            code_quality_score=code_quality_score,
            errors=[],
            warnings=[],
            details={}
        )

    def cleanup(self) -> None:
        # Clean up resources
        pass
```

2. **Use with BenchmarkRunner**:

```python
task = MyCustomTask(workspace_dir=Path("/tmp/workspace"))
runner = BenchmarkRunner()
result = runner.run_task(task, framework="smolagents", environment="local")
```

## Report Generation

### Markdown Reports

```python
from prompttodraft.benchmark_tasks.reporting.report_generator import generate_markdown_report

markdown = generate_markdown_report(aggregate_results)
print(markdown)
```

Output:
```markdown
# Benchmark Report

## Summary
- **Framework**: smolagents
- **Environment**: local
- **Tasks Completed**: 1
- **Success Rate**: 100.0%

## Performance Metrics
| Metric | Value |
|--------|-------|
| Avg Execution Time | 45.23s |
| Avg Tool Calls | 12.0 |
...
```

### HTML Reports

```python
from prompttodraft.benchmark_tasks.reporting.report_generator import save_report

save_report(aggregate_results, "report.html", format="html")
```

Generates a beautiful HTML report with:
- Summary cards with key metrics
- Tool usage breakdown
- Individual task results
- Color-coded success/failure indicators

## Running Multiple Tasks

```python
from prompttodraft.benchmark_tasks.runner import BenchmarkRunner

# Create tasks
tasks = [
    SearchReplaceTask(workspace_dir=workspace1),
    # Add more tasks...
]

# Run suite
runner = BenchmarkRunner()
results = runner.run_suite(
    tasks=tasks,
    framework="smolagents",
    environment="local",
    verbose=True
)

# Generate aggregate report
aggregate = AggregateResults.from_results(
    results=results,
    framework="smolagents",
    environment="local",
    model="Qwen/Qwen2.5-72B-Instruct"
)
```

## Comparing Frameworks

To compare different frameworks:

```python
frameworks = ["smolagents", "openai", "pydantic-ai"]
all_results = {}

for framework in frameworks:
    results = []
    for task_class in [Task1, Task2, Task3]:
        task = task_class(workspace_dir=create_workspace())
        result = runner.run_task(task, framework=framework)
        results.append(result)

    all_results[framework] = AggregateResults.from_results(
        results=results,
        framework=framework,
        environment="local",
        model="gpt-4"
    )

# Compare
for framework, aggregate in all_results.items():
    print(f"{framework}: {aggregate.task_success_rate:.0%} success, "
          f"${aggregate.avg_cost:.3f} per task, "
          f"{aggregate.avg_execution_time:.1f}s average")
```

## Interpreting Results

### Success Metrics
- **Success Rate > 80%**: Excellent
- **Success Rate 60-80%**: Good
- **Success Rate < 60%**: Needs improvement

### Efficiency Metrics
- **Tool Calls per Task**: Lower is generally better (more efficient)
- **Execution Time**: Consider cost/quality tradeoffs
- **Cost per Successful Task**: Important for production use

### Quality Metrics
- **Test Pass Rate**: Should be close to 100%
- **Correctness Score**: Task-specific, aim for > 0.9
- **Code Quality**: Should be > 0.8 for production code

## Best Practices

### 1. Use Consistent Environments
- Run all comparisons on the same machine
- Use the same model for fair comparisons
- Set consistent timeout/iteration limits

### 2. Run Multiple Times
- Run each task 3-5 times to account for variability
- Report median and standard deviation
- Watch for outliers

### 3. Isolate Workspaces
- Always use fresh workspaces
- Clean up after each run
- Don't reuse directories

### 4. Track Everything
- Save all results to JSON
- Keep logs of execution
- Record environment details (OS, Python version, etc.)

### 5. Validate Benchmarks
- Manually verify task solutions
- Check that evaluation is fair
- Ensure tasks are realistic

## Example Output

```
============================================================
Running task: search_replace
Framework: smolagents, Environment: local
============================================================

Setting up workspace...
Running agent...

Task completed:
  Success: True
  Test pass rate: 100.0%
  Correctness: 100.0%
  Code quality: 100.0%
  Tool calls: 12
  Time: 42.3s

============================================================
DETAILED RESULTS
============================================================

Task: search_replace
Framework: smolagents
Environment: local
Model: Qwen/Qwen2.5-72B-Instruct

Metrics:
  Success: True
  Execution time: 42.31s
  Tool calls: 12
  Test pass rate: 100.0%
  Correctness: 100.0%
  Code quality: 100.0%

Tool usage:
  grep: 3
  edit: 4
  bash: 3
  view: 2

Results saved to: benchmark_results.json
```

## Future Enhancements

### Planned Features
- [ ] More benchmark tasks (7 total planned)
- [ ] Docker backend integration
- [ ] E2B backend integration
- [ ] OpenAI framework adapter
- [ ] Pydantic-AI framework adapter
- [ ] Autogen framework adapter
- [ ] Cost estimation for different models
- [ ] Token usage tracking
- [ ] Comparative visualizations (charts, graphs)
- [ ] CI/CD integration for automated benchmarking
- [ ] Leaderboard generation

### Extensibility
The benchmark suite is designed to be easily extended:

- **New Tasks**: Subclass `BenchmarkTask`
- **New Frameworks**: Implement adapter in `tools/adapters/`
- **New Backends**: Implement `ExecutionBackend` interface
- **New Metrics**: Add fields to `BenchmarkResult`
- **New Reports**: Extend `report_generator.py`

## Contributing

To add a new benchmark task:

1. Create a new file in `benchmarks/tasks/`
2. Subclass `BenchmarkTask`
3. Implement all abstract methods
4. Add tests in `tests/benchmarks/`
5. Update this README

## License

Same as parent project.
