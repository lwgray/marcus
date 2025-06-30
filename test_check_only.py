#!/usr/bin/env python3
"""
Just check existing task details without creating new ones
"""

import asyncio
import sys
import json
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


async def check_existing_tasks():
    """Check the task details of existing cards"""
    
    print("Checking existing task details...")
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Get all lists
            lists_result = await session.call_tool(
                "mcp_kanban_list_manager",
                {
                    "action": "get_all",
                    "boardId": "1533859887128249584"
                }
            )
            
            if lists_result and hasattr(lists_result, 'content'):
                lists_data = json.loads(lists_result.content[0].text)
                lists = lists_data if isinstance(lists_data, list) else lists_data.get("items", [])
                
                # Find the TODO/Backlog list
                target_list = None
                for lst in lists:
                    if "todo" in lst.get("name", "").lower() or "backlog" in lst.get("name", "").lower():
                        target_list = lst
                        break
                
                if target_list:
                    print(f"\nChecking cards in list: {target_list['name']}")
                    
                    # Get cards from the TODO list
                    cards_result = await session.call_tool(
                        "mcp_kanban_card_manager",
                        {
                            "action": "get_all",
                            "listId": target_list["id"]
                        }
                    )
                    
                    if cards_result and hasattr(cards_result, 'content'):
                        cards_data = json.loads(cards_result.content[0].text)
                        cards = cards_data if isinstance(cards_data, list) else cards_data.get("items", [])
                        
                        print(f"Found {len(cards)} cards")
                        
                        # Find cards with "Implement Non-Functional Requirements" in the name
                        matching_cards = []
                        for card in cards:
                            if "Non-Functional" in card.get('name', ''):
                                matching_cards.append(card)
                        
                        print(f"Found {len(matching_cards)} cards with 'Non-Functional' in name")
                        
                        for card in matching_cards[:1]:  # Check first matching card
                            print(f"\n{'='*60}")
                            print(f"Card: {card.get('name')}")
                            print(f"Card ID: {card.get('id')}")
                            print(f"{'='*60}")
                            
                            # Get checklist items with full debug
                            print("\nGetting checklist items...")
                            tasks_result = await session.call_tool(
                                "mcp_kanban_task_manager",
                                {
                                    "action": "get_all",
                                    "cardId": card["id"]
                                }
                            )
                            
                            print(f"Response type: {type(tasks_result)}")
                            print(f"Has content: {hasattr(tasks_result, 'content')}")
                            
                            if tasks_result and hasattr(tasks_result, 'content'):
                                print(f"Content length: {len(tasks_result.content)}")
                                if tasks_result.content:
                                    raw_text = tasks_result.content[0].text
                                    print(f"Raw response: {raw_text[:200]}...")
                                    
                                    try:
                                        tasks_data = json.loads(raw_text)
                                        print(f"Parsed type: {type(tasks_data)}")
                                        
                                        if isinstance(tasks_data, list):
                                            print(f"Direct list with {len(tasks_data)} items")
                                            for i, task in enumerate(tasks_data[:3]):
                                                print(f"  Task {i}: {task}")
                                        elif isinstance(tasks_data, dict):
                                            print(f"Dict with keys: {list(tasks_data.keys())}")
                                            if 'items' in tasks_data:
                                                items = tasks_data['items']
                                                print(f"Found {len(items)} items")
                                                for i, task in enumerate(items[:3]):
                                                    print(f"  Task {i}: {task}")
                                    except Exception as e:
                                        print(f"Parse error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(check_existing_tasks())
    except Exception as e:
        print(f"\nError occurred: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()