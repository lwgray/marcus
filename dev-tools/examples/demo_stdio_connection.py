#!/usr/bin/env python3
"""
Demo: Inspector with STDIO connection (spawns separate Marcus instance).

This demonstrates how to programmatically test Marcus by spawning an isolated
instance via stdio for testing without affecting the main Marcus server.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.worker.inspector import Inspector  # noqa: E402


def pretty_print_result(label: str, result: Any) -> None:
    """Pretty print MCP tool results."""
    print(f"\n{label}")
    if hasattr(result, "content") and result.content:
        # Extract text from MCP result
        text = result.content[0].text if result.content else str(result)
        try:
            # Try to parse and pretty print JSON
            data = json.loads(text)
            print(json.dumps(data, indent=2))
        except (json.JSONDecodeError, AttributeError):
            print(text)
    else:
        print(result)


async def main() -> None:
    """
    Demo: Connect via stdio (spawns a separate Marcus instance).

    Use this when:
    - You want an isolated testing environment
    - You don't care about sharing state with other Marcus instances
    - You want to test without affecting the main Marcus server
    - You're running automated tests or development workflows

    This is the RECOMMENDED way to test Inspector!
    """
    print("\n" + "=" * 70)
    print("🚀 Inspector STDIO Connection Demo")
    print("=" * 70)
    print("\nSpawning separate Marcus instance for isolated testing...")
    print("Note: This may take 10-15 seconds to initialize...\n")

    client = Inspector(connection_type="stdio")

    try:
        async with client.connect() as session:
            # First authenticate as admin to get access to ALL tools
            # Options: "observer", "developer", "agent", "admin"
            print("🔐 Authenticating as admin...")
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": "stdio-test-worker",
                    "client_type": "admin",  # Admin access
                    "role": "admin",
                    "metadata": {"test_mode": True, "connection": "stdio"},
                },
            )
            print("✅ Authenticated as admin (full access)")

            # List available projects
            print("\n" + "=" * 70)
            print("📂 PROJECT MANAGEMENT")
            print("=" * 70)

            projects_result = await session.call_tool("list_projects", arguments={})
            pretty_print_result("Available projects:", projects_result)

            # Get current project
            current_result = await session.call_tool(
                "get_current_project", arguments={}
            )
            pretty_print_result("Current project:", current_result)

            # Register agent
            print("\n" + "=" * 70)
            print("🤖 AGENT WORKFLOW")
            print("=" * 70)

            print("\n🔧 Registering test agent...")
            result = await client.register_agent(
                agent_id="stdio-test-worker",
                name="STDIO Test Worker",
                role="Developer",
                skills=["python", "testing", "automation"],
            )
            pretty_print_result("Agent registered:", result)

            # Request a task
            print("\n📋 Requesting next task...")
            task = await client.request_next_task("stdio-test-worker")
            pretty_print_result("Task received:", task)

            print("\n" + "=" * 70)
            print("✅ Demo complete!")
            print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
