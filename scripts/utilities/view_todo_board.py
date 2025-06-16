#!/usr/bin/env python3
"""
View the current state of the Todo App board
"""

import asyncio
import json
import os
from datetime import datetime
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'

BOARD_ID = "1533859887128249584"


async def view_board():
    """Display board in a nice format"""
    
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
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
                    "includeTaskDetails": True,
                    "includeComments": True
                }
            )
            
            summary = json.loads(result.content[0].text)
            
            print("\n" + "=" * 80)
            print(f"📋 TODO APP BOARD - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            print("=" * 80)
            
            # Stats
            stats = summary.get('stats', {})
            print(f"\n📊 Statistics:")
            print(f"   Total Cards: {stats.get('totalCards', 0)}")
            print(f"   Completion: {stats.get('completionPercentage', 0)}%")
            
            # Lists and cards
            print(f"\n🗂️  Lists:\n")
            
            for lst in summary.get('lists', []):
                cards = lst.get('cards', [])
                print(f"{lst['name'].upper()} ({len(cards)} cards)")
                print("-" * 40)
                
                if cards:
                    for card in cards:
                        # Card name with labels
                        labels = card.get('labels', [])
                        label_str = " ".join([f"[{l['name']}]" for l in labels])
                        print(f"  📌 {card['name']} {label_str}")
                        
                        # Tasks
                        tasks = card.get('tasks', [])
                        if tasks:
                            completed = sum(1 for t in tasks if t.get('isCompleted'))
                            print(f"     Tasks: {completed}/{len(tasks)} completed")
                            for task in tasks[:3]:  # Show first 3 tasks
                                status = "✅" if task.get('isCompleted') else "⬜"
                                print(f"     {status} {task['name']}")
                            if len(tasks) > 3:
                                print(f"     ... and {len(tasks) - 3} more tasks")
                        
                        # Time tracking
                        if card.get('stopwatch'):
                            print(f"     ⏱️  Time tracked: {card['stopwatch'].get('total', 0)} seconds")
                        
                        print()
                else:
                    print("  (empty)\n")
            
            print("=" * 80)
            print("💡 Run 'python interactive_test.py' to modify the board")
            print("🌐 View in browser: http://localhost:3333")


if __name__ == "__main__":
    asyncio.run(view_board())