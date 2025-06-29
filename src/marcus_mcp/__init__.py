"""
Marcus MCP (Model Context Protocol) Server

This package contains the MCP server implementation for Marcus,
organized into modular components for better maintainability.
"""

from .server import MarcusServer, main

__all__ = ['MarcusServer', 'main']