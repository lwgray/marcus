#!/usr/bin/env python3
"""
Debug the create_project MCP tool to see why it returns 0 tasks
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.marcus_mcp.server import MarcusServer
from src.integrations.mcp_natural_language_tools import create_project_from_natural_language


async def debug_create_project():
    """Debug why create_project returns success with 0 tasks"""
    
    print("=== Debugging create_project MCP Tool ===\n")
    
    # Create Marcus server state
    server = MarcusServer()
    await server.initialize_kanban()
    
    # Test project description
    description = "Create a simple todo list app with add, delete, and mark complete features"
    project_name = "Debug Test Project"
    
    print(f"1. Testing with simple project:")
    print(f"   Name: {project_name}")
    print(f"   Description: {description[:50]}...")
    
    try:
        # Call the actual create_project function
        result = await create_project_from_natural_language(
            description=description,
            project_name=project_name,
            state=server,
            options={"max_tasks": 5}
        )
        
        print(f"\n2. Result:")
        print(f"   Success: {result.get('success')}")
        print(f"   Tasks created: {result.get('tasks_created')}")
        print(f"   Error: {result.get('error', 'None')}")
        
        if result.get('tasks_created') == 0:
            print("\n3. Debugging why 0 tasks were created...")
            
            # Check if AI engine is working
            print("\n   Testing AI engine...")
            test_prompt = "Hello, are you working?"
            try:
                if hasattr(server.ai_engine, 'client') and server.ai_engine.client:
                    response = server.ai_engine.client.messages.create(
                        model=server.ai_engine.model,
                        max_tokens=10,
                        messages=[{"role": "user", "content": test_prompt}]
                    )
                    print("   ✓ AI engine responds")
                else:
                    print("   ✗ AI engine client not initialized")
            except Exception as e:
                print(f"   ✗ AI engine error: {e}")
            
            # Check the PRD parser
            print("\n   Testing PRD parser...")
            from src.integrations.mcp_natural_language_tools import NaturalLanguageProjectCreator
            creator = NaturalLanguageProjectCreator(
                kanban_client=server.kanban_client,
                ai_engine=server.ai_engine
            )
            
            # Try to parse tasks
            try:
                tasks = await creator.process_natural_language(description, project_name, {"max_tasks": 5})
                print(f"   PRD parser returned {len(tasks)} tasks")
                
                if len(tasks) == 0:
                    print("   ✗ PRD parser returned empty task list")
                    
                    # Try the parser directly
                    print("\n   Testing AdvancedPRDParser directly...")
                    from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser
                    parser = AdvancedPRDParser()
                    
                    from src.ai.advanced.prd.advanced_parser import ProjectConstraints
                    constraints = ProjectConstraints(max_tasks=5)
                    
                    prd_result = await parser.parse_prd_to_tasks(description, constraints)
                    print(f"   Direct parser returned {len(prd_result.tasks)} tasks")
                    
                    if hasattr(prd_result, 'error'):
                        print(f"   Parser error: {prd_result.error}")
                        
            except Exception as e:
                print(f"   ✗ Error in process_natural_language: {e}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"\n✗ Error in create_project: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_create_project())