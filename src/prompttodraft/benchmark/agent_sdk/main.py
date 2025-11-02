"""Main orchestrator for running all agent framework benchmarks and comparing results."""

import asyncio
import json
from pathlib import Path
from datetime import datetime

from prompttodraft.benchmark_agent_sdk import smolagents_runner
from prompttodraft.benchmark_agent_sdk import langchain_runner
from prompttodraft.benchmark_agent_sdk import openai_agents_runner
from prompttodraft.benchmark_agent_sdk import pydantic_ai_runner


def print_comparison_summary(all_results: dict[str, list[dict]]) -> None:
    """
    Print a comparison summary of all benchmark results.

    Args:
        all_results: Dictionary mapping framework names to lists of result dictionaries.
    """
    print("\n" + "=" * 80)
    print("BENCHMARK COMPARISON SUMMARY")
    print("=" * 80)

    for framework_name, results in all_results.items():
        if not results:
            continue

        print(f"\n{framework_name}:")
        print("-" * 80)

        for result in results:
            model = result.get("model", "Unknown")
            success = result.get("success", False)
            execution_time = result.get("execution_time", 0)
            tool_calls = result.get("tool_calls_total", 0)
            cart_total = result.get("cart_total", 0)
            budget_efficiency = result.get("budget_efficiency", 0)

            print(f"\n  Model: {model}")
            print(f"  Success: {'✓' if success else '✗'}")
            print(f"  Execution time: {execution_time:.2f}s")
            print(f"  Tool calls: {tool_calls}")
            print(f"  Cart total: ${cart_total:.2f}")
            print(f"  Budget efficiency: {budget_efficiency:.1%}")

    print("\n" + "=" * 80)


def generate_comparison_report(all_results: dict[str, list[dict]], output_dir: Path) -> None:
    """
    Generate a detailed comparison report and save to JSON.

    Args:
        all_results: Dictionary mapping framework names to lists of result dictionaries.
        output_dir: Directory to save the report.
    """
    output_dir.mkdir(exist_ok=True)

    # Create comparison data structure
    comparison = {
        "generated_at": datetime.now().isoformat(),
        "frameworks": {},
        "summary": {
            "total_frameworks": len(all_results),
            "total_benchmarks": sum(len(results) for results in all_results.values()),
        }
    }

    # Add framework-specific data
    for framework_name, results in all_results.items():
        if not results:
            continue

        framework_summary = {
            "num_benchmarks": len(results),
            "avg_execution_time": sum(r.get("execution_time", 0) for r in results) / len(results),
            "avg_tool_calls": sum(r.get("tool_calls_total", 0) for r in results) / len(results),
            "success_rate": sum(1 for r in results if r.get("success", False)) / len(results),
            "results": results
        }

        comparison["frameworks"][framework_name] = framework_summary

    # Save to file
    output_file = output_dir / f"benchmark_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(comparison, f, indent=2)

    print(f"\nComparison report saved to: {output_file}")


async def main() -> None:
    """
    Run all agent framework benchmarks and generate comparison report.
    """
    print("=" * 80)
    print("AGENT FRAMEWORK BENCHMARK SUITE")
    print("=" * 80)
    print("\nRunning benchmarks for all frameworks...")

    all_results = {}

    # Run Smolagents benchmarks
    print("\n" + "=" * 80)
    print("1. SMOLAGENTS BENCHMARKS")
    print("=" * 80)
    smolagents_results = smolagents_runner.main()
    all_results["Smolagents"] = smolagents_results

    # Run LangChain benchmarks
    print("\n" + "=" * 80)
    print("2. LANGCHAIN BENCHMARKS")
    print("=" * 80)
    langchain_results = langchain_runner.main()
    all_results["LangChain"] = langchain_results

    # Run OpenAI Agents SDK benchmarks (async)
    print("\n" + "=" * 80)
    print("3. OPENAI AGENTS SDK BENCHMARKS")
    print("=" * 80)
    openai_agents_results = await openai_agents_runner.main()
    all_results["OpenAI Agents SDK"] = openai_agents_results

    # Run Pydantic AI benchmarks
    print("\n" + "=" * 80)
    print("4. PYDANTIC AI BENCHMARKS")
    print("=" * 80)
    pydantic_ai_results = pydantic_ai_runner.main()
    all_results["Pydantic AI"] = pydantic_ai_results

    # Print comparison summary
    print_comparison_summary(all_results=all_results)

    # Generate and save comparison report
    output_dir = Path.cwd() / "benchmark_results"
    generate_comparison_report(all_results=all_results, output_dir=output_dir)

    print("\n" + "=" * 80)
    print("ALL BENCHMARKS COMPLETED!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
