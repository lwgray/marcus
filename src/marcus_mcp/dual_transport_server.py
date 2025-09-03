#!/usr/bin/env python3
"""
Dual Transport Server for Marcus MCP.

This module enables Marcus to serve MCP tools over both stdio and HTTP
transports simultaneously, allowing gradual client migration.
"""

import asyncio
import threading
from typing import Optional

from .server import MarcusServer


class DualTransportServer:
    """
    Run Marcus MCP server with both stdio and HTTP transports.

    This allows:
    - Claude to connect via stdio (current)
    - Seneca to connect via stdio (current)
    - Future clients to use HTTP for enhanced features
    - Gradual migration without breaking changes
    """

    def __init__(self) -> None:
        """Initialize dual transport server."""
        self.marcus_server = MarcusServer()
        self.http_thread: Optional[threading.Thread] = None

    async def initialize(self) -> None:
        """Initialize the Marcus server."""
        await self.marcus_server.initialize()

    def run_http_server(self, host: str = "127.0.0.1", port: int = 8080) -> None:
        """Run HTTP server in a separate thread."""
        import uvicorn

        # Create FastMCP app
        fastmcp = self.marcus_server._create_fastmcp()
        app = fastmcp.streamable_http_app()

        # Run in thread to not block stdio
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="error",  # Quiet to not interfere with stdio
            access_log=False,
        )

    async def run(self) -> None:
        """Run both stdio and HTTP transports simultaneously."""
        # Get config
        from src.config.config_loader import get_config

        config = get_config()
        transport_config = config.get("transport", {})

        # Check if dual mode is enabled
        if transport_config.get("dual_mode", False):
            http_config = transport_config.get("http", {})
            if http_config.get("enabled", True):
                # Start HTTP server in background thread
                self.http_thread = threading.Thread(
                    target=self.run_http_server,
                    args=(
                        http_config.get("host", "127.0.0.1"),
                        http_config.get("port", 8080),
                    ),
                    daemon=True,
                )
                self.http_thread.start()

                # Log that HTTP is running (to stderr to not interfere)
                import sys

                print(
                    f"HTTP transport available at "
                    f"http://{http_config.get('host')}:{http_config.get('port')}/mcp",
                    file=sys.stderr,
                )

        # Run stdio transport (primary)
        await self.marcus_server.run()


async def main() -> None:
    """Run Marcus with dual transport support."""
    server = DualTransportServer()
    await server.initialize()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
