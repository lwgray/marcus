#!/usr/bin/env python3
"""
Create test tasks for Marcus experiments
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.kanban_factory import KanbanFactory

# Test tasks that simulate real coding work
TEST_TASKS = [
    {
        "title": "Fix authentication bug",
        "description": "Users report that login fails with special characters in password. Need to fix escaping in auth.py",
        "labels": ["bug", "authentication", "high-priority"]
    },
    {
        "title": "Add unit tests for user service",
        "description": "The user service module lacks test coverage. Add comprehensive unit tests.",
        "labels": ["testing", "backend"]
    },
    {
        "title": "Implement password reset feature",
        "description": "Add forgot password functionality with email verification",
        "labels": ["feature", "authentication"]
    },
    {
        "title": "Optimize database queries",
        "description": "The main dashboard is slow. Profile and optimize database queries.",
        "labels": ["performance", "database"]
    },
    {
        "title": "Fix type errors in utils.py",
        "description": "TypeScript build fails due to type mismatches in utility functions",
        "labels": ["bug", "typescript"]
    }
]

async def create_test_tasks():
    """Create test tasks in the configured Kanban board"""
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
    
    # Get Kanban client
    provider = os.getenv('KANBAN_PROVIDER', 'planka')
    kanban = await KanbanFactory.create(provider)
    
    # Create each task
    created_count = 0
    for task_data in TEST_TASKS:
        try:
            # Create task with proper structure
            task = await kanban.create_task(
                title=task_data["title"],
                description=task_data["description"],
                labels=task_data.get("labels", [])
            )
            print(f"✓ Created task: {task_data['title']}")
            created_count += 1
        except Exception as e:
            print(f"✗ Failed to create task '{task_data['title']}': {e}")
    
    print(f"\nCreated {created_count}/{len(TEST_TASKS)} tasks")
    
if __name__ == "__main__":
    import asyncio
    asyncio.run(create_test_tasks())