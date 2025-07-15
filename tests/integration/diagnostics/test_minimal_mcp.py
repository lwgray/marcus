#!/usr/bin/env python3
"""
Minimal test matching the working pattern
Tests the bare minimum MCP connection setup
"""

import asyncio
import json
import os
import sys

from mcp.client.stdio import stdio_client

from mcp import ClientSession, StdioServerParameters

# Add parent directories to path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Set environment variables
os.environ["PLANKA_BASE_URL"] = "http://localhost:3333"
os.environ["PLANKA_AGENT_EMAIL"] = "demo@demo.demo"
os.environ["PLANKA_AGENT_PASSWORD"] = "demo"


async def test_minimal():
    """Minimal test that should work if kanban-mcp is accessible"""
    print("🔍 Testing Minimal MCP Connection")
    print("=" * 60)

    # Try to find kanban-mcp
    kanban_paths = [
        "../kanban-mcp/dist/index.js",
        "../../kanban-mcp/dist/index.js",
        "../../../kanban-mcp/dist/index.js",
        os.path.expanduser("~/dev/kanban-mcp/dist/index.js"),
    ]

    kanban_path = None
    for path in kanban_paths:
        if os.path.exists(path):
            kanban_path = path
            print(f"Found kanban-mcp at: {path}")
            break

    if not kanban_path:
        print("❌ Could not find kanban-mcp/dist/index.js")
        print("Tried paths:", kanban_paths)
        return

    # Use the working pattern
    server_params = StdioServerParameters(
        command="node", args=[kanban_path], env=os.environ.copy()
    )

    try:
        print("\n1. Connecting to kanban-mcp...")
        async with stdio_client(server_params) as (read, write):
            print("✅ Transport connected")

            print("\n2. Creating session...")
            async with ClientSession(read, write) as session:
                print("✅ Session created")

                print("\n3. Initializing...")
                await session.initialize()
                print("✅ Session initialized")

                print("\n4. Testing API call...")
                result = await session.call_tool(
                    "mcp_kanban_project_board_manager",
                    {"action": "get_projects", "page": 1, "perPage": 5},
                )
                print("✅ Tool called successfully")

                if hasattr(result, "content") and result.content:
                    data = json.loads(result.content[0].text)
                    print(f"\nFound {len(data.get('items', []))} projects")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_minimal())
