#!/usr/bin/env python3
"""Debug script to test kanban-mcp connectivity"""

import asyncio
import json
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Add project to path
sys.path.append('.')

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Set up environment
os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'

async def test_kanban_mcp():
    """Test kanban-mcp server connectivity and list retrieval"""
    
    print("Environment variables:")
    print(f"  PLANKA_BASE_URL: {os.environ.get('PLANKA_BASE_URL')}")
    print(f"  PLANKA_AGENT_EMAIL: {os.environ.get('PLANKA_AGENT_EMAIL')}")
    print(f"  PLANKA_AGENT_PASSWORD: {os.environ.get('PLANKA_AGENT_PASSWORD')}")
    print()
    
    # Load config
    board_id = None
    if os.path.exists('config_marcus.json'):
        with open('config_marcus.json', 'r') as f:
            config = json.load(f)
            board_id = config.get("board_id")
            print(f"Board ID from config: {board_id}")
    
    print("\nStarting kanban-mcp client...")
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            print("Connected to kanban-mcp server")
            
            async with ClientSession(read, write) as session:
                print("Initializing session...")
                await session.initialize()
                print("Session initialized")
                
                # Skip listing tools - not available in this version
                
                # Test getting lists
                print(f"\nGetting lists for board {board_id}...")
                try:
                    result = await session.call_tool(
                        "mcp_kanban_list_manager",
                        {
                            "action": "get_all",
                            "boardId": board_id
                        }
                    )
                    
                    print(f"Result type: {type(result)}")
                    print(f"Has content: {hasattr(result, 'content')}")
                    
                    if result and hasattr(result, 'content') and result.content:
                        print(f"Content length: {len(result.content)}")
                        print(f"First content type: {type(result.content[0])}")
                        
                        text = result.content[0].text
                        print(f"\nRaw response: {text[:500]}...")
                        
                        data = json.loads(text)
                        print(f"\nParsed data type: {type(data)}")
                        
                        if isinstance(data, dict):
                            print(f"Dict keys: {list(data.keys())}")
                            if 'items' in data:
                                print(f"Items count: {len(data['items'])}")
                        elif isinstance(data, list):
                            print(f"List length: {len(data)}")
                            
                except Exception as e:
                    print(f"Error calling tool: {e}")
                    import traceback
                    traceback.print_exc()
                
    except Exception as e:
        print(f"Error connecting to kanban-mcp: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_kanban_mcp())