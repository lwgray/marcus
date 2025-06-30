#!/usr/bin/env python3
"""
Test script for Marcus MCP server tools.

This script tests the MCP tools in order to verify the fixes are working.
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_tool(session: ClientSession, tool_name: str, arguments: Optional[Dict[str, Any]] = None):
    """Test a single MCP tool and return the result."""
    print(f"\n{'='*60}")
    print(f"Testing tool: {tool_name}")
    print(f"Arguments: {arguments if arguments else 'None'}")
    print('-'*60)
    
    try:
        result = await session.call_tool(tool_name, arguments=arguments or {})
        print(f"✅ Success!")
        print(f"Result: {json.dumps(result.content, indent=2)}")
        return True, result.content
    except Exception as e:
        print(f"❌ Failed!")
        print(f"Error: {str(e)}")
        return False, str(e)


async def run_tests():
    """Run all MCP tool tests."""
    # Start the Marcus MCP server
    server_params = StdioServerParameters(
        command="python",
        args=[str(Path(__file__).parent / "marcus.py")],
        env=None
    )
    
    print("Starting Marcus MCP server...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("\nMarcus MCP server initialized successfully!")
            print(f"Available tools: {[tool.name for tool in session.tools]}")
            
            # Test 1: ping - Basic connectivity test
            success, result = await test_tool(session, "ping", {"echo": "Hello Marcus!"})
            
            # Test 2: get_project_status - Should return project metrics
            success, result = await test_tool(session, "get_project_status")
            
            # Test 3: list_registered_agents - Should list any registered agents
            success, result = await test_tool(session, "list_registered_agents")
            
            # Test 4: register_agent - Register a test agent
            success, result = await test_tool(session, "register_agent", {
                "agent_id": "test_agent_001",
                "name": "Test Agent",
                "role": "Backend Developer",
                "skills": ["Python", "Testing", "MCP"]
            })
            
            # Test 5: request_next_task - Request a task for the test agent
            success, result = await test_tool(session, "request_next_task", {
                "agent_id": "test_agent_001"
            })
            
            print(f"\n{'='*60}")
            print("All tests completed!")


if __name__ == "__main__":
    asyncio.run(run_tests())