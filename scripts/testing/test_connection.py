#!/usr/bin/env python3
"""Test MCP connection to kanban server"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set Planka credentials
os.environ["PLANKA_BASE_URL"] = "http://localhost:3333"
os.environ["PLANKA_AGENT_EMAIL"] = "demo@demo.demo"
os.environ["PLANKA_AGENT_PASSWORD"] = "demo"

async def test_connection():
    from mcp import ClientSession, StdioServerParameters
    from mcp import stdio_client
    
    print("Testing MCP connection...")
    print(f"Command: {os.environ.get('KANBAN_MCP_COMMAND', 'node')}")
    print(f"Args: {os.environ.get('KANBAN_MCP_ARGS', '../kanban-mcp/dist/index.js')}")
    
    # Get command and args
    command = os.environ.get("KANBAN_MCP_COMMAND", "node")
    args = os.environ.get("KANBAN_MCP_ARGS", "../kanban-mcp/dist/index.js").split()
    
    server_params = StdioServerParameters(
        command=command,
        args=args,
        env={
            **os.environ,
            "PLANKA_BASE_URL": "http://localhost:3333",
            "PLANKA_AGENT_EMAIL": "demo@demo.demo", 
            "PLANKA_AGENT_PASSWORD": "demo"
        }
    )
    
    try:
        print("Creating stdio client...")
        transport = stdio_client(server_params)
        
        print("Connecting to transport...")
        read, write = await transport.__aenter__()
        
        print("Creating session...")
        session = ClientSession(read, write)
        
        print("Initializing session...")
        await session.initialize()
        
        print("✅ Connection successful!")
        
        # Try to list projects
        print("\nTesting MCP tool call...")
        result = await session.call_tool("mcp_kanban_project_board_manager", {
            "action": "get_projects"
        })
        
        print(f"Result: {result}")
        
        # Cleanup
        await transport.__aexit__(None, None, None)
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())