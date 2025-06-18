#!/usr/bin/env python3
"""
Run the PM Agent Visualization Server

This script starts the web-based visualization interface for monitoring
PM Agent's real-time decision-making and data flow.
"""

import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.visualization.ui_server import VisualizationServer


def main():
    """Run the visualization server"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start server
    server = VisualizationServer(host="127.0.0.1", port=8080)
    
    print("\n" + "="*60)
    print("PM Agent Visualization Server")
    print("="*60)
    print(f"Starting server at http://127.0.0.1:8080")
    print("\nFeatures:")
    print("- Real-time conversation flow visualization")
    print("- Decision tree exploration") 
    print("- Knowledge graph viewer")
    print("- System metrics dashboard")
    print("\nPress Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\nShutting down visualization server...")
        

if __name__ == "__main__":
    main()