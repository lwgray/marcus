"""
MCP protocol handlers for the Marcus server.

This module contains the handler registration logic for MCP protocol
events like list_tools, call_tool, etc.
"""

import logging
from typing import Any, Dict, List

import mcp.types as types

from src.marcus_mcp.handlers import handle_tool_call
from src.marcus_mcp.tools.auth import get_tool_definitions_for_client

logger = logging.getLogger(__name__)


class ProtocolHandlers:
    """Manages MCP protocol handler registration."""

    def __init__(self, server):
        """
        Initialize protocol handlers.

        Args:
        ----
            server: The MarcusServer instance
        """
        self.server = server

    def register_handlers(self) -> None:
        """Register all MCP protocol handlers."""
        self._register_tool_handlers()
        self._register_prompt_handlers()
        self._register_resource_handlers()

    def _register_tool_handlers(self) -> None:
        """Register tool-related handlers."""

        @self.server.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """Return list of available tools based on client role."""
            # Get current client ID if available
            client_id = None
            if hasattr(self.server, "_current_client_id"):
                client_id = self.server._current_client_id

            # Get tools for this client
            return get_tool_definitions_for_client(client_id)

        @self.server.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any] | None
        ) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Handle tool execution requests."""
            return await handle_tool_call(name, arguments or {}, self.server)

    def _register_prompt_handlers(self) -> None:
        """Register prompt-related handlers."""

        @self.server.server.list_prompts()
        async def handle_list_prompts() -> List[types.Prompt]:
            """Return list of available prompts."""
            # Currently no prompts defined
            return []

        @self.server.server.get_prompt()
        async def handle_get_prompt(
            name: str, arguments: Dict[str, Any] | None
        ) -> types.GetPromptResult:
            """Get a specific prompt."""
            # Currently no prompts defined
            raise ValueError(f"Unknown prompt: {name}")

    def _register_resource_handlers(self) -> None:
        """Register resource-related handlers."""

        @self.server.server.list_resources()
        async def handle_list_resources() -> List[types.Resource]:
            """Return list of available resources."""
            # Currently no resources defined
            return []

        @self.server.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read a specific resource."""
            # Currently no resources defined
            raise ValueError(f"Unknown resource: {uri}")
