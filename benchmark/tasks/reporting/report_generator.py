"""
Report generation for benchmark results.

This module provides functions to generate HTML and Markdown reports from benchmark results.
"""
from datetime import datetime
from prompttodraft.benchmark.tasks.metrics import BenchmarkResult, AggregateResults


def generate_markdown_report(aggregate: AggregateResults) -> str:
    """
    Generate a Markdown report from aggregate results.

    Args:
        aggregate: AggregateResults object

    Returns:
        Markdown-formatted report string
    """
    report = []
    report.append(f"# Benchmark Report")
    report.append(f"\nGenerated: {aggregate.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Summary
    report.append("## Summary\n")
    report.append(f"- **Framework**: {aggregate.framework}")
    report.append(f"- **Environment**: {aggregate.environment}")
    report.append(f"- **Model**: {aggregate.model}")
    report.append(f"- **Tasks Completed**: {aggregate.num_tasks}")
    report.append(f"- **Success Rate**: {aggregate.task_success_rate:.1%}\n")

    # Performance Metrics
    report.append("## Performance Metrics\n")
    report.append(f"| Metric | Value |")
    report.append(f"|--------|-------|")
    report.append(f"| Avg Execution Time | {aggregate.avg_execution_time:.2f}s |")
    report.append(f"| Avg Tool Calls | {aggregate.avg_tool_calls:.1f} |")
    report.append(f"| Total Tool Calls | {aggregate.total_tool_calls} |")

    if aggregate.task_success_rate > 0:
        report.append(f"| Time per Successful Task | {aggregate.time_per_successful_task:.2f}s |")

    report.append("")

    # Quality Metrics
    report.append("## Quality Metrics\n")
    report.append(f"| Metric | Score |")
    report.append(f"|--------|-------|")
    report.append(f"| Avg Test Pass Rate | {aggregate.avg_test_pass_rate:.1%} |")
    report.append(f"| Avg Correctness | {aggregate.avg_correctness:.1%} |")
    report.append(f"| Avg Code Quality | {aggregate.avg_code_quality:.1%} |")
    report.append("")

    # Tool Usage
    report.append("## Tool Usage\n")
    report.append(f"| Tool | Count | % of Total |")
    report.append(f"|------|-------|------------|")
    for tool, count in aggregate.most_used_tools:
        pct = (count / aggregate.total_tool_calls * 100) if aggregate.total_tool_calls > 0 else 0
        report.append(f"| {tool} | {count} | {pct:.1f}% |")
    report.append("")

    # Individual Task Results
    report.append("## Individual Task Results\n")
    for i, task_result in enumerate(aggregate.task_results, 1):
        status = "✓" if task_result.success else "✗"
        report.append(f"### {i}. {task_result.task_name} {status}\n")
        report.append(f"- **Execution Time**: {task_result.execution_time:.2f}s")
        report.append(f"- **Tool Calls**: {task_result.tool_calls_total}")
        report.append(f"- **Test Pass Rate**: {task_result.test_pass_rate:.1%}")
        report.append(f"- **Correctness**: {task_result.correctness_score:.1%}")
        report.append(f"- **Code Quality**: {task_result.code_quality_score:.1%}")

        if task_result.errors:
            report.append(f"\n**Errors**: {len(task_result.errors)}")
            for error in task_result.errors[:3]:
                report.append(f"- {error}")

        report.append("")

    return "\n".join(report)


def generate_html_report(aggregate: AggregateResults) -> str:
    """
    Generate an HTML report from aggregate results.

    Args:
        aggregate: AggregateResults object

    Returns:
        HTML-formatted report string
    """
    html = []
    html.append("<!DOCTYPE html>")
    html.append("<html>")
    html.append("<head>")
    html.append("<title>Benchmark Report</title>")
    html.append("<style>")
    html.append("""
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
        background: #f5f5f5;
    }
    .header {
        background: white;
        padding: 30px;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    h1 { color: #333; margin: 0; }
    .timestamp { color: #666; margin-top: 10px; }
    .metrics {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        margin-bottom: 20px;
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-title { color: #666; font-size: 14px; margin-bottom: 8px; }
    .metric-value { font-size: 32px; font-weight: bold; color: #333; }
    .metric-unit { font-size: 14px; color: #999; }
    .success { color: #4CAF50; }
    .failure { color: #f44336; }
    table {
        width: 100%;
        background: white;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    th {
        background: #f8f9fa;
        padding: 12px;
        text-align: left;
        font-weight: 600;
        color: #333;
    }
    td {
        padding: 12px;
        border-top: 1px solid #e9ecef;
    }
    .task-card {
        background: white;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .task-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
    }
    .task-title { font-size: 18px; font-weight: bold; color: #333; }
    .task-status { font-size: 24px; }
    .task-metrics {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 10px;
    }
    .task-metric { font-size: 14px; color: #666; }
    .task-metric strong { color: #333; }
    .section { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    h2 { color: #333; margin-top: 0; }
    """)
    html.append("</style>")
    html.append("</head>")
    html.append("<body>")

    # Header
    html.append("<div class='header'>")
    html.append("<h1>Benchmark Report</h1>")
    html.append(f"<div class='timestamp'>Generated: {aggregate.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</div>")
    html.append("</div>")

    # Summary Metrics
    html.append("<div class='metrics'>")
    html.append("<div class='metric-card'>")
    html.append("<div class='metric-title'>Tasks Completed</div>")
    html.append(f"<div class='metric-value'>{aggregate.num_tasks}</div>")
    html.append("</div>")

    success_class = "success" if aggregate.task_success_rate >= 0.8 else "failure"
    html.append("<div class='metric-card'>")
    html.append("<div class='metric-title'>Success Rate</div>")
    html.append(f"<div class='metric-value {success_class}'>{aggregate.task_success_rate:.0%}</div>")
    html.append("</div>")

    html.append("<div class='metric-card'>")
    html.append("<div class='metric-title'>Avg Execution Time</div>")
    html.append(f"<div class='metric-value'>{aggregate.avg_execution_time:.1f}<span class='metric-unit'>s</span></div>")
    html.append("</div>")

    html.append("<div class='metric-card'>")
    html.append("<div class='metric-title'>Avg Tool Calls</div>")
    html.append(f"<div class='metric-value'>{aggregate.avg_tool_calls:.0f}</div>")
    html.append("</div>")
    html.append("</div>")

    # Configuration
    html.append("<div class='section'>")
    html.append("<h2>Configuration</h2>")
    html.append("<table>")
    html.append("<tr><td><strong>Framework</strong></td><td>" + aggregate.framework + "</td></tr>")
    html.append("<tr><td><strong>Environment</strong></td><td>" + aggregate.environment + "</td></tr>")
    html.append("<tr><td><strong>Model</strong></td><td>" + aggregate.model + "</td></tr>")
    html.append("</table>")
    html.append("</div>")

    # Tool Usage
    html.append("<div class='section'>")
    html.append("<h2>Tool Usage</h2>")
    html.append("<table>")
    html.append("<tr><th>Tool</th><th>Count</th><th>% of Total</th></tr>")
    for tool, count in aggregate.most_used_tools:
        pct = (count / aggregate.total_tool_calls * 100) if aggregate.total_tool_calls > 0 else 0
        html.append(f"<tr><td>{tool}</td><td>{count}</td><td>{pct:.1f}%</td></tr>")
    html.append("</table>")
    html.append("</div>")

    # Individual Tasks
    html.append("<div class='section'>")
    html.append("<h2>Individual Task Results</h2>")
    for i, task_result in enumerate(aggregate.task_results, 1):
        status = "✓" if task_result.success else "✗"
        status_class = "success" if task_result.success else "failure"

        html.append("<div class='task-card'>")
        html.append("<div class='task-header'>")
        html.append(f"<div class='task-title'>{i}. {task_result.task_name}</div>")
        html.append(f"<div class='task-status {status_class}'>{status}</div>")
        html.append("</div>")

        html.append("<div class='task-metrics'>")
        html.append(f"<div class='task-metric'><strong>Time:</strong> {task_result.execution_time:.2f}s</div>")
        html.append(f"<div class='task-metric'><strong>Tool Calls:</strong> {task_result.tool_calls_total}</div>")
        html.append(f"<div class='task-metric'><strong>Tests:</strong> {task_result.test_pass_rate:.0%}</div>")
        html.append(f"<div class='task-metric'><strong>Correctness:</strong> {task_result.correctness_score:.0%}</div>")
        html.append(f"<div class='task-metric'><strong>Quality:</strong> {task_result.code_quality_score:.0%}</div>")
        html.append("</div>")

        if task_result.errors:
            html.append("<div style='margin-top: 10px; color: #f44336;'>")
            html.append(f"<strong>Errors ({len(task_result.errors)}):</strong>")
            html.append("<ul style='margin: 5px 0;'>")
            for error in task_result.errors[:3]:
                html.append(f"<li>{error}</li>")
            html.append("</ul>")
            html.append("</div>")

        html.append("</div>")
    html.append("</div>")

    html.append("</body>")
    html.append("</html>")

    return "\n".join(html)


def save_report(aggregate: AggregateResults, output_path: str, format: str = "markdown") -> None:
    """
    Save a report to a file.

    Args:
        aggregate: AggregateResults object
        output_path: Path to save the report
        format: "markdown" or "html"
    """
    if format == "markdown":
        content = generate_markdown_report(aggregate=aggregate)
    elif format == "html":
        content = generate_html_report(aggregate=aggregate)
    else:
        raise ValueError(f"Unsupported format: {format}")

    with open(output_path, "w") as f:
        f.write(content)

    print(f"Report saved to: {output_path}")
