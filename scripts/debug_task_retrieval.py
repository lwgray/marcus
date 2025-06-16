#!/usr/bin/env python3
"""
Debug script to test task retrieval from PM Agent
"""

import asyncio
import json
import sys
sys.path.insert(0, '.')

from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient


async def debug_task_retrieval():
    """Debug why tasks aren't being retrieved"""
    client = MCPKanbanClient()
    
    print("🔍 Debug Task Retrieval")
    print("=" * 60)
    
    print(f"\n📋 Configuration:")
    print(f"   Project ID: {client.project_id}")
    print(f"   Board ID: {client.board_id}")
    
    try:
        print("\n🔗 Connecting to kanban board...")
        async with client.connect() as conn:
            print("✅ Connected successfully")
            
            # Get all cards from the board
            print("\n📑 Getting all cards from board...")
            result = await conn.call_tool("mcp_kanban_card_manager", {
                "action": "get_all",
                "boardId": client.board_id
            })
            
            if hasattr(result, 'content') and result.content:
                data = json.loads(result.content[0].text)
                cards = data if isinstance(data, list) else data.get("items", [])
                
                print(f"\n📊 Found {len(cards)} total cards")
                
                # Debug each card
                for i, card in enumerate(cards):
                    print(f"\n--- Card {i+1} ---")
                    print(f"   ID: {card.get('id')}")
                    print(f"   Name: {card.get('name', card.get('title', 'N/A'))}")
                    print(f"   List Name: {card.get('listName', 'N/A')}")
                    print(f"   List ID: {card.get('listId', 'N/A')}")
                    print(f"   Description: {card.get('description', 'N/A')[:50]}...")
                    
                    # Check if it would be considered available
                    list_name = card.get("listName", "").upper()
                    available_states = ["TODO", "TO DO", "BACKLOG", "READY"]
                    is_available = any(state in list_name for state in available_states)
                    print(f"   Would be available: {is_available}")
                
                # Now test the actual get_available_tasks method
                print("\n\n🔍 Testing get_available_tasks method...")
                available_tasks = await client.get_available_tasks()
                print(f"\n📋 Available tasks: {len(available_tasks)}")
                
                for task in available_tasks:
                    print(f"\n   • {task.name}")
                    print(f"     ID: {task.id}")
                    print(f"     Assigned to: {task.assigned_to}")
                    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_task_retrieval())