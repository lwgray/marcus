"""
MCP Handlers Module.

This module provides backward compatibility while the actual implementation
has been refactored into submodules for better organization.
"""

# Import main functions for backward compatibility
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
