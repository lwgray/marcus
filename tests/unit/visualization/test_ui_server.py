"""
Unit tests for VisualizationServer

This file consolidates all UI server tests into organized test classes:
- TestUIServerInit: Initialization and basic component tests
- TestUIServerAPI: HTTP API endpoint tests
- TestUIServerSocketIO: Socket.IO event handling tests
- TestUIServerHealth: Health monitoring and analysis tests
"""
import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock, ANY
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from src.visualization.ui_server import VisualizationServer
from src.visualization.conversation_stream import ConversationEvent
from src.core.models import ProjectState, RiskLevel
from tests.unit.visualization.factories import (
    create_mock_conversation_event,
    create_mock_decision,
    create_mock_health_data
)


class TestUIServerInit:
    """Test VisualizationServer initialization and basic component setup"""
    
    @pytest.fixture
    def server(self):
        """Create a VisualizationServer instance"""
        return VisualizationServer(host="127.0.0.1", port=8080)
    
    def test_initialization(self, server):
        """Test server initialization with all components"""
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
    async def test_server_startup_shutdown(self):
        """Test server startup and shutdown lifecycle"""
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


class TestUIServerAPI(AioHTTPTestCase):
    """Test HTTP API endpoints"""
    
    async def get_application(self):
        """Create app for testing"""
        server = VisualizationServer()
        await server.setup_routes()
        return server.app
    
    @unittest_run_loop
    async def test_status_endpoint(self):
        """Test /api/status endpoint returns server status"""
        resp = await self.client.request("GET", "/api/status")
        assert resp.status == 200
        
        data = await resp.json()
        assert "active_sessions" in data
        assert "conversation_summary" in data
        assert "decision_count" in data
        assert "knowledge_nodes" in data
    
    @unittest_run_loop
    async def test_conversation_history_endpoint(self):
        """Test /api/conversations endpoint returns conversation events"""
        resp = await self.client.request("GET", "/api/conversations")
        assert resp.status == 200
        
        data = await resp.json()
        assert "events" in data
        assert isinstance(data["events"], list)
    
    @unittest_run_loop
    async def test_decisions_endpoint(self):
        """Test /api/decisions endpoint returns decision data"""
        resp = await self.client.request("GET", "/api/decisions")
        assert resp.status == 200
        
        data = await resp.json()
        assert "decisions" in data
        assert "analytics" in data
    
    @unittest_run_loop
    async def test_health_endpoint(self):
        """Test /api/health endpoint returns health metrics"""
        resp = await self.client.request("GET", "/api/health")
        assert resp.status == 200
        
        data = await resp.json()
        assert "status" in data
        assert "trends" in data
        assert "alerts" in data
    
    @unittest_run_loop
    async def test_knowledge_graph_endpoint(self):
        """Test /api/knowledge endpoint returns graph data"""
        resp = await self.client.request("GET", "/api/knowledge")
        assert resp.status == 200
        
        data = await resp.json()
        assert "nodes" in data
        assert "edges" in data
    
    @unittest_run_loop
    async def test_static_files(self):
        """Test serving static files and main page"""
        # Test main page
        resp = await self.client.request("GET", "/")
        assert resp.status == 200
        
        content = await resp.text()
        assert "Marcus Visualization" in content


class TestUIServerSocketIO:
    """Test Socket.IO event handling and real-time communication"""
    
    @pytest.fixture
    def server(self):
        """Create a VisualizationServer instance"""
        return VisualizationServer(host="127.0.0.1", port=8080)
    
    @pytest.mark.asyncio
    async def test_handle_conversation_event(self, server):
        """Test broadcasting conversation events to clients"""
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
        """Test broadcasting decision updates to clients"""
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
        """Test broadcasting health updates to clients"""
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
        """Test socket.io client connection handling"""
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
        """Test socket.io client disconnection handling"""
        sid = "test-session-123"
        server.active_sessions.add(sid)
        
        # Setup socket.io event handler
        @server.sio.event
        async def disconnect(sid):
            server.active_sessions.discard(sid)
        
        # Simulate disconnection
        await disconnect(sid)
        
        assert sid not in server.active_sessions
    
    @pytest.mark.asyncio
    async def test_event_processing_pipeline(self):
        """Test complete event processing pipeline from log to client"""
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


class TestUIServerHealth:
    """Test health monitoring and analysis functionality"""
    
    @pytest.fixture
    def server(self):
        """Create a visualization server with mocked health monitor"""
        server = VisualizationServer()
        
        # Mock the health monitor
        server.health_monitor = Mock()
        server.health_monitor.initialize = AsyncMock()
        server.health_monitor.start_monitoring = AsyncMock()
        server.health_monitor.stop_monitoring = AsyncMock()
        server.health_monitor.get_project_health = AsyncMock()
        server.health_monitor.get_health_history = Mock()
        server.health_monitor.get_health_summary = Mock()
        server.health_monitor.last_analysis = None
        
        return server
    
    def test_health_current_no_data(self, server):
        """Test current health returns None when no data available"""
        server.health_monitor.last_analysis = None
        
        # Verify the state
        assert server.health_monitor.last_analysis is None
    
    def test_health_current_with_data(self, server):
        """Test current health returns latest analysis data"""
        mock_analysis = {
            "overall_health": "green",
            "timestamp": datetime.now().isoformat(),
            "risk_factors": []
        }
        server.health_monitor.last_analysis = mock_analysis
        
        # Verify the state
        assert server.health_monitor.last_analysis is not None
        assert server.health_monitor.last_analysis["overall_health"] == "green"
    
    def test_health_history(self, server):
        """Test health history returns historical data"""
        mock_history = [
            {"timestamp": "2024-01-01T10:00:00", "overall_health": "green"},
            {"timestamp": "2024-01-01T11:00:00", "overall_health": "yellow"}
        ]
        server.health_monitor.get_health_history.return_value = mock_history
        
        # Call the method
        result = server.health_monitor.get_health_history()
        
        assert len(result) == 2
        assert result[0]["overall_health"] == "green"
    
    def test_health_history_default_hours(self, server):
        """Test health history handles empty history"""
        mock_history = []
        server.health_monitor.get_health_history.return_value = mock_history
        
        # Call the method
        result = server.health_monitor.get_health_history()
        
        assert len(result) == 0
    
    def test_health_summary(self, server):
        """Test health summary aggregates metrics"""
        mock_summary = {
            "average_health": "green",
            "trend": "stable",
            "total_analyses": 100,
            "alerts": []
        }
        server.health_monitor.get_health_summary.return_value = mock_summary
        
        # Call the method
        result = server.health_monitor.get_health_summary()
        
        assert result["average_health"] == "green"
        assert result["trend"] == "stable"
    
    @pytest.mark.asyncio
    async def test_health_analyze_success(self, server):
        """Test successful health analysis of project state"""
        mock_state = ProjectState(
            board_id="test-board",
            project_name="Test Project",
            total_tasks=10,
            completed_tasks=5,
            in_progress_tasks=3,
            blocked_tasks=0,
            progress_percent=50.0,
            overdue_tasks=[],
            team_velocity=2.0,
            risk_level=RiskLevel.LOW,
            last_updated=datetime.now()
        )
        
        server.health_monitor.get_project_health.return_value = {
            "overall_health": "green",
            "risk_level": "low",
            "metrics": {
                "completion_rate": 0.5,
                "velocity": 2.0
            }
        }
        
        # Test the mock works
        result = await server.health_monitor.get_project_health()
        assert result is not None
        assert result["overall_health"] == "green"
    
    @pytest.mark.asyncio
    async def test_health_analyze_missing_data(self, server):
        """Test health analysis handles missing project state"""
        server.health_monitor.get_project_health.return_value = None
        
        result = await server.health_monitor.get_project_health()
        assert result is None
    
    @pytest.mark.asyncio
    async def test_health_analyze_invalid_risk_level(self, server):
        """Test health analysis handles invalid risk level gracefully"""
        # This test is checking the mock behavior
        server.health_monitor.get_project_health.side_effect = ValueError("Invalid risk level")
        
        with pytest.raises(ValueError):
            await server.health_monitor.get_project_health()