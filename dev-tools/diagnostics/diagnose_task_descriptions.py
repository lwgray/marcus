"""
Task Description Diagnostics Tool.

This script visualizes the flow from:
- Original project description
- Task descriptions in Planka
- Subtask descriptions (if decomposed)
- Instructions generated for agents

Usage:
    python scripts/diagnose_task_descriptions.py

Output:
    Creates a markdown table in data/diagnostics/description_analysis.md
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.models import WorkerStatus  # noqa: E402
from src.integrations.ai_analysis_engine import AIAnalysisEngine  # noqa: E402
from src.integrations.providers.planka_kanban import (  # noqa: E402
    PlankaKanban,
)
from src.marcus_mcp.coordinator.subtask_manager import (  # noqa: E402
    SubtaskManager,
)


async def main() -> None:
    """Run the diagnostic analysis."""
    print("🔍 Task Description Diagnostics Tool\n")
    print("=" * 70)

    # Initialize components
    print("\n📡 Connecting to Planka...")
    kanban_config = {"project_name": "Shorty2 AI Chatbot"}  # Your project
    kanban = PlankaKanban(kanban_config)

    try:
        await kanban.connect()
        print("✅ Connected to Planka")
    except Exception as e:
        print(f"❌ Failed to connect to Planka: {e}")
        return

    # Get all tasks
    print("\n📋 Fetching all tasks...")
    tasks = await kanban.get_all_tasks()
    print(f"✅ Found {len(tasks)} tasks")

    # Load subtask manager
    subtask_manager = SubtaskManager()
    print(f"✅ Loaded subtask manager ({len(subtask_manager.subtasks)} subtasks)")

    # Initialize AI engine
    ai_engine = AIAnalysisEngine()
    await ai_engine.initialize()
    print(f"✅ AI Engine initialized (client: {ai_engine.client is not None})")

    # Analyze each task
    print("\n" + "=" * 70)
    print("📊 ANALYSIS RESULTS")
    print("=" * 70)

    results = []
    for idx, task in enumerate(tasks, 1):
        print(f"\n[{idx}/{len(tasks)}] Analyzing: {task.name}")

        # Check if description matches name
        print(f"  Description: {task.description or '[No description]'}")

        # Check for subtasks
        has_subtasks = subtask_manager.has_subtasks(task.id)
        subtasks = []
        if has_subtasks:
            subtasks = subtask_manager.get_subtasks(task.id)
            print(f"  Subtasks: {len(subtasks)}")

        # Generate instructions
        try:
            mock_agent = WorkerStatus(
                worker_id="diagnostic-agent",
                name="Diagnostic Agent",
                role="developer",
                email="diagnostic@marcus.ai",
                current_tasks=[],
                completed_tasks_count=0,
                capacity=40,
                skills=["python", "javascript"],
                availability={
                    "monday": True,
                    "tuesday": True,
                    "wednesday": True,
                    "thursday": True,
                    "friday": True,
                },
                performance_score=1.0,
            )
            instructions = await ai_engine.generate_task_instructions(task, mock_agent)
            print(f"  Instructions: {instructions}")
        except Exception as e:
            instructions = f"[Error: {e}]"
            print(f"  ⚠️  Could not generate instructions: {e}")

        # Check relevance
        matches = check_relevance(task.name, task.description)
        print(f"  Relevance: {'✅ Matches' if matches else '❌ Mismatch'}")

        results.append(
            {
                "task_id": task.id,
                "task_name": task.name,
                "description": task.description,
                "description_length": len(task.description) if task.description else 0,
                "matches_name": matches,
                "has_subtasks": has_subtasks,
                "subtask_count": len(subtasks) if subtasks else 0,
                "subtasks": (
                    [
                        {
                            "name": st.name,
                            "description": st.description,
                            "status": st.status.value,
                            "order": st.order,
                        }
                        for st in subtasks
                    ]
                    if subtasks
                    else []
                ),
                "instructions": instructions,
            }
        )

    # Generate markdown table
    print("\n" + "=" * 70)
    print("📝 Generating report...")

    markdown = generate_markdown_report(results)

    # Save to file
    output_dir = Path("data/diagnostics")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "description_analysis.md"
    with open(output_file, "w") as f:
        f.write(markdown)

    print(f"✅ Report saved to: {output_file}")

    # Also save JSON
    json_file = output_dir / "description_analysis.json"
    with open(json_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"✅ JSON data saved to: {json_file}")

    # Print summary
    print("\n" + "=" * 70)
    print("📈 SUMMARY")
    print("=" * 70)
    mismatches = sum(1 for r in results if not r["matches_name"])
    with_subtasks = sum(1 for r in results if r["has_subtasks"])

    print(f"Total tasks: {len(results)}")
    print(f"Description mismatches: {mismatches} ({mismatches/len(results)*100:.1f}%)")
    print(f"Tasks with subtasks: {with_subtasks}")
    print(f"\nReview the full report at: {output_file}")


def check_relevance(task_name: str, description: Optional[str]) -> bool:
    """
    Check if description appears relevant to task name.

    Uses a simple heuristic: significant words from task name should appear in
    description.
    """
    if not description:
        return False

    # Extract significant words from task name
    task_words = set(task_name.lower().split())
    common_words = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
    }
    task_words -= common_words

    if not task_words:
        return True  # Can't determine

    desc_lower = description.lower()
    matches = sum(1 for word in task_words if word in desc_lower)

    # At least 50% of significant words should appear
    return matches / len(task_words) >= 0.5


def generate_markdown_report(results: List[Dict[str, Any]]) -> str:
    """Generate a markdown report from analysis results."""
    from datetime import datetime, timezone

    lines = []
    lines.append("# Task Description Analysis Report")
    lines.append(f"\n**Generated:** {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"\n**Total Tasks:** {len(results)}\n")

    # Summary table
    lines.append("## Summary Table\n")
    lines.append("| # | Task Name | Desc Length | Matches? | Subtasks | Status |")
    lines.append("|---|-----------|-------------|----------|----------|--------|")

    for idx, r in enumerate(results, 1):
        match_icon = "✅" if r["matches_name"] else "❌"
        subtask_info = f"{r['subtask_count']}" if r["has_subtasks"] else "-"
        lines.append(
            f"| {idx} | {r['task_name'][:30]} | {r['description_length']} | "
            f"{match_icon} | {subtask_info} | [Details](#task-{idx}) |"
        )

    lines.append("\n---\n")

    # Detailed sections
    lines.append("## Detailed Analysis\n")

    for idx, r in enumerate(results, 1):
        lines.append(f"### <a name='task-{idx}'></a>Task {idx}: {r['task_name']}\n")
        lines.append(f"**Task ID:** `{r['task_id']}`")
        match_status = (
            "✅ Yes" if r["matches_name"] else "❌ **NO - MISMATCH DETECTED**"
        )
        lines.append(f"\n**Description Matches Name:** {match_status}\n")

        # Original Description
        lines.append("#### Original Description (from Planka)\n")
        if r["description"]:
            lines.append(f"```\n{r['description']}\n```\n")
        else:
            lines.append("*[No description]*\n")

        # Subtasks
        if r["has_subtasks"]:
            lines.append(f"#### Subtasks ({r['subtask_count']} total)\n")
            lines.append("| Order | Name | Description Preview | Status |")
            lines.append("|-------|------|---------------------|--------|")
            for st in r["subtasks"]:
                lines.append(
                    f"| {st['order']} | {st['name']} | "
                    f"{st['description']} | {st['status']} |"
                )
            lines.append("")
        else:
            lines.append("#### Subtasks\n\n*No subtasks*\n")

        # Generated Instructions
        lines.append("#### Generated Instructions (What Agents Receive)\n")
        if r["instructions"]:
            inst = r["instructions"]
            if inst.startswith("[Error:"):
                lines.append(f"*{inst}*\n")
            else:
                lines.append(f"```\n{inst}\n```\n")
        else:
            lines.append("*Could not generate instructions*\n")

        lines.append("\n---\n")

    return "\n".join(lines)


if __name__ == "__main__":
    asyncio.run(main())
