#!/usr/bin/env python3
"""
Task Redundancy Analysis CLI Tool.

Standalone command-line tool for analyzing task redundancy in
Marcus projects. Detects redundant work, duplicate tasks, and
over-decomposition.

Usage:
    python -m src.cli.analyze_task_redundancy --project-id <id>
    python -m src.cli.analyze_task_redundancy --project-id <id> \
        --output-format json
    python -m src.cli.analyze_task_redundancy --project-id <id> \
        --output-file results.json
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.analysis.aggregator import ProjectHistoryAggregator  # noqa: E402
from src.analysis.analyzers.task_redundancy import (  # noqa: E402
    TaskRedundancyAnalysis,
    TaskRedundancyAnalyzer,
)


def format_text_output(analysis: TaskRedundancyAnalysis) -> str:
    """
    Format analysis results as human-readable text.

    Parameters
    ----------
    analysis : TaskRedundancyAnalysis
        Analysis results to format

    Returns
    -------
    str
        Formatted text output
    """
    lines = []
    lines.append("=" * 80)
    lines.append("TASK REDUNDANCY ANALYSIS RESULTS")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Project ID: {analysis.project_id}")
    lines.append(f"Redundancy Score: {analysis.redundancy_score:.2%}")
    lines.append(f"Total Time Wasted: {analysis.total_time_wasted:.1f} hours")
    lines.append(
        f"Over-Decomposition Detected: "
        f"{'Yes' if analysis.over_decomposition_detected else 'No'}"
    )
    lines.append(f"Recommended Complexity: {analysis.recommended_complexity}")
    lines.append("")

    if analysis.redundant_pairs:
        lines.append(f"Redundant Task Pairs Found: {len(analysis.redundant_pairs)}")
        lines.append("-" * 80)
        for i, pair in enumerate(analysis.redundant_pairs, 1):
            lines.append(f"\nPair {i}:")
            lines.append(f"  Task 1: {pair.task_1_name} (ID: {pair.task_1_id})")
            lines.append(f"  Task 2: {pair.task_2_name} (ID: {pair.task_2_id})")
            lines.append(f"  Overlap Score: {pair.overlap_score:.2%}")
            lines.append(f"  Time Wasted: {pair.time_wasted:.1f} hours")
            lines.append(f"  Evidence: {pair.evidence}")
    else:
        lines.append("No redundant task pairs detected.")
        lines.append("")

    if analysis.recommendations:
        lines.append("")
        lines.append("RECOMMENDATIONS:")
        lines.append("-" * 80)
        for rec in analysis.recommendations:
            lines.append(f"  • {rec}")
    else:
        lines.append("")
        lines.append("No recommendations.")

    lines.append("")
    lines.append("=" * 80)

    return "\n".join(lines)


def format_json_output(analysis: TaskRedundancyAnalysis) -> str:
    """
    Format analysis results as JSON.

    Parameters
    ----------
    analysis : TaskRedundancyAnalysis
        Analysis results to format

    Returns
    -------
    str
        JSON formatted output
    """
    result: dict[str, Any] = {
        "project_id": analysis.project_id,
        "redundancy_score": analysis.redundancy_score,
        "total_time_wasted": analysis.total_time_wasted,
        "over_decomposition_detected": analysis.over_decomposition_detected,
        "recommended_complexity": analysis.recommended_complexity,
        "redundant_pairs": [
            {
                "task_1_id": pair.task_1_id,
                "task_1_name": pair.task_1_name,
                "task_2_id": pair.task_2_id,
                "task_2_name": pair.task_2_name,
                "overlap_score": pair.overlap_score,
                "evidence": pair.evidence,
                "time_wasted": pair.time_wasted,
            }
            for pair in analysis.redundant_pairs
        ],
        "recommendations": analysis.recommendations,
        "raw_data": analysis.raw_data,
    }

    return json.dumps(result, indent=2)


async def analyze_project_redundancy(
    project_id: str,
    output_format: str = "text",
    output_file: str | None = None,
) -> None:
    """
    Analyze task redundancy for a project.

    Parameters
    ----------
    project_id : str
        ID of the project to analyze
    output_format : str
        Output format: "text" or "json"
    output_file : str | None
        Optional file path to write output to
    """
    print(f"Loading project history for project: {project_id}")
    print()

    # Load project history
    aggregator = ProjectHistoryAggregator()
    try:
        project_history = await aggregator.aggregate_project(
            project_id=project_id,
            include_conversations=True,
            include_kanban=False,
        )
    except Exception as e:
        print(f"ERROR: Failed to load project history: {e}", file=sys.stderr)
        sys.exit(1)

    tasks = project_history.tasks
    conversations = project_history.conversations

    if not tasks:
        print("WARNING: No tasks found in project history.", file=sys.stderr)
        print("Cannot perform redundancy analysis on empty project.")
        sys.exit(1)

    print(f"Loaded {len(tasks)} tasks from project history")
    print(f"Loaded {len(conversations)} conversation messages")
    print()

    # Run redundancy analysis
    print("Analyzing task redundancy...")
    print()

    analyzer = TaskRedundancyAnalyzer()
    try:
        analysis = await analyzer.analyze_project(
            tasks=tasks,
            conversations=conversations,
        )
        # Set project_id since analyzer doesn't have it
        analysis.project_id = project_id
    except Exception as e:
        print(f"ERROR: Analysis failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Format output
    if output_format == "json":
        output = format_json_output(analysis)
    else:
        output = format_text_output(analysis)

    # Write output
    if output_file:
        output_path = Path(output_file)
        try:
            output_path.write_text(output)
            print(f"Results written to: {output_file}")
        except Exception as e:
            print(f"ERROR: Failed to write output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)


def main() -> None:
    """Run CLI tool for task redundancy analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze task redundancy in Marcus projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze project with text output
  python -m src.cli.analyze_task_redundancy --project-id abc123

  # Analyze project with JSON output
  python -m src.cli.analyze_task_redundancy --project-id abc123 \\
      --output-format json

  # Save results to file
  python -m src.cli.analyze_task_redundancy --project-id abc123 \\
      --output-file results.json

  # Combine options
  python -m src.cli.analyze_task_redundancy \\
      --project-id abc123 \\
      --output-format json \\
      --output-file redundancy_analysis.json
        """,
    )

    parser.add_argument(
        "--project-id",
        required=True,
        help="ID of the Marcus project to analyze",
    )

    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument(
        "--output-file",
        help="Optional file path to write output to (default: stdout)",
    )

    args = parser.parse_args()

    # Run analysis
    try:
        asyncio.run(
            analyze_project_redundancy(
                project_id=args.project_id,
                output_format=args.output_format,
                output_file=args.output_file,
            )
        )
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
