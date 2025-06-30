#!/usr/bin/env python3
"""
Test environment variables and label creation
"""

import asyncio
import json
import os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

# Import to trigger environment setup
from src.integrations.mcp_kanban_client_simple import SimpleMCPKanbanClient


async def test_env_and_labels():
    """Test environment variables and label creation"""
    
    # Create client to trigger env setup
    print("1. Creating SimpleMCPKanbanClient to load config...")
    client = SimpleMCPKanbanClient()
    
    # Check environment
    print("\n2. Checking environment variables:")
    print(f"   PLANKA_BASE_URL: {os.environ.get('PLANKA_BASE_URL', 'NOT SET')}")
    print(f"   PLANKA_AGENT_EMAIL: {os.environ.get('PLANKA_AGENT_EMAIL', 'NOT SET')}")
    print(f"   PLANKA_AGENT_PASSWORD: {'SET' if os.environ.get('PLANKA_AGENT_PASSWORD') else 'NOT SET'}")
    
    board_id = client.board_id or "1533859887128249584"
    print(f"   Board ID: {board_id}")
    
    # Now test label creation
    print("\n3. Testing label creation with MCP...")
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()  # Pass the environment with credentials
    )
    
    # Debug: print what we're passing
    print(f"\n4. Environment being passed to MCP:")
    print(f"   PLANKA_BASE_URL: {server_params.env.get('PLANKA_BASE_URL', 'NOT IN ENV')}")
    print(f"   PLANKA_AGENT_EMAIL: {server_params.env.get('PLANKA_AGENT_EMAIL', 'NOT IN ENV')}")
    print(f"   PLANKA_AGENT_PASSWORD: {'IN ENV' if server_params.env.get('PLANKA_AGENT_PASSWORD') else 'NOT IN ENV'}")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Try to create a label
            print("\n5. Creating label...")
            result = await session.call_tool(
                "mcp_kanban_label_manager",
                {
                    "action": "create",
                    "boardId": board_id,
                    "name": "test-backend",
                    "color": "berry-red",
                    "position": 65536
                }
            )
            
            if hasattr(result, 'content') and result.content:
                response = result.content[0].text
                print(f"   Response: {response}")
                
                try:
                    label_data = json.loads(response)
                    print(f"   Success! Label created with ID: {label_data.get('id')}")
                except:
                    print(f"   Failed: {response}")


if __name__ == "__main__":
    try:
        asyncio.run(test_env_and_labels())
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()