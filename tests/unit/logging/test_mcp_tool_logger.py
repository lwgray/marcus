"""
Unit tests for MCP tool response logger.

Tests the MCP tool response logging system that tracks tool activity
(WHAT failed and WHEN) and points operators to diagnostic logs for
root cause analysis.
"""

from unittest.mock import patch

import pytest

from src.logging.mcp_tool_logger import (
    _log_mcp_tool_failure,
    log_mcp_tool_response,
    log_request_next_task_failure,
)


class TestLogMcpToolResponse:
    """Test suite for main MCP tool response logging function."""

    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_log_success_response_at_debug_level(self, mock_logger):
        """Test successful responses are logged at DEBUG level."""
        tool_name = "request_next_task"
        arguments = {"agent_id": "agent_123"}
        response = {
            "success": True,
            "task": {"id": "task_456", "name": "Implement feature"},
        }

        log_mcp_tool_response(tool_name, arguments, response)

        # Should call log_pm_thinking (DEBUG level)
        mock_logger.log_pm_thinking.assert_called_once()
        call_args = mock_logger.log_pm_thinking.call_args

        assert "succeeded" in call_args[0][0]
        assert call_args[1]["context"]["tool_name"] == tool_name
        assert call_args[1]["context"]["arguments"] == arguments

    @patch("src.logging.mcp_tool_logger._log_mcp_tool_failure")
    def test_log_failure_response_delegates_to_failure_handler(
        self, mock_failure_handler
    ):
        """Test failure responses are delegated to failure logging."""
        tool_name = "request_next_task"
        arguments = {"agent_id": "agent_123"}
        response = {"success": False, "error": "No tasks available"}

        log_mcp_tool_response(tool_name, arguments, response)

        # Should delegate to failure handler
        mock_failure_handler.assert_called_once_with(tool_name, arguments, response)


class TestLogMcpToolFailure:
    """Test suite for MCP tool failure logging."""

    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_log_failure_at_warning_level(self, mock_logger):
        """Test all failures are logged at WARNING level."""
        tool_name = "request_next_task"
        arguments = {"agent_id": "agent_123"}
        response = {
            "success": False,
            "error": "No tasks available",
            "retry_reason": "All tasks assigned",
        }

        _log_mcp_tool_failure(tool_name, arguments, response)

        # Should log at WARNING level
        mock_logger.pm_logger.warning.assert_called_once()
        call_args = mock_logger.pm_logger.warning.call_args

        assert "returned failure" in call_args[0][0]
        assert call_args[1]["tool_name"] == tool_name
        assert call_args[1]["error"] == "No tasks available"
        assert call_args[1]["retry_reason"] == "All tasks assigned"

    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_log_failure_includes_full_response(self, mock_logger):
        """Test failure log includes complete response for investigation."""
        response = {
            "success": False,
            "error": "Test error",
            "retry_reason": "Test reason",
            "retry_after_seconds": 60,
            "custom_field": "custom_value",
        }

        _log_mcp_tool_failure("test_tool", {"arg": "value"}, response)

        call_kwargs = mock_logger.pm_logger.warning.call_args[1]
        assert call_kwargs["response"] == response
        assert call_kwargs["arguments"] == {"arg": "value"}

    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_log_failure_handles_missing_fields(self, mock_logger):
        """Test graceful handling when response lacks error/retry_reason."""
        response = {"success": False}

        _log_mcp_tool_failure("test_tool", {}, response)

        call_kwargs = mock_logger.pm_logger.warning.call_args[1]
        assert call_kwargs["error"] == "Unknown error"
        assert call_kwargs["retry_reason"] == ""

    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_request_next_task_failure_adds_diagnostic_pointer(self, mock_logger):
        """Test request_next_task failures point to diagnostic logs."""
        response = {"success": False, "error": "No suitable tasks"}

        _log_mcp_tool_failure("request_next_task", {"agent_id": "agent_123"}, response)

        # Should log pointer to diagnostic logs
        assert mock_logger.log_pm_thinking.called
        thinking_call = mock_logger.log_pm_thinking.call_args

        assert "Diagnostic Report" in thinking_call[0][0]
        assert "logs/marcus_*.log" in thinking_call[0][0]

    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_non_request_next_task_failure_no_diagnostic_pointer(self, mock_logger):
        """Test other tools don't add diagnostic pointer."""
        response = {"success": False, "error": "Test failure"}

        _log_mcp_tool_failure("other_tool", {"param": "value"}, response)

        # Should NOT call log_pm_thinking
        mock_logger.log_pm_thinking.assert_not_called()


class TestLogRequestNextTaskFailure:
    """Test suite for request_next_task-specific logging."""

    @patch("src.logging.mcp_tool_logger.log_mcp_tool_response")
    def test_delegates_to_generic_logger(self, mock_log_response):
        """Test request_next_task failures use generic MCP logger."""
        agent_id = "agent_456"
        response = {
            "success": False,
            "error": "No tasks available",
            "retry_after_seconds": 60,
        }

        log_request_next_task_failure(agent_id, response)

        # Should call generic log_mcp_tool_response
        mock_log_response.assert_called_once_with(
            tool_name="request_next_task",
            arguments={"agent_id": agent_id},
            response=response,
        )

    @patch("src.logging.mcp_tool_logger.log_mcp_tool_response")
    def test_convenience_function_simplifies_usage(self, mock_log_response):
        """Test convenience function reduces boilerplate."""
        # Instead of calling log_mcp_tool_response with full arguments,
        # callers can use simpler log_request_next_task_failure
        agent_id = "agent_789"
        response = {"success": False, "error": "Test"}

        log_request_next_task_failure(agent_id, response)

        # Verify it properly constructs the full call
        call_kwargs = mock_log_response.call_args[1]
        assert call_kwargs["tool_name"] == "request_next_task"
        assert call_kwargs["arguments"]["agent_id"] == agent_id
        assert call_kwargs["response"] == response


class TestIntegrationWithConversationLogger:
    """Test integration with existing conversation logger."""

    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_uses_existing_logger_instance(self, mock_logger):
        """Test that we use the existing conversation_logger instance."""
        response = {"success": False, "error": "Test failure"}

        _log_mcp_tool_failure("test_tool", {}, response)

        # Should use pm_logger from conversation_logger
        assert mock_logger.pm_logger.warning.called

    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_structured_logging_format(self, mock_logger):
        """Test that log output follows structured logging format."""
        tool_name = "request_next_task"
        arguments = {"agent_id": "agent_123", "extra_param": "value"}
        response = {
            "success": False,
            "error": "No suitable tasks",
            "retry_after_seconds": 30,
        }

        _log_mcp_tool_failure(tool_name, arguments, response)

        # Check that all required fields are present for structured logging
        call_kwargs = mock_logger.pm_logger.warning.call_args[1]

        assert "tool_name" in call_kwargs
        assert "arguments" in call_kwargs
        assert "error" in call_kwargs
        assert "retry_reason" in call_kwargs
        assert "response" in call_kwargs


class TestActivityTrackingPurpose:
    """Test that logger acts as activity tracker, not diagnostic tool."""

    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_logs_what_and_when_not_why(self, mock_logger):
        """Test logger records WHAT failed and WHEN, not WHY."""
        response = {
            "success": False,
            "error": "No suitable tasks",
            "retry_reason": "All tasks assigned or blocked",
        }

        _log_mcp_tool_failure("request_next_task", {"agent_id": "agent_123"}, response)

        # Should log the error message (WHAT)
        call_kwargs = mock_logger.pm_logger.warning.call_args[1]
        assert call_kwargs["error"] == "No suitable tasks"

        # Should NOT categorize or diagnose WHY
        assert "failure_category" not in call_kwargs
        assert "dependency_issue" not in str(call_kwargs)

    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_points_to_diagnostic_logs_for_why(self, mock_logger):
        """Test that for WHY, logger points to diagnostic logs."""
        response = {"success": False, "error": "Cannot assign task"}

        _log_mcp_tool_failure("request_next_task", {"agent_id": "agent_123"}, response)

        # Should point to diagnostic logs for root cause
        thinking_call = mock_logger.log_pm_thinking.call_args
        assert "root cause analysis" in thinking_call[0][0]
        assert "Diagnostic Report" in thinking_call[0][0]

    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_no_assumptions_about_failure_cause(self, mock_logger):
        """Test logger doesn't make assumptions about failure causes."""
        # Response with dependency-related keywords
        response = {
            "success": False,
            "error": "Task waiting for dependencies",
            "retry_reason": "Blocked by incomplete tasks",
        }

        _log_mcp_tool_failure("request_next_task", {"agent_id": "agent_123"}, response)

        # Should log the error as-is without categorizing
        call_kwargs = mock_logger.pm_logger.warning.call_args[1]
        assert call_kwargs["error"] == "Task waiting for dependencies"

        # Should NOT add labels like "dependency_issue" or change log level
        mock_logger.pm_logger.critical.assert_not_called()
        mock_logger.pm_logger.warning.assert_called_once()
