#!/usr/bin/env python3
"""
Marcus Agent MCP Server

A restricted MCP server for coding agents with limited tool access.
This server only exposes the tools necessary for agents to perform their tasks.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import mcp.types as types  # noqa: E402

from src.marcus_mcp.handlers import get_tool_definitions
from src.marcus_mcp.server import MarcusServer


class AgentMarcusServer(MarcusServer):
    """Marcus MCP Server configured specifically for coding agents"""

    def _register_handlers(self) -> None:
        """Register MCP tool handlers with agent restrictions"""

        @self.server.list_tools()  # type: ignore[no-untyped-call,misc]
        async def handle_list_tools() -> List[types.Tool]:
            """Return list of available tools for agents"""
            # Force "agent" role to restrict tool access
            return get_tool_definitions(role="agent")

        # Use parent class tool handler
        @self.server.call_tool()  # type: ignore[no-untyped-call,misc]
        async def handle_call_tool(
            name: str, arguments: Optional[Dict[str, Any]]
        ) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Handle tool calls"""
            # Check if this is an allowed agent tool
            allowed_tools = [
                "register_agent",
                "get_agent_status",
                "list_registered_agents",
                "request_next_task",
                "report_task_progress",
                "report_blocker",
                "get_project_status",
                "ping",
                "check_assignment_health",
            ]

            if name not in allowed_tools:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error: Tool '{name}' is not available to agents",
                    )
                ]

            # Call parent handler
            from src.marcus_mcp.handlers import handle_tool_call

            return await handle_tool_call(name, arguments, self)


async def main() -> None:
    """Main entry point for agent server"""
    import sys

    server = AgentMarcusServer()
    print("\nMarcus Agent MCP Server Running (Restricted Tools)", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
