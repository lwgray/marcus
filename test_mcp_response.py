#!/usr/bin/env python3
"""
Test MCP response format
"""

import asyncio
import json
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Set environment variables
os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'


async def test_mcp_response():
    """Test MCP response format"""
    
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("🚀 Testing MCP response format...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("✅ Connected to kanban-mcp")
            
            # Test get projects
            print("\n📋 Getting projects...")
            result = await session.call_tool("mcp_kanban_project_board_manager", {
                "action": "get_projects",
                "page": 1,
                "perPage": 25
            })
            
            print(f"\nResponse type: {type(result)}")
            print(f"Response content: {result.content}")
            
            # Extract the actual content
            if result.content:
                content = result.content[0].text
                print(f"\nContent type: {type(content)}")
                print(f"Content: {content}")
                
                # Try to parse if it's JSON string
                if isinstance(content, str):
                    try:
                        parsed = json.loads(content)
                        print(f"\nParsed type: {type(parsed)}")
                        print(f"Parsed content: {json.dumps(parsed, indent=2)}")
                    except:
                        print("Not JSON")


if __name__ == "__main__":
    asyncio.run(test_mcp_response())