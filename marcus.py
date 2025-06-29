#!/usr/bin/env python3
"""
Marcus MCP Server - Entry Point

This is the main entry point for the Marcus MCP server.
It delegates to the modularized implementation in src/mcp/
"""

import asyncio
from src.mcp import main

if __name__ == "__main__":
    asyncio.run(main())