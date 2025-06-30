#!/usr/bin/env python3
"""
Test current implementation to verify labels and subtasks
"""

import asyncio
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.marcus_mcp.server import MarcusServer
from src.marcus_mcp.handlers import handle_tool_call


async def test_current_implementation():
    """Test creating a single task to verify improvements"""
    print("=== Testing Current Implementation ===\n")
    
    # Initialize server
    server = MarcusServer()
    await server.initialize_kanban()
    
    # Create a very simple project
    print("Creating test project...")
    result = await handle_tool_call(
        'create_project',
        {
            'project_name': 'Label and Subtask Test',
            'description': 'A simple TODO app with user authentication',
            'options': {
                'tech_stack': ['React', 'Node.js'],
                'team_size': 1
            }
        },
        server
    )
    
    result_data = json.loads(result[0].text)
    print(f"\nProject created: {result_data.get('success')}")
    print(f"Tasks created: {result_data.get('tasks_created')}")
    
    # Now let's check the actual tasks created
    print("\n=== Checking Tasks ===")
    tasks = await server.kanban_client.get_all_tasks()
    
    # Find the most recent tasks (should have highest IDs)
    recent_tasks = sorted(tasks, key=lambda t: t.id, reverse=True)[:3]
    
    for i, task in enumerate(recent_tasks):
        print(f"\n--- Task {i+1} ---")
        print(f"Name: {task.name}")
        print(f"Status: {task.status}")
        print(f"Priority: {task.priority}")
        print(f"Labels: {task.labels}")
        print(f"Estimated Hours: {task.estimated_hours}")
        
        # Check if task has dynamic attributes
        if hasattr(task, 'acceptance_criteria'):
            print(f"Acceptance Criteria: {len(task.acceptance_criteria)} items")
            for j, criteria in enumerate(task.acceptance_criteria[:2]):
                print(f"  {j+1}. {criteria}")
        
        if hasattr(task, 'subtasks'):
            print(f"Subtasks: {len(task.subtasks)} items")
            for j, subtask in enumerate(task.subtasks[:2]):
                print(f"  {j+1}. {subtask}")


if __name__ == "__main__":
    try:
        asyncio.run(test_current_implementation())
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()