#!/usr/bin/env python3
"""
Test PM Agent MCP Server
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_pm_agent():
    """Test PM Agent MCP server"""
    print("🧪 Testing PM Agent MCP Server...")
    
    # Connect to PM Agent MCP server
    server_params = StdioServerParameters(
        command="python",
        args=["pm_agent_mcp_server_v2.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List available tools
            print("\n📋 Available PM Agent tools:")
            tools = await session.list_tools()
            for tool in tools:
                print(f"   - {tool.name}: {tool.description}")
            
            # Test ping
            print("\n🏓 Testing ping...")
            result = await session.call_tool("ping", {"echo": "Hello PM Agent!"})
            if result.content:
                response = json.loads(result.content[0].text)
                print(f"   Response: {response}")
            
            # Register a test agent
            print("\n👤 Registering test agent...")
            result = await session.call_tool("register_agent", {
                "agent_id": "test-agent-001",
                "name": "Test Developer",
                "role": "Backend Developer",
                "skills": ["python", "api", "testing"]
            })
            if result.content:
                response = json.loads(result.content[0].text)
                print(f"   Response: {response}")
            
            # Request a task
            print("\n📋 Requesting task...")
            result = await session.call_tool("request_next_task", {
                "agent_id": "test-agent-001"
            })
            if result.content:
                response = json.loads(result.content[0].text)
                print(f"   Response: {response}")
            
            # Get project status
            print("\n📊 Getting project status...")
            result = await session.call_tool("get_project_status", {})
            if result.content:
                response = json.loads(result.content[0].text)
                print(f"   Response: {json.dumps(response, indent=2)}")


if __name__ == "__main__":
    asyncio.run(test_pm_agent())