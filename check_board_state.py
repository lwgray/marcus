#!/usr/bin/env python3
"""
Check what's currently on the board
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from marcus import load_config
load_config()

from src.integrations.kanban_client_with_create import KanbanClientWithCreate


async def check_board():
    """Check current board state"""
    client = KanbanClientWithCreate()
    
    print("Checking current board state...")
    print("=" * 60)
    
    tasks = await client.get_all_tasks()
    print(f"\nTotal tasks on board: {len(tasks)}")
    
    if tasks:
        print("\nAll tasks:")
        for i, task in enumerate(tasks):
            created = task.created_at if hasattr(task, 'created_at') else 'Unknown'
            print(f"\n{i+1}. {task.name}")
            print(f"   Status: {task.status}")
            print(f"   Created: {created}")
            print(f"   Labels: {task.labels if hasattr(task, 'labels') else 'N/A'}")
            
        # Check for recent tasks (last hour)
        now = datetime.now()
        recent_tasks = []
        for task in tasks:
            if hasattr(task, 'created_at') and task.created_at:
                if (now - task.created_at).total_seconds() < 3600:  # Last hour
                    recent_tasks.append(task)
        
        if recent_tasks:
            print(f"\n\nTasks created in the last hour: {len(recent_tasks)}")
            for task in recent_tasks:
                print(f"  - {task.name} (created {task.created_at})")
        else:
            print("\n\nNo tasks created in the last hour")
    else:
        print("\nThe board is empty!")


if __name__ == "__main__":
    asyncio.run(check_board())