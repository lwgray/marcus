#!/usr/bin/env python3
"""
Fix Demo Issues

This script helps diagnose and fix common demo issues:
1. End running experiments
2. Check what tasks exist on the board
3. Check agent registrations
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    """Main diagnostic and fix routine."""
    demo_root = Path(__file__).parent
    project_info_file = demo_root / "project_info.json"

    if not project_info_file.exists():
        print("❌ No project_info.json found. Run the demo first.")
        sys.exit(1)

    with open(project_info_file, "r") as f:
        project_info = json.load(f)

    project_id = project_info.get("project_id")
    board_id = project_info.get("board_id")

    print("=" * 60)
    print("Marcus Demo Diagnostic & Fix Tool")
    print("=" * 60)
    print(f"\nProject ID: {project_id}")
    print(f"Board ID: {board_id}")

    # Connect to Marcus MCP
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.marcus_mcp.server"],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. End any running experiment
            print("\n[1/3] Ending any running experiments...")
            try:
                result = await session.call_tool("end_experiment", arguments={})
                print(f"  ✓ Experiment ended: {result}")
            except Exception as e:
                print(f"  ℹ️  No experiment to end or error: {e}")

            # 2. Check tasks on the board
            print("\n[2/3] Checking tasks on board...")
            try:
                result = await session.call_tool(
                    "get_all_board_tasks",
                    arguments={"board_id": board_id, "project_id": project_id}
                )

                # Extract content from CallToolResult
                result_dict = {}
                if hasattr(result, 'content'):
                    content = result.content
                    if isinstance(content, list) and len(content) > 0:
                        first_content = content[0]
                        if hasattr(first_content, 'text'):
                            result_dict = json.loads(first_content.text)

                if isinstance(result_dict, dict) and "tasks" in result_dict:
                    tasks = result_dict["tasks"]
                    print(f"  ✓ Found {len(tasks)} tasks on board")

                    # Group by status
                    by_status: Dict[str, int] = {}
                    for task in tasks:
                        status = task.get("status", "unknown")
                        by_status[status] = by_status.get(status, 0) + 1

                    print("\n  Task Status Breakdown:")
                    for status, count in by_status.items():
                        print(f"    {status}: {count}")

                    # Show unassigned tasks
                    unassigned = [t for t in tasks if not t.get("assigned_to")]
                    print(f"\n  Unassigned tasks: {len(unassigned)}")
                    if unassigned:
                        print("\n  Sample unassigned tasks:")
                        for task in unassigned[:5]:
                            print(f"    - {task.get('name')} (ID: {task.get('id')})")
                            if task.get('labels'):
                                print(f"      Labels: {', '.join(task.get('labels', []))}")
                else:
                    print(f"  Unexpected result: {result_dict}")

            except Exception as e:
                print(f"  ❌ Error getting tasks: {e}")

            # 3. List registered agents
            print("\n[3/3] Checking registered agents...")
            try:
                # Try to get agent status for common agent IDs
                agent_ids = [
                    "agent_foundation",
                    "agent_auth",
                    "agent_api",
                    "agent_integration"
                ]

                registered = []
                for agent_id in agent_ids:
                    try:
                        result = await session.call_tool(
                            "get_agent_status",
                            arguments={"agent_id": agent_id}
                        )
                        if result:
                            registered.append(agent_id)
                            print(f"  ✓ {agent_id}: Registered")
                    except:
                        print(f"  ✗ {agent_id}: Not registered")

                print(f"\n  Total registered: {len(registered)}/{len(agent_ids)}")

            except Exception as e:
                print(f"  ℹ️  Could not check agent registrations: {e}")

            print("\n" + "=" * 60)
            print("Diagnostic Complete")
            print("=" * 60)
            print("\nRecommendations:")
            print("  1. If experiment was ended, you can run the demo again")
            print("  2. If tasks exist but agents can't find them:")
            print("     - Check that agent skills match task labels")
            print("     - Ensure agents are calling request_next_task correctly")
            print("  3. If no agents registered:")
            print("     - Check agent terminal windows for errors")
            print("     - Verify MCP server is running")


if __name__ == "__main__":
    asyncio.run(main())
