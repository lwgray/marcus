#!/usr/bin/env python3
"""
Debug script to find the exact location of the dictionary iteration error
"""

import asyncio
import sys
import logging
import traceback
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

# Monkey patch to catch dictionary iteration errors
import builtins
original_iter = builtins.iter

def debug_iter(obj):
    if isinstance(obj, dict) and hasattr(obj, 'keys'):
        # Log when we're iterating over a dictionary
        frame = sys._getframe(1)
        print(f"[DICT ITER] {frame.f_code.co_filename}:{frame.f_lineno} in {frame.f_code.co_name}")
    return original_iter(obj)

# Enable for debugging
# builtins.iter = debug_iter

from src.marcus_mcp.server import MarcusServer
from src.marcus_mcp.handlers import handle_tool_call


async def test_create_project():
    """Test creating a project with debug logging"""
    print("Initializing Marcus server...")
    server = MarcusServer()
    
    # Initialize kanban
    await server.initialize_kanban()
    
    print("\nCalling create_project tool...")
    
    try:
        # Call create_project with the same parameters
        result = await handle_tool_call(
            'create_project',
            {
                'project_name': 'Collaborative Markdown Editor',
                'description': '''Build a real-time collaborative markdown editor with the following features:
- Live markdown preview with syntax highlighting
- Real-time collaboration using WebSockets
- User authentication and session management
- Document versioning and history
- Export to PDF and HTML
- Dark/light theme toggle
- Support for markdown extensions (tables, mermaid diagrams)
- Auto-save functionality
- Share documents via public links''',
                'options': {
                    'tech_stack': ['React', 'TypeScript', 'Node.js', 'Socket.io', 'PostgreSQL', 'Redis'],
                    'team_size': 3
                }
            },
            server
        )
        
        print("\nResult:")
        import json
        print(json.dumps(json.loads(result[0].text), indent=2))
        
    except RuntimeError as e:
        if "dictionary changed size during iteration" in str(e):
            print(f"\nCaught the error: {e}")
            
            # Get the full traceback
            tb_str = traceback.format_exc()
            print("\nFull traceback:")
            print(tb_str)
            
            # Try to identify the exact line
            tb_lines = tb_str.split('\n')
            for i, line in enumerate(tb_lines):
                if 'dictionary changed size during iteration' in line:
                    # Look at the previous lines to find the actual location
                    for j in range(max(0, i-10), i):
                        if 'File' in tb_lines[j]:
                            print(f"\nError location: {tb_lines[j]}")
                            if j+1 < len(tb_lines):
                                print(f"Line content: {tb_lines[j+1]}")
        else:
            raise


if __name__ == "__main__":
    try:
        asyncio.run(test_create_project())
    except Exception as e:
        print(f"\nError occurred: {type(e).__name__}: {e}")
        traceback.print_exc()