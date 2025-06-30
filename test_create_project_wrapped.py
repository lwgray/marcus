#!/usr/bin/env python3
"""
Test script with wrapped error handling
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.marcus_mcp.server import MarcusServer
from src.marcus_mcp.handlers import handle_tool_call


async def test_create_project():
    """Test creating a project with wrapped error handling"""
    print("Initializing Marcus server...")
    server = MarcusServer()
    
    # Initialize kanban
    await server.initialize_kanban()
    
    print("\nCalling create_project tool with simplified description...")
    
    # Try with a simpler description first
    try:
        result = await handle_tool_call(
            'create_project',
            {
                'project_name': 'Simple Test Project',
                'description': 'A simple project with basic features',
                'options': {
                    'tech_stack': ['Python'],
                    'team_size': 1
                }
            },
            server
        )
        
        print("\nResult:")
        import json
        print(json.dumps(json.loads(result[0].text), indent=2))
        
    except Exception as e:
        print(f"\nError with simple project: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
        # Check the actual exception chain
        current_exception = e
        while hasattr(current_exception, '__cause__') and current_exception.__cause__:
            print(f"\nCaused by: {type(current_exception.__cause__).__name__}: {current_exception.__cause__}")
            current_exception = current_exception.__cause__


if __name__ == "__main__":
    try:
        asyncio.run(test_create_project())
    except Exception as e:
        print(f"\nOuter error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()