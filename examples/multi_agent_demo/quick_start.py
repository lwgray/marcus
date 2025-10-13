#!/usr/bin/env python3
"""
Quick Start Script for Marcus Multi-Agent Demo

This script helps you quickly create the project in Marcus and get started.
"""

import asyncio
import sys
from pathlib import Path


async def create_marcus_project() -> None:
    """Create the Task Management API project in Marcus."""
    try:
        from mcp.client.stdio import stdio_client

        from mcp import ClientSession, StdioServerParameters
    except ImportError:
        print("Error: MCP client not installed")
        print("Run: pip install mcp")
        sys.exit(1)

    demo_root = Path(__file__).parent
    project_spec_path = demo_root / "PROJECT_SPEC.md"

    if not project_spec_path.exists():
        print(f"Error: PROJECT_SPEC.md not found at {project_spec_path}")
        sys.exit(1)

    print("=" * 60)
    print("Creating Task Management API Project in Marcus")
    print("=" * 60)

    # Read project specification
    with open(project_spec_path, "r") as f:
        project_description = f.read()

    print(f"\n📋 Loaded specification: {len(project_description)} characters")
    print(f"📍 Demo root: {demo_root}")

    # Connect to Marcus MCP server
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.marcus_mcp.server"],
        env=None,
    )

    print("\n🔌 Connecting to Marcus MCP server...")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✓ Connected to Marcus")

                # Create project
                print("\n🚀 Creating project (this may take a moment)...")

                result = await session.call_tool(
                    "create_project",
                    arguments={
                        "project_name": "Task Management API Demo",
                        "description": project_description,
                        "options": {
                            "complexity": "standard",
                            "provider": "planka",
                            "mode": "new_project",
                        },
                    },
                )

                # Extract content from CallToolResult
                result_dict = {}
                if hasattr(result, 'content'):
                    content = result.content
                    if isinstance(content, list) and len(content) > 0:
                        first_content = content[0]
                        if hasattr(first_content, 'text'):
                            import json
                            result_dict = json.loads(first_content.text)

                print("\n" + "=" * 60)
                if result_dict.get("success"):
                    print("✅ PROJECT CREATED SUCCESSFULLY!")
                    print("=" * 60)
                    print(f"\n📊 Project Details:")
                    print(f"   Project ID: {result_dict.get('project_id')}")
                    print(f"   Board ID: {result_dict.get('board', {}).get('board_id')}")
                    print(f"   Tasks Created: {result_dict.get('tasks_created', 0)}")

                    board_info = result_dict.get("board", {})
                    print(f"\n📋 Board: {board_info.get('board_name', 'N/A')}")

                    print("\n✨ Next Steps:")
                    print("   1. View your project in the Planka board")
                    print("   2. Run the demo_runner.py to start agents")
                    print("   3. Or manually work on tasks yourself")

                    # Save project info for later use
                    info_file = demo_root / "project_info.json"

                    with open(info_file, "w") as f:
                        json.dump(
                            {
                                "project_id": result_dict.get("project_id"),
                                "board_id": board_info.get("board_id"),
                                "tasks_created": result_dict.get("tasks_created"),
                                "created_at": str(asyncio.get_event_loop().time()),
                            },
                            f,
                            indent=2,
                        )

                    print(f"\n💾 Project info saved to: {info_file}")

                else:
                    print("❌ PROJECT CREATION FAILED")
                    print("=" * 60)
                    print(f"\n Error: {result_dict.get('error', 'Unknown error')}")
                    sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure Marcus MCP server is configured")
        print("  2. Check that Planka is accessible")
        print("  3. Verify credentials in .env file")
        sys.exit(1)


async def start_experiment_tracking() -> None:
    """Start MLflow experiment for tracking metrics."""
    try:
        from mcp.client.stdio import stdio_client

        from mcp import ClientSession, StdioServerParameters
    except ImportError:
        print("Error: MCP client not installed")
        return

    from datetime import datetime

    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.marcus_mcp.server"],
        env=None,
    )

    print("\n🔬 Starting experiment tracking...")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "start_experiment",
                    arguments={
                        "experiment_name": "marcus_multi_agent_demo",
                        "run_name": f"task_api_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "tags": {
                            "project_type": "rest_api",
                            "framework": "fastapi",
                            "demo": "multi_agent",
                        },
                        "params": {
                            "num_agents": 4,
                            "target_coverage": 80,
                            "api_endpoints": 15,
                        },
                    },
                )

                print("✓ Experiment tracking started")
                print(f"  View in MLflow UI: http://localhost:5000")

    except Exception as e:
        print(f"⚠️  Experiment tracking failed: {e}")
        print("   (Continuing without experiment tracking)")


async def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Quick start script for Marcus multi-agent demo"
    )
    parser.add_argument(
        "--with-experiment",
        action="store_true",
        help="Start MLflow experiment tracking",
    )
    args = parser.parse_args()

    # Create project
    await create_marcus_project()

    # Optionally start experiment tracking
    if args.with_experiment:
        await start_experiment_tracking()

    print("\n" + "=" * 60)
    print("Setup Complete! 🎉")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
