"""
Unit tests for MCP tool response logger.

Tests the centralized MCP tool response logging system that categorizes
and logs tool failures, especially dependency-related issues.
"""

from unittest.mock import Mock, patch

import pytest

from src.logging.mcp_tool_logger import (
    _categorize_failure,
    _log_mcp_tool_failure,
    log_mcp_tool_response,
    log_request_next_task_failure,
)


class TestCategorizeFailure:
    """Test suite for failure categorization logic."""

    def test_categorize_dependency_issue_from_error_message(self):
        """Test dependency issue detection from error message."""
        response = {
            "success": False,
            "error": "Task waiting for incomplete dependencies",
            "retry_reason": "",
        }

        category = _categorize_failure(response)

        assert category == "dependency_issue"

    def test_categorize_dependency_issue_from_blocking_task(self):
        """Test dependency issue detection when blocking_task present."""
        response = {
            "success": False,
            "error": "No suitable tasks available",
            "retry_reason": "Waiting for task completion",
            "blocking_task": {"id": "task_123", "name": "Setup DB"},
        }

        category = _categorize_failure(response)

        assert category == "dependency_issue"

    def test_categorize_dependency_issue_from_retry_reason(self):
        """Test dependency issue detection from retry_reason."""
        response = {
            "success": False,
            "error": "Cannot proceed",
            "retry_reason": "waiting for dependencies to complete",
        }

        category = _categorize_failure(response)

        assert category == "dependency_issue"

    def test_categorize_dependency_circular_keyword(self):
        """Test circular dependency detection."""
        response = {
            "success": False,
            "error": "Circular dependency detected in task chain",
        }

        category = _categorize_failure(response)

        assert category == "dependency_issue"

    def test_categorize_agent_busy_from_error(self):
        """Test agent busy detection from error message."""
        response = {"success": False, "error": "Agent is busy with another task"}

        category = _categorize_failure(response)

        assert category == "agent_busy"

    def test_categorize_agent_busy_from_retry_reason(self):
        """Test agent busy detection from retry reason."""
        response = {
            "success": False,
            "error": "Cannot assign task",
            "retry_reason": "Agent is busy working on task_456",
        }

        category = _categorize_failure(response)

        assert category == "agent_busy"

    def test_categorize_no_suitable_tasks(self):
        """Test no suitable tasks detection."""
        response = {"success": False, "error": "No suitable tasks available for agent"}

        category = _categorize_failure(response)

        assert category == "no_suitable_tasks"

    def test_categorize_skill_mismatch(self):
        """Test skill mismatch detection."""
        response = {
            "success": False,
            "error": "Agent skills do not match available tasks",
        }

        category = _categorize_failure(response)

        assert category == "no_suitable_tasks"

    def test_categorize_unknown_failure(self):
        """Test unknown failure category for unrecognized errors."""
        response = {"success": False, "error": "Database connection failed"}

        category = _categorize_failure(response)

        assert category == "unknown"

    def test_categorize_empty_response(self):
        """Test categorization with minimal response data."""
        response = {"success": False}

        category = _categorize_failure(response)

        assert category == "unknown"


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
    def test_log_dependency_issue_at_critical_level(self, mock_logger):
        """Test dependency issues are logged at CRITICAL level."""
        tool_name = "request_next_task"
        arguments = {"agent_id": "agent_123"}
        response = {
            "success": False,
            "error": "Task blocked by dependencies",
            "blocking_task": {"id": "task_456", "name": "Setup DB"},
        }

        _log_mcp_tool_failure(tool_name, arguments, response)

        # Should log at CRITICAL level
        mock_logger.pm_logger.critical.assert_called_once()
        call_kwargs = mock_logger.pm_logger.critical.call_args[1]

        assert call_kwargs["failure_category"] == "dependency_issue"
        assert call_kwargs["tool_name"] == tool_name
        assert call_kwargs["error"] == "Task blocked by dependencies"

    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_log_dependency_issue_includes_diagnostic_info(self, mock_logger):
        """Test dependency failures include diagnostic context."""
        response = {
            "success": False,
            "error": "Waiting for dependencies",
            "blocking_task": {
                "id": "task_789",
                "name": "Create API",
                "progress": 45,
            },
            "retry_after_seconds": 120,
        }

        _log_mcp_tool_failure("request_next_task", {"agent_id": "agent_123"}, response)

        # Should log diagnostic info via log_pm_thinking
        assert mock_logger.log_pm_thinking.called
        diagnostic_call = [
            call
            for call in mock_logger.log_pm_thinking.call_args_list
            if "diagnostic" in call[0][0].lower()
        ]
        assert len(diagnostic_call) > 0

    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_log_agent_busy_at_warning_level(self, mock_logger):
        """Test agent busy failures are logged at WARNING level."""
        response = {
            "success": False,
            "error": "Agent is busy with another task",  # Must match keyword
            "current_task": {"id": "task_123"},
        }

        _log_mcp_tool_failure("request_next_task", {"agent_id": "agent_123"}, response)

        # Should log at WARNING level
        mock_logger.pm_logger.warning.assert_called_once()
        call_kwargs = mock_logger.pm_logger.warning.call_args[1]

        assert call_kwargs["failure_category"] == "agent_busy"

    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_log_no_suitable_tasks_at_warning_level(self, mock_logger):
        """Test no suitable tasks failures are logged at WARNING."""
        response = {"success": False, "error": "No suitable tasks for agent skills"}

        _log_mcp_tool_failure("request_next_task", {"agent_id": "agent_123"}, response)

        mock_logger.pm_logger.warning.assert_called_once()
        call_kwargs = mock_logger.pm_logger.warning.call_args[1]

        assert call_kwargs["failure_category"] == "no_suitable_tasks"

    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_log_unknown_failure_at_warning_level(self, mock_logger):
        """Test unknown failures are logged at WARNING level."""
        response = {"success": False, "error": "Unexpected error occurred"}

        _log_mcp_tool_failure("request_next_task", {"agent_id": "agent_123"}, response)

        mock_logger.pm_logger.warning.assert_called_once()
        call_kwargs = mock_logger.pm_logger.warning.call_args[1]

        assert call_kwargs["failure_category"] == "unknown"

    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_log_decision_records_failure_context(self, mock_logger):
        """Test that log_pm_decision is called for all failures."""
        response = {"success": False, "error": "Test error", "retry_reason": "Testing"}

        _log_mcp_tool_failure("test_tool", {"arg": "value"}, response)

        # Should log decision with failure context
        mock_logger.log_pm_decision.assert_called_once()
        call_kwargs = mock_logger.log_pm_decision.call_args[1]

        assert "failure" in call_kwargs["decision"].lower()
        assert call_kwargs["decision_factors"]["failure_category"] in [
            "dependency_issue",
            "agent_busy",
            "no_suitable_tasks",
            "unknown",
        ]


class TestLogRequestNextTaskFailure:
    """Test suite for request_next_task-specific logging."""

    @patch("src.logging.mcp_tool_logger.log_mcp_tool_response")
    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_logs_via_generic_handler(self, mock_logger, mock_log_response):
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
    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_adds_dependency_diagnostic_context(self, mock_logger, mock_log_response):
        """Test additional diagnostic context for dependency issues."""
        response = {
            "success": False,
            "error": "Dependencies incomplete",
            "blocking_task": {"id": "task_999", "name": "Setup Auth"},
            "retry_after_seconds": 180,
        }

        log_request_next_task_failure("agent_789", response)

        # Should log additional diagnostic info
        assert mock_logger.log_pm_thinking.called
        thinking_call = mock_logger.log_pm_thinking.call_args

        assert "blocked by dependencies" in thinking_call[0][0]
        assert "investigate dependency chain" in thinking_call[0][0]


class TestIntegrationWithConversationLogger:
    """Test integration with existing conversation logger."""

    @patch("src.logging.mcp_tool_logger.conversation_logger")
    def test_uses_existing_logger_instance(self, mock_logger):
        """Test that we use the existing conversation_logger instance."""
        response = {"success": False, "error": "Test failure"}

        _log_mcp_tool_failure("test_tool", {}, response)

        # Should use pm_logger from conversation_logger
        assert mock_logger.pm_logger.warning.called
        assert mock_logger.log_pm_decision.called

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

        # Check that all required fields are present
        call_kwargs = mock_logger.pm_logger.warning.call_args[1]

        assert "tool_name" in call_kwargs
        assert "arguments" in call_kwargs
        assert "error" in call_kwargs
        assert "failure_category" in call_kwargs
        assert "response" in call_kwargs
