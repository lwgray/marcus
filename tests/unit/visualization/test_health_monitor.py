"""
Unit tests for HealthMonitor
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.visualization.health_monitor import HealthMonitor
from src.core.models import ProjectState, RiskLevel, WorkerStatus
from tests.unit.visualization.factories import (
    create_mock_project_state,
    create_mock_worker_status,
    create_mock_health_data
)


class TestHealthMonitor:
    """Test cases for HealthMonitor"""
    
    @pytest.fixture
    def mock_ai_engine(self):
        """Create a mock AI engine"""
        engine = MagicMock()
        engine.initialize = AsyncMock()
        engine.analyze_project_health = AsyncMock(return_value={
            "risk_assessment": {"level": "medium", "score": 0.6},
            "recommendations": ["Reassign blocked tasks", "Review timeline"],
            "key_insights": ["3 tasks are blocked", "Team velocity is declining"]
        })
        return engine
    
    @pytest.fixture
    def monitor(self, mock_ai_engine):
        """Create a HealthMonitor instance with mocked AI engine"""
        return HealthMonitor(ai_engine=mock_ai_engine)
    
    def test_initialization(self, monitor, mock_ai_engine):
        """Test monitor initialization"""
        assert monitor.ai_engine == mock_ai_engine
        assert monitor.analysis_interval == 300  # 5 minutes
        assert monitor.analysis_history == []
        assert monitor.last_analysis is None
        assert monitor._monitoring_task is None
    
    @pytest.mark.asyncio
    async def test_initialize(self, monitor):
        """Test async initialization"""
        await monitor.initialize()
        monitor.ai_engine.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_project_health(self, monitor):
        """Test getting project health analysis"""
        project_state = create_mock_project_state(
            total_tasks=20,
            risk_level=RiskLevel.MEDIUM
        )
        
        recent_activities = [
            {
                "type": "task_completed",
                "timestamp": datetime.now() - timedelta(hours=1),
                "task_id": "task-001"
            }
        ]
        
        team_status = [
            create_mock_worker_status(),
            create_mock_worker_status()
        ]
        
        result = await monitor.get_project_health(
            project_state=project_state,
            recent_activities=recent_activities,
            team_status=team_status
        )
        
        assert "timestamp" in result
        assert "health_score" in result
        assert "risk_level" in result
        assert "metrics" in result
        
        # Should have cached the analysis
        assert monitor.last_analysis is not None
        assert len(monitor.analysis_history) == 1
    
    @pytest.mark.asyncio
    async def test_analyze_health(self, monitor):
        """Test health analysis"""
        project_state = create_mock_project_state()
        recent_activities = []
        team_status = [create_mock_worker_status()]
        
        analysis = await monitor.analyze_health(
            project_state=project_state,
            recent_activities=recent_activities,
            team_status=team_status
        )
        
        # Check AI engine was called
        monitor.ai_engine.analyze_project_health.assert_called_once()
        
        # Check result structure
        assert "overall_health" in analysis
        assert "risk_level" in analysis
        assert "metrics" in analysis
        assert "ai_insights" in analysis
    
    @pytest.mark.asyncio
    async def test_start_monitoring(self, monitor):
        """Test starting health monitoring"""
        get_state_func = AsyncMock(return_value=(
            create_mock_project_state(),
            [],  # recent activities
            [create_mock_worker_status()]  # team status
        ))
        
        # Start monitoring
        monitor.start_monitoring(
            get_project_state_func=get_state_func,
            interval=1  # 1 second for testing
        )
        
        # Check monitoring started
        assert monitor._monitoring_task is not None
        assert not monitor._monitoring_task.done()
        
        # Wait a bit to ensure monitoring runs
        await asyncio.sleep(1.5)
        
        # Should have called get_state_func
        assert get_state_func.call_count >= 1
        
        # Stop monitoring
        await monitor.stop_monitoring()
        assert monitor._monitoring_task.cancelled()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring(self, monitor):
        """Test stopping health monitoring"""
        # Start monitoring first
        monitor._monitoring_task = asyncio.create_task(asyncio.sleep(10))
        
        # Stop monitoring
        await monitor.stop_monitoring()
        
        # Task should be cancelled
        assert monitor._monitoring_task.cancelled()
    
    def test_get_health_trends(self, monitor):
        """Test getting health trends"""
        # Add some historical data
        base_time = datetime.now()
        for i in range(5):
            monitor.analysis_history.append({
                "timestamp": base_time - timedelta(hours=i),
                "health_score": 0.7 + i * 0.05,
                "risk_level": "medium"
            })
        
        trends = monitor.get_health_trends(hours=6)
        
        assert len(trends) == 5
        # Should be sorted by time (oldest first)
        for i in range(1, len(trends)):
            assert trends[i]["timestamp"] > trends[i-1]["timestamp"]
    
    def test_get_critical_alerts(self, monitor):
        """Test getting critical alerts"""
        # Set up analysis with alerts
        monitor.last_analysis = {
            "alerts": [
                {"severity": "critical", "message": "Blockers increasing"},
                {"severity": "warning", "message": "Velocity declining"},
                {"severity": "critical", "message": "Deadline at risk"}
            ]
        }
        
        alerts = monitor.get_critical_alerts()
        
        # Should only return critical alerts
        assert len(alerts) == 2
        for alert in alerts:
            assert alert["severity"] == "critical"
    
    @pytest.mark.asyncio
    async def test_generate_health_report(self, monitor):
        """Test generating health report"""
        # Set up some analysis history
        monitor.analysis_history = [
            {
                "timestamp": datetime.now() - timedelta(hours=i),
                "health_score": 0.8 - i * 0.1,
                "risk_level": "low" if i < 2 else "medium"
            }
            for i in range(3)
        ]
        
        report = await monitor.generate_health_report()
        
        assert "summary" in report
        assert "trends" in report
        assert "recommendations" in report
        assert "time_range" in report
    
    @pytest.mark.asyncio
    async def test_health_analysis_caching(self, monitor):
        """Test that health analysis is cached appropriately"""
        project_state = create_mock_project_state()
        activities = []
        team = [create_mock_worker_status()]
        
        # First call should analyze
        result1 = await monitor.get_project_health(project_state, activities, team)
        assert monitor.ai_engine.analyze_project_health.call_count == 1
        
        # Immediate second call should use cache
        result2 = await monitor.get_project_health(project_state, activities, team)
        assert monitor.ai_engine.analyze_project_health.call_count == 1
        assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_error_handling(self, monitor):
        """Test error handling in health analysis"""
        # Make AI engine raise an error
        monitor.ai_engine.analyze_project_health.side_effect = Exception("AI error")
        
        project_state = create_mock_project_state()
        activities = []
        team = [create_mock_worker_status()]
        
        # Should not raise, but return basic analysis
        result = await monitor.analyze_health(project_state, activities, team)
        
        assert result["overall_health"] == "unknown"
        assert "error" in result["ai_insights"]