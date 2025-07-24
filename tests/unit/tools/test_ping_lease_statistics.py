"""
Unit tests for ping tool lease statistics functionality.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from src.marcus_mcp.tools.system import ping


class TestPingLeaseStatistics:
    """Test suite for ping tool lease statistics in health response."""

    @pytest.fixture
    def mock_state(self):
        """Create a mock state object with lease manager."""
        state = Mock()

        # Basic state attributes
        state.provider = "test_provider"
        state.instance_id = "test_instance"
        state.tasks_being_assigned = set()
        state.agent_status = {}
        state.agent_tasks = {}
        state._shutdown_event = Mock(is_set=Mock(return_value=False))
        state._active_operations = set()

        # Mock realtime log
        state.realtime_log = Mock()
        state.realtime_log.name = "/tmp/test_log.jsonl"

        # Mock assignment components
        state.assignment_persistence = Mock()
        state.kanban_client = Mock()
        state.assignment_monitor = Mock()

        # Mock lease manager
        state.lease_manager = Mock()
        state.lease_manager.get_lease_statistics = Mock(
            return_value={
                "active_leases": 2,
                "expired_leases": 1,
                "total_renewals": 5,
                "average_lease_duration_hours": 1.5,
                "expiring_soon": ["task-123"],
                "oldest_lease": "task-100",
            }
        )

        # Mock log_event
        state.log_event = Mock()

        return state

    @pytest.mark.asyncio
    async def test_ping_health_includes_lease_statistics(self, mock_state):
        """Test that ping health response includes lease statistics when available."""
        # Call ping with health command
        result = await ping(echo="health", state=mock_state)

        # Verify response structure
        assert result["success"] is True
        assert result["status"] == "online"
        assert "health" in result

        # Verify lease statistics are included
        assert "lease_statistics" in result["health"]
        lease_stats = result["health"]["lease_statistics"]

        # Verify lease statistics content
        assert lease_stats["active_leases"] == 2
        assert lease_stats["expired_leases"] == 1
        assert lease_stats["total_renewals"] == 5
        assert lease_stats["average_lease_duration_hours"] == 1.5
        assert lease_stats["expiring_soon"] == ["task-123"]
        assert lease_stats["oldest_lease"] == "task-100"

        # Verify lease manager method was called
        mock_state.lease_manager.get_lease_statistics.assert_called_once()

    @pytest.mark.asyncio
    async def test_ping_health_without_lease_manager(self, mock_state):
        """Test ping health response when lease manager is not initialized."""
        # Remove lease manager
        mock_state.lease_manager = None

        # Call ping with health command
        result = await ping(echo="health", state=mock_state)

        # Verify response structure
        assert result["success"] is True
        assert "health" in result

        # Verify lease statistics show not initialized
        assert "lease_statistics" in result["health"]
        lease_stats = result["health"]["lease_statistics"]
        assert lease_stats["status"] == "not_initialized"
        assert lease_stats["message"] == "Lease manager not yet initialized"

    @pytest.mark.asyncio
    async def test_ping_health_lease_statistics_error(self, mock_state):
        """Test ping health response when lease statistics retrieval fails."""
        # Make get_lease_statistics raise an error
        mock_state.lease_manager.get_lease_statistics.side_effect = Exception(
            "Database error"
        )

        # Call ping with health command
        result = await ping(echo="health", state=mock_state)

        # Verify response structure
        assert result["success"] is True
        assert "health" in result

        # Verify lease statistics show error
        assert "lease_statistics" in result["health"]
        lease_stats = result["health"]["lease_statistics"]
        assert "error" in lease_stats
        assert lease_stats["error"] == "Database error"

    @pytest.mark.asyncio
    async def test_ping_health_with_empty_lease_statistics(self, mock_state):
        """Test ping health response with empty lease statistics."""
        # Return empty statistics
        mock_state.lease_manager.get_lease_statistics.return_value = {
            "active_leases": 0,
            "expired_leases": 0,
            "total_renewals": 0,
            "average_lease_duration_hours": 0,
            "expiring_soon": [],
            "oldest_lease": None,
        }

        # Call ping with health command
        result = await ping(echo="health", state=mock_state)

        # Verify lease statistics are included even when empty
        assert "lease_statistics" in result["health"]
        lease_stats = result["health"]["lease_statistics"]
        assert lease_stats["active_leases"] == 0
        assert lease_stats["expiring_soon"] == []
        assert lease_stats["oldest_lease"] is None

    @pytest.mark.asyncio
    async def test_ping_non_health_command_no_lease_stats(self, mock_state):
        """Test that non-health ping commands don't include lease statistics."""
        # Test regular ping
        result = await ping(echo="test", state=mock_state)
        assert "health" not in result
        assert "lease_statistics" not in result

        # Test cleanup command
        result = await ping(echo="cleanup", state=mock_state)
        assert "cleanup" in result
        assert "health" not in result
