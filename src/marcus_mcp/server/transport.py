"""
Transport layer management for Marcus server.

This module handles FastMCP and HTTP endpoint creation and tool registration.
"""

import logging

from mcp.server.fastmcp import FastMCP

from src.marcus_mcp.audit import get_audit_logger

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()


class TransportManager:
    """Manages transport layer (FastMCP/HTTP) functionality."""

    def __init__(self, server):
        """
        Initialize transport manager.

        Args:
        ----
            server: The MarcusServer instance
        """
        self.server = server

    def create_fastmcp(self) -> FastMCP:
        """
        Create and configure FastMCP instance.

        Returns
        -------
            Configured FastMCP instance
        """
        if self.server._fastmcp is None:
            # Create FastMCP wrapper
            self.server._fastmcp = FastMCP(
                self.server.server,
                info={
                    "name": "Marcus MCP Server",
                    "version": "1.0.0",
                    "description": "AI-powered engineering orchestration server",
                },
            )

            # Register tools
            from .tool_registry import ToolRegistry

            registry = ToolRegistry(self.server)
            registry.register_fastmcp_tools(self.server._fastmcp)

            # Configure middleware
            @self.server._fastmcp.middleware
            async def log_requests(request, call_next):
                """Log all incoming requests."""
                audit_logger.info(f"FastMCP request: {request.url.path}")
                response = await call_next(request)
                return response

        return self.server._fastmcp

    def create_endpoint_app(self, endpoint_type: str) -> FastMCP:
        """
        Create a FastMCP app for a specific endpoint type.

        Args:
        ----
            endpoint_type: Type of endpoint (e.g., "agent", "admin", "public")

        Returns
        -------
            Configured FastMCP instance for the endpoint
        """
        if endpoint_type not in self.server._endpoint_apps:
            # Create endpoint-specific app
            app = FastMCP(
                self.server.server,
                info={
                    "name": f"Marcus {endpoint_type.title()} Endpoint",
                    "version": "1.0.0",
                    "description": f"Marcus MCP {endpoint_type} endpoint",
                },
            )

            # Register endpoint-specific tools
            from .tool_registry import ToolRegistry

            registry = ToolRegistry(self.server)
            registry.register_endpoint_tools(app, endpoint_type)

            # Configure middleware
            @app.middleware
            async def log_endpoint_requests(request, call_next):
                """Log endpoint-specific requests."""
                audit_logger.info(
                    f"{endpoint_type.upper()} endpoint request: {request.url.path}"
                )
                response = await call_next(request)
                return response

            self.server._endpoint_apps[endpoint_type] = app

        return self.server._endpoint_apps[endpoint_type]


# Export convenience functions for backward compatibility
def create_fastmcp(server) -> FastMCP:
    """Create FastMCP instance for server."""
    transport = TransportManager(server)
    return transport.create_fastmcp()


def create_endpoint_app(server, endpoint_type: str) -> FastMCP:
    """Create endpoint-specific FastMCP app."""
    transport = TransportManager(server)
    return transport.create_endpoint_app(endpoint_type)
