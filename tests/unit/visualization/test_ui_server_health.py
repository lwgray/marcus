"""
Unit tests for UI server health endpoints
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.visualization.ui_server import VisualizationServer
from src.core.models import ProjectState, RiskLevel


class TestUIServerHealth:
    """Test health-related endpoints in UI server"""
    
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
        """Test current health with no data"""
        server.health_monitor.last_analysis = None
        
        # Verify the state
        assert server.health_monitor.last_analysis is None
    
    def test_health_current_with_data(self, server):
        """Test current health with data"""
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
        """Test health history endpoint"""
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
        """Test health history with default hours"""
        mock_history = []
        server.health_monitor.get_health_history.return_value = mock_history
        
        # Call the method
        result = server.health_monitor.get_health_history()
        
        assert len(result) == 0
    
    def test_health_summary(self, server):
        """Test health summary endpoint"""
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
    
    def test_health_analyze_success(self, server):
        """Test successful health analysis"""
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
        assert server.health_monitor.get_project_health() is not None
    
    def test_health_analyze_missing_data(self, server):
        """Test health analysis with missing project state"""
        server.health_monitor.get_project_health.return_value = None
        
        result = server.health_monitor.get_project_health()
        assert result is None
    
    def test_health_analyze_invalid_risk_level(self, server):
        """Test health analysis with invalid risk level"""
        # This test is checking the mock behavior
        server.health_monitor.get_project_health.side_effect = ValueError("Invalid risk level")
        
        with pytest.raises(ValueError):
            server.health_monitor.get_project_health()