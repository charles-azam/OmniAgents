# Benchmark Suite

Compare AI coding agents across frameworks (smolagents, Pydantic-AI, LangChain) and execution environments (local, Docker, E2B).

## Features

- **Framework Comparison** - Objectively compare different AI frameworks
- **Cost Tracking** - Token usage and estimated API costs
- **Tool Usage Analysis** - Which tools are used and how often
- **Quality Metrics** - Test pass rates, correctness, code quality
- **Efficiency Metrics** - Execution time, tool calls per task

## Quick Start

```python
from pathlib import Path
import tempfile
from prompttodraft.benchmark.tasks.runner import BenchmarkRunner
from prompttodraft.benchmark.tasks.tasks.task_search_replace import SearchReplaceTask
from prompttodraft.benchmark.tasks.reporting.report_generator import save_report
from prompttodraft.benchmark.tasks.metrics import AggregateResults

# Create workspace and task
with tempfile.TemporaryDirectory() as tmpdir:
    workspace = Path(tmpdir) / "workspace"
    workspace.mkdir()

    task = SearchReplaceTask(workspace_dir=workspace)
    runner = BenchmarkRunner(model_id="Qwen/Qwen2.5-72B-Instruct")

    # Run benchmark
    result = runner.run_task(
        task=task,
        framework="smolagents",
        environment="local",
        verbose=True
    )

    # Generate HTML report
    aggregate = AggregateResults.from_results(
        results=[result],
        framework="smolagents",
        environment="local",
        model="Qwen/Qwen2.5-72B-Instruct"
    )

    save_report(aggregate, "report.html", format="html")
```

## Available Tasks

### Implemented

| Task | Difficulty | Tools Used | Expected Time |
|------|-----------|------------|---------------|
| **Search and Replace** | Easy | grep, edit, bash | 1-2 min |

### Planned

| Task | Difficulty | Description |
|------|-----------|-------------|
| **Bug Hunt** | Medium | Find and fix 3 bugs |
| **Feature Implementation** | Hard | Implement new feature from spec |
| **Code Refactoring** | Medium | Refactor to pass linting |
| **Test Generation** | Medium | Generate tests for coverage |
| **Documentation** | Easy | Add docstrings to functions |
| **Dependency Update** | Hard | Update deprecated library |

## Metrics Collected

### Performance
- **Total Tokens** - Input + output tokens
- **Estimated Cost** - Based on model pricing
- **Execution Time** - Wall-clock time for task
- **Tool Calls** - Total and per-tool breakdown

### Quality
- **Success** - Did the agent complete the task?
- **Test Pass Rate** - % of tests passing
- **Correctness Score** - Task-specific correctness (0-1)
- **Code Quality** - Linting, formatting, style (0-1)

## Creating Custom Tasks

Subclass `BenchmarkTask` and implement required methods:

```python
from prompttodraft.benchmark.tasks.base_task import BenchmarkTask, TaskSetup, TaskEvaluation

class MyTask(BenchmarkTask):
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
        # Create files, install dependencies
        (self.workspace_dir / "main.py").write_text("print('hello')")

    def get_initial_prompt(self) -> str:
        return self.task_config.initial_prompt

    def evaluate(self) -> TaskEvaluation:
        # Check solution quality
        success = True
        test_pass_rate = 1.0
        correctness_score = 1.0
        code_quality_score = 1.0

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

## Running Multiple Tasks

```python
from prompttodraft.benchmark.tasks.runner import BenchmarkRunner

tasks = [
    SearchReplaceTask(workspace_dir=workspace1),
    BugHuntTask(workspace_dir=workspace2),
    # ...
]

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

```python
frameworks = ["smolagents", "pydantic-ai", "langchain"]
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

# Compare results
for framework, aggregate in all_results.items():
    print(f"{framework}: {aggregate.task_success_rate:.0%} success, "
          f"${aggregate.avg_cost:.3f} per task, "
          f"{aggregate.avg_execution_time:.1f}s average")
```

## Report Generation

### HTML Reports

```python
from prompttodraft.benchmark.tasks.reporting.report_generator import save_report

save_report(aggregate_results, "report.html", format="html")
```

Generates a report with:
- Summary cards with key metrics
- Tool usage breakdown
- Individual task results
- Color-coded success/failure indicators

### Markdown Reports

```python
from prompttodraft.benchmark.tasks.reporting.report_generator import generate_markdown_report

markdown = generate_markdown_report(aggregate_results)
print(markdown)
```

## Interpreting Results

### Success Metrics
- **> 80%** - Excellent
- **60-80%** - Good
- **< 60%** - Needs improvement

### Efficiency
- **Tool Calls per Task** - Lower is generally better
- **Execution Time** - Consider cost/quality tradeoffs
- **Cost per Successful Task** - Important for production

## Best Practices

1. **Consistent Environments** - Same machine, model, timeout limits
2. **Run Multiple Times** - 3-5 runs to account for variability
3. **Isolate Workspaces** - Always use fresh workspaces
4. **Track Everything** - Save all results to JSON
5. **Validate Benchmarks** - Manually verify task solutions

## See Also

- [agent/README.md](../../agent/README.md) - Tool catalog, framework integration
- [backends/README.md](../../agent/backends/README.md) - Backend options
