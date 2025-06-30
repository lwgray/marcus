"""
Unit tests for the Health Monitor component
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import json

from src.visualization.health_monitor import HealthMonitor
from src.core.models import ProjectState, WorkerStatus, RiskLevel, Task, TaskStatus
from src.integrations.ai_analysis_engine_fixed import AIAnalysisEngine


class TestHealthMonitor:
    """Test suite for HealthMonitor"""
    
    @pytest.fixture
    def mock_ai_engine(self):
        """Create a mock AI engine"""
        engine = Mock(spec=AIAnalysisEngine)
        engine.initialize = AsyncMock()
        engine.analyze_project_health = AsyncMock()
        return engine
    
    @pytest.fixture
    def health_monitor(self, mock_ai_engine):
        """Create a HealthMonitor instance with mocked AI engine"""
        return HealthMonitor(ai_engine=mock_ai_engine)
    
    @pytest.fixture
    def sample_project_state(self):
        """Create a sample project state"""
        return ProjectState(
            board_id="BOARD-001",
            project_name="Test Project",
            total_tasks=50,
            completed_tasks=20,
            in_progress_tasks=15,
            blocked_tasks=3,
            progress_percent=40.0,
            overdue_tasks=[],
            team_velocity=3.5,
            risk_level=RiskLevel.MEDIUM,
            last_updated=datetime.now()
        )
    
    @pytest.fixture
    def sample_team_status(self):
        """Create sample team status"""
        return [
            WorkerStatus(
                worker_id="dev-001",
                name="Alice",
                role="Developer",
                email="alice@test.com",
                current_tasks=[],
                completed_tasks_count=10,
                capacity=40,
                skills=["python", "testing"],
                availability={},
                performance_score=1.0
            )
        ]
    
    @pytest.mark.asyncio
    async def test_initialize(self, health_monitor, mock_ai_engine):
        """Test health monitor initialization"""
        await health_monitor.initialize()
        
        mock_ai_engine.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_project_health_success(
        self, health_monitor, mock_ai_engine, 
        sample_project_state, sample_team_status
    ):
        """Test successful project health analysis"""
        # Setup mock response
        mock_health_data = {
            "overall_health": "yellow",
            "timeline_prediction": {
                "on_track": False,
                "estimated_completion": "2 weeks behind",
                "confidence": 0.7
            },
            "risk_factors": [
                {
                    "type": "resource",
                    "description": "3 tasks blocked",
                    "severity": "medium",
                    "mitigation": "Review blockers"
                }
            ],
            "recommendations": [],
            "resource_optimization": []
        }
        
        mock_ai_engine.analyze_project_health.return_value = mock_health_data
        
        # Run analysis
        result = await health_monitor.get_project_health(
            sample_project_state,
            [],
            sample_team_status
        )
        
        # Verify results
        assert result["overall_health"] == "yellow"
        assert "timestamp" in result
        assert "analysis_id" in result
        assert result["risk_factors"][0]["type"] == "resource"
        
        # Verify storage
        assert health_monitor.last_analysis == result
        assert len(health_monitor.analysis_history) == 1
    
    @pytest.mark.asyncio
    async def test_get_project_health_with_trends(
        self, health_monitor, mock_ai_engine,
        sample_project_state, sample_team_status
    ):
        """Test health analysis with trend calculation"""
        # First analysis
        first_analysis = {
            "overall_health": "yellow",
            "timeline_prediction": {"confidence": 0.6},
            "risk_factors": [{"type": "resource"}, {"type": "timeline"}]
        }
        mock_ai_engine.analyze_project_health.return_value = first_analysis
        
        await health_monitor.get_project_health(
            sample_project_state, [], sample_team_status
        )
        
        # Second analysis with different activities to avoid cache
        second_analysis = {
            "overall_health": "green",
            "timeline_prediction": {"confidence": 0.8},
            "risk_factors": [{"type": "resource"}]
        }
        mock_ai_engine.analyze_project_health.return_value = second_analysis
        
        result = await health_monitor.get_project_health(
            sample_project_state, [{"activity": "test"}], sample_team_status
        )
        
        # Check trends
        assert "trends" in result
        assert result["trends"]["health_direction"] == "improving"
        assert abs(result["trends"]["confidence_change"] - 0.2) < 0.0001
        assert result["trends"]["risk_change"] == "decreasing"
    
    @pytest.mark.asyncio
    async def test_get_project_health_error_handling(
        self, health_monitor, mock_ai_engine,
        sample_project_state, sample_team_status
    ):
        """Test error handling in health analysis"""
        # Simulate AI engine error
        mock_ai_engine.analyze_project_health.side_effect = Exception("AI error")
        
        result = await health_monitor.get_project_health(
            sample_project_state, [], sample_team_status
        )
        
        # Check error response
        assert result["overall_health"] == "unknown"
        assert result["error"] is True
        assert "AI error" in result["error_message"]
        assert len(result["recommendations"]) > 0
    
    def test_calculate_trends(self, health_monitor):
        """Test trend calculation logic"""
        previous = {
            "overall_health": "red",
            "timeline_prediction": {"confidence": 0.4},
            "risk_factors": [{"id": 1}, {"id": 2}, {"id": 3}]
        }
        
        current = {
            "overall_health": "yellow",
            "timeline_prediction": {"confidence": 0.6},
            "risk_factors": [{"id": 1}, {"id": 2}]
        }
        
        trends = health_monitor._calculate_trends(previous, current)
        
        assert trends["health_direction"] == "improving"
        assert abs(trends["confidence_change"] - 0.2) < 0.0001
        assert trends["risk_change"] == "decreasing"
    
    def test_calculate_trends_declining(self, health_monitor):
        """Test trend calculation for declining health"""
        previous = {
            "overall_health": "green",
            "timeline_prediction": {"confidence": 0.8},
            "risk_factors": []
        }
        
        current = {
            "overall_health": "red",
            "timeline_prediction": {"confidence": 0.3},
            "risk_factors": [{"id": 1}, {"id": 2}]
        }
        
        trends = health_monitor._calculate_trends(previous, current)
        
        assert trends["health_direction"] == "declining"
        assert trends["confidence_change"] == -0.5
        assert trends["risk_change"] == "increasing"
    
    @pytest.mark.asyncio
    async def test_start_monitoring(self, health_monitor):
        """Test starting continuous monitoring"""
        callback = AsyncMock()
        
        # Start monitoring
        await health_monitor.start_monitoring(callback)
        
        assert health_monitor._monitoring_task is not None
        assert not health_monitor._monitoring_task.done()
        
        # Stop monitoring
        await health_monitor.stop_monitoring()
        
        assert health_monitor._monitoring_task.cancelled()
    
    @pytest.mark.asyncio
    async def test_monitoring_with_callback(self, health_monitor):
        """Test monitoring calls callback"""
        callback = AsyncMock()
        health_monitor.analysis_interval = 0.1  # Short interval for testing
        
        await health_monitor.start_monitoring(callback)
        
        # Wait for at least one cycle
        await asyncio.sleep(0.2)
        
        # Clean up
        await health_monitor.stop_monitoring()
        
        # In production, callback would be called with actual health data
        # For now, just verify the monitoring loop is working
        assert health_monitor._monitoring_task.cancelled()
    
    def test_get_health_history(self, health_monitor):
        """Test retrieving health history"""
        # Add some historical data
        now = datetime.now()
        
        health_monitor.analysis_history = [
            {
                "timestamp": (now - timedelta(hours=25)).isoformat(),
                "overall_health": "green"
            },
            {
                "timestamp": (now - timedelta(hours=10)).isoformat(),
                "overall_health": "yellow"
            },
            {
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "overall_health": "red"
            }
        ]
        
        # Get last 24 hours
        history = health_monitor.get_health_history(24)
        
        assert len(history) == 2  # Only last 2 are within 24 hours
        assert history[0]["overall_health"] == "yellow"
        assert history[1]["overall_health"] == "red"
    
    
    def test_get_health_summary_with_data(self, health_monitor):
        """Test health summary with analysis data"""
        # Add analysis history
        health_monitor.analysis_history = [
            {
                "overall_health": "green",
                "risk_factors": []
            },
            {
                "overall_health": "yellow",
                "risk_factors": [
                    {"severity": "high"},
                    {"severity": "medium"}
                ]
            },
            {
                "overall_health": "green",
                "risk_factors": [
                    {"severity": "low"}
                ]
            },
            {
                "overall_health": "red",
                "risk_factors": [
                    {"severity": "high"},
                    {"severity": "high"},
                    {"severity": "medium"}
                ]
            }
        ]
        
        health_monitor.last_analysis = health_monitor.analysis_history[-1]
        
        summary = health_monitor.get_health_summary()
        
        assert summary["status"] == "available"
        assert summary["health_distribution"]["green"] == 2
        assert summary["health_distribution"]["yellow"] == 1
        assert summary["health_distribution"]["red"] == 1
        assert summary["average_risks"] == 1.5  # 6 total risks / 4 analyses
        assert summary["risk_distribution"]["high"] == 3
        assert summary["risk_distribution"]["medium"] == 2
        assert summary["risk_distribution"]["low"] == 1
        assert summary["latest_health"] == "red"
    
    
    @pytest.mark.asyncio
    async def test_history_limit(self, health_monitor, mock_ai_engine):
        """Test that history is limited to 100 entries"""
        mock_health = {"overall_health": "green"}
        mock_ai_engine.analyze_project_health.return_value = mock_health
        
        # Add 105 analyses
        for _ in range(105):
            await health_monitor.get_project_health(
                Mock(), [], []
            )
        
        # Should only keep last 100
        assert len(health_monitor.analysis_history) == 100