"""
Worker package for Marcus.

This package provides the MCP client for testing Marcus workflows and
validating Marcus functionality. Inspector supports both stdio (isolated
testing) and HTTP (integration testing) connections.

The Inspector client enables:
- Testing Marcus MCP tool functionality
- Validating task assignment workflows
- Debugging Marcus coordination logic
- Simulating agent behavior for development

Classes
-------
Inspector
    Unified MCP testing client supporting stdio and HTTP connections

Examples
--------
Test Marcus with isolated stdio connection:

>>> from src.worker import Inspector
>>> client = Inspector(connection_type='stdio')
>>> async with client.connect() as session:
...     # Test Marcus functionality
...     await client.register_agent("test-1", "Test Agent", "Developer", ["python"])
...     task = await client.request_next_task("test-1")

Test Marcus with HTTP connection:

>>> from src.worker import Inspector
>>> client = Inspector(connection_type='http')
>>> async with client.connect(url="http://localhost:4298/mcp") as session:
...     # Test against running Marcus instance
...     await client.register_agent("test-1", "Test Agent", "Developer", [])

Notes
-----
Inspector is designed for TESTING Marcus, not for production AI agents.
Use stdio for isolated tests, HTTP for integration testing against a
running Marcus server.
"""

from src.worker.inspector import Inspector, create_inspector

__all__ = ['Inspector', 'create_inspector']
