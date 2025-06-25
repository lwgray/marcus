"""
Worker package for PM Agent.

This package provides the core infrastructure for worker agents to communicate
with the PM Agent server through the Model Context Protocol (MCP). It handles
agent registration, task requests, progress reporting, and error handling.

The worker package is designed to enable autonomous agents to:
- Register themselves with the PM Agent system
- Request and receive task assignments
- Report progress and completion status
- Handle blockers and errors gracefully
- Maintain reliable communication with the PM Agent server

Modules
-------
mcp_client : module
    MCP client implementation for worker-to-server communication

Examples
--------
Basic usage for creating a worker agent:

>>> from src.worker.mcp_client import WorkerMCPClient
>>> client = WorkerMCPClient()
>>> async with client.connect_to_pm_agent() as session:
...     await client.register_agent("worker-1", "Test Worker", "Developer", ["python"])
...     task = await client.request_next_task("worker-1")

Notes
-----
This package requires an active PM Agent MCP server to be running for
proper functionality. Workers operate in isolation and cannot directly
communicate with each other.
"""