#!/usr/bin/env python3
"""Debug Kanban connection error"""

import asyncio
import traceback
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def debug_kanban():
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"]
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ Connected to Kanban MCP")
                
                # Get projects
                try:
                    result = await session.call_tool("mcp_kanban_project_board_manager", {
                        "action": "get_projects",
                        "page": 1,
                        "perPage": 25
                    })
                    print(f"Result type: {type(result)}")
                    print(f"Result: {result}")
                except Exception as e:
                    print(f"Error calling tool: {e}")
                    traceback.print_exc()
                    
    except Exception as e:
        print(f"Connection error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_kanban())