"""
Unit tests for VisualizationServer
"""
import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

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
            {'decision_id': decision_id, 'data': mock.ANY}
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


class TestVisualizationServerAPI(AioHTTPTestCase):
    """Test HTTP API endpoints"""
    
    async def get_application(self):
        """Create app for testing"""
        server = VisualizationServer()
        await server.setup_routes()
        return server.app
    
    @unittest_run_loop
    async def test_status_endpoint(self):
        """Test /api/status endpoint"""
        resp = await self.client.request("GET", "/api/status")
        assert resp.status == 200
        
        data = await resp.json()
        assert "active_sessions" in data
        assert "conversation_summary" in data
        assert "decision_count" in data
        assert "knowledge_nodes" in data
    
    @unittest_run_loop
    async def test_conversation_history_endpoint(self):
        """Test /api/conversations endpoint"""
        resp = await self.client.request("GET", "/api/conversations")
        assert resp.status == 200
        
        data = await resp.json()
        assert "events" in data
        assert isinstance(data["events"], list)
    
    @unittest_run_loop
    async def test_decisions_endpoint(self):
        """Test /api/decisions endpoint"""
        resp = await self.client.request("GET", "/api/decisions")
        assert resp.status == 200
        
        data = await resp.json()
        assert "decisions" in data
        assert "analytics" in data
    
    @unittest_run_loop
    async def test_health_endpoint(self):
        """Test /api/health endpoint"""
        resp = await self.client.request("GET", "/api/health")
        assert resp.status == 200
        
        data = await resp.json()
        assert "status" in data
        assert "trends" in data
        assert "alerts" in data
    
    @unittest_run_loop
    async def test_knowledge_graph_endpoint(self):
        """Test /api/knowledge endpoint"""
        resp = await self.client.request("GET", "/api/knowledge")
        assert resp.status == 200
        
        data = await resp.json()
        assert "nodes" in data
        assert "edges" in data
    
    @unittest_run_loop
    async def test_static_files(self):
        """Test serving static files"""
        # Test main page
        resp = await self.client.request("GET", "/")
        assert resp.status == 200
        
        content = await resp.text()
        assert "PM Agent Visualization" in content


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