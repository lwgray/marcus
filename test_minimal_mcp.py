#!/usr/bin/env python3
"""
Minimal test matching the working quick_board_view.py
"""

import asyncio
import json
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'


async def test_minimal():
    print("Testing minimal MCP connection...")
    
    # Exact same as working script
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            print("✅ Transport connected")
            
            async with ClientSession(read, write) as session:
                print("✅ Session created")
                
                await session.initialize()
                print("✅ Session initialized")
                
                # Test a simple call
                result = await session.call_tool(
                    "mcp_kanban_project_board_manager",
                    {"action": "get_projects", "page": 1, "perPage": 5}
                )
                print("✅ Tool called successfully")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_minimal())