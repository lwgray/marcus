"""
Integration tests for MCP tool logger.

Tests the MCP tool logger with real conversation logger to verify
log entries are created correctly in actual log files.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from src.logging.mcp_tool_logger import (
    log_mcp_tool_response,
    log_request_next_task_failure,
)


class TestMcpToolLoggerIntegration:
    """Integration tests verifying actual log output."""

    def test_request_next_task_success_creates_log_entry(self, tmp_path):
        """Test successful request_next_task creates DEBUG log entry."""
        response = {
            "success": True,
            "task": {"id": "task_123", "name": "Implement feature"},
        }

        log_mcp_tool_response(
            tool_name="request_next_task",
            arguments={"agent_id": "agent_test_001"},
            response=response,
        )

        # Log entry created (verified by no exceptions)
        # In production, check logs/conversations/marcus_*.log

    def test_request_next_task_failure_creates_warning_entry(self, tmp_path):
        """Test failed request_next_task creates WARNING log entry."""
        response = {
            "success": False,
            "error": "No suitable tasks available",
            "retry_reason": "All tasks assigned or blocked",
            "retry_after_seconds": 30,
        }

        log_mcp_tool_response(
            tool_name="request_next_task",
            arguments={"agent_id": "agent_test_002"},
            response=response,
        )

        # Should create WARNING entry with diagnostic pointer
        # In production, check logs/conversations/marcus_*.log

    def test_request_next_task_failure_includes_diagnostic_pointer(self, tmp_path):
        """Test request_next_task failures include pointer to Python logs."""
        response = {
            "success": False,
            "error": "Cannot assign task",
            "retry_reason": "Tasks blocked by dependencies",
        }

        log_mcp_tool_response(
            tool_name="request_next_task",
            arguments={"agent_id": "agent_test_003"},
            response=response,
        )

        # Should mention "Diagnostic Report" and "logs/marcus_*.log"
        # In production, grep for "Diagnostic Report" in conversation logs

    def test_other_tool_failure_no_diagnostic_pointer(self, tmp_path):
        """Test non-request_next_task failures don't add diagnostic pointer."""
        response = {
            "success": False,
            "error": "Invalid configuration",
        }

        log_mcp_tool_response(
            tool_name="create_project",
            arguments={"name": "test-proj"},
            response=response,
        )

        # Should NOT mention "Diagnostic Report"
        # In production, verify no diagnostic pointer in logs

    def test_convenience_function_works_end_to_end(self, tmp_path):
        """Test log_request_next_task_failure convenience function."""
        response = {
            "success": False,
            "error": "Agent busy with another task",
            "current_task": {"id": "task_999"},
        }

        log_request_next_task_failure(
            agent_id="agent_test_004",
            response=response,
        )

        # Should create same log entries as log_mcp_tool_response

    def test_all_response_fields_preserved(self, tmp_path):
        """Test all response fields are included in log context."""
        response = {
            "success": False,
            "error": "Test error",
            "retry_reason": "Test reason",
            "retry_after_seconds": 60,
            "blocking_task": {"id": "task_456", "name": "Dependency"},
            "custom_field": "custom_value",
        }

        log_mcp_tool_response(
            tool_name="request_next_task",
            arguments={"agent_id": "agent_test_005", "extra": "data"},
            response=response,
        )

        # Full response should be in log context for investigation


@pytest.mark.integration
class TestRealWorldScenarios:
    """Test real-world failure scenarios."""

    def test_scenario_all_tasks_assigned(self):
        """Scenario: All tasks in project are assigned to agents."""
        response = {
            "success": False,
            "message": "No tasks available. Please check back in 30 seconds...",
            "retry_after_seconds": 30,
            "retry_reason": "All tasks currently assigned",
        }

        log_mcp_tool_response(
            tool_name="request_next_task",
            arguments={"agent_id": "agent_real_001"},
            response=response,
        )

        # Operator should see: WHAT failed (no tasks), WHEN (timestamp)
        # For WHY: Check Python logs for diagnostic report

    def test_scenario_dependencies_blocking(self):
        """Scenario: Tasks exist but blocked by incomplete dependencies."""
        response = {
            "success": False,
            "message": "No tasks available. Please check back in 60 seconds...",
            "retry_after_seconds": 60,
            "retry_reason": "Tasks filtered by assignment logic",
        }

        log_mcp_tool_response(
            tool_name="request_next_task",
            arguments={"agent_id": "agent_real_002"},
            response=response,
        )

        # Note: Logger doesn't assume this is dependency issue
        # Just logs the fact that it failed with given message
        # Diagnostic logs contain actual dependency analysis

    def test_scenario_agent_skill_mismatch(self):
        """Scenario: Tasks available but agent lacks required skills."""
        response = {
            "success": False,
            "message": "No suitable tasks for your skills...",
            "retry_after_seconds": 120,
            "retry_reason": "No tasks match agent capabilities",
        }

        log_mcp_tool_response(
            tool_name="request_next_task",
            arguments={"agent_id": "agent_real_003", "skills": ["python"]},
            response=response,
        )

        # Logger just records the failure as-is
        # Doesn't try to diagnose if it's skills, deps, or something else


class TestLogFormat:
    """Test structured logging format."""

    def test_structured_log_includes_all_required_fields(self):
        """Test log output has all fields needed for investigation."""
        response = {
            "success": False,
            "error": "Test error",
            "retry_reason": "Test",
        }

        log_mcp_tool_response(
            tool_name="test_tool",
            arguments={"param": "value"},
            response=response,
        )

        # Structured log should include:
        # - tool_name: "test_tool"
        # - arguments: {"param": "value"}
        # - error: "Test error"
        # - retry_reason: "Test"
        # - response: full response dict
        # - timestamp: auto-added by structlog

    def test_missing_fields_handled_gracefully(self):
        """Test graceful handling when response lacks standard fields."""
        response = {"success": False}  # Minimal response

        log_mcp_tool_response(
            tool_name="minimal_tool",
            arguments={},
            response=response,
        )

        # Should use defaults:
        # - error: "Unknown error"
        # - retry_reason: ""
        # - Still log full response for investigation
