#!/usr/bin/env python3
"""
Quick view of the current board state
"""

import asyncio
import json
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'

BOARD_ID = "1533859887128249584"


async def quick_view():
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Get board summary
            result = await session.call_tool(
                "mcp_kanban_project_board_manager",
                {
                    "action": "get_board_summary",
                    "boardId": BOARD_ID,
                    "includeTaskDetails": False
                }
            )
            
            summary = json.loads(result.content[0].text)
            
            print("\n🎯 CURRENT BOARD STATE")
            print("=" * 60)
            
            # Show statistics
            stats = summary.get('stats', {})
            print(f"\n📊 Statistics:")
            print(f"  Total Cards: {stats.get('totalCards', 0)}")
            print(f"  Completed: {stats.get('completionPercentage', 0)}%")
            print(f"  In Progress: {stats.get('inProgressCount', 0)}")
            print(f"  Testing: {stats.get('testingCount', 0)}")
            
            # Show cards by list
            print(f"\n📋 Cards by List:")
            for lst in summary.get('lists', []):
                cards = lst.get('cards', [])
                print(f"\n{lst['name']} ({len(cards)} cards):")
                for card in cards[:5]:  # Show first 5 cards
                    print(f"  • {card['name']}")
                if len(cards) > 5:
                    print(f"  ... and {len(cards) - 5} more")
            
            print("\n" + "=" * 60)
            print("✅ Board view complete!")


if __name__ == "__main__":
    asyncio.run(quick_view())