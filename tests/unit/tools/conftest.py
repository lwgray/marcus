"""
Minimal conftest for tools unit tests.

This overrides the global conftest to avoid MCP/pydantic dependency issues.
"""

# Note: pytest_plugins must be defined at top-level conftest only
# pytest-asyncio is configured in /tests/conftest.py
