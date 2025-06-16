#!/usr/bin/env python3
"""
Test kanban-mcp as an MCP stdio server
"""

import asyncio
import json
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Set environment
os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'


async def test_kanban_mcp():
    """Test kanban-mcp connection"""
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("🔍 Testing kanban-mcp as MCP stdio server...")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ Successfully connected to kanban-mcp!")
                
                # List available tools
                tools = session.get_available_tools()
                print(f"\n📋 Available tools: {len(tools)}")
                for tool in tools[:3]:  # Show first 3
                    print(f"  - {tool.name}")
                
                # Test listing projects
                result = await session.call_tool(
                    "mcp_kanban_project_board_manager",
                    {"action": "get_projects"}
                )
                
                projects = json.loads(result.content[0].text)
                print(f"\n📁 Found {len(projects)} projects")
                
                return True
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_kanban_mcp())
    if success:
        print("\n✅ kanban-mcp is working correctly as an MCP stdio server!")
        print("\nNote: kanban-mcp is not a standalone server - it's an MCP server")
        print("that communicates via stdio. Your Python scripts connect to it")
        print("automatically when needed.")
    else:
        print("\n❌ Failed to connect to kanban-mcp")