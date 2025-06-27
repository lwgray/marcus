#!/usr/bin/env python3
"""Check Planka board status"""

import asyncio
import json
from src.integrations.mcp_kanban_client_simple import SimpleMCPKanbanClient

async def main():
    client = SimpleMCPKanbanClient()
    
    print("🔍 Checking board status...")
    
    if not client.board_id:
        print("❌ No board ID configured")
        return
        
    print(f"✅ Board ID: {client.board_id}")
    print(f"✅ Project ID: {client.project_id}")
    
    try:
        tasks = await client.get_available_tasks()
        print(f"\n📋 Found {len(tasks)} available tasks:")
        
        for i, task in enumerate(tasks, 1):
            print(f"\n[{i}] {task.name}")
            print(f"    ID: {task.id}")
            print(f"    Status: {task.status.value}")
            print(f"    Priority: {task.priority.value}")
            if task.description:
                print(f"    Description: {task.description[:100]}...")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())