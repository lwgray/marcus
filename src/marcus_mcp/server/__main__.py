"""
Main entry point for the Marcus MCP server when run as a module.

This allows the server to be executed with: python -m src.marcus_mcp.server
"""

from .main import run

if __name__ == "__main__":
    run()