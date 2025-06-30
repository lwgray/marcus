#!/usr/bin/env python3
"""
Test creating labels with the required position parameter
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


async def test_label_creation_with_position():
    """Test creating labels with all required parameters"""
    
    board_id = "1533859887128249584"
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("=== Testing Label Creation with Position ===\n")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Test creating a label with position
            print("1. Creating label with all required params...")
            result = await session.call_tool(
                "mcp_kanban_label_manager",
                {
                    "action": "create",
                    "boardId": board_id,
                    "name": "backend",
                    "color": "berry-red",
                    "position": 65536  # Standard position increment
                }
            )
            
            print(f"   Response type: {type(result)}")
            if hasattr(result, 'content') and result.content:
                response_text = result.content[0].text
                print(f"   Response: {response_text}")
                
                # Try to parse the response
                try:
                    label_data = json.loads(response_text)
                    print(f"   Created label: {json.dumps(label_data, indent=2)}")
                except:
                    print(f"   Raw response: {response_text}")
            
            # Test adding label to a card
            # First, get a card to test with
            print("\n2. Getting a card to test with...")
            lists_result = await session.call_tool(
                "mcp_kanban_list_manager",
                {
                    "action": "get_all",
                    "boardId": board_id
                }
            )
            
            if lists_result and hasattr(lists_result, 'content'):
                lists_data = json.loads(lists_result.content[0].text)
                if lists_data:
                    first_list = lists_data[0]
                    
                    # Get cards from first list
                    cards_result = await session.call_tool(
                        "mcp_kanban_card_manager",
                        {
                            "action": "get_all",
                            "listId": first_list["id"]
                        }
                    )
                    
                    if cards_result and hasattr(cards_result, 'content'):
                        cards_data = json.loads(cards_result.content[0].text)
                        if cards_data:
                            test_card = cards_data[0]
                            print(f"   Found card: {test_card['name']} (ID: {test_card['id']})")
                            
                            # Now test adding the label to the card
                            print("\n3. Adding label to card...")
                            if 'label_data' in locals() and 'id' in label_data:
                                add_result = await session.call_tool(
                                    "mcp_kanban_label_manager",
                                    {
                                        "action": "add_to_card",
                                        "cardId": test_card["id"],
                                        "labelId": label_data["id"]
                                    }
                                )
                                
                                print(f"   Add result: {add_result.content[0].text if add_result.content else 'No content'}")


if __name__ == "__main__":
    try:
        asyncio.run(test_label_creation_with_position())
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()