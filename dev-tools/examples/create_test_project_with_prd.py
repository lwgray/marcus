#!/usr/bin/env python3
r"""
CLI tool to test project creation and VIEW the PRD analysis.

This enhanced version shows the full PRD (Product Requirements Document)
that Marcus generates before creating tasks.

Usage:
    python create_test_project_with_prd.py prototype \
        "Build an MCP server for utilities"

    python create_test_project_with_prd.py standard \
        "Create a task management app" --show-prd-only
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ai.advanced.prd.advanced_parser import (  # noqa: E402
    AdvancedPRDParser,
    ProjectConstraints,
)
from src.ai.providers.llm_abstraction import LLMAbstraction  # noqa: E402
from src.worker.inspector import Inspector  # noqa: E402


def print_separator(title: str = "", char: str = "=") -> None:
    """Print a formatted separator line."""
    if title:
        width = 70
        title_text = f" {title} "
        padding = (width - len(title_text)) // 2
        print(f"\n{char * padding}{title_text}{char * padding}")
    else:
        print(f"\n{char * 70}")


def format_requirement(req: dict[str, Any], index: int) -> str:
    """Format a requirement for display."""
    output = f"\n  {index}. {req.get('name', 'Unnamed')}"
    output += f"\n     ID: {req.get('id', 'no-id')}"
    if desc := req.get("description"):
        output += f"\n     Description: {desc}"
    if complexity := req.get("complexity"):
        output += f"\n     Complexity: {complexity}"
    if priority := req.get("priority"):
        output += f"\n     Priority: {priority}"
    return output


def display_prd_analysis(prd_result: Any) -> None:
    """Display the PRD analysis in a readable format."""
    print_separator("PRD ANALYSIS RESULTS", "=")

    # Project Overview
    print("\n📋 PROJECT OVERVIEW")
    print(f"  Project Type: {getattr(prd_result, 'project_type', 'N/A')}")
    print(f"  Complexity: {getattr(prd_result, 'complexity', 'N/A')}")
    print(f"  Total Tasks: {len(prd_result.tasks) if prd_result.tasks else 0}")

    # Functional Requirements
    if hasattr(prd_result, "functional_requirements"):
        print_separator("FUNCTIONAL REQUIREMENTS", "-")
        func_reqs = prd_result.functional_requirements
        if func_reqs:
            print(f"\n  Total Functional Requirements: {len(func_reqs)}")
            for idx, req in enumerate(func_reqs, 1):
                print(format_requirement(req, idx))
        else:
            print("\n  ⚠️  No functional requirements extracted")

    # Integration Requirements
    if hasattr(prd_result, "integration_requirements"):
        print_separator("INTEGRATION REQUIREMENTS", "-")
        int_reqs = prd_result.integration_requirements
        if int_reqs:
            print(f"\n  Total Integration Requirements: {len(int_reqs)}")
            for idx, req in enumerate(int_reqs, 1):
                print(format_requirement(req, idx))
        else:
            print("\n  ℹ️  No integration requirements extracted")

    # Task Breakdown
    if prd_result.tasks:
        print_separator("GENERATED TASKS", "-")
        print(f"\n  Total Tasks: {len(prd_result.tasks)}")

        # Group by type/label
        task_types: dict[str, list[Any]] = {}
        for task in prd_result.tasks:
            labels = task.labels if hasattr(task, "labels") else []
            key = labels[0] if labels else "unlabeled"
            if key not in task_types:
                task_types[key] = []
            task_types[key].append(task)

        print("\n  Task Breakdown by Type:")
        for task_type, tasks in sorted(task_types.items()):
            print(f"    - {task_type}: {len(tasks)} tasks")

        # Show first few tasks as examples
        print("\n  Sample Tasks (first 5):")
        for idx, task in enumerate(prd_result.tasks[:5], 1):
            print(f"\n    {idx}. {task.name}")
            print(f"       Description: {task.description[:100]}...")
            print(f"       Labels: {', '.join(task.labels)}")
            print(f"       Estimated: {task.estimated_hours}h")

    # Dependencies
    if hasattr(prd_result, "dependencies") and prd_result.dependencies:
        print_separator("TASK DEPENDENCIES", "-")
        print(f"\n  Total Dependencies: {len(prd_result.dependencies)}")
        for idx, dep in enumerate(prd_result.dependencies[:10], 1):
            print(
                f"\n    {idx}. {dep.get('dependent_task_id')} → "
                f"{dep.get('dependency_task_id')}"
            )
            if reason := dep.get("reasoning"):
                print(f"       Reason: {reason}")

    print_separator("", "=")


async def analyze_prd_only(
    complexity: str,
    description: str,
) -> None:
    """Analyze PRD without creating a project."""
    print_separator("PRD ANALYSIS MODE")
    print(f"Complexity: {complexity}")
    print(f"Description: {description}")
    print_separator()

    # Initialize AI client
    print("\n🤖 Initializing AI client...")
    ai_client = LLMAbstraction()

    # Initialize PRD parser
    print("📝 Initializing PRD parser...")
    prd_parser = AdvancedPRDParser()

    # Build constraints
    constraints = ProjectConstraints(
        team_size=1,
        complexity_mode=complexity,
        quality_requirements={
            "project_size": complexity,
            "complexity": "simple" if complexity == "prototype" else "moderate",
        },
    )

    print(f"\n⚙️  Parsing PRD with {complexity} mode...")

    try:
        # Parse PRD
        prd_result = await prd_parser.parse_prd_to_tasks(description, constraints)

        # Display results
        display_prd_analysis(prd_result)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Cleanup
        if hasattr(ai_client, "cleanup"):
            await ai_client.cleanup()


async def create_project_with_prd(
    complexity: str,
    description: str,
    project_name: str | None = None,
    url: str = "http://localhost:4298/mcp",
) -> None:
    """Create a test project and show the PRD analysis."""
    print_separator("PROJECT CREATION WITH PRD ANALYSIS")
    print(f"Complexity: {complexity}")
    print(f"Description: {description[:100]}{'...' if len(description) > 100 else ''}")
    print_separator()

    # Auto-generate project name if not provided
    if not project_name:
        project_name = f"Test {complexity.capitalize()} Project"

    print(f"\n📡 Connecting to Marcus server at {url}...")

    client = Inspector(connection_type="http")

    try:
        async with client.connect(url=url) as session:
            # Authenticate
            print("🔐 Authenticating...")
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": "cli-test",
                    "client_type": "admin",
                    "role": "admin",
                    "metadata": {"test": "cli_tool"},
                },
            )
            print("✅ Authenticated\n")

            # First, analyze the PRD
            print("📝 Analyzing PRD...")
            ai_client = LLMAbstraction()
            prd_parser = AdvancedPRDParser()

            constraints = ProjectConstraints(
                team_size=1,
                complexity_mode=complexity,
                quality_requirements={
                    "project_size": complexity,
                    "complexity": "simple" if complexity == "prototype" else "moderate",
                },
            )

            prd_result = await prd_parser.parse_prd_to_tasks(description, constraints)

            # Display PRD analysis
            display_prd_analysis(prd_result)

            # Cleanup AI client
            if hasattr(ai_client, "cleanup"):
                await ai_client.cleanup()

            # Now create the project
            print("\n\n")
            print_separator("CREATING PROJECT ON SERVER")
            print(f"📝 Creating '{project_name}' in {complexity.upper()} mode...")

            result = await session.call_tool(
                "create_project",
                arguments={
                    "description": description,
                    "project_name": project_name,
                    "options": {
                        "complexity": complexity,
                        "provider": "planka",
                    },
                },
            )

            print_separator("SERVER RESPONSE")

            # Parse and display result
            if hasattr(result, "content") and result.content:
                text = result.content[0].text
                data = json.loads(text)

                if data.get("success"):
                    print("\n✅ SUCCESS!")
                    print(f"Project: {data.get('project_name')}")
                    print(f"Tasks created: {data.get('tasks_created', 0)}")

                    if "task_breakdown" in data:
                        breakdown = data["task_breakdown"]
                        print("\nTask Breakdown:")
                        for task_type, count in breakdown.items():
                            if task_type != "total":
                                print(f"  - {task_type.capitalize()}: {count}")

                    if "project_id" in data:
                        print(f"\nMarcus Project ID: {data['project_id']}")

                    print("\n💡 View in Planka: http://localhost:3333")
                else:
                    print("\n❌ FAILED!")
                    error = data.get("error", {})
                    if isinstance(error, dict):
                        print(f"Error: {error.get('message', 'Unknown error')}")
                    else:
                        print(f"Error: {error}")

            print_separator()

    except Exception as e:
        print_separator("ERROR")
        print(f"{e}")
        print("\n💡 Troubleshooting:")
        print("   1. Make sure Marcus server is running:")
        print("      python -m src.marcus_mcp.server --http")
        print("   2. Make sure Planka is running:")
        print("      docker-compose up -d")
        print(f"   3. Verify the URL is correct: {url}")
        import traceback

        traceback.print_exc()


def main() -> None:
    """Parse arguments and run project creation."""
    parser = argparse.ArgumentParser(
        description="Test Marcus project creation and view PRD analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show PRD analysis only (no project creation)
  python create_test_project_with_prd.py prototype \\
      "Build an MCP server for utilities" --show-prd-only

  # Create project and show PRD analysis
  python create_test_project_with_prd.py standard \\
      "Build a task management MCP server" --name "Task Manager"

  # Analyze complex project PRD
  python create_test_project_with_prd.py enterprise \\
      "Build a microservices platform" --show-prd-only
        """,
    )

    parser.add_argument(
        "complexity",
        choices=["prototype", "standard", "enterprise"],
        help="Complexity mode for the project",
    )

    parser.add_argument("description", help="Project description or PRD")

    parser.add_argument(
        "--name", "-n", dest="project_name", help="Custom project name (optional)"
    )

    parser.add_argument(
        "--url",
        "-u",
        default="http://localhost:4298/mcp",
        help="Marcus HTTP server URL (default: http://localhost:4298/mcp)",
    )

    parser.add_argument(
        "--show-prd-only",
        action="store_true",
        help="Only show PRD analysis without creating project",
    )

    args = parser.parse_args()

    # Run async function
    if args.show_prd_only:
        # PRD analysis only
        asyncio.run(
            analyze_prd_only(
                complexity=args.complexity,
                description=args.description,
            )
        )
    else:
        # Full project creation with PRD display
        asyncio.run(
            create_project_with_prd(
                complexity=args.complexity,
                description=args.description,
                project_name=args.project_name,
                url=args.url,
            )
        )


if __name__ == "__main__":
    main()
