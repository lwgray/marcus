#!/usr/bin/env python3
"""Test MCP handshake with kanban-mcp"""

import asyncio
import json
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp_handshake():
    """Test MCP handshake step by step"""
    print("🔍 Testing MCP Handshake with Kanban-MCP")
    print("-" * 50)
    
    # Set up environment
    env = {
        **os.environ,
        "PLANKA_BASE_URL": "http://localhost:3333",
        "PLANKA_AGENT_EMAIL": "demo@demo.demo",
        "PLANKA_AGENT_PASSWORD": "demo",
        "PLANKA_ADMIN_EMAIL": "demo@demo.demo"  # Add admin email too
    }
    
    server_params = StdioServerParameters(
        command="/opt/homebrew/bin/node",
        args=["../kanban-mcp/dist/index.js"],
        env=env
    )
    
    print("1. Starting MCP server process...")
    print(f"   Command: {server_params.command}")
    print(f"   Args: {server_params.args}")
    print(f"   Key env vars set: PLANKA_BASE_URL, PLANKA_AGENT_EMAIL, PLANKA_AGENT_PASSWORD")
    
    try:
        # Create the transport
        transport = stdio_client(server_params)
        
        print("\n2. Creating stdio transport...")
        read, write = await transport.__aenter__()
        print("   ✅ Transport created")
        
        print("\n3. Creating client session...")
        session = ClientSession(read, write)
        print("   ✅ Session created")
        
        print("\n4. Initializing session (MCP handshake)...")
        # This is where it usually hangs
        await asyncio.wait_for(session.initialize(), timeout=10)
        print("   ✅ Session initialized!")
        
        print("\n5. Testing tool listing...")
        tools = await session.list_tools()
        print(f"   ✅ Found {len(tools.tools)} tools:")
        for tool in tools.tools[:3]:  # Show first 3
            print(f"      - {tool.name}")
        
        print("\n6. Testing a simple tool call...")
        result = await session.call_tool("mcp_kanban_project_board_manager", {
            "action": "get_projects",
            "page": 1,
            "perPage": 10
        })
        print("   ✅ Tool call successful!")
        
        # Cleanup
        await transport.__aexit__(None, None, None)
        print("\n✅ All tests passed!")
        
    except asyncio.TimeoutError:
        print("\n❌ TIMEOUT: Session initialization took too long")
        print("\nPossible issues:")
        print("- The kanban-mcp server might be failing to start")
        print("- There might be an error in the MCP handshake")
        print("- The server might be waiting for input we're not providing")
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_handshake())