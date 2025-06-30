#!/usr/bin/env python3
"""
Direct test of Marcus MCP server tools without using MCP client.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.marcus_mcp.server import MarcusServer
from src.marcus_mcp.handlers import handle_tool_call


async def test_tool(server: MarcusServer, tool_name: str, arguments: dict = None):
    """Test a single tool and display results."""
    print(f"\n{'='*60}")
    print(f"Testing tool: {tool_name}")
    print(f"Arguments: {json.dumps(arguments, indent=2) if arguments else 'None'}")
    print('-'*60)
    
    try:
        result = await handle_tool_call(tool_name, arguments, server)
        result_text = result[0].text if result else "No result"
        result_data = json.loads(result_text) if result_text != "No result" else {}
        
        if "error" in result_data:
            print(f"❌ Failed!")
            print(f"Error: {result_data['error']}")
            return False, result_data
        else:
            print(f"✅ Success!")
            print(f"Result: {json.dumps(result_data, indent=2)}")
            return True, result_data
            
    except Exception as e:
        print(f"❌ Failed with exception!")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, str(e)


async def run_tests():
    """Run all MCP tool tests directly."""
    print("Initializing Marcus server...")
    server = MarcusServer()
    
    print("\nRunning MCP tool tests...\n")
    
    # Test 1: ping - Basic connectivity test
    success, result = await test_tool(server, "ping", {"echo": "Hello Marcus!"})
    
    # Test 2: get_project_status - Should return project metrics
    success, result = await test_tool(server, "get_project_status")
    
    # Test 3: list_registered_agents - Should list any registered agents
    success, result = await test_tool(server, "list_registered_agents")
    
    # Test 4: register_agent - Register a test agent
    success, result = await test_tool(server, "register_agent", {
        "agent_id": "test_agent_001",
        "name": "Test Agent",
        "role": "Backend Developer",
        "skills": ["Python", "Testing", "MCP"]
    })
    
    # Test 5: request_next_task - Request a task for the test agent
    success, result = await test_tool(server, "request_next_task", {
        "agent_id": "test_agent_001"
    })
    
    print(f"\n{'='*60}")
    print("All tests completed!")
    
    # Close the realtime log
    server.realtime_log.close()


if __name__ == "__main__":
    asyncio.run(run_tests())