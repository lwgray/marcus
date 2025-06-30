#!/usr/bin/env python3
"""
Test script to verify improvements to task quality
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.marcus_mcp.server import MarcusServer
from src.marcus_mcp.handlers import handle_tool_call


async def test_simple_project():
    """Test creating a simple project to verify improvements"""
    print("Initializing Marcus server...")
    server = MarcusServer()
    
    # Initialize kanban
    await server.initialize_kanban()
    
    print("\nCalling create_project tool...")
    
    # Call create_project with a simple project
    result = await handle_tool_call(
        'create_project',
        {
            'project_name': 'Simple TODO App',
            'description': 'Create a simple TODO application with add, edit, delete, and mark as complete functionality',
            'options': {
                'tech_stack': ['React', 'Node.js'],
                'team_size': 1
            }
        },
        server
    )
    
    print("\nResult:")
    import json
    result_data = json.loads(result[0].text)
    print(json.dumps(result_data, indent=2))
    
    # Now fetch the created tasks to see their details
    print("\n\nFetching created tasks...")
    
    # Get project status
    status_result = await handle_tool_call(
        'get_project_status',
        {},
        server
    )
    
    print("\nProject Status:")
    status_data = json.loads(status_result[0].text)
    print(json.dumps(status_data, indent=2))
    
    # Now let's check if we can get task details from the kanban board
    # We'll need to use the kanban client directly to see tasks
    print("\n\nChecking actual board state...")
    
    # Get all tasks from kanban
    tasks = await server.kanban_client.get_all_tasks()
    
    # Display first few tasks to check quality
    for i, task in enumerate(tasks[:3]):
        print(f"\n--- Task {i+1} ---")
        print(f"ID: {task.id}")
        print(f"Name: {task.name}")
        print(f"Description: {task.description[:100] if task.description else 'No description'}...")
        print(f"Status: {task.status}")
        print(f"Priority: {task.priority}")
        print(f"Labels: {task.labels}")
        print(f"Estimated Hours: {task.estimated_hours}")
        
    print(f"\n\nTotal tasks on board: {len(tasks)}")


if __name__ == "__main__":
    try:
        asyncio.run(test_simple_project())
    except Exception as e:
        print(f"\nError occurred: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()