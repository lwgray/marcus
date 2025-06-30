#!/usr/bin/env python3
"""
Test MCP create_project directly to find the actual issue
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the actual function that gets called
from src.integrations.mcp_natural_language_tools import create_project_from_natural_language


class MockState:
    """Mock state object to test the function"""
    def __init__(self):
        from src.integrations.kanban_client_with_create import KanbanClientWithCreate
        from src.ai.core.ai_engine import MarcusAIEngine
        
        self.kanban_client = KanbanClientWithCreate()
        self.ai_engine = MarcusAIEngine()
        self.project_tasks = []
    
    async def initialize_kanban(self):
        """Mock initialization"""
        pass
    
    async def refresh_project_state(self):
        """Mock refresh"""
        self.project_tasks = await self.kanban_client.get_all_tasks()


async def test_create_project_directly():
    """Test the create_project function to see where it fails/times out"""
    
    print("=== Testing create_project_from_natural_language directly ===\n")
    
    # Create mock state
    state = MockState()
    
    # Test with your recipe manager description
    description = """Build a web application that helps users manage their recipes, plan meals for the
week, and automatically generate shopping lists. The app should allow
users to add/edit/delete recipes with ingredients and instructions,
search recipes by ingredients or dietary restrictions, plan meals by
dragging recipes to calendar days, and generate consolidated shopping
lists from selected meals. Include features for scaling recipes up/down
based on servings, tracking nutritional information"""
    
    project_name = "Smart Recipe Manager Test"
    
    print(f"Testing with project: {project_name}")
    print(f"Description length: {len(description)} characters")
    print("\nStarting test...\n")
    
    start_time = time.time()
    checkpoint_times = {}
    
    try:
        # Patch the function to add timing checkpoints
        original_parse = None
        if hasattr(state.ai_engine, 'parse_prd_to_tasks'):
            original_parse = state.ai_engine.parse_prd_to_tasks
            
            async def timed_parse(*args, **kwargs):
                parse_start = time.time()
                print(f"[{parse_start - start_time:.1f}s] Starting AI parsing...")
                result = await original_parse(*args, **kwargs)
                print(f"[{time.time() - start_time:.1f}s] AI parsing completed (took {time.time() - parse_start:.1f}s)")
                return result
            
            state.ai_engine.parse_prd_to_tasks = timed_parse
        
        # Call the function
        print(f"[0.0s] Calling create_project_from_natural_language...")
        
        result = await create_project_from_natural_language(
            description=description,
            project_name=project_name,
            state=state,
            options={
                "max_tasks": 10,  # Limit tasks
                "tech_stack": ["react", "nodejs", "postgresql"]
            }
        )
        
        total_time = time.time() - start_time
        print(f"\n[{total_time:.1f}s] ✓ Function completed successfully!")
        
        if result.get("success"):
            print(f"\nResult:")
            print(f"  - Tasks created: {result.get('tasks_created', 0)}")
            print(f"  - Task breakdown: {result.get('task_breakdown', {})}")
            print(f"  - Estimated days: {result.get('estimated_days', 0)}")
        else:
            print(f"\n✗ Function failed: {result.get('error', 'Unknown error')}")
        
        print(f"\nTotal execution time: {total_time:.1f} seconds")
        
        if total_time > 120:
            print("\n⚠️  This exceeds the default MCP timeout of 120 seconds!")
            print("   This confirms the timeout issue.")
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n[{elapsed:.1f}s] ✗ Exception occurred:")
        print(f"  Type: {type(e).__name__}")
        print(f"  Message: {e}")
        
        import traceback
        traceback.print_exc()
        
        print(f"\nFailed after {elapsed:.1f} seconds")


if __name__ == "__main__":
    print("Running direct test of create_project functionality...\n")
    asyncio.run(test_create_project_directly())