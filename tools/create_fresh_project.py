#!/usr/bin/env python3
"""
Create a fresh test project on the Kanban board.

Default: Creates a Simple Weather API project
Can also create custom projects via command line or description file.
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.worker.inspector import Inspector

# Default project description
DEFAULT_DESCRIPTION = """Create a Weather API service with:
- Design weather data models (temperature, humidity, location)
- Implement GET /weather/current endpoint
- Test weather endpoint with mock data"""

DEFAULT_PROJECT_NAME = "Simple Weather API"


async def create_project(
    project_name: str,
    description: str,
    complexity: str = "prototype",
    provider: str = "planka",
):
    """
    Create a new project on the Kanban board.

    Parameters
    ----------
    project_name : str
        Name for the project
    description : str
        Project description with requirements
    complexity : str
        Project complexity: "prototype", "standard", or "enterprise"
    provider : str
        Kanban provider: "planka", "github", or "linear"
    """
    print("\n" + "=" * 70)
    print("Creating Fresh Project")
    print("=" * 70)
    print(f"Project name: {project_name}")
    print(f"Complexity: {complexity}")
    print(f"Provider: {provider}")
    print("\nDescription:")
    print(description)
    print("=" * 70)

    inspector = Inspector(connection_type="http")

    try:
        async with inspector.connect(url="http://localhost:4298/mcp") as session:
            # Authenticate
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": "project-creator",
                    "client_type": "agent",
                    "role": "project-manager",
                    "metadata": {"purpose": "testing"},
                },
            )
            print("\n✅ Authenticated")

            # Create project
            print("\n📦 Creating project...")
            result = await session.call_tool(
                "create_project",
                arguments={
                    "description": description,
                    "project_name": project_name,
                    "options": {
                        "mode": "new_project",
                        "complexity": complexity,
                        "provider": provider,
                    },
                },
            )

            # Parse result
            if hasattr(result, "structuredContent"):
                result_data = result.structuredContent.get("result", {})

                print("\n" + "=" * 70)
                print("✅ Project created successfully!")
                print("=" * 70)
                print(f"Project ID: {result_data.get('project_id')}")
                print(f"Tasks created: {result_data.get('tasks_created')}")

                task_breakdown = result_data.get("task_breakdown", {})
                if task_breakdown:
                    print(f"\nTask breakdown:")
                    print(f"  Total: {task_breakdown.get('total')}")
                    print(f"  Design: {task_breakdown.get('design', 0)}")
                    print(
                        f"  Implementation: {task_breakdown.get('implementation', 0)}"
                    )
                    print(f"  Testing: {task_breakdown.get('testing', 0)}")

                print(f"\nEstimated days: {result_data.get('estimated_days')}")
                print(f"Risk level: {result_data.get('risk_level')}")
                print(f"Dependencies mapped: {result_data.get('dependencies_mapped')}")
                print("=" * 70)
            else:
                print(f"\n✅ Project created!")
                print(f"Result: {result}")

    except Exception as e:
        print(f"\n❌ Error creating project: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a fresh project on the Kanban board",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create default Simple Weather API project
  python3 create_fresh_project.py

  # Create custom project via command line
  python3 create_fresh_project.py -n "Task Manager" -d "Build a task management system with users and projects"

  # Create project from description file
  python3 create_fresh_project.py -n "E-commerce Platform" -f project_description.txt

  # Create enterprise-level project
  python3 create_fresh_project.py -n "Banking System" -f bank_spec.txt -c enterprise
        """,
    )

    parser.add_argument(
        "-n",
        "--name",
        type=str,
        default=DEFAULT_PROJECT_NAME,
        help=f"Project name (default: '{DEFAULT_PROJECT_NAME}')",
    )

    parser.add_argument(
        "-d",
        "--description",
        type=str,
        help="Project description (overrides default)",
    )

    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        help="Read project description from file (overrides -d and default)",
    )

    parser.add_argument(
        "-c",
        "--complexity",
        type=str,
        choices=["prototype", "standard", "enterprise"],
        default="prototype",
        help="Project complexity level (default: prototype)",
    )

    parser.add_argument(
        "-p",
        "--provider",
        type=str,
        choices=["planka", "github", "linear"],
        default="planka",
        help="Kanban provider (default: planka)",
    )

    args = parser.parse_args()

    # Determine description source (priority: file > command line > default)
    if args.file:
        if not args.file.exists():
            parser.error(f"Description file not found: {args.file}")
        description = args.file.read_text().strip()
        print(f"📄 Loaded description from: {args.file}")
    elif args.description:
        description = args.description
    else:
        description = DEFAULT_DESCRIPTION
        print("📝 Using default Weather API description")

    asyncio.run(
        create_project(
            project_name=args.name,
            description=description,
            complexity=args.complexity,
            provider=args.provider,
        )
    )
