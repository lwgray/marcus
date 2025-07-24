#!/usr/bin/env python3
"""
Simple launcher for Marcus MCP server.

Usage:
    python run_marcus.py          # Run with config settings
    python run_marcus.py --http   # Force HTTP mode
    python run_marcus.py --stdio  # Force stdio mode
"""

import subprocess
import sys
from pathlib import Path

# Add marcus to path
marcus_dir = Path(__file__).parent
sys.path.insert(0, str(marcus_dir))

from src.config.config_loader import get_config  # noqa: E402


def main():
    """Run Marcus with simple command."""
    config = get_config()
    transport_config = config.get("transport", {})
    transport_type = transport_config.get("type", "stdio")

    # Check for command line overrides
    if "--http" in sys.argv:
        transport_type = "http"
    elif "--stdio" in sys.argv:
        transport_type = "stdio"

    print("Starting Marcus MCP Server")
    print(f"Transport: {transport_type}")

    if transport_type == "http":
        http_config = transport_config.get("http", {})
        print(
            f"URL: http://{http_config.get('host', '127.0.0.1')}:"
            f"{http_config.get('port', 4298)}{http_config.get('path', '/mcp')}"
        )

    # Run the server
    cmd = [sys.executable, "-m", "src.marcus_mcp.server"] + sys.argv[1:]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n✅ Marcus server stopped")


if __name__ == "__main__":
    main()
