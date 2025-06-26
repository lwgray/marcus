"""
Integration tests for VisualizationServer
"""
import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock, ANY
from aiohttp import web

from src.visualization.ui_server import VisualizationServer
from src.visualization.conversation_stream import ConversationEvent
from tests.unit.visualization.factories import (
    create_mock_conversation_event,
    create_mock_decision,
    create_mock_health_data
)


class TestVisualizationServerIntegration:
    """Integration tests for the full server"""
    
    @pytest.mark.asyncio
    async def test_server_startup_shutdown(self):
        """Test server startup and shutdown"""
        server = VisualizationServer(port=0)  # Use random port
        
        # Start server in background
        runner = web.AppRunner(server.app)
        await runner.setup()
        site = web.TCPSite(runner, server.host, server.port)
        await site.start()
        
        # Server should be running
        assert site._server is not None
        
        # Cleanup
        await runner.cleanup()
    
    @pytest.mark.asyncio
    async def test_event_processing_pipeline(self):
        """Test complete event processing pipeline"""
        server = VisualizationServer()
        
        # Mock components
        server.sio.emit = AsyncMock()
        
        # Create and process event
        event = create_mock_conversation_event()
        server.conversation_processor.add_event_handler(
            server.handle_conversation_event
        )
        
        # Process event through pipeline
        await server.conversation_processor._process_log_line(
            json.dumps({
                "timestamp": datetime.now().isoformat(),
                "event": "worker_communication",
                "worker_id": "worker-123",
                "conversation_type": "worker_to_pm",
                "message": "Test message",
                "metadata": {}
            })
        )
        
        # Should have emitted event
        server.sio.emit.assert_called()
    
    @pytest.mark.asyncio
    async def test_concurrent_client_handling(self):
        """Test handling multiple concurrent clients"""
        server = VisualizationServer()
        server.sio.emit = AsyncMock()
        
        # Simulate multiple clients
        clients = [f"client-{i}" for i in range(5)]
        for client in clients:
            server.active_sessions.add(client)
        
        # Broadcast event
        event = create_mock_conversation_event()
        await server.handle_conversation_event(event)
        
        # Should broadcast to all clients
        server.sio.emit.assert_called_once_with(
            'conversation_event',
            event.to_dict()
        )