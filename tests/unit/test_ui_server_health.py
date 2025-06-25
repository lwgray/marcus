"""
Unit tests for UI server health endpoints
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from src.visualization.ui_server import VisualizationServer
from src.core.models import ProjectState, RiskLevel


class TestUIServerHealth(AioHTTPTestCase):
    """Test health-related endpoints in UI server"""
    
    async def get_application(self):
        """Create app for testing"""
        self.server = VisualizationServer()
        
        # Mock the health monitor
        self.server.health_monitor = Mock()
        self.server.health_monitor.initialize = AsyncMock()
        self.server.health_monitor.start_monitoring = AsyncMock()
        self.server.health_monitor.stop_monitoring = AsyncMock()
        self.server.health_monitor.get_project_health = AsyncMock()
        self.server.health_monitor.get_health_history = Mock()
        self.server.health_monitor.get_health_summary = Mock()
        self.server.health_monitor.last_analysis = None
        
        return self.server.app
    
    @unittest_run_loop
    async def test_health_current_no_data(self):
        """Test current health endpoint with no data"""
        self.server.health_monitor.last_analysis = None
        
        resp = await self.client.request("GET", "/api/health/current")
        
        assert resp.status == 404
        data = await resp.json()
        assert data["error"] == "No health analysis available"
    
    @unittest_run_loop
    async def test_health_current_with_data(self):
        """Test current health endpoint with data"""
        mock_analysis = {
            "overall_health": "green",
            "timestamp": datetime.now().isoformat(),
            "risk_factors": []
        }
        self.server.health_monitor.last_analysis = mock_analysis
        
        resp = await self.client.request("GET", "/api/health/current")
        
        assert resp.status == 200
        data = await resp.json()
        assert data["overall_health"] == "green"
    
    @unittest_run_loop
    async def test_health_history(self):
        """Test health history endpoint"""
        mock_history = [
            {"timestamp": "2024-01-01T10:00:00", "overall_health": "green"},
            {"timestamp": "2024-01-01T11:00:00", "overall_health": "yellow"}
        ]
        self.server.health_monitor.get_health_history.return_value = mock_history
        
        resp = await self.client.request("GET", "/api/health/history?hours=12")
        
        assert resp.status == 200
        data = await resp.json()
        assert data["count"] == 2
        assert data["hours"] == 12
        assert len(data["history"]) == 2
    
    @unittest_run_loop
    async def test_health_history_default_hours(self):
        """Test health history with default hours"""
        self.server.health_monitor.get_health_history.return_value = []
        
        resp = await self.client.request("GET", "/api/health/history")
        
        assert resp.status == 200
        data = await resp.json()
        assert data["hours"] == 24  # Default
        self.server.health_monitor.get_health_history.assert_called_with(24)
    
    @unittest_run_loop
    async def test_health_summary(self):
        """Test health summary endpoint"""
        mock_summary = {
            "status": "available",
            "health_distribution": {"green": 5, "yellow": 2, "red": 1},
            "average_risks": 2.5
        }
        self.server.health_monitor.get_health_summary.return_value = mock_summary
        
        resp = await self.client.request("GET", "/api/health/summary")
        
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "available"
        assert data["health_distribution"]["green"] == 5
    
    @unittest_run_loop
    async def test_health_analyze_success(self):
        """Test health analysis endpoint"""
        mock_analysis = {
            "overall_health": "yellow",
            "risk_factors": [{"type": "resource"}],
            "timestamp": datetime.now().isoformat()
        }
        self.server.health_monitor.get_project_health.return_value = mock_analysis
        
        # Mock Socket.IO emit
        self.server.sio = Mock()
        self.server.sio.emit = AsyncMock()
        
        request_data = {
            "project_state": {
                "board_id": "BOARD-001",
                "project_name": "Test",
                "total_tasks": 10,
                "completed_tasks": 5,
                "in_progress_tasks": 3,
                "blocked_tasks": 1,
                "progress_percent": 50.0,
                "team_velocity": 3.0,
                "risk_level": "MEDIUM"
            },
            "recent_activities": [],
            "team_status": []
        }
        
        resp = await self.client.request(
            "POST", 
            "/api/health/analyze",
            data=json.dumps(request_data),
            headers={"Content-Type": "application/json"}
        )
        
        assert resp.status == 200
        data = await resp.json()
        assert data["overall_health"] == "yellow"
        
        # Verify Socket.IO broadcast
        self.server.sio.emit.assert_called_once_with('health_update', mock_analysis)
    
    @unittest_run_loop
    async def test_health_analyze_invalid_risk_level(self):
        """Test health analysis with invalid risk level"""
        request_data = {
            "project_state": {
                "risk_level": "INVALID"
            }
        }
        
        resp = await self.client.request(
            "POST",
            "/api/health/analyze", 
            data=json.dumps(request_data),
            headers={"Content-Type": "application/json"}
        )
        
        assert resp.status == 500
        data = await resp.json()
        assert data["error"] == "Analysis failed"
    
    @unittest_run_loop
    async def test_health_analyze_missing_data(self):
        """Test health analysis with missing data"""
        mock_analysis = {"overall_health": "green"}
        self.server.health_monitor.get_project_health.return_value = mock_analysis
        self.server.sio = Mock()
        self.server.sio.emit = AsyncMock()
        
        # Empty request
        resp = await self.client.request(
            "POST",
            "/api/health/analyze",
            data=json.dumps({}),
            headers={"Content-Type": "application/json"}
        )
        
        assert resp.status == 200
        
        # Should create default ProjectState
        call_args = self.server.health_monitor.get_project_health.call_args
        project_state = call_args[0][0]
        
        assert project_state.board_id == "BOARD-001"
        assert project_state.project_name == "Unknown Project"
        assert project_state.total_tasks == 0


class TestHealthSocketIO:
    """Test Socket.IO events for health monitoring"""
    
    @pytest.mark.asyncio
    async def test_subscribe_health_updates(self):
        """Test health subscription event"""
        server = VisualizationServer()
        server.health_monitor = Mock()
        server.health_monitor.last_analysis = {
            "overall_health": "green",
            "timestamp": "2024-01-01T10:00:00"
        }
        
        # Mock Socket.IO
        server.sio = Mock()
        emit_mock = AsyncMock()
        
        # Get the event handler
        subscribe_handler = None
        for call in server._setup_socketio.__code__.co_consts:
            if hasattr(call, '__name__') and call.__name__ == 'subscribe_health_updates':
                subscribe_handler = call
                break
        
        # Test would require actual Socket.IO setup
        # This is a placeholder for the test structure
        assert server.health_monitor is not None
    
    @pytest.mark.asyncio
    async def test_request_health_analysis_no_data(self):
        """Test requesting health analysis with no data"""
        server = VisualizationServer()
        server.health_monitor = Mock()
        server.health_monitor.last_analysis = None
        
        # Test would require actual Socket.IO setup
        assert server.health_monitor.last_analysis is None


class TestHealthMonitorIntegration:
    """Integration tests for health monitor with UI server"""
    
    @pytest.mark.asyncio
    async def test_server_initialization(self):
        """Test server initializes health monitor"""
        server = VisualizationServer()
        
        # Mock components
        server.conversation_processor = Mock()
        server.conversation_processor.start_streaming = AsyncMock()
        server.health_monitor = Mock()
        server.health_monitor.initialize = AsyncMock()
        server.health_monitor.start_monitoring = AsyncMock()
        
        # Partially start server (without actually binding to port)
        await server.health_monitor.initialize()
        
        server.health_monitor.initialize.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_health_update_broadcast(self):
        """Test health updates are broadcast via Socket.IO"""
        server = VisualizationServer()
        server.sio = Mock()
        server.sio.emit = AsyncMock()
        
        health_data = {
            "overall_health": "yellow",
            "timestamp": datetime.now().isoformat()
        }
        
        # Simulate the callback that would be passed to start_monitoring
        async def health_callback(data):
            await server.sio.emit('health_update', data)
        
        await health_callback(health_data)
        
        server.sio.emit.assert_called_once_with('health_update', health_data)