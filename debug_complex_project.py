#!/usr/bin/env python3
"""
Debug script to find the exact location of dictionary iteration error in complex projects
"""

import asyncio
import sys
import traceback
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

# Monkey patch dict iteration to catch the exact location
import builtins

original_iter = builtins.iter
call_count = 0

def debug_iter(obj):
    global call_count
    call_count += 1
    
    if isinstance(obj, dict):
        # Get the calling frame
        frame = sys._getframe(1)
        filename = frame.f_code.co_filename
        line_number = frame.f_lineno
        function_name = frame.f_code.co_name
        
        print(f"[DICT ITER {call_count}] {filename}:{line_number} in {function_name}() - dict size: {len(obj)}")
        
        # Create a snapshot and check if it changes during iteration
        original_keys = set(obj.keys())
        try:
            result = original_iter(obj)
            # Check if keys changed after creating iterator
            current_keys = set(obj.keys())
            if original_keys != current_keys:
                print(f"WARNING: Dict keys changed! Original: {len(original_keys)}, Current: {len(current_keys)}")
            return result
        except RuntimeError as e:
            if "dictionary changed size during iteration" in str(e):
                print(f"ERROR CAUGHT: Dictionary iteration failed at {filename}:{line_number}")
                print(f"  Function: {function_name}")
                print(f"  Dict size: {len(obj)}")
                print(f"  Dict keys: {list(obj.keys())[:10]}...")  # Show first 10 keys
                traceback.print_stack()
                raise
            raise
    
    return original_iter(obj)

builtins.iter = debug_iter

from src.marcus_mcp.server import MarcusServer
from src.marcus_mcp.handlers import handle_tool_call


async def test_complex_project():
    """Test complex project with detailed debugging"""
    print("Initializing Marcus server...")
    server = MarcusServer()
    
    # Initialize kanban
    await server.initialize_kanban()
    
    print("\nCreating complex project with debug monitoring...")
    
    try:
        result = await handle_tool_call(
            'create_project',
            {
                'project_name': 'Debug Complex Project',
                'description': '''Build a comprehensive e-commerce platform with the following features:
                - User authentication and authorization system
                - Product catalog with categories and search
                - Shopping cart and checkout process
                - Payment gateway integration
                - Order management system
                - Admin dashboard for inventory management
                - Real-time notifications
                - Email marketing integration
                - Analytics and reporting
                - Mobile responsive design
                - API for third-party integrations
                - Multi-language support
                - SEO optimization
                - Performance monitoring
                - Security features and audit logging''',
                'options': {
                    'team_size': 5,
                    'tech_stack': ['React', 'Node.js', 'PostgreSQL', 'Redis', 'Docker', 'AWS'],
                    'deadline': '2025-12-31'
                }
            },
            server
        )
        
        print(f"\nTotal dictionary iterations: {call_count}")
        print("\nResult:")
        import json
        print(json.dumps(json.loads(result[0].text), indent=2))
        
    except Exception as e:
        print(f"\nError after {call_count} dictionary iterations")
        print(f"Exception type: {type(e)}")
        print(f"Exception message: {str(e)}")
        
        print("\nFull traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(test_complex_project())
    except Exception as e:
        print(f"\nOuter error: {type(e).__name__}: {e}")
        traceback.print_exc()