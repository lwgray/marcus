#!/usr/bin/env python3
"""Quick test to verify task request functionality"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_task_request():
    """Test agent registration and task request"""
    server_params = StdioServerParameters(
        command="python",
        args=["pm_agent_mcp_server_v2.py"],
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Test 1: Ping to verify connection
            print("1. Testing ping...")
            result = await session.call_tool("ping", {"echo": "test"})
            print(f"Ping result: {json.loads(result[0].text)}")
            
            # Test 2: Register agent
            print("\n2. Registering agent...")
            result = await session.call_tool("register_agent", {
                "agent_id": "test-agent-001",
                "name": "Test Agent",
                "role": "Developer",
                "skills": ["Python", "JavaScript"]
            })
            print(f"Registration result: {json.loads(result[0].text)}")
            
            # Test 3: Request task
            print("\n3. Requesting task...")
            result = await session.call_tool("request_next_task", {
                "agent_id": "test-agent-001"
            })
            print(f"Task request result: {json.loads(result[0].text)}")
            
            # Test 4: Check project status
            print("\n4. Checking project status...")
            result = await session.call_tool("get_project_status", {})
            print(f"Project status: {json.loads(result[0].text)}")
            
            print("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(test_task_request())