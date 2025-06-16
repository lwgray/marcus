#!/usr/bin/env python3
"""
Helper script to find and select the Task Master board
"""

import asyncio
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient


async def find_task_master_boards():
    """Find all boards in the Task Master project"""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    config_path = os.path.join(project_root, 'config_pm_agent.json')
    
    client = MCPKanbanClient()
    client.project_id = "1533678301472621705"
    
    print("🔍 Finding boards in Task Master project...")
    
    async with client.connect() as conn:
        # List all boards
        result = await conn.call_tool("mcp_kanban_project_board_manager", {
            "action": "get_boards",
            "projectId": client.project_id
        })
        
        boards = json.loads(result.content[0].text)
        
        if not boards:
            print("❌ No boards found in Task Master project")
            return None
        
        print(f"\n📋 Found {len(boards)} board(s) in Task Master project:\n")
        
        for i, board in enumerate(boards):
            print(f"{i+1}. {board['name']}")
            print(f"   ID: {board['id']}")
            print(f"   Cards: {board.get('cardCount', 'Unknown')}")
            print()
        
        if len(boards) == 1:
            selected_board = boards[0]
            print(f"✅ Auto-selected the only board: {selected_board['name']}")
        else:
            # Let user choose
            choice = input("Select board number (or press Enter for first board): ").strip()
            if not choice:
                selected_board = boards[0]
            else:
                try:
                    idx = int(choice) - 1
                    selected_board = boards[idx]
                except (ValueError, IndexError):
                    print("❌ Invalid selection, using first board")
                    selected_board = boards[0]
        
        print(f"\n✅ Selected board: {selected_board['name']}")
        print(f"   Board ID: {selected_board['id']}")
        
        # Save configuration
        config = {
            "project_id": client.project_id,
            "project_name": "Task Master Test",
            "board_id": selected_board['id'],
            "board_name": selected_board['name'],
            "auto_find_board": False,
            "planka": {
                "base_url": "http://localhost:3333",
                "email": "demo@demo.demo",
                "password": "demo"
            }
        }
        
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        
        print(f"\n💾 Configuration saved to {config_path}")
        print("\nTo start PM Agent with this configuration:")
        print("  python -m src.enhancements.configurable_pm_agent")
        
        return selected_board


if __name__ == "__main__":
    asyncio.run(find_task_master_boards())