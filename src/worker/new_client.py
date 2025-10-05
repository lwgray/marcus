"""
Inspector - Unified MCP Client for Worker Agents.

This module provides a unified client that supports both stdio and HTTP connections
to Marcus MCP server, replacing the need for separate client implementations.

Connection Types
----------------
- stdio: Spawns isolated Marcus instance for testing (recommended for development)
- http: Connects to running Marcus HTTP server (recommended for production)

Classes
-------
Inspector
    Unified client class supporting both stdio and HTTP connections

Examples
--------
Basic stdio connection (isolated testing):

>>> import asyncio
>>> from src.worker.new_client import Inspector
>>>
>>> async def worker_main():
...     client = Inspector(connection_type='stdio')
...     async with client.connect() as session:
...         # Register agent
...         result = await client.register_agent(
...             "worker-001",
...             "Backend Developer",
...             "Developer",
...             ["python", "fastapi", "postgresql"]
...         )
...
...         # Work loop
...         while True:
...             task = await client.request_next_task("worker-001")
...             if not task.get('task'):
...                 break
...
...             # Complete task
...             await client.report_task_progress(
...                 "worker-001", task['task']['id'], "completed", 100
...             )
>>>
>>> asyncio.run(worker_main())

Basic HTTP connection (production):

>>> async def worker_main():
...     client = Inspector(connection_type='http')
...     async with client.connect(url="http://localhost:4298/mcp") as session:
...         # Same workflow as stdio
...         result = await client.register_agent(
...             "worker-001", "Developer", "Developer", []
...         )
>>>
>>> asyncio.run(worker_main())

Notes
-----
- stdio: Uses stdio_client to spawn isolated Marcus instance
- http: Uses streamablehttp_client for FastMCP compatibility
- Worker methods work with both connection types
"""

import os
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, List, Literal, Optional, cast

from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from mcp import ClientSession, StdioServerParameters

# Import the original client to inherit helper methods
from src.worker.client import WorkerMCPClient


class Inspector(WorkerMCPClient):
    """
    Unified Worker MCP Client supporting both stdio and HTTP connections.

    This client provides a single interface for connecting to Marcus via either
    stdio (isolated instance) or HTTP (shared server), using the appropriate
    transport for each connection type.

    Attributes
    ----------
    session : Optional[ClientSession]
        The active MCP client session, None if not connected
    connection_type : Literal['stdio', 'http']
        The type of connection to use

    Methods
    -------
    connect(url: Optional[str] = None) -> AsyncIterator[ClientSession]
        Connect to Marcus using the configured connection type
    register_agent(agent_id, name, role, skills) -> Dict[str, Any]
        Register an agent with the Marcus system
    request_next_task(agent_id) -> Dict[str, Any]
        Request the next task assignment for an agent
    report_task_progress(agent_id, task_id, status, progress, message) -> Dict[str, Any]
        Report progress on a task
    report_blocker(agent_id, task_id, description, severity) -> Dict[str, Any]
        Report a blocker on a task
    get_project_status() -> Dict[str, Any]
        Get current project status
    get_agent_status(agent_id) -> Dict[str, Any]
        Get status for a specific agent

    Examples
    --------
    Connect using stdio (isolated testing):

    >>> client = Inspector(connection_type='stdio')
    >>> async with client.connect() as session:
    ...     result = await client.register_agent("worker-1", "Test", "Developer", [])
    ...     print(result)

    Connect using HTTP (production):

    >>> client = Inspector(connection_type='http')
    >>> async with client.connect(url="http://localhost:4298/mcp") as session:
    ...     result = await client.register_agent("worker-1", "Test", "Developer", [])
    ...     print(result)
    """

    def __init__(self, connection_type: Literal["stdio", "http"] = "stdio") -> None:
        """
        Initialize the Inspector client.

        Parameters
        ----------
        connection_type : Literal['stdio', 'http'], default='stdio'
            The type of connection to use:
            - 'stdio': Spawn isolated Marcus instance (recommended for testing)
            - 'http': Connect to running Marcus HTTP server (recommended for production)
        """
        super().__init__()
        self.connection_type = connection_type

    @asynccontextmanager
    async def connect(
        self,
        url: Optional[str] = None,
        timeout: float = 30,
        sse_read_timeout: float = 300,
    ) -> AsyncIterator[ClientSession]:
        """
        Connect to Marcus MCP server using the configured connection type.

        This method automatically uses the appropriate transport (stdio or HTTP)
        based on the connection_type specified during initialization.

        Parameters
        ----------
        url : str, optional
            The HTTP URL of the Marcus MCP server endpoint (required for http mode)
            Default: "http://localhost:4298/mcp"
            Ignored for stdio mode
        timeout : float, optional
            HTTP timeout for regular operations in seconds (http mode only)
            Default: 30
        sse_read_timeout : float, optional
            Timeout for SSE read operations in seconds (http mode only)
            Default: 300

        Yields
        ------
        ClientSession
            An active MCP client session for communicating with Marcus

        Raises
        ------
        RuntimeError
            If connection fails
        ValueError
            If http mode is selected but no URL is provided

        Examples
        --------
        Stdio connection:

        >>> client = Inspector(connection_type='stdio')
        >>> async with client.connect() as session:
        ...     await client.register_agent("worker-1", "Test", "Developer", [])

        HTTP connection:

        >>> client = Inspector(connection_type='http')
        >>> async with client.connect(url="http://localhost:4298/mcp") as session:
        ...     await client.register_agent("worker-1", "Test", "Developer", [])

        Notes
        -----
        - stdio: Spawns isolated Marcus instance for testing
        - http: Connects to running Marcus HTTP server using streamablehttp_client
        - Session cleanup is guaranteed even if exceptions occur
        """
        if self.connection_type == "stdio":
            # Stdio connection - spawn isolated Marcus instance
            project_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..")
            )
            server_cmd = [
                sys.executable,
                "-m",
                "src.marcus_mcp.server",
                "--stdio",  # Force stdio mode to avoid port conflicts
            ]

            # Inherit current environment and add PYTHONPATH
            env = os.environ.copy()
            env["PYTHONPATH"] = project_root

            server_params = StdioServerParameters(
                command=server_cmd[0], args=server_cmd[1:], env=env
            )

            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    self.session = session
                    await session.initialize()

                    # List available tools to verify connection
                    tools_response = await session.list_tools()
                    if hasattr(tools_response, "tools"):
                        tools = tools_response.tools
                    else:
                        tools = cast(List[Any], tools_response)
                    tool_names = [t.name for t in tools]
                    print(
                        f"Connected to Marcus (stdio). "
                        f"Available tools: {tool_names}"
                    )

                    yield session

        elif self.connection_type == "http":
            # HTTP connection - connect to running Marcus server
            if url is None:
                url = "http://localhost:4298/mcp"

            async with streamablehttp_client(
                url,
                timeout=timeout,
                sse_read_timeout=sse_read_timeout,
            ) as (read_stream, write_stream, get_session_id):
                async with ClientSession(read_stream, write_stream) as session:
                    self.session = session
                    await session.initialize()

                    # Get session ID from the transport
                    session_id = get_session_id()
                    if session_id:
                        print(f"Connected to Marcus HTTP server at {url}")
                        print(f"Session ID: {session_id}")

                    # List available tools to verify connection
                    tools_response = await session.list_tools()
                    if hasattr(tools_response, "tools"):
                        tools = tools_response.tools
                    else:
                        tools = cast(List[Any], tools_response)
                    tool_names = [t.name for t in tools]
                    print(f"Available tools: {', '.join(tool_names)}")

                    yield session
        else:
            raise ValueError(
                f"Invalid connection_type: {self.connection_type}. "
                "Must be 'stdio' or 'http'"
            )


# Convenience function to maintain API compatibility
async def create_inspector(
    connection_type: Literal["stdio", "http"] = "stdio",
) -> Inspector:
    """
    Create and return a new Inspector client.

    Parameters
    ----------
    connection_type : Literal['stdio', 'http'], default='stdio'
        The type of connection to use:
        - 'stdio': Spawn isolated Marcus instance (recommended for testing)
        - 'http': Connect to running Marcus HTTP server (recommended for production)

    Returns
    -------
    Inspector
        A new client instance ready for connection

    Examples
    --------
    >>> client = await create_inspector('stdio')
    >>> async with client.connect() as session:
    ...     pass

    >>> client = await create_inspector('http')
    >>> async with client.connect(url="http://localhost:4298/mcp") as session:
    ...     pass
    """
    return Inspector(connection_type)
