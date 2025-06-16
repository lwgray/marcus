#!/usr/bin/env python3
"""
Clean all cards from the board without repopulating
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

# Configuration
BOARD_ID = "1533859887128249584"


async def clean_board_quick():
    """Quick clean - only removes cards, keeps lists"""
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("🧹 Board Cleaner")
    print("=" * 40)
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Get board summary first
            summary_result = await session.call_tool(
                "mcp_kanban_project_board_manager",
                {
                    "action": "get_board_summary",
                    "boardId": BOARD_ID,
                    "includeTaskDetails": False
                }
            )
            summary = json.loads(summary_result.content[0].text)
            
            total_cards = 0
            for lst in summary.get('lists', []):
                total_cards += len(lst.get('cards', []))
            
            if total_cards == 0:
                print("✅ Board is already clean!")
                return
            
            print(f"\nFound {total_cards} cards to remove")
            confirm = input("Continue? (y/n): ").strip().lower()
            
            if confirm != 'y':
                print("❌ Cancelled")
                return
            
            # Delete all cards
            print("\nDeleting cards...")
            deleted = 0
            
            for lst in summary.get('lists', []):
                for card in lst.get('cards', []):
                    try:
                        await session.call_tool(
                            "mcp_kanban_card_manager",
                            {"action": "delete", "id": card['id']}
                        )
                        deleted += 1
                        print(f"  ❌ {card['name']}")
                    except:
                        print(f"  ⚠️  Failed to delete: {card['name']}")
            
            print(f"\n✅ Cleaned {deleted} cards from the board")
            print("\nBoard is now empty and ready for new tasks!")


if __name__ == "__main__":
    asyncio.run(clean_board_quick())