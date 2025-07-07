"""
Fixed MCP Tool Handlers - Testing different response format

This version tries returning the raw dict instead of JSON string
"""

from typing import Any, Dict, List, Optional

import mcp.types as types

from .tools import ping  # ... other imports remain the same


async def handle_tool_call_fixed(
    name: str, arguments: Optional[Dict[str, Any]], state: Any
) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool calls by routing to appropriate tool functions.

    This version tries to fix the vertical text issue by returning
    the result dict directly as text, not JSON.
    """
    if arguments is None:
        arguments = {}

    try:
        # Just test with ping for now
        if name == "ping":
            result = await ping(echo=arguments.get("echo", ""), state=state)

            # Try different response formats:

            # Option 1: Return the dict as a formatted string (not JSON)
            text = f"Success: {result['success']}\nStatus: {result['status']}\nProvider: {result['provider']}\nEcho: {result['echo']}\nTimestamp: {result['timestamp']}"

            return [types.TextContent(type="text", text=text)]

        else:
            result = {"error": f"Unknown tool: {name}"}
            return [
                types.TextContent(type="text", text=f"Error: Unknown tool '{name}'")
            ]

    except Exception as e:
        return [
            types.TextContent(
                type="text", text=f"Error: Tool execution failed - {str(e)}"
            )
        ]
