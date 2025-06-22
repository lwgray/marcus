#!/usr/bin/env python3
"""Debug script to check available tasks"""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

# Set to use Planka
os.environ['KANBAN_PROVIDER'] = 'planka'

from src.integrations.mcp_kanban_client_simplified import MCPKanbanClientSimplified as SimpleMCPKanbanClient

async def check_tasks():
    print("Checking tasks in Planka...")
    client = SimpleMCPKanbanClient()
    
    try:
        tasks = await client.get_available_tasks()
        print(f"\nFound {len(tasks)} available tasks:")
        for i, task in enumerate(tasks):
            print(f"\n{i+1}. {task.name}")
            print(f"   ID: {task.id}")
            print(f"   Status: {task.status.value}")
            print(f"   Priority: {task.priority.value}")
            print(f"   Assigned to: {task.assigned_to}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_tasks())