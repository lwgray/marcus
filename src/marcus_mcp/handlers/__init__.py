"""
MCP Handlers Module.

This module organizes tool handling functionality into logical components.
"""

# Core exports
from .tool_definitions import (
    get_all_tool_definitions,
    get_all_tool_names,
    get_tool_definitions,
)
from .tool_executor import handle_tool_call

__all__ = [
    "get_all_tool_definitions",
    "get_all_tool_names",
    "get_tool_definitions",
    "handle_tool_call",
]
