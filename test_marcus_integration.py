#!/usr/bin/env python3
"""
Test Marcus integration without running the full web server.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.visualization.pipeline_flow_manager import PipelineFlowManager
from src.marcus_mcp.client import SimpleMarcusClient
from src.workflow.project_workflow_manager import ProjectWorkflowManager


async def test_marcus_integration():
    """Test the Marcus MCP integration."""
    print("=== Testing Marcus Integration ===\n")
    
    # Initialize components
    print("1. Initializing components...")
    flow_manager = PipelineFlowManager()
    marcus_client = SimpleMarcusClient()
    workflow_manager = ProjectWorkflowManager(marcus_client, flow_manager)
    
    # Initialize Marcus client
    await marcus_client.initialize()
    print("✓ Marcus client initialized")
    
    # Test 1: Ping Marcus
    print("\n2. Testing Marcus connection...")
    ping_result = await marcus_client.call_tool('ping', {})
    if ping_result:
        print(f"✓ Marcus responded: {ping_result}")
    else:
        print("✗ Failed to ping Marcus")
        return
    
    # Test 2: Create a project
    print("\n3. Creating test project...")
    project_name = "Test Todo App"
    prd_content = """# Test Todo App

## Description
A simple todo application for testing the Marcus integration.

## Features

### User Authentication
**Priority:** high
Implement basic user login and registration.

**Acceptance Criteria:**
- Users can register with email and password
- Users can login
- Sessions are maintained

### Todo CRUD
**Priority:** high
Basic todo operations.

**Acceptance Criteria:**
- Create new todos
- List all todos
- Mark todos as complete
- Delete todos
"""
    
    create_result = await marcus_client.call_tool('create_project', {
        'name': project_name,
        'description': prd_content
    })
    
    if create_result:
        print(f"✓ Project created: {create_result}")
    else:
        print("✗ Failed to create project")
        return
    
    # Test 3: Get project status
    print("\n4. Getting project status...")
    status_result = await marcus_client.call_tool('get_project_status', {})
    if status_result:
        print(f"✓ Project status: {status_result}")
    else:
        print("✗ Failed to get project status")
    
    # Test 4: List registered agents
    print("\n5. Listing registered agents...")
    agents_result = await marcus_client.call_tool('list_registered_agents', {})
    if agents_result:
        print(f"✓ Registered agents: {agents_result}")
    else:
        print("✗ Failed to list agents")
    
    # Test 5: Register a test agent
    print("\n6. Registering test agent...")
    register_result = await marcus_client.call_tool('register_agent', {
        'agent_id': 'test-agent-001',
        'name': 'Test Backend Agent',
        'role': 'Backend Developer',
        'skills': ['Python', 'API Development', 'Database']
    })
    
    if register_result:
        print(f"✓ Agent registered: {register_result}")
    else:
        print("✗ Failed to register agent")
    
    # Test 6: Request task for agent
    print("\n7. Requesting task for agent...")
    task_result = await marcus_client.call_tool('request_next_task', {
        'agent_id': 'test-agent-001'
    })
    
    if task_result and 'task' in task_result:
        print(f"✓ Task assigned: {task_result['task']}")
        
        # Test 7: Report progress
        print("\n8. Reporting task progress...")
        progress_result = await marcus_client.call_tool('report_task_progress', {
            'agent_id': 'test-agent-001',
            'task_id': task_result['task']['id'],
            'status': 'in_progress',
            'progress': 50,
            'message': 'Working on implementation'
        })
        
        if progress_result:
            print(f"✓ Progress reported: {progress_result}")
    else:
        print("✗ No tasks available or failed to request task")
    
    # Close client
    await marcus_client.close()
    print("\n✓ Test complete!")


async def main():
    """Main entry point."""
    try:
        await test_marcus_integration()
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())