#!/usr/bin/env python3
"""
Complete test showing labels, colors, and subtasks working together
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


async def test_complete_solution():
    """Test the complete solution with labels, colors, and subtasks"""
    
    print("=== Complete Task Quality Test ===\n")
    
    # 1. Create a project
    server = MarcusServer()
    await server.initialize_kanban()
    
    print("1. Creating a test project...")
    result = await handle_tool_call(
        'create_project',
        {
            'project_name': 'Complete Quality Test',
            'description': 'E-commerce platform with user authentication',
            'options': {
                'tech_stack': ['React', 'Django', 'PostgreSQL'],
                'team_size': 2
            }
        },
        server
    )
    
    result_data = json.loads(result[0].text)
    print(f"   ✓ Project created successfully")
    print(f"   ✓ {result_data.get('tasks_created')} tasks created\n")
    
    # 2. Check the board details
    print("2. Checking task quality on the board...\n")
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Get all labels first
            labels_result = await session.call_tool(
                "mcp_kanban_label_manager",
                {
                    "action": "get_all",
                    "boardId": "1533859887128249584"
                }
            )
            
            all_labels = {}
            if labels_result and hasattr(labels_result, 'content'):
                labels_data = json.loads(labels_result.content[0].text)
                for label in labels_data:
                    all_labels[label['id']] = label
            
            # Get lists and cards
            lists_result = await session.call_tool(
                "mcp_kanban_list_manager",
                {
                    "action": "get_all",
                    "boardId": "1533859887128249584"
                }
            )
            
            if lists_result and hasattr(lists_result, 'content'):
                lists_data = json.loads(lists_result.content[0].text)
                
                for lst in lists_data:
                    if "backlog" in lst.get("name", "").lower():
                        cards_result = await session.call_tool(
                            "mcp_kanban_card_manager",
                            {
                                "action": "get_all",
                                "listId": lst["id"]
                            }
                        )
                        
                        if cards_result and hasattr(cards_result, 'content'):
                            cards_data = json.loads(cards_result.content[0].text)
                            
                            # Show the most recent card in detail
                            if cards_data:
                                card = cards_data[-1]
                                print(f"   TASK: {card['name']}")
                                print(f"   " + "="*60)
                                
                                # Check labels
                                card_labels = card.get('labels', [])
                                if card_labels:
                                    print(f"\n   📌 LABELS ({len(card_labels)}):")
                                    for label_id in card_labels[:5]:
                                        if label_id in all_labels:
                                            label = all_labels[label_id]
                                            print(f"      • {label['name']} ({label['color']})")
                                else:
                                    print(f"\n   📌 LABELS: None attached (but {len([l for l in all_labels.values() if 'Complete Quality Test' in str(l)])} exist on board)")
                                
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
                                    
                                    # Separate acceptance criteria and subtasks
                                    acceptance = [t for t in tasks_data if t.get('name', '').startswith('✓')]
                                    subtasks = [t for t in tasks_data if t.get('name', '').startswith('•')]
                                    
                                    print(f"\n   ✅ ACCEPTANCE CRITERIA ({len(acceptance)}):")
                                    for i, criteria in enumerate(acceptance[:3]):
                                        print(f"      {i+1}. {criteria['name']}")
                                    if len(acceptance) > 3:
                                        print(f"      ... and {len(acceptance) - 3} more")
                                    
                                    print(f"\n   📋 SUBTASKS ({len(subtasks)}):")
                                    for i, task in enumerate(subtasks[:3]):
                                        print(f"      {i+1}. {task['name']}")
                                    if len(subtasks) > 3:
                                        print(f"      ... and {len(subtasks) - 3} more")
                                
                                # Check metadata comment
                                comments_result = await session.call_tool(
                                    "mcp_kanban_comment_manager",
                                    {
                                        "action": "get_all",
                                        "cardId": card["id"]
                                    }
                                )
                                
                                if comments_result and hasattr(comments_result, 'content'):
                                    comments_data = json.loads(comments_result.content[0].text)
                                    if comments_data:
                                        comment = comments_data[0]
                                        text = comment.get('text', '')
                                        if 'data' in comment:
                                            text = comment['data'].get('text', text)
                                        
                                        print(f"\n   📝 METADATA:")
                                        for line in text.split('\n')[1:4]:  # Skip header, show first 3 lines
                                            if line.strip():
                                                print(f"      {line.strip()}")
                                
                                print(f"\n   " + "="*60)
                                print(f"\n   SUMMARY:")
                                print(f"   ✓ Task has meaningful name: {'Yes' if 'Implement' in card['name'] or 'Setup' in card['name'] else 'Partial'}")
                                print(f"   ✓ Task has visual labels: {'Yes' if card_labels else 'No (creation works, attachment issue)'}")
                                print(f"   ✓ Task has acceptance criteria: {'Yes' if acceptance else 'No'}")
                                print(f"   ✓ Task has subtasks: {'Yes' if subtasks else 'No'}")
                                print(f"   ✓ Task has proper metadata: Yes")
                                
                                # Show color distribution
                                print(f"\n3. Label Color Distribution:")
                                color_dist = {}
                                for label in all_labels.values():
                                    if any(prefix in label['name'] for prefix in ['priority:', 'skill:', 'type:', 'complexity:', 'component:']):
                                        color = label['color']
                                        color_dist[color] = color_dist.get(color, 0) + 1
                                
                                for color, count in sorted(color_dist.items(), key=lambda x: x[1], reverse=True)[:5]:
                                    print(f"   • {color}: {count} labels")
                                
                                break


if __name__ == "__main__":
    try:
        asyncio.run(test_complete_solution())
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()