#!/usr/bin/env python3
"""
Test full flow: create project and check task details
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


async def test_full_flow():
    """Test creating a project and checking the resulting task details"""
    
    # Part 1: Create a simple project
    print("Step 1: Creating a simple project...")
    server = MarcusServer()
    await server.initialize_kanban()
    
    result = await handle_tool_call(
        'create_project',
        {
            'project_name': 'Task Quality Test',
            'description': 'Build a simple blog with posts, comments, and user profiles',
            'options': {
                'tech_stack': ['Django', 'PostgreSQL'],
                'team_size': 1
            }
        },
        server
    )
    
    print("Project created:")
    result_data = json.loads(result[0].text)
    print(f"  - Tasks created: {result_data.get('tasks_created')}")
    print(f"  - Success: {result_data.get('success')}")
    
    # Part 2: Check the task details
    print("\n\nStep 2: Checking task details...")
    
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
                        
                        # Filter cards by today's date to get only newly created ones
                        import datetime
                        today = datetime.datetime.now().date()
                        recent_cards = []
                        for card in cards:
                            created_at = card.get('createdAt', '')
                            if created_at and created_at.startswith(str(today)):
                                recent_cards.append(card)
                        
                        # If no cards from today, fall back to last 3
                        if not recent_cards:
                            recent_cards = cards[-3:] if len(cards) >= 3 else cards
                        else:
                            recent_cards = recent_cards[:3]  # Take first 3 from today
                        
                        print(f"Checking {len(recent_cards)} recent cards...")
                        
                        for i, card in enumerate(recent_cards):
                            print(f"\n{'='*60}")
                            print(f"Card: {card.get('name')}")
                            print(f"Created: {card.get('createdAt', 'Unknown')}")
                            print(f"{'='*60}")
                            
                            # Check for labels
                            print(f"\nLabels on card: {card.get('labels', [])}")
                            
                            # Get comments
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
                                    print(f"\nComments ({len(comments)}):")
                                    for comment in comments:
                                        # Handle nested data structure
                                        text = comment.get('text', '')
                                        if not text and 'data' in comment:
                                            text = comment['data'].get('text', '')
                                        if text:
                                            # Show first few lines of comment
                                            lines = text.split('\n')
                                            for line in lines[:5]:
                                                print(f"  {line}")
                                            if len(lines) > 5:
                                                print(f"  ... and {len(lines) - 5} more lines")
                                except Exception as e:
                                    print(f"Comments: Error parsing - {e}")
                            
                            # Get checklist items
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
                                    # Debug: show raw data structure
                                    print(f"DEBUG: Raw checklist response type: {type(tasks_data)}")
                                    if isinstance(tasks_data, dict):
                                        print(f"DEBUG: Dict keys: {list(tasks_data.keys())}")
                                    
                                    tasks = tasks_data if isinstance(tasks_data, list) else tasks_data.get("items", [])
                                    print(f"\nChecklist items ({len(tasks)}):")
                                    for task in tasks[:5]:  # Show first 5
                                        print(f"  □ {task.get('name', '')}")
                                    if len(tasks) > 5:
                                        print(f"  ... and {len(tasks) - 5} more")
                                except Exception as e:
                                    print(f"Checklist items: Error parsing - {e}")
                            else:
                                print(f"DEBUG: No checklist response or no content")


if __name__ == "__main__":
    try:
        asyncio.run(test_full_flow())
    except Exception as e:
        print(f"\nError occurred: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()