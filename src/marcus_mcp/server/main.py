"""
Main entry point for Marcus MCP Server.

This module contains the main() function and command-line handling.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.config.config_loader import get_config  # noqa: E402
from src.core.service_registry import register_marcus_service  # noqa: E402

from .core import MarcusServer  # noqa: E402
from .handlers import ProtocolHandlers  # noqa: E402
from .initialization import ServerInitializer  # noqa: E402
from .lifecycle import LifecycleManager, run_multi_endpoint_server  # noqa: E402

# Cost tracking middleware removed - not in original server
# Logging setup removed - not in original server


logger = logging.getLogger(__name__)


async def main() -> None:
    """Execute the main entry point for Marcus MCP server."""
    # Load configuration (already loaded by marcus.py if running through it)
    config = get_config()

    # Logging setup removed - not in original server

    # Cost tracking middleware removed - not in original server

    # Create server instance
    server = MarcusServer()

    # Register MCP protocol handlers
    protocol_handlers = ProtocolHandlers(server)
    protocol_handlers.register_handlers()

    # Setup lifecycle management
    lifecycle = LifecycleManager(server)
    lifecycle.setup_signal_handlers()

    # Check transport mode
    transport = os.getenv("MCP_TRANSPORT", "stdio")

    if transport == "http":
        # HTTP transport with multiple endpoints
        endpoints = config.get("http_endpoints", {})
        if not endpoints:
            logger.error("HTTP transport requested but no endpoints configured")
            sys.exit(1)

        logger.info("Starting Marcus in HTTP transport mode...")

        # Register service
        register_marcus_service(
            name="marcus-mcp-http",
            transport="http",
            endpoints=endpoints,
        )

        # Run multi-endpoint server
        await run_multi_endpoint_server(server)

    else:
        # Default stdio transport
        logger.info("Starting Marcus in stdio transport mode...")

        # Register service
        register_marcus_service(
            name="marcus-mcp-stdio",
            transport="stdio",
        )

        # Initialize server
        initializer = ServerInitializer(server)
        await initializer.initialize()

        # Run stdio server
        await lifecycle.run_stdio_server()


def run() -> None:
    """Run the server."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server failed: {e}", exc_info=True)
        sys.exit(1)


# Script entry point
if __name__ == "__main__":
    # Check if running through marcus.py or directly
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Marcus MCP Server")
        print("\nUsage:")
        print("  Through marcus.py:  python -m marcus mcp [--http]")
        print("  Direct:            python -m src.marcus_mcp.server")
        print("\nOptions:")
        print("  --http    Use HTTP transport instead of stdio")
        print("\nEnvironment Variables:")
        print("  MCP_TRANSPORT    Set to 'http' for HTTP transport")
        sys.exit(0)

    # Check for HTTP flag
    if "--http" in sys.argv:
        os.environ["MCP_TRANSPORT"] = "http"

    # Run the server
    run()
