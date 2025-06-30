#!/usr/bin/env python3
"""
Final verification that labels and subtasks are working
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


async def verify_improvements():
    """Verify that all improvements are working"""
    
    print("=== Final Verification of Task Quality Improvements ===\n")
    
    # Create a small test project
    server = MarcusServer()
    await server.initialize_kanban()
    
    print("1. Creating test project...")
    result = await handle_tool_call(
        'create_project',
        {
            'project_name': 'Final Verification Test',
            'description': 'A simple task management app',
            'options': {
                'tech_stack': ['Python', 'FastAPI'],
                'team_size': 1
            }
        },
        server
    )
    
    result_data = json.loads(result[0].text)
    print(f"   Project created: {result_data.get('success')}")
    print(f"   Tasks created: {result_data.get('tasks_created')}")
    
    # Now check the actual board state
    print("\n2. Checking board state...")
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Get the most recent card
            lists_result = await session.call_tool(
                "mcp_kanban_list_manager",
                {
                    "action": "get_all",
                    "boardId": "1533859887128249584"  # Use the known board ID
                }
            )
            
            if lists_result and hasattr(lists_result, 'content'):
                lists_data = json.loads(lists_result.content[0].text)
                
                # Find backlog list
                for lst in lists_data:
                    if "backlog" in lst.get("name", "").lower():
                        # Get cards
                        cards_result = await session.call_tool(
                            "mcp_kanban_card_manager",
                            {
                                "action": "get_all",
                                "listId": lst["id"]
                            }
                        )
                        
                        if cards_result and hasattr(cards_result, 'content'):
                            cards_data = json.loads(cards_result.content[0].text)
                            
                            # Check the most recent card
                            if cards_data:
                                card = cards_data[-1]  # Last card (most recent)
                                print(f"\n3. Checking card: {card['name']}")
                                
                                # Check labels
                                labels = card.get('labels', [])
                                print(f"   ✓ Visual Labels: {len(labels)} labels")
                                if labels:
                                    for label in labels[:3]:
                                        print(f"     - {label.get('name', 'Unknown')} ({label.get('color', 'Unknown')})")
                                
                                # Check checklist items
                                tasks_result = await session.call_tool(
                                    "mcp_kanban_task_manager",
                                    {
                                        "action": "get_all",
                                        "cardId": card["id"]
                                    }
                                )
                                
                                if tasks_result and hasattr(tasks_result, 'content'):
                                    tasks_data = json.loads(tasks_result.content[0].text)
                                    print(f"   ✓ Checklist Items: {len(tasks_data)} items")
                                    
                                    # Count acceptance criteria vs subtasks
                                    acceptance_count = sum(1 for t in tasks_data if t.get('name', '').startswith('✓'))
                                    subtask_count = sum(1 for t in tasks_data if t.get('name', '').startswith('•'))
                                    
                                    print(f"     - Acceptance Criteria: {acceptance_count}")
                                    print(f"     - Subtasks: {subtask_count}")
                                    
                                    # Show a few examples
                                    if tasks_data:
                                        print("\n   Examples:")
                                        for task in tasks_data[:3]:
                                            print(f"     {task.get('name', '')}")
                                
                                # Summary
                                print("\n4. Summary:")
                                print(f"   ✓ Task has meaningful name: {'Implement' in card['name'] or 'Setup' in card['name']}")
                                print(f"   ✓ Task has visual labels: {len(labels) > 0}")
                                print(f"   ✓ Task has acceptance criteria: {acceptance_count > 0}")
                                print(f"   ✓ Task has subtasks: {subtask_count > 0}")
                                
                                return


if __name__ == "__main__":
    try:
        asyncio.run(verify_improvements())
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()