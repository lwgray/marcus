#!/usr/bin/env python3
"""
Compare scoring results from Marcus vs Single Agent implementations.

Generates a comprehensive comparison report showing strengths, weaknesses,
and overall winner.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def load_score(file_path: Path) -> Dict[str, Any]:
    """Load a score JSON file."""
    return json.loads(file_path.read_text())


def generate_comparison_report(
    marcus_score: Dict[str, Any],
    single_score: Dict[str, Any],
    time_marcus: float = None,
    time_single: float = None,
) -> str:
    """
    Generate a markdown comparison report.

    Parameters
    ----------
    marcus_score : Dict
        Marcus system score data
    single_score : Dict
        Single agent score data
    time_marcus : float, optional
        Time taken by Marcus in minutes
    time_single : float, optional
        Time taken by single agent in minutes

    Returns
    -------
    str
        Markdown-formatted comparison report
    """
    report = []
    report.append("# Marcus vs Single Agent: Project Comparison Report\n")
    report.append("=" * 70)
    report.append("\n")

    # Overall Scores
    report.append("## Overall Scores\n")
    report.append("| Metric | Marcus | Single Agent | Winner |")
    report.append("|--------|--------|--------------|--------|")

    marcus_total = marcus_score["total_score"]
    single_total = single_score["total_score"]
    score_winner = "Marcus" if marcus_total > single_total else "Single Agent"
    if abs(marcus_total - single_total) < 1:
        score_winner = "Tie"

    report.append(
        f"| **Total Score** | {marcus_total:.1f}/100 ({marcus_score['percentage']:.1f}%) | "
        f"{single_total:.1f}/100 ({single_score['percentage']:.1f}%) | **{score_winner}** |"
    )

    if time_marcus and time_single:
        time_winner = "Marcus" if time_marcus < time_single else "Single Agent"
        if abs(time_marcus - time_single) < 1:
            time_winner = "Tie"

        report.append(
            f"| **Time** | {time_marcus:.1f} min | {time_single:.1f} min | **{time_winner}** |"
        )

        # Quality/Time Ratio (higher is better)
        marcus_ratio = marcus_total / time_marcus
        single_ratio = single_total / time_single
        ratio_winner = "Marcus" if marcus_ratio > single_ratio else "Single Agent"

        report.append(
            f"| **Quality/Time** | {marcus_ratio:.2f} pts/min | {single_ratio:.2f} pts/min | "
            f"**{ratio_winner}** |"
        )

    report.append("\n")

    # Score Difference
    diff = abs(marcus_total - single_total)
    report.append(f"**Absolute Difference**: {diff:.1f} points\n")
    if time_marcus and time_single:
        time_diff = abs(time_marcus - time_single)
        report.append(f"**Time Difference**: {time_diff:.1f} minutes\n")
    report.append("\n")

    # Category-by-Category Comparison
    report.append("## Category Breakdown\n")
    report.append("| Category | Marcus | Single Agent | Difference | Winner |")
    report.append("|----------|--------|--------------|------------|--------|")

    for m_cat, s_cat in zip(marcus_score["categories"], single_score["categories"]):
        m_score = m_cat["points_earned"]
        s_score = s_cat["points_earned"]
        diff = m_score - s_score
        winner = "Marcus" if diff > 0.5 else ("Single Agent" if diff < -0.5 else "Tie")

        report.append(
            f"| {m_cat['category']} | {m_score:.1f}/{m_cat['points_possible']} | "
            f"{s_score:.1f}/{s_cat['points_possible']} | {diff:+.1f} | **{winner}** |"
        )

    report.append("\n")

    # Marcus Strengths
    report.append("## Marcus Strengths\n")
    marcus_wins = []
    for m_cat, s_cat in zip(marcus_score["categories"], single_score["categories"]):
        if m_cat["points_earned"] > s_cat["points_earned"] + 0.5:
            diff = m_cat["points_earned"] - s_cat["points_earned"]
            marcus_wins.append(
                f"✓ **{m_cat['category']}**: {diff:.1f} points better "
                f"({m_cat['percentage']:.0f}% vs {s_cat['percentage']:.0f}%)"
            )

    if marcus_wins:
        report.extend(marcus_wins)
    else:
        report.append("*(No significant strengths)*")
    report.append("\n")

    # Single Agent Strengths
    report.append("## Single Agent Strengths\n")
    single_wins = []
    for m_cat, s_cat in zip(marcus_score["categories"], single_score["categories"]):
        if s_cat["points_earned"] > m_cat["points_earned"] + 0.5:
            diff = s_cat["points_earned"] - m_cat["points_earned"]
            single_wins.append(
                f"✓ **{s_cat['category']}**: {diff:.1f} points better "
                f"({s_cat['percentage']:.0f}% vs {m_cat['percentage']:.0f}%)"
            )

    if single_wins:
        report.extend(single_wins)
    else:
        report.append("*(No significant strengths)*")
    report.append("\n")

    # Detailed Category Analysis
    report.append("## Detailed Category Analysis\n")

    for m_cat, s_cat in zip(marcus_score["categories"], single_score["categories"]):
        report.append(f"\n### {m_cat['category']}\n")
        report.append(
            f"- **Marcus**: {m_cat['points_earned']:.1f}/{m_cat['points_possible']} "
            f"({m_cat['percentage']:.0f}%)"
        )
        report.append(
            f"- **Single Agent**: {s_cat['points_earned']:.1f}/{s_cat['points_possible']} "
            f"({s_cat['percentage']:.0f}%)"
        )

        # Show key details if available
        if "details" in m_cat and "details" in s_cat:
            report.append("\n**Key Metrics**:")
            report.append("| Metric | Marcus | Single Agent |")
            report.append("|--------|--------|--------------|")

            # Get common keys
            m_details = m_cat["details"]
            s_details = s_cat["details"]
            common_keys = set(m_details.keys()) & set(s_details.keys())

            for key in sorted(common_keys):
                m_val = m_details[key]
                s_val = s_details[key]
                # Format based on type
                if isinstance(m_val, bool):
                    m_val = "✓" if m_val else "✗"
                    s_val = "✓" if s_val else "✗"
                elif isinstance(m_val, float):
                    m_val = f"{m_val:.1f}"
                    s_val = f"{s_val:.1f}"

                report.append(
                    f"| {key.replace('_', ' ').title()} | {m_val} | {s_val} |"
                )

    report.append("\n")

    # Overall Assessment
    report.append("## Overall Assessment\n")

    # Determine winner
    overall_winner = None
    if time_marcus and time_single:
        # If we have timing, use quality/time ratio
        marcus_ratio = marcus_total / time_marcus
        single_ratio = single_total / time_single

        if marcus_ratio > single_ratio * 1.1:  # 10% better
            overall_winner = "Marcus"
        elif single_ratio > marcus_ratio * 1.1:
            overall_winner = "Single Agent"
        else:
            overall_winner = "Tie"
    else:
        # Just use score
        if marcus_total > single_total + 5:
            overall_winner = "Marcus"
        elif single_total > marcus_total + 5:
            overall_winner = "Single Agent"
        else:
            overall_winner = "Tie"

    if overall_winner == "Marcus":
        report.append("**Winner: Marcus Multi-Agent System** 🏆\n")
        report.append(f"Marcus outperformed the single agent with:")
        if time_marcus and time_single:
            report.append(
                f"- {marcus_ratio - single_ratio:.2f} higher quality/time ratio"
            )
        report.append(f"- {marcus_total - single_total:.1f} point score advantage")
    elif overall_winner == "Single Agent":
        report.append("**Winner: Single Agent** 🏆\n")
        report.append(f"The single agent outperformed Marcus with:")
        if time_marcus and time_single:
            report.append(
                f"- {single_ratio - marcus_ratio:.2f} higher quality/time ratio"
            )
        report.append(f"- {single_total - marcus_total:.1f} point score advantage")
    else:
        report.append("**Result: Tie** 🤝\n")
        report.append("Both approaches delivered comparable results:")
        report.append(
            f"- Score difference: {abs(marcus_total - single_total):.1f} points"
        )
        if time_marcus and time_single:
            report.append(
                f"- Quality/time difference: {abs(marcus_ratio - single_ratio):.2f} pts/min"
            )

    report.append("\n")

    # Interpretation
    report.append("## Interpretation\n")

    marcus_pct = marcus_score["percentage"]
    single_pct = single_score["percentage"]

    def get_grade(pct: float) -> str:
        if pct >= 90:
            return "Excellent"
        elif pct >= 75:
            return "Good"
        elif pct >= 60:
            return "Acceptable"
        elif pct >= 40:
            return "Poor"
        else:
            return "Failing"

    report.append(f"- **Marcus**: {get_grade(marcus_pct)} ({marcus_pct:.0f}%)")
    report.append(f"- **Single Agent**: {get_grade(single_pct)} ({single_pct:.0f}%)")
    report.append("\n")

    if time_marcus and time_single:
        speedup = time_single / time_marcus if time_marcus > 0 else 0
        if speedup > 1.5:
            report.append(
                f"Marcus was **{speedup:.1f}x faster** than the single agent "
                f"({time_marcus:.1f} vs {time_single:.1f} minutes)."
            )
        elif speedup < 0.67:
            report.append(
                f"Single agent was **{1/speedup:.1f}x faster** than Marcus "
                f"({time_single:.1f} vs {time_marcus:.1f} minutes)."
            )
        else:
            report.append(
                f"Time performance was comparable "
                f"({time_marcus:.1f} vs {time_single:.1f} minutes)."
            )

    report.append("\n")

    # Recommendations
    report.append("## Recommendations\n")

    if overall_winner == "Marcus":
        report.append(
            "Marcus demonstrates clear advantages for this project type. "
            "Consider using Marcus for:"
        )
        report.append("- Projects requiring parallel task execution")
        report.append("- Time-sensitive prototypes")
        report.append("- Projects with clear subtask decomposition")
    elif overall_winner == "Single Agent":
        report.append(
            "Single agent approach shows strong performance. "
            "Consider using single agents for:"
        )
        report.append("- Projects requiring deep sequential thinking")
        report.append("- When code quality is paramount over speed")
        report.append("- Simpler projects with fewer dependencies")
    else:
        report.append(
            "Both approaches are viable for this project complexity. "
            "Choice depends on:"
        )
        report.append("- Team familiarity with each approach")
        report.append("- Infrastructure requirements")
        report.append("- Specific quality vs speed trade-offs")

    report.append("\n")
    report.append("=" * 70)

    return "\n".join(report)


def main():
    """Run the comparison tool."""
    parser = argparse.ArgumentParser(
        description="Compare Marcus and Single Agent project scores"
    )
    parser.add_argument(
        "--marcus",
        type=Path,
        required=True,
        help="Marcus score JSON file",
    )
    parser.add_argument(
        "--single",
        type=Path,
        required=True,
        help="Single agent score JSON file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output markdown file for comparison report",
    )
    parser.add_argument(
        "--time-marcus",
        type=float,
        help="Time taken by Marcus in minutes",
    )
    parser.add_argument(
        "--time-single",
        type=float,
        help="Time taken by single agent in minutes",
    )

    args = parser.parse_args()

    # Load scores
    marcus_score = load_score(args.marcus)
    single_score = load_score(args.single)

    # Generate report
    report = generate_comparison_report(
        marcus_score, single_score, args.time_marcus, args.time_single
    )

    # Print to console
    print(report)

    # Save to file if requested
    if args.output:
        args.output.write_text(report)
        print(f"\nComparison report saved to: {args.output}")

    return 0


if __name__ == "__main__":
    exit(main())
