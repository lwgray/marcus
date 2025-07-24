"""
Example HTTP Client Implementation for Seneca → Marcus Migration

This demonstrates how to implement the HTTP transport layer for Seneca
to communicate with Marcus MCP server over HTTP instead of stdio.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientError, ClientTimeout

logger = logging.getLogger(__name__)


class MarcusHttpClient:
    """
    HTTP-based MCP client for connecting to Marcus server

    This client implements the same interface as the stdio-based MarcusClient
    but uses HTTP transport instead of stdio pipes.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        Initialize Marcus HTTP client

        Parameters
        ----------
        base_url : Optional[str]
            Base URL for Marcus HTTP endpoint (e.g., "http://localhost:3000")
        timeout : int
            Request timeout in seconds
        """
        self.base_url = base_url
        self.timeout = ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
        self.connected = False
        self._client_id = f"seneca-{uuid.uuid4().hex[:8]}"

    async def connect(self, auto_discover: bool = True) -> bool:
        """
        Connect to Marcus HTTP server

        Parameters
        ----------
        auto_discover : bool
            If True, try to discover running Marcus HTTP endpoints first

        Returns
        -------
        bool
            True if connection successful
        """
        # Try auto-discovery first
        if auto_discover and not self.base_url:
            discovered_endpoint = self._discover_marcus_http_endpoint()
            if discovered_endpoint:
                self.base_url = discovered_endpoint
                logger.info(f"Discovered Marcus HTTP endpoint: {self.base_url}")

        if not self.base_url:
            logger.error(
                "No Marcus HTTP endpoint specified and no running instances found"
            )
            return False

        try:
            # Create HTTP session
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers={
                    "User-Agent": f"Seneca-MCP-Client/1.0 ({self._client_id})",
                    "Content-Type": "application/json",
                },
            )

            # Test connection with ping
            result = await self.ping()
            if result:
                self.connected = True
                logger.info(f"Connected to Marcus HTTP server at {self.base_url}")
                return True
            else:
                await self.disconnect()
                return False

        except Exception as e:
            logger.error(f"Failed to connect to Marcus HTTP endpoint: {e}")
            await self.disconnect()
            return False

    def _discover_marcus_http_endpoint(self) -> Optional[str]:
        """
        Discover running Marcus HTTP endpoints from service registry

        Returns
        -------
        Optional[str]
            HTTP endpoint URL if found, None otherwise
        """
        try:
            import platform

            import psutil

            # Get registry directory
            if platform.system() == "Windows":
                import os
                import tempfile

                base_dir = Path(os.environ.get("APPDATA", tempfile.gettempdir()))
            else:
                base_dir = Path.home()

            registry_dir = base_dir / ".marcus" / "services"

            if not registry_dir.exists():
                return None

            # Read service files looking for HTTP endpoints
            for service_file in registry_dir.glob("marcus_*.json"):
                try:
                    with open(service_file, "r") as f:
                        service_info = json.load(f)

                    # Check if service has HTTP endpoint
                    http_endpoint = service_info.get("http_endpoint")
                    if http_endpoint:
                        # Verify process is still running
                        pid = service_info.get("pid")
                        if pid and psutil.pid_exists(pid):
                            return http_endpoint

                except (json.JSONDecodeError, FileNotFoundError):
                    continue

            return None

        except Exception as e:
            logger.warning(f"HTTP endpoint discovery failed: {e}")
            return None

    async def disconnect(self):
        """Disconnect from Marcus HTTP server"""
        if self.session:
            await self.session.close()
            self.session = None
            self.connected = False
            logger.info("Disconnected from Marcus HTTP server")

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Call a tool on Marcus MCP server via HTTP

        Parameters
        ----------
        tool_name : str
            Name of the tool to call
        arguments : Dict[str, Any], optional
            Arguments to pass to the tool

        Returns
        -------
        Dict[str, Any]
            Tool response
        """
        if not self.connected or not self.session:
            raise ConnectionError("Not connected to Marcus HTTP server")

        # Prepare JSON-RPC request
        request_id = str(uuid.uuid4())
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments or {}},
            "id": request_id,
        }

        try:
            # Make HTTP request
            async with self.session.post(
                f"{self.base_url}/mcp", json=request_data
            ) as response:
                response.raise_for_status()
                result = await response.json()

                # Handle JSON-RPC response
                if "error" in result:
                    error = result["error"]
                    logger.error(f"MCP error: {error.get('message', 'Unknown error')}")
                    return {"error": error.get("message", "Unknown error")}

                # Extract result content
                if "result" in result:
                    content = result["result"].get("content", [])
                    if content and len(content) > 0:
                        return json.loads(content[0].get("text", "{}"))
                    return {}

                return {"error": "Invalid response format"}

        except ClientError as e:
            logger.error(f"HTTP request failed: {tool_name} - {e}")
            return {"error": f"HTTP error: {str(e)}"}
        except Exception as e:
            logger.error(f"Tool call failed: {tool_name} - {e}")
            return {"error": str(e)}

    # Convenience methods matching the original MarcusClient interface

    async def get_project_status(self) -> Dict[str, Any]:
        """Get current project status from Marcus"""
        return await self.call_tool("get_project_status")

    async def list_registered_agents(self) -> List[Dict[str, Any]]:
        """Get list of registered agents"""
        result = await self.call_tool("list_registered_agents")
        return result.get("agents", [])

    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get status of specific agent"""
        return await self.call_tool("get_agent_status", {"agent_id": agent_id})

    async def get_conversations(
        self, limit: int = 100, agent_id: str = None
    ) -> List[Dict[str, Any]]:
        """Get recent conversations"""
        args = {"limit": limit}
        if agent_id:
            args["agent_id"] = agent_id
        result = await self.call_tool("get_conversations", args)
        return result.get("conversations", [])

    async def ping(self) -> Dict[str, Any]:
        """Ping Marcus to check connectivity and identify as Seneca"""
        return await self.call_tool("ping", {"echo": "seneca_http_client"})


class MarcusClientFactory:
    """
    Factory for creating Marcus clients with different transports

    This allows seamless switching between stdio and HTTP transports
    based on configuration or auto-detection.
    """

    @staticmethod
    async def create_client(
        transport: str = "auto",
        stdio_path: Optional[str] = None,
        http_url: Optional[str] = None,
    ) -> Any:
        """
        Create a Marcus client with the specified transport

        Parameters
        ----------
        transport : str
            Transport type: "stdio", "http", or "auto"
        stdio_path : Optional[str]
            Path to Marcus stdio server (for stdio transport)
        http_url : Optional[str]
            URL for Marcus HTTP endpoint (for HTTP transport)

        Returns
        -------
        MarcusClient or MarcusHttpClient
            Configured client instance
        """
        if transport == "http":
            client = MarcusHttpClient(http_url)
            success = await client.connect()
            if not success:
                raise ConnectionError("Failed to connect via HTTP")
            return client

        elif transport == "stdio":
            # Import the original stdio client
            from mcp_client.marcus_client import MarcusClient

            client = MarcusClient(stdio_path)
            success = await client.connect()
            if not success:
                raise ConnectionError("Failed to connect via stdio")
            return client

        else:  # auto mode
            # Try HTTP first if URL provided
            if http_url:
                try:
                    client = MarcusHttpClient(http_url)
                    success = await client.connect(auto_discover=False)
                    if success:
                        logger.info("Auto-selected HTTP transport")
                        return client
                except Exception as e:
                    logger.warning(f"HTTP connection failed, trying stdio: {e}")

            # Fallback to stdio
            from mcp_client.marcus_client import MarcusClient

            client = MarcusClient(stdio_path)
            success = await client.connect()
            if success:
                logger.info("Auto-selected stdio transport")
                return client

            raise ConnectionError("Failed to connect with any transport")


# Example usage and testing
async def test_http_client():
    """Test the HTTP client implementation"""
    # Create HTTP client
    client = MarcusHttpClient("http://localhost:3000")

    try:
        # Connect
        connected = await client.connect(auto_discover=False)
        if not connected:
            print("Failed to connect")
            return

        # Test ping
        print("Testing ping...")
        result = await client.ping()
        print(f"Ping result: {result}")

        # Get project status
        print("\nGetting project status...")
        status = await client.get_project_status()
        print(f"Project status: {json.dumps(status, indent=2)}")

        # List agents
        print("\nListing agents...")
        agents = await client.list_registered_agents()
        print(f"Registered agents: {json.dumps(agents, indent=2)}")

    finally:
        await client.disconnect()


async def test_factory():
    """Test the client factory with auto-detection"""
    print("Testing client factory with auto transport...")

    try:
        # Let factory auto-detect transport
        client = await MarcusClientFactory.create_client(
            transport="auto", http_url="http://localhost:3000"
        )

        # Use the client
        result = await client.ping()
        print(f"Factory client ping: {result}")

        # Check which transport was selected
        if isinstance(client, MarcusHttpClient):
            print("Factory selected HTTP transport")
        else:
            print("Factory selected stdio transport")

    finally:
        if hasattr(client, "disconnect"):
            await client.disconnect()


if __name__ == "__main__":
    # Run tests
    print("Marcus HTTP Client Example")
    print("=" * 50)

    # Test HTTP client directly
    asyncio.run(test_http_client())

    print("\n" + "=" * 50 + "\n")

    # Test factory pattern
    asyncio.run(test_factory())
