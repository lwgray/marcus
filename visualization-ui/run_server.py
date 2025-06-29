#!/usr/bin/env python3
"""
Run Marcus Visualization UI Server

This starts the web UI for monitoring Marcus operations.
Access at: http://localhost:8080
"""

import sys
import os
import logging
from pathlib import Path

# Add Marcus to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_file = project_root / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment from {env_file}")
except ImportError:
    print("Warning: python-dotenv not installed, skipping .env file")

# Check dependencies
try:
    import aiohttp
    import aiohttp_cors
    import socketio
    import jinja2
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("\nInstall required packages:")
    print("pip install aiohttp aiohttp-cors python-socketio jinja2")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress some noisy loggers
logging.getLogger('socketio').setLevel(logging.WARNING)
logging.getLogger('engineio').setLevel(logging.WARNING)

try:
    from src.visualization.ui_server import VisualizationServer
    
    print("=" * 60)
    print("Marcus Visualization UI Server")
    print("=" * 60)
    print()
    print("Starting server on http://localhost:8080")
    print()
    print("Features:")
    print("- Real-time agent conversation monitoring")
    print("- Decision visualization") 
    print("- Knowledge graph")
    print("- System health metrics")
    print()
    print("Note: This UI is optional. Marcus works through MCP without it.")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    server = VisualizationServer(host="0.0.0.0", port=8080)
    server.run()
    
except KeyboardInterrupt:
    print("\nShutting down UI server...")
    
except Exception as e:
    print(f"\nError starting UI server: {e}")
    import traceback
    traceback.print_exc()
    print("\nThe UI server has issues but Marcus MCP still works!")
    print("You can monitor experiments through:")
    print("- Marcus MCP logs")
    print("- Git commit history") 
    print("- Your kanban board")