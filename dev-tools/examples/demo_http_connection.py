#!/usr/bin/env python3
"""
Demo: Inspector with HTTP connection (connects to running Marcus instance).

This demonstrates how to connect to an existing Marcus HTTP server,
allowing multiple clients to share the same server instance.
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
    Demo: Connect via HTTP to a running Marcus instance.

    Use this when:
    - You want to connect to an existing Marcus server
    - You want to share state with other clients
    - Multiple workers need to coordinate through the same server

    Prerequisites:
    - Marcus server must be running in HTTP mode
    - Default URL: http://localhost:4299/mcp (agent endpoint)
    - Alternative URLs:
      - http://localhost:4298/mcp (main/human endpoint)
      - http://localhost:4300/mcp (analytics endpoint)
    """
    print("\n" + "=" * 70)
    print("🚀 Inspector HTTP Connection Demo")
    print("=" * 70)
    print("\nConnecting to running Marcus HTTP server...")
    print("Note: Make sure Marcus server is running in HTTP mode!\n")

    client = Inspector(connection_type="http")

    # You can customize the URL here
    url = "http://localhost:4298/mcp"  # Main endpoint (recommended)
    # url = "http://localhost:4299/mcp"  # Agent endpoint (deprecated)
    # url = "http://localhost:4300/mcp"  # Analytics endpoint

    try:
        async with client.connect(url=url) as session:
            # First authenticate as admin to get access to ALL MCP tools
            print("🔐 Authenticating as admin...")
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": "http-test-worker",
                    "client_type": "admin",
                    "role": "admin",
                    "metadata": {"test_mode": True, "connection": "http"},
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
                agent_id="http-test-worker",
                name="HTTP Test Worker",
                role="Developer",
                skills=["python", "fastapi", "testing"],
            )
            pretty_print_result("Agent registered:", result)

            # Request a task
            print("\n📋 Requesting next task...")
            task = await client.request_next_task("http-test-worker")
            pretty_print_result("Task received:", task)

            print("\n" + "=" * 70)
            print("✅ Demo complete!")
            print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Make sure Marcus server is running in HTTP mode")
        print("   2. Start server with: python -m src.marcus_mcp.server --http")
        print(f"   3. Verify the URL is correct: {url}")
        print("   4. Check that the server is configured for external HTTP access")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
