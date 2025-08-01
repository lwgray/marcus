"""
Marcus MCP Server Module.

This module provides backward compatibility while organizing the server
functionality into logical components.
"""

# Import main server class for backward compatibility
from .core import MarcusServer

# Import key functions that might be used externally
from .lifecycle import run_multi_endpoint_server
from .transport import create_endpoint_app, create_fastmcp

# Maintain backward compatibility
__all__ = [
    "MarcusServer",
    "run_multi_endpoint_server",
    "create_fastmcp",
    "create_endpoint_app",
]

# Import Path for test compatibility
from pathlib import Path  # noqa: F401

# Import commonly used items for test compatibility
from mcp.server.stdio import stdio_server  # noqa: F401

from src.config.config_loader import get_config  # noqa: F401
from src.core.service_registry import register_marcus_service  # noqa: F401


# Lazy loading for less common imports
def __getattr__(name):
    """Lazy import for backward compatibility."""
    if name == "main":
        from .main import main

        return main
    if name == "ServerInitializer":
        from .initialization import ServerInitializer

        return ServerInitializer
    if name == "LifecycleManager":
        from .lifecycle import LifecycleManager

        return LifecycleManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
