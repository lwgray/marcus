#!/usr/bin/env python3
r"""
CLI tool to test project creation with different complexity modes.

Usage:
    python create_test_project.py prototype "Build an MCP server for utilities"
    python create_test_project.py standard "Create a task management app"
    python create_test_project.py --explicit prototype \
        "Create these tools: 1. ping 2. echo"

This tool makes it easy to test how different PRD descriptions and complexity
modes affect project creation and task generation.
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

from src.worker.inspector import Inspector  # noqa: E402


def pretty_print_result(result: Any) -> None:
    """Pretty print MCP tool results."""
    if hasattr(result, "content") and result.content:
        text = result.content[0].text if result.content else str(result)
        try:
            data = json.loads(text)
            print(json.dumps(data, indent=2))
        except (json.JSONDecodeError, AttributeError):
            print(text)
    else:
        print(result)


async def create_project(
    complexity: str,
    description: str,
    project_name: str | None = None,
    url: str = "http://localhost:4298/mcp",
) -> None:
    """
    Create a test project using Marcus MCP server.

    Parameters
    ----------
    complexity : str
        Complexity mode: prototype, standard, or enterprise
    description : str
        Project description/PRD
    project_name : str | None
        Optional project name (auto-generated if not provided)
    url : str
        Marcus HTTP server URL
    """
    print("=" * 70)
    print("🧪 Testing Project Creation")
    print("=" * 70)
    print(f"Complexity: {complexity}")
    print(f"Description: {description[:100]}{'...' if len(description) > 100 else ''}")
    print("=" * 70)

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

            # Create project
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

            print("\n" + "=" * 70)
            print("📊 RESULT:")
            print("=" * 70)
            pretty_print_result(result)

            # Parse and display summary
            if hasattr(result, "content") and result.content:
                text = result.content[0].text
                data = json.loads(text)

                if data.get("success"):
                    print("\n" + "=" * 70)
                    print("✅ SUCCESS!")
                    print("=" * 70)
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
                    print("\n" + "=" * 70)
                    print("❌ FAILED!")
                    print("=" * 70)
                    error = data.get("error", {})
                    if isinstance(error, dict):
                        print(f"Error: {error.get('message', 'Unknown error')}")
                        if "remediation" in error:
                            print("\nRemediation:")
                            for key, value in error["remediation"].items():
                                print(f"  {key}: {value}")
                    else:
                        print(f"Error: {error}")

    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ ERROR!")
        print("=" * 70)
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
        description="Test Marcus project creation with different complexity modes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Prototype mode with open-ended description
  python create_test_project.py prototype "Build an MCP server for utilities"

  # Standard mode with explicit requirements
  python create_test_project.py standard "Create these tools: 1. ping 2. echo 3. time"

  # Enterprise mode with custom project name
  python create_test_project.py enterprise "Build a task manager" \\
      --name "Enterprise Task Manager"

  # Use custom server URL
  python create_test_project.py prototype "Build a chat app" \\
      --url http://localhost:8000/mcp
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

    args = parser.parse_args()

    # Run async function
    asyncio.run(
        create_project(
            complexity=args.complexity,
            description=args.description,
            project_name=args.project_name,
            url=args.url,
        )
    )


if __name__ == "__main__":
    main()
