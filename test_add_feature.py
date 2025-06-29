#!/usr/bin/env python3
"""
Test script for add_feature functionality
"""

import asyncio
from src.mcp.server import MarcusServer
from src.mcp.tools.nlp_tools import add_feature


async def test_add_feature():
    """Test adding a feature with the modular server"""
    # Create server instance
    server = MarcusServer()
    
    # Initialize kanban and refresh state to get existing tasks
    await server.initialize_kanban()
    await server.refresh_project_state()
    
    # Check if there are existing tasks
    if not server.project_tasks:
        print("No existing tasks found. Creating a project first would be needed.")
        return
    
    print(f"Found {len(server.project_tasks)} existing tasks")
    
    # Test feature addition
    result = await add_feature(
        feature_description="Add user profile management with avatar upload and bio editing",
        integration_point="auto_detect",
        state=server
    )
    
    print("\nAdd Feature Result:")
    print(f"Success: {result.get('success')}")
    print(f"Tasks Created: {result.get('tasks_created')}")
    if result.get('success'):
        print(f"Task Breakdown: {result.get('task_breakdown')}")
        print(f"Integration Points: {result.get('integration_points')}")
        print(f"Feature Phase: {result.get('feature_phase')}")
        print(f"Complexity: {result.get('complexity')}")
    else:
        print(f"Error: {result.get('error')}")


if __name__ == "__main__":
    asyncio.run(test_add_feature())