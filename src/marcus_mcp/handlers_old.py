#!/usr/bin/env python3
"""
MCP Handlers - Compatibility Shim.

This file provides backward compatibility while the actual implementation
has been refactored into the handlers/ submodule.
"""

# Import everything from the refactored modules
from .handlers import (
    get_all_tool_definitions,
    get_all_tool_names,
    get_tool_definitions,
    handle_tool_call,
)

# Maintain backward compatibility
__all__ = [
    "get_all_tool_definitions",
    "get_all_tool_names",
    "get_tool_definitions",
    "handle_tool_call",
]