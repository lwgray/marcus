#!/usr/bin/env python3
"""
Test create_project directly to debug the issue
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from marcus import load_config
load_config()

from src.marcus_mcp.server import MarcusServer
from src.integrations.mcp_natural_language_tools import create_project_from_natural_language


async def test_create_project():
    """Test project creation directly"""
    
    # Initialize server
    server = MarcusServer()
    await server.initialize_kanban()
    
    description = """Create a Friday Night Funkin' rhythm game clone with the following features:
- Core rhythm gameplay with arrow key inputs synced to music
- Health bar system that responds to player performance
- Multiple difficulty levels (Easy, Normal, Hard)
- Character animation system for Boyfriend, Girlfriend, and opponents
- Song chart system to define note patterns"""
    
    project_name = "Friday Night Funkin Clone"
    
    print(f"Creating project: {project_name}")
    print(f"Description: {description[:100]}...")
    
    result = await create_project_from_natural_language(
        description=description,
        project_name=project_name,
        state=server,
        options={"tech_stack": ["JavaScript", "HTML5", "Canvas", "Web Audio API"], "team_size": 3}
    )
    
    print(f"\nResult:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    
    # Check what tasks were actually created on the board
    if server.kanban_client:
        print("\nChecking board for tasks...")
        tasks = await server.kanban_client.get_all_tasks()
        print(f"Total tasks on board: {len(tasks)}")
        
        # Show last few tasks
        for task in tasks[-5:]:
            if hasattr(task, 'name'):
                print(f"  - {task.name} (Status: {task.status})")
            else:
                print(f"  - {task.get('name', 'Unnamed')} (ID: {task.get('id')})")


if __name__ == "__main__":
    asyncio.run(test_create_project())