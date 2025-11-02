"""
Marcus Error Response System.

Standardized error response formatting for different contexts:
- MCP protocol responses
- JSON API responses
- User-friendly messages
- Logging formats
- Monitoring/alerting formats
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from .error_framework import (
    ErrorContext,
    ErrorSeverity,
    IntegrationError,
    MarcusBaseError,
)

logger = logging.getLogger(__name__)


class ResponseFormat(Enum):
    """Supported response formats."""

    MCP = "mcp"
    JSON_API = "json_api"
    USER_FRIENDLY = "user_friendly"
    LOGGING = "logging"
    MONITORING = "monitoring"
    DEBUG = "debug"


@dataclass
class ErrorResponseConfig:
    """Configuration for error response formatting."""

    include_debug_info: bool = False
    include_stack_trace: bool = False
    include_system_context: bool = False
    include_remediation: bool = True
    max_message_length: int = 500
    sanitize_sensitive_data: bool = True
    custom_fields: Dict[str, Any] = field(default_factory=dict)


class ErrorResponseFormatter:
    """
    Comprehensive error response formatter for Marcus errors.

    Provides standardized formatting across different contexts while
    maintaining security and usability.
    """

    def __init__(self, config: Optional[ErrorResponseConfig] = None):
        self.config = config or ErrorResponseConfig()
        self.sensitive_fields = {
            "password",
            "token",
            "key",
            "secret",
            "credential",
            "auth",
            "api_key",
            "access_token",
            "refresh_token",
        }

    def format_error(
        self,
        error: Union[MarcusBaseError, Exception],
        format_type: ResponseFormat,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Format error for specified response type.

        Parameters
        ----------
            error
                The error to format.
            format_type
                Target format for the response.
            additional_context
                Additional context to include.

        Returns
        -------
            Formatted error response dictionary
        """
        # Convert regular exceptions to Marcus errors for consistent handling
        if not isinstance(error, MarcusBaseError):
            error = self._convert_to_marcus_error(error)

        # Apply additional context
        if additional_context:
            error.context.custom_context = error.context.custom_context or {}
            error.context.custom_context.update(additional_context)

        # Route to appropriate formatter
        formatters = {
            ResponseFormat.MCP: self._format_for_mcp,
            ResponseFormat.JSON_API: self._format_for_json_api,
            ResponseFormat.USER_FRIENDLY: self._format_for_user,
            ResponseFormat.LOGGING: self._format_for_logging,
            ResponseFormat.MONITORING: self._format_for_monitoring,
            ResponseFormat.DEBUG: self._format_for_debug,
        }

        formatter = formatters.get(format_type, self._format_for_json_api)
        response = formatter(error)

        # Apply post-processing
        if self.config.sanitize_sensitive_data:
            response = self._sanitize_response(response)

        return response

    def _convert_to_marcus_error(self, error: Exception) -> MarcusBaseError:
        """Convert regular exception to Marcus error."""
        return IntegrationError(
            str(error),  # Pass original error message
            service_name="unknown",
            operation="unknown",
            context=ErrorContext(operation="unknown"),
            cause=error,
        )

    def _format_for_mcp(self, error: MarcusBaseError) -> Dict[str, Any]:
        """Format error for MCP protocol response."""
        base_response: Dict[str, Any] = {
            "success": False,
            "error": {
                "code": error.error_code,
                "message": self._truncate_message(error.message),
                "type": error.__class__.__name__,
                "severity": error.severity.value,
                "retryable": error.retryable,
            },
        }

        # Add context information
        if error.context:
            error_dict = base_response["error"]
            error_dict["context"] = {
                "operation": error.context.operation,
                "correlation_id": error.context.correlation_id,
                "timestamp": error.context.timestamp.isoformat(),
                "agent_id": error.context.agent_id,
                "task_id": error.context.task_id,
            }

            # Add custom context if present
            if error.context.custom_context:
                error_dict["context"]["custom_context"] = error.context.custom_context

        # Add remediation if enabled
        if self.config.include_remediation and error.remediation:
            remediation = {}
            if error.remediation.immediate_action:
                remediation["immediate"] = error.remediation.immediate_action
            if error.remediation.fallback_strategy:
                remediation["fallback"] = error.remediation.fallback_strategy
            if error.remediation.retry_strategy:
                remediation["retry"] = error.remediation.retry_strategy

            if remediation:
                error_dict["remediation"] = remediation

        # Add debug information if enabled
        if self.config.include_debug_info:
            debug_info = self._build_debug_info(error)
            if debug_info:
                error_dict["debug"] = debug_info

        return base_response

    def _format_for_json_api(self, error: MarcusBaseError) -> Dict[str, Any]:
        """Format error for JSON API response."""
        response: Dict[str, Any] = {
            "error": {
                "id": error.context.correlation_id,
                "status": self._get_http_status_code(error),
                "code": error.error_code,
                "title": error.__class__.__name__,
                "detail": self._truncate_message(error.message),
                "meta": {
                    "severity": error.severity.value,
                    "category": error.category.value,
                    "retryable": error.retryable,
                    "timestamp": error.context.timestamp.isoformat(),
                },
            }
        }

        # Add source information
        error_dict = response["error"]
        if error.context.operation:
            error_dict["source"] = {
                "operation": error.context.operation,
                "agent_id": error.context.agent_id,
                "task_id": error.context.task_id,
            }

        # Add remediation suggestions
        if self.config.include_remediation and error.remediation:
            suggestions = []
            if error.remediation.immediate_action:
                suggestions.append(
                    {
                        "type": "immediate",
                        "description": error.remediation.immediate_action,
                    }
                )
            if error.remediation.long_term_solution:
                suggestions.append(
                    {
                        "type": "long_term",
                        "description": error.remediation.long_term_solution,
                    }
                )
            if error.remediation.fallback_strategy:
                suggestions.append(
                    {
                        "type": "fallback",
                        "description": error.remediation.fallback_strategy,
                    }
                )

            if suggestions:
                error_dict["meta"]["suggestions"] = suggestions

        return response

    def _format_for_user(self, error: MarcusBaseError) -> Dict[str, Any]:
        """Format error for user-friendly display."""
        # Build user-friendly message
        user_message = error.message

        # Add immediate action if available
        if error.remediation and error.remediation.immediate_action:
            user_message += f"\n\n💡 What to do: {error.remediation.immediate_action}"

        # Add fallback strategy if available
        if error.remediation and error.remediation.fallback_strategy:
            user_message += f"\n\n🔄 Alternative: {error.remediation.fallback_strategy}"

        # Add retry information if retryable
        if error.retryable and error.remediation and error.remediation.retry_strategy:
            user_message += f"\n\n🔁 Retry: {error.remediation.retry_strategy}"

        return {
            "message": user_message,
            "severity": error.severity.value,
            "can_retry": error.retryable,
            "error_id": error.context.correlation_id,
            "help_needed": error.severity
            in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL],
        }

    def _format_for_logging(self, error: MarcusBaseError) -> Dict[str, Any]:
        """Format error for structured logging."""
        log_data: Dict[str, Any] = {
            "error_code": error.error_code,
            "error_type": error.__class__.__name__,
            "message": error.message,
            "severity": error.severity.value,
            "category": error.category.value,
            "retryable": error.retryable,
            "correlation_id": error.context.correlation_id,
            "timestamp": error.context.timestamp.isoformat(),
        }

        # Add context fields
        if error.context.operation:
            log_data["operation"] = error.context.operation
        if error.context.agent_id:
            log_data["agent_id"] = error.context.agent_id
        if error.context.task_id:
            log_data["task_id"] = error.context.task_id
        if error.context.integration_name:
            log_data["integration"] = error.context.integration_name

        # Add cause information
        if error.cause:
            log_data["caused_by"] = str(error.cause)
            log_data["cause_type"] = error.cause.__class__.__name__

        # Add custom context
        if error.context.custom_context:
            log_data["custom_context"] = error.context.custom_context

        return log_data

    def _format_for_monitoring(self, error: MarcusBaseError) -> Dict[str, Any]:
        """Format error for monitoring/alerting systems."""
        return {
            "alert_id": error.context.correlation_id,
            "alert_type": "marcus_error",
            "severity": error.severity.value,
            "category": error.category.value,
            "error_code": error.error_code,
            "service": error.context.integration_name or "marcus",
            "operation": error.context.operation or "unknown",
            "agent_id": error.context.agent_id,
            "task_id": error.context.task_id,
            "timestamp": error.context.timestamp.isoformat(),
            "retryable": error.retryable,
            "message": self._truncate_message(error.message, 200),
            "tags": [
                error.category.value,
                error.severity.value,
                error.__class__.__name__.lower(),
            ],
        }

    def _format_for_debug(self, error: MarcusBaseError) -> Dict[str, Any]:
        """Format error with full debug information."""
        debug_response = {
            "error": error.to_dict(),
            "debug": self._build_debug_info(error, include_all=True),
        }

        # Add custom config fields
        if self.config.custom_fields:
            debug_response.update(self.config.custom_fields)

        return debug_response

    def _build_debug_info(
        self, error: MarcusBaseError, include_all: bool = False
    ) -> Dict[str, Any]:
        """Build debug information for error."""
        debug_info: Dict[str, Any] = {}

        # Stack trace
        if self.config.include_stack_trace or include_all:
            debug_info["stack_trace"] = error.stack_trace

        # System context
        if (
            self.config.include_system_context or include_all
        ) and error.context.system_state:
            debug_info["system_state"] = error.context.system_state

        # Integration context
        if error.context.integration_state:
            debug_info["integration_state"] = error.context.integration_state

        # Agent context
        if error.context.agent_state:
            debug_info["agent_state"] = error.context.agent_state

        # Cause chain
        if error.cause:
            debug_info["cause_chain"] = self._build_cause_chain(error.cause)

        return debug_info

    def _build_cause_chain(
        self, cause: Exception, max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """Build chain of exception causes."""
        chain = []
        current: Optional[Exception] = cause
        depth = 0

        while current and depth < max_depth:
            chain.append(
                {
                    "type": current.__class__.__name__,
                    "message": str(current),
                    "module": current.__class__.__module__,
                }
            )

            current = getattr(current, "__cause__", None)
            depth += 1

        return chain

    def _get_http_status_code(self, error: MarcusBaseError) -> int:
        """Map Marcus error to HTTP status code."""
        from .error_framework import (
            BusinessLogicError,
            ConfigurationError,
            IntegrationError,
            SecurityError,
            SystemError,
            TransientError,
        )

        if isinstance(error, SecurityError):
            return 403  # Forbidden
        elif isinstance(error, ConfigurationError):
            return 400  # Bad Request
        elif isinstance(error, BusinessLogicError):
            return 422  # Unprocessable Entity
        elif isinstance(error, TransientError):
            return 503  # Service Unavailable
        elif isinstance(error, IntegrationError):
            return 502  # Bad Gateway
        elif isinstance(error, SystemError):
            return 500  # Internal Server Error
        else:
            return 500  # Internal Server Error

    def _truncate_message(self, message: str, max_length: Optional[int] = None) -> str:
        """Truncate message to maximum length."""
        max_len = max_length or self.config.max_message_length
        if len(message) <= max_len:
            return message

        return message[: max_len - 3] + "..."

    def _sanitize_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from response."""

        def sanitize_dict(obj: Any) -> Any:
            if isinstance(obj, dict):
                sanitized = {}
                for key, value in obj.items():
                    if any(
                        sensitive in key.lower() for sensitive in self.sensitive_fields
                    ):
                        sanitized[key] = "[REDACTED]"
                    else:
                        sanitized[key] = sanitize_dict(value)
                return sanitized
            elif isinstance(obj, list):
                return [sanitize_dict(item) for item in obj]
            else:
                return obj

        result = sanitize_dict(response)
        # Type guard to help mypy understand the return type
        if not isinstance(result, dict):
            raise TypeError(
                f"Sanitization failed: expected dict, got {type(result).__name__}"
            )
        return result


class BatchErrorResponseFormatter:
    """
    Formats responses for batch operations with multiple errors.

    Provides summary views and detailed breakdowns of batch operation results.
    """

    def __init__(self, formatter: Optional[ErrorResponseFormatter] = None):
        self.formatter = formatter or ErrorResponseFormatter()

    def format_batch_response(
        self,
        operation_name: str,
        errors: List[MarcusBaseError],
        successes: int,
        total_operations: int,
        format_type: ResponseFormat = ResponseFormat.JSON_API,
    ) -> Dict[str, Any]:
        """Format response for batch operation with multiple errors."""
        # Calculate statistics
        error_count = len(errors)
        success_rate = successes / total_operations if total_operations > 0 else 0

        # Group errors by type
        error_groups: Dict[str, List[MarcusBaseError]] = {}
        for error in errors:
            error_type = error.__class__.__name__
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(error)

        # Build summary
        summary = {
            "operation": operation_name,
            "total_operations": total_operations,
            "successes": successes,
            "errors": error_count,
            "success_rate": round(success_rate, 3),
            "error_types": {
                error_type: len(error_list)
                for error_type, error_list in error_groups.items()
            },
        }

        # Format individual errors
        formatted_errors = []
        for error in errors[:10]:  # Limit to first 10 errors
            formatted_error = self.formatter.format_error(error, format_type)
            formatted_errors.append(formatted_error)

        # Build response based on format
        if format_type == ResponseFormat.MCP:
            return {
                "success": error_count == 0,
                "batch_summary": summary,
                "errors": formatted_errors,
                "has_more_errors": len(errors) > 10,
            }

        elif format_type == ResponseFormat.JSON_API:
            return {
                "data": None if error_count > 0 else {"success": True},
                "meta": summary,
                "errors": formatted_errors,
                "has_more_errors": len(errors) > 10,
            }

        else:
            return {
                "summary": summary,
                "errors": formatted_errors,
                "has_more_errors": len(errors) > 10,
            }

    def format_error_summary(self, errors: List[MarcusBaseError]) -> Dict[str, Any]:
        """Create a summary view of multiple errors."""
        if not errors:
            return {"total_errors": 0}

        # Group by severity
        severity_counts: Dict[str, int] = {}
        for error in errors:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Group by category
        category_counts: Dict[str, int] = {}
        for error in errors:
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1

        # Find most common error types
        error_type_counts: Dict[str, int] = {}
        for error in errors:
            error_type = error.__class__.__name__
            error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1

        # Sort by frequency
        top_error_types = sorted(
            error_type_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]

        return {
            "total_errors": len(errors),
            "severity_breakdown": severity_counts,
            "category_breakdown": category_counts,
            "top_error_types": dict(top_error_types),
            "retryable_errors": sum(1 for error in errors if error.retryable),
            "critical_errors": sum(
                1 for error in errors if error.severity == ErrorSeverity.CRITICAL
            ),
        }


# =============================================================================
# RESPONSE HELPERS
# =============================================================================


def create_success_response(
    data: Any = None,
    message: str = "Operation completed successfully",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a standardized success response."""
    response = {
        "success": True,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if data is not None:
        response["data"] = data

    if metadata:
        response["metadata"] = metadata

    return response


def create_error_response(
    error: Union[MarcusBaseError, Exception],
    format_type: ResponseFormat = ResponseFormat.MCP,
    config: Optional[ErrorResponseConfig] = None,
    additional_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a standardized error response."""
    formatter = ErrorResponseFormatter(config)
    return formatter.format_error(error, format_type, additional_context)


def handle_mcp_tool_error(
    error: Exception, tool_name: str, arguments: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Handle errors in MCP tool calls."""
    from .error_framework import ErrorContext

    context = ErrorContext(
        operation=f"mcp_tool_{tool_name}",
        custom_context={"tool_name": tool_name, "arguments": arguments or {}},
    )

    if not isinstance(error, MarcusBaseError):
        error = IntegrationError(
            str(error),  # Include original error message
            service_name="mcp_tool",
            operation=tool_name,
            context=context,
            cause=error,
        )

    return create_error_response(error, ResponseFormat.MCP)


# =============================================================================
# GLOBAL FORMATTER INSTANCE
# =============================================================================

# Default formatter instance for convenient usage
default_formatter = ErrorResponseFormatter()
