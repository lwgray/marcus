#!/usr/bin/env python3
"""
Fixed version of board selector
"""

import asyncio
import json
import sys
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Set environment variables first
os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'

PROJECT_ID = "1533678301472621705"


async def select_board():
    """Select a board from the Task Master project"""
    
    # Server parameters for kanban-mcp
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("🔍 Connecting to kanban-mcp...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("✅ Connected to kanban-mcp")
            
            # Get boards for the project
            print(f"\n📋 Getting boards for project {PROJECT_ID}...")
            
            result = await session.call_tool(
                "mcp_kanban_project_board_manager",
                {
                    "action": "get_boards",
                    "projectId": PROJECT_ID
                }
            )
            
            boards = json.loads(result.content[0].text)
            
            if not boards:
                print("❌ No boards found in Task Master project")
                return None
            
            print(f"\nFound {len(boards)} board(s):")
            for i, board in enumerate(boards):
                print(f"\n{i+1}. {board['name']}")
                print(f"   ID: {board['id']}")
                print(f"   Position: {board.get('position', 'N/A')}")
            
            # Select board (auto-select if only one)
            selected_board = boards[0]
            print(f"\n✅ Selected board: {selected_board['name']} (ID: {selected_board['id']})")
            
            # Save configuration
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config_pm_agent.json')
            config = {
                "project_id": PROJECT_ID,
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
            
            # Get board summary - handle potential missing keys
            print("\n📊 Getting board summary...")
            try:
                summary_result = await session.call_tool(
                    "mcp_kanban_project_board_manager",
                    {
                        "action": "get_board_summary",
                        "boardId": selected_board['id'],
                        "includeTaskDetails": True
                    }
                )
                
                summary = json.loads(summary_result.content[0].text)
                print(f"\nBoard Summary:")
                print(f"  Raw data: {json.dumps(summary, indent=2)}")
                
                # Safely access keys
                if 'listCount' in summary:
                    print(f"  Lists: {summary['listCount']}")
                if 'cardCount' in summary:
                    print(f"  Cards: {summary['cardCount']}")
                if 'lists' in summary:
                    print(f"\nLists ({len(summary['lists'])}):")
                    for lst in summary['lists']:
                        print(f"  - {lst.get('name', 'Unknown')} (ID: {lst.get('id', 'Unknown')})")
                        if 'cards' in lst:
                            print(f"    Cards: {len(lst['cards'])}")
                
            except Exception as e:
                print(f"⚠️  Could not get board summary: {e}")
            
            return selected_board


if __name__ == "__main__":
    asyncio.run(select_board())