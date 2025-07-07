"""
Integration tests for health analysis and visualization
"""

import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest
from aiohttp import web

from src.core.models import ProjectState, RiskLevel, WorkerStatus
from src.integrations.ai_analysis_engine import AIAnalysisEngine
from src.visualization.health_monitor import HealthMonitor
from src.visualization.ui_server import VisualizationServer


class TestHealthVisualizationIntegration:
    """Integration tests for the complete health visualization system"""

    @pytest.fixture
    async def server(self):
        """Create and start test server"""
        server = VisualizationServer(host="127.0.0.1", port=0)  # Random port

        # Mock external dependencies
        server.conversation_processor.start_streaming = AsyncMock()

        # Start server
        runner = web.AppRunner(server.app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()

        # Get actual port
        port = site._server.sockets[0].getsockname()[1]
        server.port = port
        server.base_url = f"http://127.0.0.1:{port}"

        yield server

        # Cleanup
        await runner.cleanup()

    @pytest.fixture
    def sample_project_state(self):
        """Sample project state for testing"""
        return ProjectState(
            board_id="BOARD-001",
            project_name="Integration Test Project",
            total_tasks=100,
            completed_tasks=45,
            in_progress_tasks=30,
            blocked_tasks=5,
            progress_percent=45.0,
            overdue_tasks=[],
            team_velocity=4.0,
            risk_level=RiskLevel.MEDIUM,
            last_updated=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_full_health_analysis_flow(self, server, sample_project_state):
        """Test complete flow from analysis request to response"""
        async with aiohttp.ClientSession() as session:
            # Request health analysis
            analysis_data = {
                "project_state": {
                    "board_id": sample_project_state.board_id,
                    "project_name": sample_project_state.project_name,
                    "total_tasks": sample_project_state.total_tasks,
                    "completed_tasks": sample_project_state.completed_tasks,
                    "in_progress_tasks": sample_project_state.in_progress_tasks,
                    "blocked_tasks": sample_project_state.blocked_tasks,
                    "progress_percent": sample_project_state.progress_percent,
                    "team_velocity": sample_project_state.team_velocity,
                    "risk_level": "MEDIUM",
                },
                "recent_activities": [
                    {"type": "task_completed", "count": 5, "timeframe": "last_day"},
                    {"type": "task_blocked", "count": 2, "timeframe": "last_day"},
                ],
                "team_status": [],
            }

            async with session.post(
                f"{server.base_url}/api/health/analyze", json=analysis_data
            ) as resp:
                assert resp.status == 200
                result = await resp.json()

                # Verify response structure
                assert "overall_health" in result
                assert "timestamp" in result
                assert "analysis_id" in result
                assert "timeline_prediction" in result
                assert "risk_factors" in result
                assert "recommendations" in result

    @pytest.mark.asyncio
    async def test_health_history_tracking(self, server):
        """Test that health analyses are tracked in history"""
        async with aiohttp.ClientSession() as session:
            # Run multiple analyses
            for i in range(3):
                analysis_data = {
                    "project_state": {
                        "board_id": f"BOARD-{i}",
                        "total_tasks": 10 + i,
                        "completed_tasks": 5 + i,
                        "risk_level": "LOW",
                    }
                }

                async with session.post(
                    f"{server.base_url}/api/health/analyze", json=analysis_data
                ) as resp:
                    assert resp.status == 200

            # Check history
            async with session.get(
                f"{server.base_url}/api/health/history?hours=1"
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data["count"] >= 3
                assert len(data["history"]) >= 3

    @pytest.mark.asyncio
    async def test_health_summary_aggregation(self, server):
        """Test health summary with multiple analyses"""
        async with aiohttp.ClientSession() as session:
            # Create analyses with different health states
            health_states = ["green", "yellow", "green", "red"]

            for i, health in enumerate(health_states):
                # Mock the health monitor to return specific health
                server.health_monitor.ai_engine.analyze_project_health = AsyncMock(
                    return_value={
                        "overall_health": health,
                        "risk_factors": [{"severity": "high"}] * i,
                    }
                )

                async with session.post(
                    f"{server.base_url}/api/health/analyze",
                    json={"project_state": {"risk_level": "MEDIUM"}},
                ) as resp:
                    assert resp.status == 200

            # Get summary
            async with session.get(f"{server.base_url}/api/health/summary") as resp:
                assert resp.status == 200
                summary = await resp.json()

                assert summary["status"] == "available"
                assert "health_distribution" in summary
                assert "average_risks" in summary
                assert "latest_health" in summary

    @pytest.mark.asyncio
    async def test_real_time_updates_via_socketio(self, server):
        """Test Socket.IO health update broadcasting"""
        # Mock Socket.IO
        server.sio = Mock()
        server.sio.emit = AsyncMock()

        async with aiohttp.ClientSession() as session:
            # Trigger health analysis
            async with session.post(
                f"{server.base_url}/api/health/analyze",
                json={"project_state": {"risk_level": "HIGH"}},
            ) as resp:
                assert resp.status == 200

            # Verify Socket.IO broadcast
            await asyncio.sleep(0.1)  # Allow async operations to complete
            server.sio.emit.assert_called_with("health_update", dict)

    @pytest.mark.asyncio
    async def test_error_handling_cascade(self, server):
        """Test error handling through the full stack"""
        # Make AI engine fail
        server.health_monitor.ai_engine.analyze_project_health = AsyncMock(
            side_effect=Exception("AI service unavailable")
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{server.base_url}/api/health/analyze", json={"project_state": {}}
            ) as resp:
                assert resp.status == 200  # Should still return 200
                result = await resp.json()

                # Should return error response
                assert result["overall_health"] == "unknown"
                assert result["error"] is True
                assert "AI service unavailable" in result["error_message"]

    @pytest.mark.asyncio
    async def test_concurrent_health_requests(self, server):
        """Test handling multiple concurrent health requests"""
        async with aiohttp.ClientSession() as session:
            # Send multiple concurrent requests
            tasks = []
            for i in range(5):
                task = session.post(
                    f"{server.base_url}/api/health/analyze",
                    json={
                        "project_state": {"board_id": f"BOARD-{i}", "risk_level": "LOW"}
                    },
                )
                tasks.append(task)

            # Wait for all requests
            responses = await asyncio.gather(*[task.__aenter__() for task in tasks])

            # Verify all succeeded
            for resp in responses:
                assert resp.status == 200

            # Cleanup
            for resp in responses:
                await resp.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_health_monitor_lifecycle(self):
        """Test health monitor start/stop lifecycle"""
        monitor = HealthMonitor()
        await monitor.initialize()

        # Start monitoring
        callback = AsyncMock()
        await monitor.start_monitoring(callback)

        assert monitor._monitoring_task is not None
        assert not monitor._monitoring_task.done()

        # Stop monitoring
        await monitor.stop_monitoring()

        assert monitor._monitoring_task is None

    @pytest.mark.asyncio
    async def test_trend_calculation_over_time(self, server):
        """Test trend calculation with multiple analyses"""
        async with aiohttp.ClientSession() as session:
            # First analysis - yellow health
            server.health_monitor.ai_engine.analyze_project_health = AsyncMock(
                return_value={
                    "overall_health": "yellow",
                    "timeline_prediction": {"confidence": 0.5},
                    "risk_factors": [{"type": "resource"}, {"type": "timeline"}],
                }
            )

            async with session.post(
                f"{server.base_url}/api/health/analyze", json={"project_state": {}}
            ) as resp:
                assert resp.status == 200
                first_result = await resp.json()
                assert "trends" not in first_result  # No trends on first analysis

            # Second analysis - green health
            server.health_monitor.ai_engine.analyze_project_health = AsyncMock(
                return_value={
                    "overall_health": "green",
                    "timeline_prediction": {"confidence": 0.8},
                    "risk_factors": [{"type": "resource"}],
                }
            )

            async with session.post(
                f"{server.base_url}/api/health/analyze", json={"project_state": {}}
            ) as resp:
                assert resp.status == 200
                second_result = await resp.json()

                # Should have trends now
                assert "trends" in second_result
                assert second_result["trends"]["health_direction"] == "improving"
                assert second_result["trends"]["confidence_change"] == 0.3
                assert second_result["trends"]["risk_change"] == "decreasing"

    @pytest.mark.asyncio
    async def test_api_endpoint_validation(self, server):
        """Test API endpoint input validation"""
        async with aiohttp.ClientSession() as session:
            # Test invalid JSON
            async with session.post(
                f"{server.base_url}/api/health/analyze", data="invalid json"
            ) as resp:
                assert resp.status == 400  # Bad request

            # Test invalid risk level
            async with session.post(
                f"{server.base_url}/api/health/analyze",
                json={"project_state": {"risk_level": "INVALID_LEVEL"}},
            ) as resp:
                assert resp.status == 500
                data = await resp.json()
                assert "error" in data
