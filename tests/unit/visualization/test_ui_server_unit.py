"""
Unit tests for VisualizationServer components
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


class TestVisualizationServerUnit:
    """Unit tests for VisualizationServer components"""
    
    @pytest.fixture
    def server(self):
        """Create a VisualizationServer instance"""
        return VisualizationServer(host="127.0.0.1", port=8080)
    
    def test_initialization(self, server):
        """Test server initialization"""
        assert server.host == "127.0.0.1"
        assert server.port == 8080
        assert server.app is not None
        assert server.sio is not None
        assert server.conversation_processor is not None
        assert server.decision_visualizer is not None
        assert server.knowledge_graph is not None
        assert server.health_monitor is not None
        assert len(server.active_sessions) == 0
    
    @pytest.mark.asyncio
    async def test_handle_conversation_event(self, server):
        """Test handling conversation events"""
        event = create_mock_conversation_event()
        
        # Mock socket.io emit
        server.sio.emit = AsyncMock()
        
        await server.handle_conversation_event(event)
        
        # Should emit event to connected clients
        server.sio.emit.assert_called_once_with(
            'conversation_event',
            event.to_dict()
        )
    
    @pytest.mark.asyncio
    async def test_handle_decision_event(self, server):
        """Test handling decision events"""
        decision_data = create_mock_decision()
        
        # Mock socket.io emit
        server.sio.emit = AsyncMock()
        
        # Add decision
        decision_id = server.decision_visualizer.add_decision(decision_data)
        
        # Emit decision update
        await server.emit_decision_update(decision_id)
        
        server.sio.emit.assert_called_with(
            'decision_update',
            {'decision_id': decision_id, 'data': ANY}
        )
    
    @pytest.mark.asyncio
    async def test_handle_health_update(self, server):
        """Test handling health updates"""
        health_data = create_mock_health_data()
        
        # Mock socket.io emit
        server.sio.emit = AsyncMock()
        
        await server.emit_health_update(health_data)
        
        server.sio.emit.assert_called_once_with(
            'health_update',
            health_data
        )
    
    @pytest.mark.asyncio
    async def test_socketio_connect(self, server):
        """Test socket.io connection handling"""
        sid = "test-session-123"
        environ = {}
        
        # Setup socket.io event handler
        @server.sio.event
        async def connect(sid, environ):
            server.active_sessions.add(sid)
            await server.sio.emit('connected', {'message': 'Welcome!'}, to=sid)
        
        # Simulate connection
        await connect(sid, environ)
        
        assert sid in server.active_sessions
    
    @pytest.mark.asyncio
    async def test_socketio_disconnect(self, server):
        """Test socket.io disconnection handling"""
        sid = "test-session-123"
        server.active_sessions.add(sid)
        
        # Setup socket.io event handler
        @server.sio.event
        async def disconnect(sid):
            server.active_sessions.discard(sid)
        
        # Simulate disconnection
        await disconnect(sid)
        
        assert sid not in server.active_sessions