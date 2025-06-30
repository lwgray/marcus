#!/usr/bin/env python3
"""
Test script to reproduce the dictionary changed size during iteration error
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.marcus_mcp.server import MarcusServer
from src.marcus_mcp.handlers import handle_tool_call


async def test_create_project():
    """Test creating a project to reproduce the error"""
    print("Initializing Marcus server...")
    server = MarcusServer()
    
    # Initialize kanban
    await server.initialize_kanban()
    
    print("\nCalling create_project tool...")
    
    # Call create_project with the same parameters that caused the error
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


if __name__ == "__main__":
    try:
        asyncio.run(test_create_project())
    except Exception as e:
        print(f"\nError occurred: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()