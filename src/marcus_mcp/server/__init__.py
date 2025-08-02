"""
Marcus MCP Server Module.

This module organizes server functionality into logical components.
"""

# Core exports
from .core import MarcusServer
from .handlers import ProtocolHandlers
from .initialization import ServerInitializer
from .lifecycle import LifecycleManager, run_multi_endpoint_server
from .main import main, run
from .tool_registry import ToolRegistry
from .transport import TransportManager, create_endpoint_app, create_fastmcp

__all__ = [
    "MarcusServer",
    "ServerInitializer",
    "ProtocolHandlers",
    "LifecycleManager",
    "ToolRegistry",
    "TransportManager",
    "run_multi_endpoint_server",
    "create_fastmcp",
    "create_endpoint_app",
    "main",
    "run",
]
