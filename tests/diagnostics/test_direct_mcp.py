#!/usr/bin/env python3
"""
Test direct MCP connection to isolate connection issues.

This diagnostic test bypasses all PM Agent wrappers and tests raw MCP connection
to help identify whether connection issues are in the PM Agent layer or the MCP layer.

Notes
-----
This test is useful for troubleshooting when the main application cannot connect
to the MCP server, as it eliminates PM Agent code as a potential cause.
"""

import asyncio
import os
import sys
from typing import Optional, List, Tuple
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def test_direct() -> None:
    """
    Test direct connection to kanban-mcp server.
    
    This function attempts to establish a direct MCP connection, bypassing all
    PM Agent abstractions. It tests multiple node.js paths and kanban-mcp locations
    to ensure maximum compatibility.
    
    Notes
    -----
    The test performs the following steps:
    1. Locates node.js executable
    2. Locates kanban-mcp distribution
    3. Starts the MCP server process
    4. Creates and initializes a session
    5. Makes a test tool call
    
    Examples
    --------
    >>> asyncio.run(test_direct())
    🔍 Testing Direct MCP Connection
    ============================================================
    Using node: /opt/homebrew/bin/node
    Using kanban-mcp: /Users/lwgray/dev/kanban-mcp/dist/index.js
    ..."""
    print("🔍 Testing Direct MCP Connection")
    print("=" * 60)
    
    # Try different node paths
    node_paths = [
        "node",  # System node
        "/opt/homebrew/bin/node",  # Homebrew on M1
        "/usr/local/bin/node",  # Homebrew on Intel
        "/Users/lwgray/.nvm/versions/node/v22.14.0/bin/node"  # NVM
    ]
    
    kanban_paths = [
        "../kanban-mcp/dist/index.js",  # Relative path
        os.path.expanduser("~/dev/kanban-mcp/dist/index.js"),  # Absolute path
    ]
    
    # Find working node
    node_cmd = None
    for path in node_paths:
        if os.path.exists(path) or os.system(f"which {path} > /dev/null 2>&1") == 0:
            node_cmd = path
            break
    
    if not node_cmd:
        print("❌ Could not find node executable")
        return
    
    # Find kanban-mcp
    kanban_path = None
    for path in kanban_paths:
        if os.path.exists(path):
            kanban_path = path
            break
    
    if not kanban_path:
        print("❌ Could not find kanban-mcp/dist/index.js")
        return
    
    print(f"Using node: {node_cmd}")
    print(f"Using kanban-mcp: {kanban_path}")
    
    server_params = StdioServerParameters(
        command=node_cmd,
        args=[kanban_path],
        env={
            "PLANKA_BASE_URL": "http://localhost:3333",
            "PLANKA_AGENT_EMAIL": "demo@demo.demo",
            "PLANKA_AGENT_PASSWORD": "demo"
        }
    )
    
    print("\n1. Starting kanban-mcp process...")
    try:
        async with asyncio.timeout(10):  # 10 second timeout
            async with stdio_client(server_params) as (read, write):
                print("✅ Process started")
                
                print("\n2. Creating session...")
                async with ClientSession(read, write) as session:
                    print("✅ Session created")
                    
                    print("\n3. Initializing session...")
                    await session.initialize()
                    print("✅ Session initialized")
                    
                    print("\n4. Calling tool...")
                    result = await session.call_tool(
                        "mcp_kanban_project_board_manager",
                        {"action": "get_projects", "page": 1, "perPage": 5}
                    )
                    print("✅ Tool called successfully")
                    
                    if hasattr(result, 'content') and result.content:
                        print(f"\nResult: {result.content[0].text[:200]}...")
                    
    except asyncio.TimeoutError:
        print("❌ Connection timed out!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_direct())