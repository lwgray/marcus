"""
Simple Marcus MCP Client

A wrapper around the MCP protocol for calling Marcus tools.
"""

import asyncio
import json
import sys
from typing import Any, Dict, Optional

from mcp.client.stdio import stdio_client

from mcp import StdioServerParameters


class SimpleMarcusClient:
    """Simple client for interacting with Marcus MCP server."""

    def __init__(self, server_module: str = "src.marcus_mcp.server"):
        self.server_module = server_module
        self.client_context = None
        self.read_stream = None
        self.write_stream = None
        self.session = None
        self._initialized = False

    async def initialize(self):
        """Initialize the MCP client connection."""
        if self._initialized:
            return

        # Start the MCP server as a subprocess
        server_params = StdioServerParameters(
            command=sys.executable,  # Use current Python interpreter
            args=["-m", self.server_module],
            env={},
        )

        # Create client context
        self.client_context = stdio_client(server_params)
        self.read_stream, self.write_stream = await self.client_context.__aenter__()

        # Create and initialize session
        from mcp import ClientSession

        self.session = ClientSession(self.read_stream, self.write_stream)
        await self.session.initialize()

        self._initialized = True

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Call a Marcus MCP tool."""
        if not self._initialized:
            await self.initialize()

        try:
            # Call the tool
            result = await self.session.call_tool(tool_name, arguments)

            # Parse the result
            if result and result.content:
                # MCP tools return content as a list
                if isinstance(result.content, list) and len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, "text"):
                        # Try to parse as JSON
                        try:
                            return json.loads(content.text)
                        except json.JSONDecodeError:
                            # Return as plain text if not JSON
                            return {"result": content.text}
                    return {"result": str(content)}

            return None

        except Exception as e:
            print(f"Error calling tool {tool_name}: {e}")
            return None

    async def close(self):
        """Close the client connection."""
        if self.client_context:
            await self.client_context.__aexit__(None, None, None)
            self._initialized = False
