#!/usr/bin/env python3
"""
Clear all cards from the Task Master Test board
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


async def clear_board():
    """Clear all cards from the Task Master Test board"""
    
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("🧹 Board Cleaner for Task Master Test")
    print("=" * 50)
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Find Task Master Test project
            print("\n📋 Finding Task Master Test project...")
            result = await session.call_tool("mcp_kanban_project_board_manager", {
                "action": "get_projects",
                "page": 1,
                "perPage": 25
            })
            
            projects_data = json.loads(result.content[0].text)
            project_id = None
            board_id = None
            
            for project in projects_data["items"]:
                if project["name"] == "Task Master Test":
                    project_id = project["id"]
                    print(f"✅ Found project: {project['name']} (ID: {project_id})")
                    break
            
            if not project_id:
                print("❌ Task Master Test project not found!")
                return
            
            # Find the board
            if "boards" in projects_data.get("included", {}):
                for board in projects_data["included"]["boards"]:
                    if board["projectId"] == project_id:
                        board_id = board["id"]
                        print(f"✅ Found board: {board['name']} (ID: {board_id})")
                        break
            
            if not board_id:
                print("❌ No board found for Task Master Test!")
                return
            
            # Get board summary
            summary_result = await session.call_tool(
                "mcp_kanban_project_board_manager",
                {
                    "action": "get_board_summary",
                    "boardId": board_id,
                    "includeTaskDetails": False
                }
            )
            summary = json.loads(summary_result.content[0].text)
            
            total_cards = 0
            cards_to_delete = []
            
            for lst in summary.get('lists', []):
                list_cards = lst.get('cards', [])
                total_cards += len(list_cards)
                for card in list_cards:
                    cards_to_delete.append({
                        'id': card['id'],
                        'name': card['name'],
                        'list': lst['name']
                    })
            
            if total_cards == 0:
                print("\n✅ Board is already clean!")
                return
            
            print(f"\n📊 Found {total_cards} cards to remove:")
            
            # Group by list for better display
            lists_summary = {}
            for card in cards_to_delete:
                if card['list'] not in lists_summary:
                    lists_summary[card['list']] = 0
                lists_summary[card['list']] += 1
            
            for list_name, count in lists_summary.items():
                print(f"   • {list_name}: {count} cards")
            
            # Delete all cards
            print("\n🗑️  Deleting cards...")
            deleted = 0
            
            for card in cards_to_delete:
                try:
                    await session.call_tool(
                        "mcp_kanban_card_manager",
                        {"action": "delete", "id": card['id']}
                    )
                    deleted += 1
                    print(f"   ❌ Deleted: {card['name']}")
                except Exception as e:
                    print(f"   ⚠️  Failed to delete: {card['name']} - {str(e)}")
            
            print(f"\n✅ Successfully cleaned {deleted} cards from the board!")
            print("🎯 Board is now empty and ready for new tasks!")


async def clear_board_silent():
    """Clear board without prompts (for use by menu)"""
    
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Find Task Master Test project
            result = await session.call_tool("mcp_kanban_project_board_manager", {
                "action": "get_projects",
                "page": 1,
                "perPage": 25
            })
            
            projects_data = json.loads(result.content[0].text)
            project_id = None
            board_id = None
            
            for project in projects_data["items"]:
                if project["name"] == "Task Master Test":
                    project_id = project["id"]
                    break
            
            if not project_id:
                return False, "Task Master Test project not found!"
            
            # Find the board
            if "boards" in projects_data.get("included", {}):
                for board in projects_data["included"]["boards"]:
                    if board["projectId"] == project_id:
                        board_id = board["id"]
                        break
            
            if not board_id:
                return False, "No board found for Task Master Test!"
            
            # Get board summary
            summary_result = await session.call_tool(
                "mcp_kanban_project_board_manager",
                {
                    "action": "get_board_summary",
                    "boardId": board_id,
                    "includeTaskDetails": False
                }
            )
            summary = json.loads(summary_result.content[0].text)
            
            total_cards = 0
            deleted = 0
            
            for lst in summary.get('lists', []):
                for card in lst.get('cards', []):
                    total_cards += 1
                    try:
                        await session.call_tool(
                            "mcp_kanban_card_manager",
                            {"action": "delete", "id": card['id']}
                        )
                        deleted += 1
                    except:
                        pass
            
            return True, f"Deleted {deleted} of {total_cards} cards"


if __name__ == "__main__":
    asyncio.run(clear_board())