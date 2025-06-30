#!/usr/bin/env python3
"""
Test if create_project works now after fixes
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.marcus_mcp.server import MarcusServer
from src.marcus_mcp.handlers import handle_tool_call


async def test_create_project():
    """Test creating a random project"""
    print("Initializing Marcus server...")
    server = MarcusServer()
    
    # Initialize kanban
    await server.initialize_kanban()
    
    print("\nCreating Weather Dashboard project...")
    
    result = await handle_tool_call(
        'create_project',
        {
            'project_name': 'Weather Dashboard',
            'description': '''Create a weather dashboard application that displays current weather and forecasts. 
            Features: show current weather for user location, search weather by city name, 
            display 5-day forecast, save favorite locations, show weather maps, responsive design. 
            Backend API with weather data integration, frontend with interactive charts.''',
            'options': {
                'tech_stack': ['React', 'Node.js', 'MongoDB'],
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
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()