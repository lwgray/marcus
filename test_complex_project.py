#!/usr/bin/env python3
"""
Test with a complex project like the one that was failing
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.marcus_mcp.server import MarcusServer
from src.marcus_mcp.handlers import handle_tool_call


async def test_complex_project():
    """Test creating a complex project that was failing"""
    print("Initializing Marcus server...")
    server = MarcusServer()
    
    # Initialize kanban
    await server.initialize_kanban()
    
    print("\nCreating complex project...")
    
    try:
        result = await handle_tool_call(
            'create_project',
            {
                'project_name': 'CollabTask Pro',
                'description': '''Build a modern web-based task management application with real-time collaboration features. The app should support multiple users working on shared projects, with features including: user authentication and authorization, project creation and management, task creation with due dates and priorities, real-time updates using WebSockets, drag-and-drop task organization, commenting and activity feeds, file attachments, email notifications, and a responsive design that works on mobile devices. Use React for the frontend with Material-UI components, Node.js/Express for the backend API, PostgreSQL for data storage, Redis for caching and session management, and Socket.io for real-time updates.''',
                'options': {
                    'team_size': 4,
                    'tech_stack': ['React', 'Node.js', 'PostgreSQL', 'Redis', 'Socket.io', 'Material-UI'],
                    'deadline': '2025-08-30'
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
        
        print("\nFull traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(test_complex_project())
    except Exception as e:
        print(f"\nOuter error: {type(e).__name__}: {e}")
        traceback.print_exc()