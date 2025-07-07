#!/usr/bin/env python3
"""
Test the pipeline visualization by running the UI server
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.visualization.ui_server import VisualizationServer

async def main():
    """Start the visualization server"""
    print("Starting Marcus Visualization Server...")
    print("Open http://localhost:8080/pipeline to see the pipeline flow visualization")
    print("\nMake sure to run test_project_via_mcp.py in another terminal to see live pipeline events!")
    print("\nPress Ctrl+C to stop the server")
    
    server = VisualizationServer(host="0.0.0.0", port=8080)
    await server.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped")