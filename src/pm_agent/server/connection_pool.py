"""
Connection pooling implementation for Marcus.

This module provides connection pooling for external services
to reduce overhead and improve performance at scale.
"""

import asyncio
import logging
from typing import Dict, Optional, Any, List
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import subprocess
import json

from pm_agent.config import settings

logger = logging.getLogger(__name__)


class MCPConnection:
    """Represents a single MCP connection."""
    
    def __init__(self, connection_id: str, process: subprocess.Popen):
        self.id = connection_id
        self.process = process
        self.created_at = datetime.utcnow()
        self.last_used = datetime.utcnow()
        self.in_use = False
        self.healthy = True
    
    def is_alive(self) -> bool:
        """Check if the connection process is still alive."""
        return self.process.poll() is None
    
    def mark_used(self):
        """Mark the connection as recently used."""
        self.last_used = datetime.utcnow()
    
    def close(self):
        """Close the connection."""
        if self.is_alive():
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


class MCPConnectionPool:
    """Connection pool for MCP (Model Context Protocol) connections."""
    
    def __init__(
        self,
        service_name: str,
        command: List[str],
        min_connections: int = 2,
        max_connections: int = 10,
        max_idle_time: int = 300,  # 5 minutes
        health_check_interval: int = 60  # 1 minute
    ):
        self.service_name = service_name
        self.command = command
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.max_idle_time = timedelta(seconds=max_idle_time)
        self.health_check_interval = health_check_interval
        
        self.connections: Dict[str, MCPConnection] = {}
        self.available_connections: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._closed = False
        self._health_check_task = None
        
        # Metrics
        self.total_connections_created = 0
        self.total_connections_closed = 0
        self.connection_errors = 0
    
    async def initialize(self):
        """Initialize the connection pool."""
        logger.info(f"Initializing MCP connection pool for {self.service_name}")
        
        # Create minimum connections
        for _ in range(self.min_connections):
            await self._create_connection()
        
        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info(f"Connection pool for {self.service_name} initialized with {len(self.connections)} connections")
    
    async def close(self):
        """Close all connections and shutdown the pool."""
        self._closed = True
        
        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        async with self._lock:
            for conn in self.connections.values():
                conn.close()
                self.total_connections_closed += 1
            self.connections.clear()
        
        logger.info(f"Connection pool for {self.service_name} closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool."""
        if self._closed:
            raise RuntimeError("Connection pool is closed")
        
        connection = None
        try:
            # Try to get an available connection
            try:
                connection = await asyncio.wait_for(
                    self.available_connections.get(),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                # No available connections, create a new one if possible
                if len(self.connections) < self.max_connections:
                    connection = await self._create_connection()
                else:
                    # Wait for a connection to become available
                    connection = await self.available_connections.get()
            
            # Mark connection as in use
            connection.in_use = True
            connection.mark_used()
            
            # Yield the connection for use
            yield connection
            
        except Exception as e:
            logger.error(f"Error getting connection from pool: {e}")
            self.connection_errors += 1
            raise
        finally:
            # Return connection to pool
            if connection:
                connection.in_use = False
                if connection.healthy and not self._closed:
                    await self.available_connections.put(connection)
                else:
                    # Remove unhealthy connection
                    async with self._lock:
                        if connection.id in self.connections:
                            del self.connections[connection.id]
                            connection.close()
                            self.total_connections_closed += 1
    
    async def _create_connection(self) -> MCPConnection:
        """Create a new MCP connection."""
        async with self._lock:
            if len(self.connections) >= self.max_connections:
                raise RuntimeError(f"Maximum connections ({self.max_connections}) reached")
            
            try:
                # Start the MCP process
                process = subprocess.Popen(
                    self.command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Create connection object
                connection_id = f"{self.service_name}_{self.total_connections_created}"
                connection = MCPConnection(connection_id, process)
                
                # Add to pool
                self.connections[connection_id] = connection
                await self.available_connections.put(connection)
                self.total_connections_created += 1
                
                logger.debug(f"Created new connection {connection_id} for {self.service_name}")
                return connection
                
            except Exception as e:
                logger.error(f"Failed to create connection for {self.service_name}: {e}")
                self.connection_errors += 1
                raise
    
    async def _health_check_loop(self):
        """Periodically check connection health and clean up idle connections."""
        while not self._closed:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    async def _perform_health_check(self):
        """Perform health check on all connections."""
        async with self._lock:
            now = datetime.utcnow()
            to_remove = []
            
            for conn_id, conn in self.connections.items():
                # Check if connection is alive
                if not conn.is_alive():
                    logger.warning(f"Connection {conn_id} is dead")
                    conn.healthy = False
                    to_remove.append(conn_id)
                    continue
                
                # Check if connection is idle for too long
                if not conn.in_use and (now - conn.last_used) > self.max_idle_time:
                    if len(self.connections) > self.min_connections:
                        logger.info(f"Removing idle connection {conn_id}")
                        to_remove.append(conn_id)
            
            # Remove unhealthy or idle connections
            for conn_id in to_remove:
                conn = self.connections[conn_id]
                del self.connections[conn_id]
                conn.close()
                self.total_connections_closed += 1
            
            # Ensure minimum connections
            while len(self.connections) < self.min_connections:
                try:
                    await self._create_connection()
                except Exception as e:
                    logger.error(f"Failed to create connection during health check: {e}")
                    break
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        return {
            "service": self.service_name,
            "active_connections": len(self.connections),
            "available_connections": self.available_connections.qsize(),
            "in_use_connections": sum(1 for c in self.connections.values() if c.in_use),
            "total_created": self.total_connections_created,
            "total_closed": self.total_connections_closed,
            "connection_errors": self.connection_errors,
            "min_connections": self.min_connections,
            "max_connections": self.max_connections
        }


class KanbanConnectionPool:
    """Specialized connection pool for Kanban services."""
    
    def __init__(self, kanban_type: str = "planka"):
        self.kanban_type = kanban_type
        self._pools: Dict[str, MCPConnectionPool] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize kanban connection pools."""
        if self._initialized:
            return
        
        # Create pools for different kanban operations
        kanban_config = settings.get('kanban', {})
        
        for operation in ['boards', 'cards', 'lists', 'comments']:
            command = self._get_mcp_command(operation)
            pool = MCPConnectionPool(
                service_name=f"{self.kanban_type}_{operation}",
                command=command,
                min_connections=kanban_config.get('min_connections', 2),
                max_connections=kanban_config.get('max_connections', 10),
                max_idle_time=kanban_config.get('idle_timeout', 300)
            )
            await pool.initialize()
            self._pools[operation] = pool
        
        self._initialized = True
        logger.info(f"Kanban connection pools initialized for {self.kanban_type}")
    
    def _get_mcp_command(self, operation: str) -> List[str]:
        """Get the MCP command for a specific operation."""
        # This would be customized based on the actual MCP server implementation
        return ["npx", "@modelcontextprotocol/server-kanban", f"--operation={operation}"]
    
    @asynccontextmanager
    async def get_connection(self, operation: str):
        """Get a connection for a specific operation."""
        if not self._initialized:
            await self.initialize()
        
        if operation not in self._pools:
            raise ValueError(f"Unknown operation: {operation}")
        
        async with self._pools[operation].get_connection() as conn:
            yield conn
    
    async def close(self):
        """Close all connection pools."""
        for pool in self._pools.values():
            await pool.close()
        self._pools.clear()
        self._initialized = False
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all pools."""
        return {
            pool_name: pool.get_stats()
            for pool_name, pool in self._pools.items()
        }


class ConnectionPoolManager:
    """Manages all connection pools for the Marcus."""
    
    def __init__(self):
        self.pools: Dict[str, Any] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize all connection pools."""
        if self._initialized:
            return
        
        # Initialize Kanban connection pool
        self.pools['kanban'] = KanbanConnectionPool()
        await self.pools['kanban'].initialize()
        
        # Add other service pools as needed
        # self.pools['github'] = GitHubConnectionPool()
        # self.pools['slack'] = SlackConnectionPool()
        
        self._initialized = True
        logger.info("Connection pool manager initialized")
    
    async def close(self):
        """Close all connection pools."""
        for pool in self.pools.values():
            if hasattr(pool, 'close'):
                await pool.close()
        self.pools.clear()
        self._initialized = False
    
    def get_pool(self, service: str) -> Any:
        """Get a specific connection pool."""
        if not self._initialized:
            raise RuntimeError("Connection pool manager not initialized")
        
        if service not in self.pools:
            raise ValueError(f"Unknown service: {service}")
        
        return self.pools[service]
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all connection pools."""
        stats = {}
        for service, pool in self.pools.items():
            if hasattr(pool, 'get_all_stats'):
                stats[service] = pool.get_all_stats()
            elif hasattr(pool, 'get_stats'):
                stats[service] = pool.get_stats()
        return stats


# Example usage
async def example_usage():
    """Example of using the connection pools."""
    manager = ConnectionPoolManager()
    await manager.initialize()
    
    try:
        # Get kanban pool
        kanban_pool = manager.get_pool('kanban')
        
        # Use a connection for a cards operation
        async with kanban_pool.get_connection('cards') as conn:
            # Send request through the connection
            request = json.dumps({
                "method": "createCard",
                "params": {
                    "title": "New Task",
                    "listId": "list123"
                }
            })
            conn.process.stdin.write(request + '\n')
            conn.process.stdin.flush()
            
            # Read response
            response = conn.process.stdout.readline()
            result = json.loads(response)
            print(f"Created card: {result}")
        
        # Get pool statistics
        stats = manager.get_all_stats()
        print(f"Pool stats: {json.dumps(stats, indent=2)}")
        
    finally:
        await manager.close()


if __name__ == "__main__":
    asyncio.run(example_usage())