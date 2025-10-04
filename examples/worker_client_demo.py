#!/usr/bin/env python3
"""
Demo script showing how to use WorkerMCPClient with stdio connections.

This demonstrates:
1. Connecting via stdio (spawns separate Marcus instance for isolated testing)

Note: HTTP connections are available via connect_to_marcus_http() but require
      a Marcus server configured for external HTTP access with proper CORS settings.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.worker.client import WorkerMCPClient


def pretty_print_result(label: str, result):
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


async def demo_stdio_connection():
    """
    Demo: Connect via stdio (spawns a separate Marcus instance).

    Use this when:
    - You want an isolated testing environment
    - You don't care about sharing state with other Marcus instances
    - You want to test without affecting the main Marcus server
    - You're running automated tests or development workflows

    This is the RECOMMENDED way to test WorkerMCPClient!
    """
    print("\n" + "=" * 60)
    print("DEMO: STDIO Connection (Separate Test Instance)")
    print("=" * 60)

    client = WorkerMCPClient()

    try:
        print("\n📡 Starting separate Marcus instance for testing...")
        async with client.connect_to_marcus() as session:
            # First authenticate as admin to get access to ALL MCP tools
            # Options: "observer" (read-only), "developer" (project mgmt), "agent" (worker only), "admin" (ALL tools)
            print("\n🔐 Authenticating as admin...")
            auth_result = await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": "stdio-worker-1",
                    "client_type": "admin",  # Admin has access to ALL tools
                    "role": "admin",
                    "metadata": {"test_mode": True},
                },
            )
            print(f"✅ Authenticated as admin (full access to all MCP tools)")

            # List available projects
            print("\n📂 Listing available projects...")
            projects_result = await session.call_tool("list_projects", arguments={})
            pretty_print_result("Available projects:", projects_result)

            # Get current project
            print("\n📍 Getting current project...")
            current_result = await session.call_tool(
                "get_current_project", arguments={}
            )
            pretty_print_result("Current project:", current_result)

            # Register agent
            print("\n🔧 Registering test agent...")
            result = await client.register_agent(
                agent_id="stdio-worker-1",
                name="STDIO Test Worker",
                role="Developer",
                skills=["python", "testing"],
            )
            pretty_print_result("✅ Agent registered:", result)

            # Request a task
            print("\n📋 Requesting next task...")
            task = await client.request_next_task("stdio-worker-1")
            pretty_print_result("Task received:", task)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


async def demo_http_connection():
    """
    Demo: Connect via HTTP to a running Marcus instance.

    Use this when:
    - You want to connect to an existing Marcus server
    - You want to share state with other clients
    - Multiple workers need to coordinate through the same server

    Prerequisites:
    - Marcus server must be running in HTTP mode
    - Default URL: http://localhost:4299/mcp
    """
    print("\n" + "=" * 60)
    print("DEMO 2: HTTP Connection (Running Instance)")
    print("=" * 60)

    client = WorkerMCPClient()

    try:
        # Connect to the worker agent port (4299)
        async with client.connect_to_marcus_http(
            "http://localhost:4299/mcp"
        ) as session:
            # Register agent
            result = await client.register_agent(
                agent_id="http-worker-1",
                name="HTTP Test Worker",
                role="Developer",
                skills=["python", "fastapi", "testing"],
            )
            print(f"\n✅ Agent registered: {result}")

            # Request a task
            task = await client.request_next_task("http-worker-1")
            print(f"\n📋 Task received: {task}")

            # Get agent status
            status = await client.get_agent_status("http-worker-1")
            print(f"\n📊 Agent status: {status}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Make sure Marcus server is running in HTTP mode!")
        print("   Start it with: python -m src.marcus_mcp.server --http")


async def main():
    """Run the stdio demo."""
    print("\n🚀 WorkerMCPClient Connection Demo")
    print("=" * 60)
    print("\nThis demo shows how to programmatically test Marcus")
    print("by spawning a separate instance via stdio.")
    print("\nNote: This may take 10-15 seconds to initialize...")

    await demo_stdio_connection()

    print("\n" + "=" * 60)
    print("✅ Demo complete!")
    print("\n💡 Tip: For HTTP connections, use connect_to_marcus_http()")
    print("   But you'll need a Marcus server with external HTTP access configured.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
