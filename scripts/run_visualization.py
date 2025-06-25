#!/usr/bin/env python3
"""PM Agent Visualization Server startup script.

This module provides the entry point for running the PM Agent visualization
server, which offers a web-based interface for monitoring and analyzing the
system's real-time decision-making processes, data flows, and performance
metrics.

The visualization server provides several key features:
    - Real-time conversation flow visualization
    - Decision tree exploration for AI decision-making
    - Knowledge graph viewer for system relationships
    - System metrics dashboard for performance monitoring

Examples
--------
Start the visualization server:
    $ python scripts/run_visualization.py

The server will start on http://127.0.0.1:8080 by default.

Notes
-----
The server runs continuously until interrupted with Ctrl+C. It requires
the visualization UI components to be properly installed and configured.
"""

import sys
import logging
from pathlib import Path
from typing import None as NoneType

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.visualization.ui_server import VisualizationServer


def main() -> None:
    """Run the PM Agent visualization server.
    
    Initializes and starts the web-based visualization server for monitoring
    PM Agent's operations. The server provides real-time insights into the
    system's decision-making processes, conversation flows, and performance
    metrics.
    
    The function:
        1. Configures logging for server operations
        2. Creates a VisualizationServer instance on localhost:8080
        3. Displays server information and available features
        4. Runs the server until interrupted
        5. Handles graceful shutdown on KeyboardInterrupt
    
    Returns
    -------
    None
    
    Notes
    -----
    The server binds to localhost (127.0.0.1) on port 8080 by default.
    This can be modified by changing the host and port parameters when
    creating the VisualizationServer instance.
    
    Examples
    --------
    >>> main()  # Starts the server and runs until Ctrl+C
    """
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