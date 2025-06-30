"""
Unit tests for Marcus Error Response System

Tests error response formatting for different contexts including MCP,
JSON API, user-friendly messages, and logging formats.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch

from src.core.error_responses import (
    ErrorResponseFormatter, ErrorResponseConfig, ResponseFormat,
    BatchErrorResponseFormatter, create_success_response,
    create_error_response, handle_mcp_tool_error, default_formatter
)
from src.core.error_framework import (
    MarcusBaseError, NetworkTimeoutError, AuthorizationError,
    TaskAssignmentError, ErrorContext, ErrorSeverity,
    RemediationSuggestion
)


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
        assert config.custom_fields is None
    
    def test_config_custom_values(self):
        """Test ErrorResponseConfig with custom values"""
        config = ErrorResponseConfig(
            include_debug_info=True,
            include_stack_trace=True,
            max_message_length=1000,
            sanitize_sensitive_data=False,
            custom_fields={"custom": "value"}
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
            include_debug_info=True,
            include_remediation=True
        )
        self.formatter = ErrorResponseFormatter(self.config)
    
    def create_test_error(self):
        """Create a test error for formatting tests"""
        context = ErrorContext(
            operation="test_operation",
            agent_id="agent_123",
            task_id="task_456",
            correlation_id="corr_789"
        )
        remediation = RemediationSuggestion(
            immediate_action="Retry operation",
            fallback_strategy="Use cached data",
            long_term_solution="Fix configuration"
        )
        
        return NetworkTimeoutError(
            service_name="test_service",
            timeout_seconds=30,
            context=context,
            remediation=remediation
        )
    
    def test_format_for_mcp(self):
        """Test formatting error for MCP protocol"""
        error = self.create_test_error()
        
        response = self.formatter.format_error(error, ResponseFormat.MCP)
        
        assert response["success"] is False
        assert "error" in response
        
        error_data = response["error"]
        assert error_data["code"] == "NETWORKTIMEOUTERROR"
        assert "test_service" in error_data["message"]
        assert error_data["type"] == "NetworkTimeoutError"
        assert error_data["severity"] == "medium"
        assert error_data["retryable"] is True
        
        # Check context
        assert "context" in error_data
        context = error_data["context"]
        assert context["operation"] == "test_operation"
        assert context["agent_id"] == "agent_123"
        assert context["task_id"] == "task_456"
        assert context["correlation_id"] == "corr_789"
        
        # Check remediation
        assert "remediation" in error_data
        remediation = error_data["remediation"]
        assert remediation["immediate"] == "Retry operation"
        assert remediation["fallback"] == "Use cached data"
    
    def test_format_for_json_api(self):
        """Test formatting error for JSON API response"""
        error = self.create_test_error()
        
        response = self.formatter.format_error(error, ResponseFormat.JSON_API)
        
        assert "error" in response
        error_data = response["error"]
        
        assert error_data["id"] == "corr_789"
        assert error_data["status"] == 503  # Service Unavailable for transient errors
        assert error_data["code"] == "NETWORKTIMEOUTERROR"
        assert error_data["title"] == "NetworkTimeoutError"
        assert "test_service" in error_data["detail"]
        
        # Check meta information
        assert "meta" in error_data
        meta = error_data["meta"]
        assert meta["severity"] == "medium"
        assert meta["retryable"] is True
        assert "suggestions" in meta
        
        # Check source information
        assert "source" in error_data
        source = error_data["source"]
        assert source["operation"] == "test_operation"
        assert source["agent_id"] == "agent_123"
    
    def test_format_for_user_friendly(self):
        """Test formatting error for user-friendly display"""
        error = self.create_test_error()
        
        response = self.formatter.format_error(error, ResponseFormat.USER_FRIENDLY)
        
        assert "message" in response
        assert "What to do: Retry operation" in response["message"]
        assert "Alternative: Use cached data" in response["message"]
        assert "Retry:" in response["message"]  # Should include retry info for retryable errors
        
        assert response["severity"] == "medium"
        assert response["can_retry"] is True
        assert response["error_id"] == "corr_789"
        assert response["help_needed"] is False  # Medium severity doesn't need help
    
    def test_format_for_logging(self):
        """Test formatting error for structured logging"""
        error = self.create_test_error()
        
        response = self.formatter.format_error(error, ResponseFormat.LOGGING)
        
        assert response["error_code"] == "NETWORKTIMEOUTERROR"
        assert response["error_type"] == "NetworkTimeoutError"
        assert "test_service" in response["message"]
        assert response["severity"] == "medium"
        assert response["retryable"] is True
        assert response["correlation_id"] == "corr_789"
        assert response["operation"] == "test_operation"
        assert response["agent_id"] == "agent_123"
        assert response["task_id"] == "task_456"
    
    def test_format_for_monitoring(self):
        """Test formatting error for monitoring/alerting"""
        error = self.create_test_error()
        
        response = self.formatter.format_error(error, ResponseFormat.MONITORING)
        
        assert response["alert_id"] == "corr_789"
        assert response["alert_type"] == "marcus_error"
        assert response["severity"] == "medium"
        assert response["service"] == "marcus"  # No integration name set
        assert response["operation"] == "test_operation"
        assert response["agent_id"] == "agent_123"
        assert response["retryable"] is True
        
        # Check tags
        assert "tags" in response
        tags = response["tags"]
        assert "transient" in tags
        assert "medium" in tags
        assert "networktimeouterror" in tags
    
    def test_format_for_debug(self):
        """Test formatting error for debug output"""
        config = ErrorResponseConfig(
            include_debug_info=True,
            include_stack_trace=True
        )
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
        assert error_data["type"] == "ExternalServiceError"
        assert "Regular error message" in error_data["message"]
    
    def test_http_status_code_mapping(self):
        """Test HTTP status code mapping for different error types"""
        # Test different error types
        auth_error = AuthorizationError()
        timeout_error = NetworkTimeoutError("service")
        task_error = TaskAssignmentError()
        
        auth_response = self.formatter.format_error(auth_error, ResponseFormat.JSON_API)
        timeout_response = self.formatter.format_error(timeout_error, ResponseFormat.JSON_API)
        task_response = self.formatter.format_error(task_error, ResponseFormat.JSON_API)
        
        assert auth_response["error"]["status"] == 403  # Forbidden
        assert timeout_response["error"]["status"] == 503  # Service Unavailable
        assert task_response["error"]["status"] == 422  # Unprocessable Entity
    
    def test_message_truncation(self):
        """Test message truncation for long messages"""
        config = ErrorResponseConfig(max_message_length=50)
        formatter = ErrorResponseFormatter(config)
        
        long_message = "This is a very long error message that exceeds the maximum length limit"
        error = MarcusBaseError(message=long_message)
        
        response = formatter.format_error(error, ResponseFormat.MCP)
        
        truncated_message = response["error"]["message"]
        assert len(truncated_message) <= 50
        assert truncated_message.endswith("...")
    
    def test_sensitive_data_sanitization(self):
        """Test sanitization of sensitive data"""
        context = ErrorContext(
            custom_context={
                "password": "secret123",
                "api_key": "key_abc123",
                "safe_data": "this is ok",
                "user_token": "token_xyz789"
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
        
        context = ErrorContext(
            custom_context={"password": "secret123"}
        )
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
            error, 
            ResponseFormat.MCP,
            additional_context
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
            NetworkTimeoutError("service1", context=ErrorContext(operation="op1")),
            NetworkTimeoutError("service2", context=ErrorContext(operation="op2")),
            AuthorizationError(context=ErrorContext(operation="op3"))
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
            format_type=ResponseFormat.MCP
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
            format_type=ResponseFormat.JSON_API
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
        assert summary["retryable_errors"] == 2  # Only NetworkTimeoutErrors are retryable
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
            format_type=ResponseFormat.MCP
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
            metadata={"duration": "1.5s"}
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
        
        response = create_error_response(
            error, 
            ResponseFormat.DEBUG,
            config
        )
        
        assert "debug" in response
    
    def test_handle_mcp_tool_error(self):
        """Test MCP tool error handling"""
        error = ValueError("Tool execution failed")
        arguments = {"arg1": "value1", "arg2": "value2"}
        
        response = handle_mcp_tool_error(error, "test_tool", arguments)
        
        assert response["success"] is False
        error_data = response["error"]
        assert error_data["type"] == "ExternalServiceError"
        
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
            context=ErrorContext(
                operation="test_op",
                agent_id="agent_123",
                custom_context={"key": "value"}
            )
        )
        
        formatter = ErrorResponseFormatter()
        
        # Test all response formats
        formats = [
            ResponseFormat.MCP,
            ResponseFormat.JSON_API,
            ResponseFormat.USER_FRIENDLY,
            ResponseFormat.LOGGING,
            ResponseFormat.MONITORING,
            ResponseFormat.DEBUG
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
            context=ErrorContext(correlation_id="test_corr_123")
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