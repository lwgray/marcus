#!/usr/bin/env python3
"""
Simple MCP connection verification script
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp_connection():
    """Test basic MCP server connection"""
    
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"]
    )
    
    try:
        print("🔌 Connecting to MCP server...")
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                print("✅ Connected successfully!")
                
                # List available tools
                tools = await session.list_tools()
                print(f"📋 Found {len(tools.tools)} tools:")
                for tool in tools.tools:
                    print(f"  - {tool.name}")
                
                print("🎉 MCP connection verified!")
                return True
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp_connection())
    exit(0 if success else 1)