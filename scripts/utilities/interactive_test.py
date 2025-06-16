#!/usr/bin/env python3
"""
Interactive test menu for PM Agent
"""

import asyncio
import json
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Set environment
os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'

BOARD_ID = "1533859887128249584"


async def interactive_test():
    """Interactive testing menu"""
    
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Connected to kanban-mcp\n")
            
            while True:
                print("\n🧪 PM Agent Test Menu")
                print("=" * 40)
                print("1. View board summary")
                print("2. List all cards")
                print("3. Create a test card")
                print("4. Add a comment to a card")
                print("5. Start/stop time tracking")
                print("6. Complete a task")
                print("7. Move a card")
                print("8. Exit")
                
                choice = input("\nSelect option (1-8): ").strip()
                
                try:
                    if choice == "1":
                        # Board summary
                        result = await session.call_tool(
                            "mcp_kanban_project_board_manager",
                            {
                                "action": "get_board_summary",
                                "boardId": BOARD_ID,
                                "includeTaskDetails": True
                            }
                        )
                        summary = json.loads(result.content[0].text)
                        print(f"\n📊 Board Summary:")
                        print(f"Lists: {len(summary.get('lists', []))}")
                        for lst in summary.get('lists', []):
                            print(f"  - {lst['name']}: {len(lst.get('cards', []))} cards")
                    
                    elif choice == "2":
                        # List cards
                        result = await session.call_tool(
                            "mcp_kanban_project_board_manager",
                            {
                                "action": "get_board_summary",
                                "boardId": BOARD_ID,
                                "includeTaskDetails": False
                            }
                        )
                        summary = json.loads(result.content[0].text)
                        print("\n📋 All Cards:")
                        for lst in summary.get('lists', []):
                            if lst.get('cards'):
                                print(f"\n{lst['name']}:")
                                for card in lst['cards']:
                                    print(f"  - {card['name']} (ID: {card['id'][:8]}...)")
                    
                    elif choice == "3":
                        # Create card
                        list_name = input("List name (Backlog/In Progress/Testing/Done): ")
                        card_name = input("Card name: ")
                        
                        # Find list ID
                        result = await session.call_tool(
                            "mcp_kanban_list_manager",
                            {"action": "get_all", "boardId": BOARD_ID}
                        )
                        lists = json.loads(result.content[0].text)
                        list_id = None
                        for lst in lists:
                            if lst['name'].lower() == list_name.lower():
                                list_id = lst['id']
                                break
                        
                        if list_id:
                            result = await session.call_tool(
                                "mcp_kanban_card_manager",
                                {
                                    "action": "create",
                                    "listId": list_id,
                                    "name": card_name,
                                    "position": 65536
                                }
                            )
                            card = json.loads(result.content[0].text)
                            print(f"✅ Created card: {card['name']}")
                        else:
                            print(f"❌ List '{list_name}' not found")
                    
                    elif choice == "4":
                        # Add comment
                        card_id = input("Card ID (or first 8 chars): ")
                        comment = input("Comment: ")
                        
                        # Find full card ID if partial
                        if len(card_id) < 16:
                            result = await session.call_tool(
                                "mcp_kanban_project_board_manager",
                                {
                                    "action": "get_board_summary",
                                    "boardId": BOARD_ID,
                                    "includeTaskDetails": False
                                }
                            )
                            summary = json.loads(result.content[0].text)
                            for lst in summary.get('lists', []):
                                for card in lst.get('cards', []):
                                    if card['id'].startswith(card_id):
                                        card_id = card['id']
                                        break
                        
                        result = await session.call_tool(
                            "mcp_kanban_comment_manager",
                            {
                                "action": "create",
                                "cardId": card_id,
                                "text": comment
                            }
                        )
                        print("✅ Comment added")
                    
                    elif choice == "8":
                        print("\n👋 Goodbye!")
                        break
                    
                    else:
                        print("⚠️  Feature not implemented in this demo")
                
                except Exception as e:
                    print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("🚀 PM Agent Interactive Test")
    print("Make sure kanban-mcp is running!\n")
    asyncio.run(interactive_test())