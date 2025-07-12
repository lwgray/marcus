"""
Integrated Marcus Server with Web UI

Runs both the Marcus MCP server and the Flask web UI in one process.
"""

import asyncio
import os
import signal
import sys
import threading
from pathlib import Path

# Ensure marcus module is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask
from flask_socketio import SocketIO

from src.api.app import app, socketio


class IntegratedMarcusServer:
    """Runs Marcus MCP server and web UI together"""

    def __init__(self, enable_web_ui=True, web_port=5000):
        self.enable_web_ui = enable_web_ui
        self.web_port = web_port
        self.flask_thread = None
        self.mcp_task = None

    def start_flask_server(self):
        """Run Flask server in a separate thread"""
        if not self.enable_web_ui:
            return

        def run_flask():
            print(f"🌐 Starting Marcus Web UI on http://localhost:{self.web_port}")
            socketio.run(
                app,
                host="0.0.0.0",  # nosec B104
                port=self.web_port,
                debug=False,
                use_reloader=False,
                allow_unsafe_werkzeug=True,
            )

        self.flask_thread = threading.Thread(target=run_flask, daemon=True)
        self.flask_thread.start()

    async def run_mcp_server(self):
        """Run the Marcus MCP server"""
        from src.api.pattern_learning_init import init_pattern_learning_components
        from src.marcus_mcp import main as mcp_main

        print("🚀 Starting Marcus MCP Server...")

        # Initialize pattern learning components for API access
        # The MCP server will provide the kanban client and AI engine
        # We'll initialize them after the MCP server starts

        await mcp_main()

    async def run(self):
        """Run both servers"""
        # Start Flask in background thread
        self.start_flask_server()

        # Run MCP server in main async loop
        try:
            await self.run_mcp_server()
        except KeyboardInterrupt:
            print("\n👋 Shutting down Marcus...")
            sys.exit(0)


def main():
    """Main entry point for integrated server"""
    import argparse

    parser = argparse.ArgumentParser(description="Marcus Integrated Server")
    parser.add_argument(
        "--no-web", action="store_true", help="Disable web UI (run MCP server only)"
    )
    parser.add_argument(
        "--port", type=int, default=5000, help="Web UI port (default: 5000)"
    )

    args = parser.parse_args()

    # Create and run integrated server
    server = IntegratedMarcusServer(enable_web_ui=not args.no_web, web_port=args.port)

    # Run the server
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
