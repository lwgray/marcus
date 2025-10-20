#!/usr/bin/env python3
"""
Run the Marcus Visualization API server.

Usage:
    python viz_backend/run_server.py
"""

import socket
import sys

import uvicorn


def find_available_port(start_port: int = 4300, max_attempts: int = 10) -> int:
    """
    Find an available port starting from start_port.

    Parameters
    ----------
    start_port : int
        Port to start searching from
    max_attempts : int
        Maximum number of ports to try

    Returns
    -------
    int
        Available port number

    Raises
    ------
    RuntimeError
        If no available port found
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            # Try to bind to the port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", port))  # nosec B104
                return port
        except OSError:
            continue

    end_port = start_port + max_attempts
    raise RuntimeError(
        f"Could not find available port in range {start_port}-{end_port}"
    )


if __name__ == "__main__":
    try:
        port = find_available_port(start_port=4300)
        print(f"🚀 Starting Marcus Viz Backend on http://localhost:{port}")
        print(f"📊 API Documentation: http://localhost:{port}/docs")
        print(f"✅ Health Check: http://localhost:{port}/health")
        print(
            f"\n💡 Update your frontend .env to: VITE_API_URL=http://localhost:{port}\n"
        )

        uvicorn.run(
            "viz_backend.api:app",
            host="0.0.0.0",  # nosec B104
            port=port,
            reload=True,  # Enable auto-reload during development
            log_level="info",
        )
    except RuntimeError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
        sys.exit(0)
