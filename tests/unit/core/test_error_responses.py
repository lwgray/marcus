"""
Unit tests for Marcus Error Response System

Tests error response formatting for different contexts including MCP,
JSON API, user-friendly messages, and logging formats.
"""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.core.error_framework import (
    AuthorizationError,
    ErrorContext,
    ErrorSeverity,
    MarcusBaseError,
    NetworkTimeoutError,
    RemediationSuggestion,
    TaskAssignmentError,
)
from src.core.error_responses import (
    BatchErrorResponseFormatter,
    ErrorResponseConfig,
    ErrorResponseFormatter,
    ResponseFormat,
    create_error_response,
    create_success_response,
    default_formatter,
    handle_mcp_tool_error,
)
from tests.unit.test_helpers import create_test_context, create_test_remediation


class TestErrorResponseConfig:
    """Test suite for ErrorResponseConfig"""

    def test_config_defaults(self):
        """Test ErrorResponseConfig default values"""
        config = ErrorResponseConfig()

        assert config.include_debug_info is False
        assert config.include_stack_trace is False
        assert config.include_system_context is False
        assert config.include_remediation is True
        assert config.max_message_length == 500
        assert config.sanitize_sensitive_data is True
        assert config.custom_fields == {}

    def test_config_custom_values(self):
        """Test ErrorResponseConfig with custom values"""
        config = ErrorResponseConfig(
            include_debug_info=True,
            include_stack_trace=True,
            max_message_length=1000,
            sanitize_sensitive_data=False,
            custom_fields={"custom": "value"},
        )

        assert config.include_debug_info is True
        assert config.include_stack_trace is True
        assert config.max_message_length == 1000
        assert config.sanitize_sensitive_data is False
        assert config.custom_fields == {"custom": "value"}


class TestErrorResponseFormatter:
    """Test suite for ErrorResponseFormatter"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = ErrorResponseConfig(
            include_debug_info=True, include_remediation=True
        )
        self.formatter = ErrorResponseFormatter(self.config)

    def create_test_error(self):
        """Create a test error for formatting tests"""
        context = create_test_context()
        remediation = create_test_remediation()

        return NetworkTimeoutError(
            service_name="test_service",
            timeout_seconds=30,
            context=context,
            remediation=remediation,
        )

    @pytest.mark.parametrize(
        "format_type,expected_checks",
        [
            (
                ResponseFormat.MCP,
                {
                    "structure": lambda r: r["success"] is False and "error" in r,
                    "error_fields": lambda r: all(
                        [
                            r["error"]["code"] == "NETWORKTIMEOUTERROR",
                            "test_service" in r["error"]["message"],
                            r["error"]["type"] == "NetworkTimeoutError",
                            r["error"]["severity"] == "medium",
                            r["error"]["retryable"] is True,
                        ]
                    ),
                    "context": lambda r: all(
                        [
                            r["error"]["context"]["operation"] == "test_operation",
                            r["error"]["context"]["agent_id"] == "agent_123",
                            r["error"]["context"]["task_id"] == "task_456",
                            r["error"]["context"]["correlation_id"] == "corr_789",
                        ]
                    ),
                    "remediation": lambda r: all(
                        [
                            r["error"]["remediation"]["immediate"] == "Retry operation",
                            r["error"]["remediation"]["fallback"] == "Use cached data",
                        ]
                    ),
                },
            ),
            (
                ResponseFormat.JSON_API,
                {
                    "structure": lambda r: "error" in r,
                    "error_fields": lambda r: all(
                        [
                            r["error"]["id"] == "corr_789",
                            r["error"]["status"] == 503,
                            r["error"]["code"] == "NETWORKTIMEOUTERROR",
                            r["error"]["title"] == "NetworkTimeoutError",
                            "test_service" in r["error"]["detail"],
                        ]
                    ),
                    "meta": lambda r: all(
                        [
                            r["error"]["meta"]["severity"] == "medium",
                            r["error"]["meta"]["retryable"] is True,
                            "suggestions" in r["error"]["meta"],
                        ]
                    ),
                    "source": lambda r: all(
                        [
                            r["error"]["source"]["operation"] == "test_operation",
                            r["error"]["source"]["agent_id"] == "agent_123",
                        ]
                    ),
                },
            ),
            (
                ResponseFormat.USER_FRIENDLY,
                {
                    "structure": lambda r: "message" in r,
                    "message_content": lambda r: all(
                        [
                            "What to do: Retry operation" in r["message"],
                            "Alternative: Use cached data" in r["message"],
                            "🔁 Retry:" in r["message"],
                        ]
                    ),
                    "fields": lambda r: all(
                        [
                            r["severity"] == "medium",
                            r["can_retry"] is True,
                            r["error_id"] == "corr_789",
                            r["help_needed"] is False,
                        ]
                    ),
                },
            ),
            (
                ResponseFormat.LOGGING,
                {
                    "fields": lambda r: all(
                        [
                            r["error_code"] == "NETWORKTIMEOUTERROR",
                            r["error_type"] == "NetworkTimeoutError",
                            "test_service" in r["message"],
                            r["severity"] == "medium",
                            r["retryable"] is True,
                            r["correlation_id"] == "corr_789",
                            r["operation"] == "test_operation",
                            r["agent_id"] == "agent_123",
                            r["task_id"] == "task_456",
                        ]
                    )
                },
            ),
            (
                ResponseFormat.MONITORING,
                {
                    "fields": lambda r: all(
                        [
                            r["alert_id"] == "corr_789",
                            r["alert_type"] == "marcus_error",
                            r["severity"] == "medium",
                            r["service"] == "marcus",
                            r["operation"] == "test_operation",
                            r["agent_id"] == "agent_123",
                            r["retryable"] is True,
                        ]
                    ),
                    "tags": lambda r: all(
                        [
                            "transient" in r["tags"],
                            "medium" in r["tags"],
                            "networktimeouterror" in r["tags"],
                        ]
                    ),
                },
            ),
        ],
    )
    def test_format_error_various_formats(self, format_type, expected_checks):
        """Test formatting error for various response formats"""
        error = self.create_test_error()
        response = self.formatter.format_error(error, format_type)

        # Run all checks for this format
        for check_name, check_func in expected_checks.items():
            assert check_func(response), f"Failed {check_name} check for {format_type}"

    def test_format_for_debug(self):
        """Test formatting error for debug output (special case with different config)"""
        config = ErrorResponseConfig(include_debug_info=True, include_stack_trace=True)
        formatter = ErrorResponseFormatter(config)
        error = self.create_test_error()

        response = formatter.format_error(error, ResponseFormat.DEBUG)

        assert "error" in response
        assert "debug" in response

        debug_info = response["debug"]
        assert "stack_trace" in debug_info  # Should include stack trace

    def test_convert_regular_exception(self):
        """Test converting regular exception to Marcus error"""
        regular_error = ValueError("Regular error message")

        response = self.formatter.format_error(regular_error, ResponseFormat.MCP)

        assert response["success"] is False
        error_data = response["error"]
        assert error_data["type"] == "IntegrationError"
        assert "Regular error message" in error_data["message"]

    def test_http_status_code_mapping(self):
        """Test HTTP status code mapping for different error types"""
        # Test different error types
        auth_error = AuthorizationError()
        timeout_error = NetworkTimeoutError("service")
        task_error = TaskAssignmentError()

        auth_response = self.formatter.format_error(auth_error, ResponseFormat.JSON_API)
        timeout_response = self.formatter.format_error(
            timeout_error, ResponseFormat.JSON_API
        )
        task_response = self.formatter.format_error(task_error, ResponseFormat.JSON_API)

        assert auth_response["error"]["status"] == 403  # Forbidden
        assert timeout_response["error"]["status"] == 503  # Service Unavailable
        assert task_response["error"]["status"] == 422  # Unprocessable Entity

    def test_message_truncation(self):
        """Test message truncation for long messages"""
        config = ErrorResponseConfig(max_message_length=50)
        formatter = ErrorResponseFormatter(config)

        long_message = (
            "This is a very long error message that exceeds the maximum length limit"
        )
        error = MarcusBaseError(message=long_message)

        response = formatter.format_error(error, ResponseFormat.MCP)

        truncated_message = response["error"]["message"]
        assert len(truncated_message) <= 50
        assert truncated_message.endswith("...")

    def test_sensitive_data_sanitization(self):
        """Test sanitization of sensitive data"""
        context = create_test_context(
            custom_context={
                "password": "secret123",
                "api_key": "key_abc123",
                "safe_data": "this is ok",
                "user_token": "token_xyz789",
            }
        )
        error = MarcusBaseError(message="Test error", context=context)

        response = self.formatter.format_error(error, ResponseFormat.DEBUG)

        # Check that sensitive fields are redacted
        custom_context = response["error"]["context"]["custom_context"]
        assert custom_context["password"] == "[REDACTED]"
        assert custom_context["api_key"] == "[REDACTED]"
        assert custom_context["user_token"] == "[REDACTED]"
        assert custom_context["safe_data"] == "this is ok"  # Safe data preserved

    def test_disable_sanitization(self):
        """Test disabling sensitive data sanitization"""
        config = ErrorResponseConfig(sanitize_sensitive_data=False)
        formatter = ErrorResponseFormatter(config)

        context = create_test_context(custom_context={"password": "secret123"})
        error = MarcusBaseError(message="Test error", context=context)

        response = formatter.format_error(error, ResponseFormat.DEBUG)

        # Sensitive data should not be redacted
        custom_context = response["error"]["context"]["custom_context"]
        assert custom_context["password"] == "secret123"

    def test_additional_context_integration(self):
        """Test adding additional context to error"""
        error = self.create_test_error()
        additional_context = {"request_id": "req_123", "user_id": "user_456"}

        response = self.formatter.format_error(
            error, ResponseFormat.MCP, additional_context
        )

        # Additional context should be merged into custom_context
        assert error.context.custom_context["request_id"] == "req_123"
        assert error.context.custom_context["user_id"] == "user_456"


class TestBatchErrorResponseFormatter:
    """Test suite for BatchErrorResponseFormatter"""

    def setup_method(self):
        """Set up test fixtures"""
        self.formatter = BatchErrorResponseFormatter()

    def create_test_errors(self):
        """Create a list of test errors"""
        errors = [
            NetworkTimeoutError(
                "service1", context=create_test_context(operation="op1")
            ),
            NetworkTimeoutError(
                "service2", context=create_test_context(operation="op2")
            ),
            AuthorizationError(context=create_test_context(operation="op3")),
        ]
        return errors

    def test_format_batch_response_mcp(self):
        """Test formatting batch response for MCP"""
        errors = self.create_test_errors()

        response = self.formatter.format_batch_response(
            operation_name="batch_test",
            errors=errors,
            successes=7,
            total_operations=10,
            format_type=ResponseFormat.MCP,
        )

        assert response["success"] is False  # Has errors
        assert "batch_summary" in response

        summary = response["batch_summary"]
        assert summary["operation"] == "batch_test"
        assert summary["total_operations"] == 10
        assert summary["successes"] == 7
        assert summary["errors"] == 3
        assert summary["success_rate"] == 0.7

        # Check error type breakdown
        error_types = summary["error_types"]
        assert error_types["NetworkTimeoutError"] == 2
        assert error_types["AuthorizationError"] == 1

        # Check formatted errors
        assert "errors" in response
        assert len(response["errors"]) == 3

    def test_format_batch_response_json_api(self):
        """Test formatting batch response for JSON API"""
        errors = self.create_test_errors()

        response = self.formatter.format_batch_response(
            operation_name="batch_test",
            errors=errors,
            successes=5,
            total_operations=8,
            format_type=ResponseFormat.JSON_API,
        )

        assert response["data"] is None  # Has errors
        assert "meta" in response
        assert "errors" in response

        meta = response["meta"]
        assert meta["success_rate"] == 0.625  # 5/8

    def test_format_error_summary(self):
        """Test creating error summary"""
        errors = self.create_test_errors()

        summary = self.formatter.format_error_summary(errors)

        assert summary["total_errors"] == 3
        assert summary["severity_breakdown"]["medium"] == 2  # NetworkTimeoutErrors
        assert summary["severity_breakdown"]["critical"] == 1  # AuthorizationError
        assert summary["category_breakdown"]["transient"] == 2
        assert summary["category_breakdown"]["security"] == 1
        assert (
            summary["retryable_errors"] == 2
        )  # Only NetworkTimeoutErrors are retryable
        assert summary["critical_errors"] == 1

        # Check top error types
        top_types = summary["top_error_types"]
        assert top_types["NetworkTimeoutError"] == 2
        assert top_types["AuthorizationError"] == 1

    def test_format_empty_errors(self):
        """Test formatting with no errors"""
        summary = self.formatter.format_error_summary([])

        assert summary["total_errors"] == 0

    def test_large_error_list_truncation(self):
        """Test that large error lists are truncated in responses"""
        # Create 15 errors (more than the 10 limit)
        errors = []
        for i in range(15):
            errors.append(NetworkTimeoutError(f"service_{i}"))

        response = self.formatter.format_batch_response(
            operation_name="large_batch",
            errors=errors,
            successes=0,
            total_operations=15,
            format_type=ResponseFormat.MCP,
        )

        # Should only include first 10 errors
        assert len(response["errors"]) == 10
        assert response["has_more_errors"] is True


class TestResponseHelpers:
    """Test suite for response helper functions"""

    def test_create_success_response(self):
        """Test creating success response"""
        response = create_success_response(
            data={"result": "value"},
            message="Operation completed",
            metadata={"duration": "1.5s"},
        )

        assert response["success"] is True
        assert response["message"] == "Operation completed"
        assert response["data"]["result"] == "value"
        assert response["metadata"]["duration"] == "1.5s"
        assert "timestamp" in response

    def test_create_success_response_minimal(self):
        """Test creating minimal success response"""
        response = create_success_response()

        assert response["success"] is True
        assert response["message"] == "Operation completed successfully"
        assert "data" not in response
        assert "metadata" not in response

    def test_create_error_response(self):
        """Test creating error response"""
        error = NetworkTimeoutError("test_service")

        response = create_error_response(error, ResponseFormat.MCP)

        assert response["success"] is False
        assert "error" in response

    def test_create_error_response_with_config(self):
        """Test creating error response with custom config"""
        config = ErrorResponseConfig(include_debug_info=True)
        error = NetworkTimeoutError("test_service")

        response = create_error_response(error, ResponseFormat.DEBUG, config)

        assert "debug" in response

    def test_handle_mcp_tool_error(self):
        """Test MCP tool error handling"""
        error = ValueError("Tool execution failed")
        arguments = {"arg1": "value1", "arg2": "value2"}

        response = handle_mcp_tool_error(error, "test_tool", arguments)

        assert response["success"] is False
        error_data = response["error"]
        assert error_data["type"] == "IntegrationError"

        # Check context includes tool information
        context = error_data["context"]
        custom_context = context.get("custom_context", {})
        assert custom_context.get("tool_name") == "test_tool"
        assert custom_context.get("arguments") == arguments


class TestDefaultFormatter:
    """Test suite for default formatter instance"""

    def test_default_formatter_exists(self):
        """Test that default formatter is available"""
        assert default_formatter is not None
        assert isinstance(default_formatter, ErrorResponseFormatter)

    def test_default_formatter_usage(self):
        """Test using default formatter"""
        error = NetworkTimeoutError("test_service")

        response = default_formatter.format_error(error, ResponseFormat.MCP)

        assert response["success"] is False
        assert "error" in response


class TestErrorResponsesIntegration:
    """Integration tests for error response system"""

    def test_json_serialization(self):
        """Test that all response formats are JSON serializable"""
        error = NetworkTimeoutError(
            service_name="test_service",
            context=create_test_context(
                operation="test_op", custom_context={"key": "value"}
            ),
        )

        formatter = ErrorResponseFormatter()

        # Test all response formats
        formats = [
            ResponseFormat.MCP,
            ResponseFormat.JSON_API,
            ResponseFormat.USER_FRIENDLY,
            ResponseFormat.LOGGING,
            ResponseFormat.MONITORING,
            ResponseFormat.DEBUG,
        ]

        for format_type in formats:
            response = formatter.format_error(error, format_type)

            # Should be JSON serializable
            json_str = json.dumps(response, default=str)  # default=str for datetime

            # Should be able to parse back
            parsed = json.loads(json_str)
            assert isinstance(parsed, dict)

    def test_error_response_consistency(self):
        """Test consistency across different response formats"""
        error = NetworkTimeoutError(
            service_name="test_service",
            context=create_test_context(correlation_id="test_corr_123"),
        )

        formatter = ErrorResponseFormatter()

        mcp_response = formatter.format_error(error, ResponseFormat.MCP)
        api_response = formatter.format_error(error, ResponseFormat.JSON_API)
        log_response = formatter.format_error(error, ResponseFormat.LOGGING)

        # All should reference the same correlation ID
        assert mcp_response["error"]["context"]["correlation_id"] == "test_corr_123"
        assert api_response["error"]["id"] == "test_corr_123"
        assert log_response["correlation_id"] == "test_corr_123"

        # All should have consistent error codes
        assert mcp_response["error"]["code"] == "NETWORKTIMEOUTERROR"
        assert api_response["error"]["code"] == "NETWORKTIMEOUTERROR"
        assert log_response["error_code"] == "NETWORKTIMEOUTERROR"
