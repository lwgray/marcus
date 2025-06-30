#!/usr/bin/env python3
"""
Check if labels exist on the board
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

# Import to setup environment
from src.integrations.mcp_kanban_client_simple import SimpleMCPKanbanClient


async def check_labels():
    """Check what labels exist on the board"""
    
    # Setup environment
    client = SimpleMCPKanbanClient()
    board_id = "1533859887128249584"
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Get all labels
            print("1. Getting all labels on the board...")
            result = await session.call_tool(
                "mcp_kanban_label_manager",
                {
                    "action": "get_all",
                    "boardId": board_id
                }
            )
            
            if result and hasattr(result, 'content'):
                labels_data = json.loads(result.content[0].text)
                print(f"   Found {len(labels_data)} labels")
                
                # Group by name pattern
                label_groups = {}
                for label in labels_data:
                    name = label.get('name', '')
                    if ':' in name:
                        prefix = name.split(':')[0]
                    else:
                        prefix = 'other'
                    
                    if prefix not in label_groups:
                        label_groups[prefix] = []
                    label_groups[prefix].append(label)
                
                # Show summary
                print("\n2. Label Summary by Type:")
                for prefix, labels in sorted(label_groups.items()):
                    print(f"   {prefix}: {len(labels)} labels")
                    for label in labels[:3]:  # Show first 3
                        print(f"     - {label['name']} ({label['color']}) ID: {label['id'][:8]}...")
                    if len(labels) > 3:
                        print(f"     ... and {len(labels) - 3} more")
            
            # Check a specific card for labels
            print("\n3. Checking a specific card...")
            lists_result = await session.call_tool(
                "mcp_kanban_list_manager",
                {
                    "action": "get_all",
                    "boardId": board_id
                }
            )
            
            if lists_result and hasattr(lists_result, 'content'):
                lists_data = json.loads(lists_result.content[0].text)
                for lst in lists_data:
                    if "backlog" in lst.get("name", "").lower():
                        cards_result = await session.call_tool(
                            "mcp_kanban_card_manager",
                            {
                                "action": "get_all",
                                "listId": lst["id"]
                            }
                        )
                        
                        if cards_result and hasattr(cards_result, 'content'):
                            cards_data = json.loads(cards_result.content[0].text)
                            if cards_data:
                                # Check last few cards
                                for card in cards_data[-3:]:
                                    card_labels = card.get('labels', [])
                                    print(f"\n   Card: {card['name'][:50]}...")
                                    print(f"   Labels: {len(card_labels)}")
                                    if card_labels:
                                        for lbl in card_labels:
                                            print(f"     - {lbl.get('name')} ({lbl.get('color')})")
                                break


if __name__ == "__main__":
    try:
        asyncio.run(check_labels())
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()