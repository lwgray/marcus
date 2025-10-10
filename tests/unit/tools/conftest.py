"""
Minimal conftest for tools unit tests.

This overrides the global conftest to avoid MCP/pydantic dependency issues.
"""

# Minimal async configuration for pytest-asyncio
pytest_plugins = ("pytest_asyncio",)
