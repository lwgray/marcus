#!/usr/bin/env python3
"""
Test script to check task details including comments and checklists
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

from src.marcus_mcp.server import MarcusServer
from src.marcus_mcp.handlers import handle_tool_call


async def check_task_details():
    """Check details of recently created tasks"""
    print("Checking task details on the board...")
    
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
                
                # Get cards from the first list
                if lists:
                    first_list = lists[0]
                    cards_result = await session.call_tool(
                        "mcp_kanban_card_manager",
                        {
                            "action": "get_all",
                            "listId": first_list["id"]
                        }
                    )
                    
                    if cards_result and hasattr(cards_result, 'content'):
                        cards_data = json.loads(cards_result.content[0].text)
                        cards = cards_data if isinstance(cards_data, list) else cards_data.get("items", [])
                        
                        # Check first few cards
                        for i, card in enumerate(cards[:2]):
                            print(f"\n--- Card {i+1}: {card.get('name')} ---")
                            print(f"Description: {card.get('description', 'No description')[:100]}...")
                            
                            # Get comments for this card
                            comments_result = await session.call_tool(
                                "mcp_kanban_comment_manager",
                                {
                                    "action": "get_all",
                                    "cardId": card["id"]
                                }
                            )
                            
                            if comments_result and hasattr(comments_result, 'content'):
                                try:
                                    comments_data = json.loads(comments_result.content[0].text)
                                    comments = comments_data if isinstance(comments_data, list) else comments_data.get("items", [])
                                    print(f"Comments: {len(comments)}")
                                    for comment in comments:
                                        print(f"  - {comment.get('text', '')[:100]}...")
                                except:
                                    print("Comments: Unable to parse")
                            
                            # Get checklist items (tasks) for this card
                            tasks_result = await session.call_tool(
                                "mcp_kanban_task_manager",
                                {
                                    "action": "get_all",
                                    "cardId": card["id"]
                                }
                            )
                            
                            if tasks_result and hasattr(tasks_result, 'content'):
                                try:
                                    tasks_data = json.loads(tasks_result.content[0].text)
                                    tasks = tasks_data if isinstance(tasks_data, list) else tasks_data.get("items", [])
                                    print(f"Checklist items: {len(tasks)}")
                                    for task in tasks:
                                        print(f"  ✓ {task.get('name', '')} {'[completed]' if task.get('isCompleted') else ''}")
                                except:
                                    print("Checklist items: Unable to parse")
                            
                            # Get labels for this card
                            print(f"Labels: {card.get('labels', [])} (visual labels on card)")


if __name__ == "__main__":
    try:
        asyncio.run(check_task_details())
    except Exception as e:
        print(f"\nError occurred: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()