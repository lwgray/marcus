#!/usr/bin/env python3
"""
Test direct MCP connection to isolate the issue
"""

import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_direct():
    """Test direct connection like the working quick_board_view script"""
    print("🔍 Testing Direct MCP Connection")
    print("=" * 60)
    
    # Use same setup as working script
    server_params = StdioServerParameters(
        command="/Users/lwgray/.nvm/versions/node/v22.14.0/bin/node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
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
                    
    except asyncio.TimeoutError:
        print("❌ Connection timed out!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_direct())