#!/usr/bin/env python3
"""
Test with detailed stack trace to find the exact error location
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Monkey patch to catch any exception
import builtins
original_hasattr = builtins.hasattr

def debug_hasattr(obj, name):
    try:
        return original_hasattr(obj, name)
    except RuntimeError as e:
        if "dictionary changed size during iteration" in str(e):
            print(f"ERROR in hasattr({type(obj)}, {name})")
            traceback.print_stack()
            raise
        raise

# builtins.hasattr = debug_hasattr

from src.marcus_mcp.server import MarcusServer
from src.marcus_mcp.handlers import handle_tool_call


async def test_create_project():
    """Test creating a project with detailed error tracking"""
    print("Initializing Marcus server...")
    server = MarcusServer()
    
    # Initialize kanban
    await server.initialize_kanban()
    
    print("\nCreating simple project...")
    
    try:
        result = await handle_tool_call(
            'create_project',
            {
                'project_name': 'Simple App',
                'description': 'A simple web application with basic CRUD functionality.',
                'options': {
                    'tech_stack': ['Python', 'Flask'],
                    'team_size': 1
                }
            },
            server
        )
        
        print("\nResult:")
        import json
        print(json.dumps(json.loads(result[0].text), indent=2))
        
    except Exception as e:
        print(f"\nDetailed error analysis:")
        print(f"Exception type: {type(e)}")
        print(f"Exception message: {str(e)}")
        
        # Get the full exception chain
        current = e
        level = 0
        while current:
            print(f"\nLevel {level}: {type(current).__name__}: {current}")
            current = getattr(current, '__cause__', None) or getattr(current, '__context__', None)
            level += 1
            if level > 10:  # Prevent infinite loops
                break
        
        print("\nFull traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(test_create_project())
    except Exception as e:
        print(f"\nOuter error: {type(e).__name__}: {e}")
        traceback.print_exc()