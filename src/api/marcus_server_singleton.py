"""
Singleton Marcus Server instance for API usage

Provides a shared Marcus server instance that the API can use
to maintain state across requests.
"""

import asyncio
import os
from typing import Optional

from src.marcus_mcp.server import MarcusServer


class MarcusServerSingleton:
    """Singleton pattern for Marcus server instance."""
    
    _instance: Optional['MarcusServerSingleton'] = None
    _server: Optional[MarcusServer] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def get_server(self) -> MarcusServer:
        """Get or create the Marcus server instance."""
        if not self._initialized:
            await self.initialize()
        return self._server
    
    async def initialize(self):
        """Initialize the Marcus server if not already done."""
        if self._initialized:
            return
            
        # Create server instance
        self._server = MarcusServer()
        
        # Initialize the server
        await self._server.initialize()
        
        # Start background monitoring
        asyncio.create_task(self._server.token_tracker.start_monitoring())
        
        self._initialized = True
        
    async def shutdown(self):
        """Shutdown the server gracefully."""
        if self._server and self._initialized:
            await self._server.token_tracker.stop_monitoring()
            self._initialized = False


# Global singleton instance
marcus_server_singleton = MarcusServerSingleton()


async def get_marcus_server() -> MarcusServer:
    """Get the shared Marcus server instance."""
    return await marcus_server_singleton.get_server()