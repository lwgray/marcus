#!/usr/bin/env python3
"""
Simple test to confirm kanban-mcp works
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


async def simple_test():
    """Simple connection test"""
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("Testing kanban-mcp connection...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Connected successfully!")
            
            # List projects
            result = await session.call_tool(
                "mcp_kanban_project_board_manager",
                {"action": "get_projects"}
            )
            
            projects = json.loads(result.content[0].text)
            print(f"\n📁 Found {len(projects)} projects:")
            for p in projects:
                print(f"  - {p['name']}")
            
            print("\n✅ kanban-mcp is working correctly!")
            print("\n🎉 You don't need to start it manually - it works automatically!")


if __name__ == "__main__":
    asyncio.run(simple_test())