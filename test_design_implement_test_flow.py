#!/usr/bin/env python3
"""
Test script to create Design-Implement-Test task cards for Marcus execution flow testing.

This script creates three tasks with the proper dependencies to test that Marcus
follows the Design → Implement → Test execution flow.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.core.models import Priority, Task, TaskStatus
from src.integrations.kanban_client_with_create import KanbanClientWithCreate


async def get_board_lists(client):
    """Get all lists on the board to show where tasks will be created."""
    from mcp.client.stdio import stdio_client
    from mcp import ClientSession, StdioServerParameters
    
    server_params = StdioServerParameters(
        command="node", args=["../kanban-mcp/dist/index.js"], env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Get all lists for the board
            lists_result = await session.call_tool(
                "mcp_kanban_list_manager",
                {"action": "get_all", "boardId": client.board_id},
            )
            
            if lists_result and hasattr(lists_result, "content") and lists_result.content:
                lists_data = json.loads(lists_result.content[0].text)
                lists = lists_data if isinstance(lists_data, list) else lists_data.get("items", [])
                return lists
    return []


async def create_test_tasks():
    """Create three tasks for testing Design-Implement-Test flow."""
    # Initialize the kanban client
    client = KanbanClientWithCreate()
    
    print(f"\n📋 Board Configuration:")
    print(f"   Project: {client.project_id}")
    print(f"   Board: {client.board_id}")
    
    # Get and display available lists
    print("\n📍 Getting board lists...")
    lists = await get_board_lists(client)
    if lists:
        print("   Available lists:")
        for lst in lists:
            print(f"   - {lst.get('name', 'Unknown')} (ID: {lst.get('id', 'Unknown')})")
    else:
        print("   ⚠️  Could not retrieve board lists")
    
    print("\n" + "="*60)
    
    # Create Design task
    design_task = {
        "name": "Design: Authentication System Architecture",
        "description": """Design the authentication system architecture.
        
This task should be completed FIRST in the Design-Implement-Test flow.

Requirements:
- Define authentication flow (JWT vs session-based)
- Design database schema for users/sessions
- Create API endpoint specifications
- Document security considerations

📋 Task Metadata (Auto-generated)
🏷️ Original ID: auth-design-001
⏱️ Estimated: 8 hours
🟠 Priority: HIGH""",
        "priority": "high",
        "labels": ["design", "architecture", "authentication"],
        "estimated_hours": 8,
        "original_id": "auth-design-001"
    }
    
    print("Creating Design task...")
    design_result = await client.create_task(design_task)
    print(f"✅ Created Design task: {design_result.id}")
    
    # Create Implement task (depends on Design)
    implement_task = {
        "name": "Implement: Authentication API Endpoints",
        "description": f"""Implement the authentication API based on the design.

This task should be completed SECOND, after the Design task.

Requirements:
- Implement /api/auth/register endpoint
- Implement /api/auth/login endpoint
- Implement /api/auth/logout endpoint
- Add JWT token generation and validation
- Implement password hashing with bcrypt

📋 Task Metadata (Auto-generated)
🏷️ Original ID: auth-impl-001
⏱️ Estimated: 16 hours
🟠 Priority: HIGH
🔗 Dependencies: {design_result.id}""",
        "priority": "high",
        "labels": ["implementation", "backend", "authentication"],
        "estimated_hours": 16,
        "dependencies": [design_result.id],
        "original_id": "auth-impl-001"
    }
    
    print("Creating Implement task...")
    implement_result = await client.create_task(implement_task)
    print(f"✅ Created Implement task: {implement_result.id}")
    
    # Create Test task (depends on Implement)
    test_task = {
        "name": "Test: Authentication System Test Suite",
        "description": f"""Write comprehensive tests for the authentication system.

This task should be completed THIRD, after the Implementation task.

Requirements:
- Unit tests for authentication logic
- Integration tests for API endpoints
- Security tests (SQL injection, XSS, etc.)
- Performance tests for login/logout
- Test edge cases and error handling

📋 Task Metadata (Auto-generated)
🏷️ Original ID: auth-test-001
⏱️ Estimated: 12 hours
🟠 Priority: HIGH
🔗 Dependencies: {implement_result.id}""",
        "priority": "high",
        "labels": ["testing", "quality-assurance", "authentication"],
        "estimated_hours": 12,
        "dependencies": [implement_result.id],
        "original_id": "auth-test-001"
    }
    
    print("Creating Test task...")
    test_result = await client.create_task(test_task)
    print(f"✅ Created Test task: {test_result.id}")
    
    # Summary
    print("\n" + "="*60)
    print("✅ Successfully created Design-Implement-Test task flow!")
    print("="*60)
    print(f"1. Design Task: {design_result.id} - {design_result.name}")
    print(f"2. Implement Task: {implement_result.id} - {implement_result.name} (depends on Design)")
    print(f"3. Test Task: {test_result.id} - {test_result.name} (depends on Implement)")
    print("\nMarcus should execute these tasks in order:")
    print("Design → Implement → Test")
    
    # Verify tasks were created by fetching them back
    print("\n🔍 Verifying tasks on board...")
    try:
        all_tasks = await client.get_all_tasks()
        created_ids = {design_result.id, implement_result.id, test_result.id}
        found_tasks = [t for t in all_tasks if t.id in created_ids]
        
        if len(found_tasks) == 3:
            print(f"✅ All 3 tasks verified on board!")
            for task in found_tasks:
                print(f"   - {task.name} (Status: {task.status.value})")
        else:
            print(f"⚠️  Only found {len(found_tasks)} of 3 tasks on board")
    except Exception as e:
        print(f"⚠️  Could not verify tasks: {e}")
    
    print("\nYou can now test Marcus's task execution flow!")
    

if __name__ == "__main__":
    print("🚀 Creating Design-Implement-Test task flow for Marcus testing...")
    asyncio.run(create_test_tasks())