#!/usr/bin/env python3
"""Test the complete Marcus task flow"""

import asyncio
import json
import os
from pathlib import Path

# Change to script directory
os.chdir(Path(__file__).parent)

from marcus_mcp_server import (
    state, 
    register_agent, 
    request_next_task,
    report_task_progress,
    get_project_status
)

async def test_complete_flow():
    """Test the complete Marcus workflow"""
    
    print("=== Testing Marcus Task Assignment Flow ===\n")
    
    # 1. Register an agent
    print("1. Registering agent...")
    result = await register_agent(
        agent_id="test-agent-001",
        name="Test Agent",
        role="Backend Developer", 
        skills=["python", "api", "database"]
    )
    print(f"   Result: {json.dumps(result, indent=2)}")
    
    # 2. Get project status
    print("\n2. Getting project status...")
    status = await get_project_status()
    print(f"   Total tasks: {status['project']['total_tasks']}")
    print(f"   Available tasks: {status['project']['total_tasks'] - status['project']['in_progress'] - status['project']['completed']}")
    
    # 3. Request a task
    print("\n3. Requesting next task...")
    task_result = await request_next_task("test-agent-001")
    print(f"   Result: {json.dumps(task_result, indent=2)}")
    
    if task_result.get('success'):
        task = task_result['task']
        task_id = task['id']
        
        # 4. Report progress
        print("\n4. Reporting progress...")
        progress_result = await report_task_progress(
            agent_id="test-agent-001",
            task_id=task_id,
            status="in_progress",
            progress=25,
            message="Started working on the task"
        )
        print(f"   Result: {json.dumps(progress_result, indent=2)}")
        
    # 5. Final status
    print("\n5. Final project status...")
    final_status = await get_project_status()
    print(f"   In progress tasks: {final_status['project']['in_progress']}")
    print(f"   Active workers: {final_status['workers']['active']}")

async def main():
    try:
        await test_complete_flow()
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())