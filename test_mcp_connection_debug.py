#!/usr/bin/env python3
"""
Debug MCP connection with detailed output
"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient, MCPConnection
import json

async def debug_connection():
    """Debug the connection step by step"""
    client = MCPKanbanClient()
    
    print("🔍 Debugging MCP Connection")
    print("=" * 60)
    
    print(f"\n1. Configuration:")
    print(f"   Node path: {client._find_node_executable()}")
    print(f"   Kanban MCP path: {client._kanban_mcp_path}")
    print(f"   Board ID: {client.board_id}")
    
    print("\n2. Creating MCP connection...")
    
    # Create connection manually to debug
    node_path = client._find_node_executable()
    conn = MCPConnection(
        command=node_path,
        args=[client._kanban_mcp_path],
        env=client._env
    )
    
    try:
        print("3. Starting transport...")
        conn._transport_context = conn.server_params.__dict__  # Debug: show params
        print(f"   Command: {conn.server_params.command}")
        print(f"   Args: {conn.server_params.args}")
        print(f"   Env keys: {list(conn.server_params.env.keys())}")
        
        # Try with timeout
        print("\n4. Opening stdio client...")
        async with asyncio.timeout(10):
            from mcp.client.stdio import stdio_client
            
            async with stdio_client(conn.server_params) as (read, write):
                print("✅ Transport started")
                
                print("\n5. Creating session...")
                from mcp import ClientSession
                session = ClientSession(read, write)
                
                print("6. Initializing session...")
                await session.initialize()
                print("✅ Session initialized")
                
                print("\n7. Testing tool call...")
                result = await session.call_tool(
                    "mcp_kanban_project_board_manager",
                    {"action": "get_projects", "page": 1, "perPage": 5}
                )
                print("✅ Tool call successful")
                
    except asyncio.TimeoutError:
        print("\n❌ Timeout occurred!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_connection())