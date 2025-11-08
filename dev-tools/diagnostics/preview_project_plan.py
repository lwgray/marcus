"""
Preview Project Plan Tool.

This script generates a project plan from natural language WITHOUT creating it
in Planka. Use this to see what tasks Marcus will create before committing them
to the board.

Usage:
    python dev-tools/diagnostics/preview_project_plan.py \
        "Your project description" "ProjectName"

Output:
    Creates a detailed markdown preview in data/diagnostics/project_preview.md
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def preview_project_plan(description: str, project_name: str) -> Any:
    """
    Generate project plan without creating in Planka.

    Parameters
    ----------
    description : str
        Natural language project description
    project_name : str
        Name for the project

    Returns
    -------
    Any
        TaskGenerationResult with tasks, dependencies, priorities
    """
    print("🔍 Generating Project Plan Preview\n")
    print("=" * 70)
    print(f"\nProject: {project_name}")
    print(f"Description: {description}\n")

    # Import here to avoid circular import
    print("📡 Initializing AI parser...")
    from src.ai.advanced.prd.advanced_parser import (
        AdvancedPRDParser,
        ProjectConstraints,
    )

    parser = AdvancedPRDParser()

    # Process the natural language description
    print("🤖 Processing natural language description...")
    try:
        # Create constraints (use defaults for preview)
        constraints = ProjectConstraints(
            team_size=1,
            deployment_target="local",
        )

        result = await parser.parse_prd_to_tasks(
            prd_content=description,
            constraints=constraints,
        )
        print("✅ Plan generated successfully\n")
        return result
    except Exception as e:
        print(f"❌ Failed to generate plan: {e}")
        raise


def generate_preview_markdown(result: Any, description: str, project_name: str) -> str:
    """Generate a detailed markdown preview of the project plan."""
    lines = []

    lines.append("# Project Plan Preview")
    lines.append(f"\n**Generated:** {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"\n**Project Name:** {project_name}")
    lines.append("\n**Status:** ⚠️ NOT YET CREATED - PREVIEW ONLY\n")

    # Original description
    lines.append("## Original Description\n")
    lines.append(f"```\n{description}\n```\n")

    # Project metadata
    lines.append("## Project Metadata\n")
    timeline = result.estimated_timeline or {}
    risk = result.risk_assessment or {}
    lines.append(f"- **Confidence Score:** {result.generation_confidence:.2f}")
    lines.append(f"- **Total Tasks:** {len(result.tasks)}")
    lines.append(f"- **Estimated Duration:** {timeline.get('total_duration', 'N/A')}")
    lines.append(f"- **Risk Level:** {risk.get('overall_risk', 'N/A')}\n")

    # Resource requirements
    resources = result.resource_requirements or {}
    if resources:
        lines.append("## Resource Requirements\n")
        for key, value in resources.items():
            lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")
        lines.append("")

    # Task summary table
    lines.append("## Task Summary\n")
    lines.append("| # | Task Name | Priority | Est. Hours | Dependencies | Status |")
    lines.append("|---|-----------|----------|------------|--------------|--------|")

    for idx, task in enumerate(result.tasks, 1):
        task_name = task.name[:40]
        priority = (
            task.priority.value
            if hasattr(task.priority, "value")
            else str(task.priority)
        )
        est_hours = task.estimated_hours if hasattr(task, "estimated_hours") else "N/A"
        deps = len(task.dependencies) if task.dependencies else 0
        status = (
            task.status.value if hasattr(task.status, "value") else str(task.status)
        )
        row = (
            f"| {idx} | {task_name} | {priority} | {est_hours} | "
            f"{deps} deps | {status} |"
        )
        lines.append(row)

    lines.append("\n---\n")

    # Detailed task breakdown
    lines.append("## Detailed Task Breakdown\n")

    for idx, task in enumerate(result.tasks, 1):
        lines.append(f"### Task {idx}: {task.name}\n")

        # Metadata
        priority_str = (
            task.priority.value
            if hasattr(task.priority, "value")
            else str(task.priority)
        )
        status_str = (
            task.status.value if hasattr(task.status, "value") else str(task.status)
        )
        lines.append(f"**Priority:** {priority_str}")
        lines.append(f"**Status:** {status_str}")
        lines.append(f"**Estimated Hours:** {getattr(task, 'estimated_hours', 'N/A')}")

        # Tags/Labels
        tags = getattr(task, "tags", [])
        if tags:
            lines.append(f"**Tags:** {', '.join(tags)}")

        lines.append("")

        # Description
        lines.append("#### Description\n")
        desc = task.description if task.description else "*No description provided*"
        lines.append(f"```\n{desc}\n```\n")

        # Dependencies
        deps_list: List[Any] = task.dependencies or []
        if deps_list:
            lines.append("#### Dependencies\n")
            lines.append(f"This task depends on {len(deps_list)} other task(s):\n")
            for dep in deps_list:
                lines.append(f"- {dep}")
            lines.append("")
        else:
            lines.append("#### Dependencies\n\n*No dependencies*\n")

        lines.append("\n---\n")

    # Dependency graph summary
    lines.append("## Dependency Analysis\n")
    total_deps = sum(len(task.dependencies or []) for task in result.tasks)
    lines.append(f"- **Total Dependencies:** {total_deps}")

    # Find tasks with no dependencies (can start immediately)
    ready_tasks = [task.name for task in result.tasks if not task.dependencies]
    lines.append(f"- **Ready to Start:** {len(ready_tasks)} tasks\n")

    if ready_tasks:
        lines.append("**Tasks Ready to Start (no dependencies):**\n")
        for task_name in ready_tasks[:10]:  # Show first 10
            lines.append(f"- {task_name}")
        if len(ready_tasks) > 10:
            lines.append(f"- *... and {len(ready_tasks) - 10} more*")
        lines.append("")

    # Action items
    lines.append("\n---\n")
    lines.append("## Next Steps\n")
    lines.append("This is a **PREVIEW ONLY**. To create this project, use:\n")
    lines.append("```python")
    lines.append("mcp__marcus__create_project(")
    lines.append(f'    description="{description[:50]}...",')
    lines.append(f'    project_name="{project_name}",')
    lines.append('    options={"mode": "new_project"}')
    lines.append(")")
    lines.append("```\n")

    return "\n".join(lines)


async def main() -> None:
    """Run the preview tool."""
    if len(sys.argv) < 3:
        print("Usage: python dev-tools/diagnostics/preview_project_plan.py")
        print("       <description> <project_name>")
        print("\nExample:")
        print("  python dev-tools/diagnostics/preview_project_plan.py \\")
        print('         "Build a todo app" "MyTodoApp"')
        sys.exit(1)

    description = sys.argv[1]
    project_name = sys.argv[2]

    try:
        # Generate plan
        plan = await preview_project_plan(description, project_name)

        # Generate markdown
        print("=" * 70)
        print("📝 Generating preview document...")
        markdown = generate_preview_markdown(plan, description, project_name)

        # Save to file
        output_dir = Path("data/diagnostics")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "project_preview.md"
        with open(output_file, "w") as f:
            f.write(markdown)

        print(f"✅ Preview saved to: {output_file}")

        # Also save JSON
        json_file = output_dir / "project_preview.json"
        with open(json_file, "w") as f:
            json.dump(plan, f, indent=2, default=str)

        print(f"✅ JSON data saved to: {json_file}")

        # Print summary
        print("\n" + "=" * 70)
        print("📈 PREVIEW SUMMARY")
        print("=" * 70)
        timeline = plan.estimated_timeline or {}
        risk = plan.risk_assessment or {}

        print(f"Total tasks: {len(plan.tasks)}")
        print(f"Estimated duration: {timeline.get('total_duration', 'N/A')}")
        print(f"Risk level: {risk.get('overall_risk', 'N/A')}")
        print(f"Confidence: {plan.generation_confidence:.2f}")
        print("\n⚠️  This is a PREVIEW - nothing has been created yet!")
        print(f"\nReview the full plan at: {output_file}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
