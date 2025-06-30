#!/usr/bin/env python3
"""
Fix MCP get_project_status by testing the actual kanban-mcp connection
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

# Load config
with open('config_marcus.json', 'r') as f:
    config = json.load(f)

# Set environment variables
os.environ['PLANKA_BASE_URL'] = config['planka']['base_url']
os.environ['PLANKA_AGENT_EMAIL'] = config['planka']['email']
os.environ['PLANKA_AGENT_PASSWORD'] = config['planka']['password']

board_id = config['board_id']

async def test_kanban_mcp_directly():
    """Test kanban-mcp server directly to see what's failing"""
    
    print("=== Testing kanban-mcp Server Directly ===\n")
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print(f"Environment variables set:")
    print(f"  PLANKA_BASE_URL: {os.environ.get('PLANKA_BASE_URL')}")
    print(f"  PLANKA_AGENT_EMAIL: {os.environ.get('PLANKA_AGENT_EMAIL')}")
    print(f"  Board ID: {board_id}")
    print()
    
    try:
        print("1. Connecting to kanban-mcp server...")
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                print("   ✓ Connected to kanban-mcp")
                
                print("\n2. Initializing session...")
                await session.initialize()
                print("   ✓ Session initialized")
                
                print("\n3. Testing list retrieval...")
                lists_result = await session.call_tool(
                    "mcp_kanban_list_manager",
                    {
                        "action": "get_all",
                        "boardId": board_id
                    }
                )
                
                if lists_result and hasattr(lists_result, 'content') and lists_result.content:
                    lists_data = json.loads(lists_result.content[0].text)
                    print(f"   ✓ Retrieved {len(lists_data)} lists successfully")
                    
                    # Test card retrieval from first list
                    if lists_data:
                        first_list = lists_data[0]
                        print(f"\n4. Testing card retrieval from list '{first_list.get('name')}'...")
                        
                        cards_result = await session.call_tool(
                            "mcp_kanban_card_manager",
                            {
                                "action": "get_all",
                                "listId": first_list['id']
                            }
                        )
                        
                        if cards_result and hasattr(cards_result, 'content') and cards_result.content:
                            cards_text = cards_result.content[0].text
                            if cards_text and cards_text.strip():
                                cards_data = json.loads(cards_text)
                                card_count = len(cards_data) if isinstance(cards_data, list) else len(cards_data.get("items", []))
                                print(f"   ✓ Retrieved {card_count} cards successfully")
                            else:
                                print("   ⚠️  No cards found in list")
                        else:
                            print("   ✗ Failed to retrieve cards")
                    
                    print(f"\n✅ kanban-mcp server is working correctly!")
                    print("   The issue must be in Marcus MCP server initialization")
                    
                else:
                    print("   ✗ Failed to retrieve lists - this might be the 'Not initialized' source")
                    
    except Exception as e:
        print(f"\n❌ kanban-mcp connection failed: {e}")
        print("\nThis is likely the source of the 'Not initialized' error")
        print("Check:")
        print("- Is kanban-mcp server built? (npm run build)")
        print("- Is Planka running on localhost:3333?")
        print("- Are the credentials correct?")


if __name__ == "__main__":
    asyncio.run(test_kanban_mcp_directly())