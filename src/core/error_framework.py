"""
Marcus Error Handling Framework

Comprehensive error handling system designed for autonomous agent environments.
Provides structured error types, rich context, and intelligent recovery strategies.
"""

import uuid
import time
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for prioritization and alerting."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """High-level error categories for monitoring and classification."""
    TRANSIENT = "transient"
    CONFIGURATION = "configuration"
    BUSINESS_LOGIC = "business_logic"
    INTEGRATION = "integration"
    SECURITY = "security"
    SYSTEM = "system"


@dataclass
class ErrorContext:
    """Rich context information for error debugging and recovery."""
    
    # Operation context
    operation: str = ""
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Agent context
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_state: Optional[Dict[str, Any]] = None
    
    # System context
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    system_state: Optional[Dict[str, Any]] = None
    
    # Integration context
    integration_name: Optional[str] = None
    integration_state: Optional[Dict[str, Any]] = None
    
    # Additional context
    user_context: Optional[Dict[str, Any]] = None
    custom_context: Optional[Dict[str, Any]] = None


@dataclass
class RemediationSuggestion:
    """Actionable remediation suggestions for autonomous agents."""
    
    immediate_action: Optional[str] = None
    long_term_solution: Optional[str] = None
    fallback_strategy: Optional[str] = None
    retry_strategy: Optional[str] = None
    escalation_path: Optional[str] = None


class MarcusBaseError(Exception):
    """
    Base exception class for Marcus-specific errors.
    
    Provides rich context, categorization, and remediation suggestions
    for autonomous agent error handling.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = None,
        context: Optional[ErrorContext] = None,
        remediation: Optional[RemediationSuggestion] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        retryable: bool = False,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.context = context or ErrorContext()
        
        # Handle remediation as either RemediationSuggestion or dict
        if isinstance(remediation, dict):
            self.remediation = RemediationSuggestion(**remediation)
        else:
            self.remediation = remediation or RemediationSuggestion()
            
        self.severity = severity
        self.retryable = retryable
        self.cause = cause
        self.category = self._get_category()
        
        # Capture stack trace for debugging
        self.stack_trace = traceback.format_exc()
        
        # Log error immediately
        self._log_error()
    
    def _get_category(self) -> ErrorCategory:
        """Determine error category based on exception type."""
        # Override in subclasses for specific categorization
        return ErrorCategory.SYSTEM
    
    def _log_error(self):
        """Log error with appropriate level based on severity."""
        log_data = {
            'error_code': self.error_code,
            'error_message': self.message,  # Changed from 'message' to avoid conflict
            'severity': self.severity.value,
            'category': self.category.value,
            'correlation_id': self.context.correlation_id,
            'agent_id': self.context.agent_id,
            'task_id': self.context.task_id,
            'retryable': self.retryable
        }
        
        if self.severity == ErrorSeverity.CRITICAL:
            logger.critical("Critical Marcus error", extra=log_data)
        elif self.severity == ErrorSeverity.HIGH:
            logger.error("High severity Marcus error", extra=log_data)
        elif self.severity == ErrorSeverity.MEDIUM:
            logger.warning("Medium severity Marcus error", extra=log_data)
        else:
            logger.info("Low severity Marcus error", extra=log_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            'code': self.error_code,
            'message': self.message,
            'type': self.__class__.__name__,
            'category': self.category.value,
            'severity': self.severity.value,
            'retryable': self.retryable,
            'context': {
                'operation': self.context.operation,
                'operation_id': self.context.operation_id,
                'agent_id': self.context.agent_id,
                'task_id': self.context.task_id,
                'correlation_id': self.context.correlation_id,
                'timestamp': self.context.timestamp.isoformat(),
                'integration_name': self.context.integration_name,
                'custom_context': self.context.custom_context or {}
            },
            'remediation': {
                'immediate': self.remediation.immediate_action,
                'long_term': self.remediation.long_term_solution,
                'fallback': self.remediation.fallback_strategy,
                'retry': self.remediation.retry_strategy,
                'escalation': self.remediation.escalation_path
            }
        }


# =============================================================================
# TRANSIENT ERRORS (Auto-retryable)
# =============================================================================

class TransientError(MarcusBaseError):
    """Base class for transient errors that can be automatically retried."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('retryable', True)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        super().__init__(*args, **kwargs)
    
    def _get_category(self) -> ErrorCategory:
        return ErrorCategory.TRANSIENT


class NetworkTimeoutError(TransientError):
    """Network operation timed out."""
    
    def __init__(self, service_name: str = "unknown", timeout_seconds: int = 30, *args, **kwargs):
        # Extract service_name from kwargs if not provided positionally
        if 'service_name' in kwargs:
            service_name = kwargs.pop('service_name')
        if 'timeout_seconds' in kwargs:
            timeout_seconds = kwargs.pop('timeout_seconds')
            
        message = f"Network timeout connecting to {service_name} after {timeout_seconds}s"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action=f"Retry connection to {service_name}",
            long_term_solution="Check network connectivity and service availability",
            retry_strategy="Exponential backoff with max 3 attempts"
        ))
        super().__init__(message, *args, **kwargs)


class ServiceUnavailableError(TransientError):
    """External service is temporarily unavailable."""
    
    def __init__(self, service_name: str = "unknown", *args, **kwargs):
        message = f"Service {service_name} is temporarily unavailable"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action=f"Wait and retry {service_name} connection",
            fallback_strategy="Use cached data or degraded functionality",
            retry_strategy="Exponential backoff with circuit breaker"
        ))
        super().__init__(message, *args, **kwargs)


class RateLimitError(TransientError):
    """Rate limit exceeded for API calls."""
    
    def __init__(self, service_name: str = "unknown", retry_after: int = 60, *args, **kwargs):
        message = f"Rate limit exceeded for {service_name}. Retry after {retry_after}s"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action=f"Wait {retry_after} seconds before retrying",
            long_term_solution="Implement request queuing and rate limiting",
            retry_strategy=f"Wait {retry_after}s then retry"
        ))
        super().__init__(message, *args, **kwargs)


class TemporaryResourceError(TransientError):
    """Temporary resource unavailability (memory, disk, etc.)."""
    
    def __init__(self, resource_type: str = "unknown", *args, **kwargs):
        message = f"Temporary {resource_type} resource unavailability"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action="Wait for resource to become available",
            long_term_solution=f"Monitor and optimize {resource_type} usage",
            retry_strategy="Exponential backoff with resource monitoring"
        ))
        super().__init__(message, *args, **kwargs)


# =============================================================================
# CONFIGURATION ERRORS (User-fixable)
# =============================================================================

class ConfigurationError(MarcusBaseError):
    """Base class for configuration-related errors."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        kwargs.setdefault('retryable', False)
        super().__init__(*args, **kwargs)
    
    def _get_category(self) -> ErrorCategory:
        return ErrorCategory.CONFIGURATION


class MissingCredentialsError(ConfigurationError):
    """Required API credentials are missing."""
    
    def __init__(self, service_name: str = "unknown", credential_type: str = "API key", *args, **kwargs):
        message = f"Missing {credential_type} for {service_name}"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action=f"Configure {credential_type} for {service_name}",
            long_term_solution="Set up secure credential management",
            escalation_path="Contact system administrator"
        ))
        super().__init__(message, *args, **kwargs)


class InvalidConfigurationError(ConfigurationError):
    """Configuration values are invalid."""
    
    def __init__(self, config_key: str = "unknown", expected_format: str = "", *args, **kwargs):
        message = f"Invalid configuration for {config_key}"
        if expected_format:
            message += f". Expected format: {expected_format}"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action=f"Correct configuration for {config_key}",
            long_term_solution="Validate configuration on startup",
            escalation_path="Review configuration documentation"
        ))
        super().__init__(message, *args, **kwargs)


class MissingDependencyError(ConfigurationError):
    """Required dependency is missing."""
    
    def __init__(self, dependency_name: str = "unknown", *args, **kwargs):
        message = f"Missing required dependency: {dependency_name}"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action=f"Install {dependency_name}",
            long_term_solution="Add dependency to requirements",
            escalation_path="Contact development team"
        ))
        super().__init__(message, *args, **kwargs)


class EnvironmentError(ConfigurationError):
    """Environment setup is incorrect."""
    
    def __init__(self, environment_issue: str = "unknown", *args, **kwargs):
        message = f"Environment setup issue: {environment_issue}"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action="Fix environment configuration",
            long_term_solution="Automate environment setup",
            escalation_path="Review deployment documentation"
        ))
        super().__init__(message, *args, **kwargs)


# =============================================================================
# BUSINESS LOGIC ERRORS (User/Agent errors)
# =============================================================================

class BusinessLogicError(MarcusBaseError):
    """Base class for business logic violations."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('retryable', False)
        super().__init__(*args, **kwargs)
    
    def _get_category(self) -> ErrorCategory:
        return ErrorCategory.BUSINESS_LOGIC


class TaskAssignmentError(BusinessLogicError):
    """Error in task assignment logic."""
    
    def __init__(self, task_id: str = "unknown", agent_id: str = "unknown", reason: str = "", *args, **kwargs):
        message = f"Cannot assign task {task_id} to agent {agent_id}"
        if reason:
            message += f": {reason}"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action="Review task assignment criteria",
            long_term_solution="Improve task assignment algorithm",
            fallback_strategy="Assign to different agent or queue task"
        ))
        super().__init__(message, *args, **kwargs)


class WorkflowViolationError(BusinessLogicError):
    """Workflow rule violation."""
    
    def __init__(self, workflow_rule: str = "unknown", *args, **kwargs):
        message = f"Workflow violation: {workflow_rule}"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action="Revert to valid workflow state",
            long_term_solution="Strengthen workflow validation",
            escalation_path="Review workflow rules"
        ))
        super().__init__(message, *args, **kwargs)


class ValidationError(BusinessLogicError):
    """Data validation failed."""
    
    def __init__(self, field_name: str = "unknown", validation_rule: str = "", *args, **kwargs):
        message = f"Validation failed for {field_name}"
        if validation_rule:
            message += f": {validation_rule}"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action=f"Correct {field_name} to meet validation requirements",
            long_term_solution="Improve input validation",
            escalation_path="Review validation rules"
        ))
        super().__init__(message, *args, **kwargs)


class StateConflictError(BusinessLogicError):
    """System state conflict detected."""
    
    def __init__(self, conflict_description: str = "unknown", *args, **kwargs):
        message = f"State conflict: {conflict_description}"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action="Resolve state conflict",
            long_term_solution="Implement conflict resolution strategy",
            fallback_strategy="Reset to known good state"
        ))
        super().__init__(message, *args, **kwargs)


# =============================================================================
# INTEGRATION ERRORS (External service issues)
# =============================================================================

class IntegrationError(MarcusBaseError):
    """Base class for external integration errors."""
    
    def __init__(self, *args, **kwargs):
        # Handle different initialization patterns
        message = None
        service_name = "unknown"
        operation = "unknown"
        
        # Check if first arg is a message string
        if args and isinstance(args[0], str):
            message = args[0]
            args = args[1:]
            
        # Extract service_name and operation from kwargs or positional args
        if 'service_name' in kwargs:
            service_name = kwargs.pop('service_name')
        elif args and isinstance(args[0], str):
            service_name = args[0]
            args = args[1:]
            
        if 'operation' in kwargs:
            operation = kwargs.pop('operation')
        elif args and isinstance(args[0], str):
            operation = args[0]
            args = args[1:]
            
        # Store as attributes
        self.service_name = service_name
        self.operation = operation
        
        # Create message if not provided
        if not message:
            message = f"Integration error with {service_name} during {operation}"
            
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('retryable', True)
        super().__init__(message, *args, **kwargs)
    
    def _get_category(self) -> ErrorCategory:
        return ErrorCategory.INTEGRATION


class KanbanIntegrationError(IntegrationError):
    """Kanban board integration error."""
    
    def __init__(self, board_name: str = "unknown", operation: str = "unknown", *args, **kwargs):
        message = f"Kanban integration error: {operation} failed for board {board_name}"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action="Retry Kanban operation",
            fallback_strategy="Cache operation for later sync",
            long_term_solution="Implement Kanban health monitoring"
        ))
        super().__init__(message, *args, **kwargs)


class AIProviderError(IntegrationError):
    """AI provider integration error."""
    
    def __init__(self, provider_name: str = "unknown", operation: str = "unknown", *args, **kwargs):
        message = f"AI provider error: {operation} failed for {provider_name}"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action="Retry with backoff",
            fallback_strategy="Use fallback AI provider or cached results",
            long_term_solution="Implement AI provider health checks"
        ))
        super().__init__(message, *args, **kwargs)


class AuthenticationError(IntegrationError):
    """Authentication failed for external service."""
    
    def __init__(self, service_name: str = "unknown", *args, **kwargs):
        message = f"Authentication failed for {service_name}"
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        kwargs.setdefault('retryable', False)
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action="Check and refresh authentication credentials",
            long_term_solution="Implement credential rotation",
            escalation_path="Contact service provider"
        ))
        super().__init__(message, *args, **kwargs)


class ExternalServiceError(IntegrationError):
    """Generic external service error."""
    
    def __init__(self, service_name: str = "unknown", error_details: str = "", *args, **kwargs):
        message = f"External service error: {service_name}"
        if error_details:
            message += f" - {error_details}"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action="Retry service call",
            fallback_strategy="Use cached data or degraded functionality",
            long_term_solution="Implement service health monitoring"
        ))
        super().__init__(message, *args, **kwargs)


# =============================================================================
# SECURITY ERRORS (Critical, non-retryable)
# =============================================================================

class SecurityError(MarcusBaseError):
    """Base class for security-related errors."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('severity', ErrorSeverity.CRITICAL)
        kwargs.setdefault('retryable', False)
        super().__init__(*args, **kwargs)
    
    def _get_category(self) -> ErrorCategory:
        return ErrorCategory.SECURITY


class AuthorizationError(SecurityError):
    """Authorization failed - insufficient permissions."""
    
    def __init__(self, resource: str = "unknown", required_permission: str = "unknown", *args, **kwargs):
        message = f"Authorization failed: insufficient permissions for {resource}"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action="Request appropriate permissions",
            escalation_path="Contact system administrator",
            long_term_solution="Review and update permission model"
        ))
        super().__init__(message, *args, **kwargs)


class WorkspaceSecurityError(SecurityError):
    """Workspace security violation."""
    
    def __init__(self, path: str = "unknown", violation_type: str = "unknown", *args, **kwargs):
        message = f"Workspace security violation: {violation_type} for path {path}"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action="Block access to restricted path",
            escalation_path="Review workspace security policy",
            long_term_solution="Strengthen workspace isolation"
        ))
        super().__init__(message, *args, **kwargs)


class PermissionError(SecurityError):
    """Permission denied for operation."""
    
    def __init__(self, operation: str = "unknown", resource: str = "unknown", *args, **kwargs):
        message = f"Permission denied: {operation} on {resource}"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action="Check operation permissions",
            escalation_path="Request permission elevation",
            long_term_solution="Review permission model"
        ))
        super().__init__(message, *args, **kwargs)


# =============================================================================
# SYSTEM ERRORS (Critical system issues)
# =============================================================================

class SystemError(MarcusBaseError):
    """Base class for critical system errors."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('severity', ErrorSeverity.CRITICAL)
        kwargs.setdefault('retryable', False)
        super().__init__(*args, **kwargs)
    
    def _get_category(self) -> ErrorCategory:
        return ErrorCategory.SYSTEM


class ResourceExhaustionError(SystemError):
    """System resource exhaustion."""
    
    def __init__(self, resource_type: str = "unknown", current_usage: str = "", *args, **kwargs):
        message = f"Resource exhaustion: {resource_type}"
        if current_usage:
            message += f" (current usage: {current_usage})"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action="Free up resources or restart system",
            long_term_solution="Implement resource monitoring and limits",
            escalation_path="Contact system administrator"
        ))
        super().__init__(message, *args, **kwargs)


class CorruptedStateError(SystemError):
    """System state corruption detected."""
    
    def __init__(self, component: str = "unknown", corruption_details: str = "", *args, **kwargs):
        message = f"Corrupted state detected in {component}"
        if corruption_details:
            message += f": {corruption_details}"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action="Restore from backup or reinitialize",
            long_term_solution="Implement state validation and backup",
            escalation_path="Contact development team"
        ))
        super().__init__(message, *args, **kwargs)


class DatabaseError(SystemError):
    """Database operation failed."""
    
    def __init__(self, operation: str = "unknown", table: str = "unknown", *args, **kwargs):
        message = f"Database error: {operation} failed for table {table}"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action="Check database connectivity and integrity",
            fallback_strategy="Use cached data or read-only mode",
            escalation_path="Contact database administrator"
        ))
        super().__init__(message, *args, **kwargs)


class CriticalDependencyError(SystemError):
    """Critical system dependency failure."""
    
    def __init__(self, dependency_name: str = "unknown", failure_reason: str = "", *args, **kwargs):
        message = f"Critical dependency failure: {dependency_name}"
        if failure_reason:
            message += f" - {failure_reason}"
        kwargs.setdefault('remediation', RemediationSuggestion(
            immediate_action="Restart dependency or system",
            long_term_solution="Implement dependency health monitoring",
            escalation_path="Contact system administrator"
        ))
        super().__init__(message, *args, **kwargs)


# =============================================================================
# ERROR CONTEXT MANAGER
# =============================================================================

@contextmanager
def error_context(
    operation: str,
    agent_id: str = None,
    task_id: str = None,
    integration_name: str = None,
    custom_context: Dict[str, Any] = None
):
    """
    Context manager for automatic error context injection.
    
    Usage:
        with error_context("create_task", agent_id="agent_123", task_id="task_456"):
            # operations that might raise Marcus errors
            pass
    """
    context = ErrorContext(
        operation=operation,
        agent_id=agent_id,
        task_id=task_id,
        integration_name=integration_name,
        custom_context=custom_context or {}
    )
    
    try:
        yield context
    except MarcusBaseError as e:
        # Enhance existing Marcus errors with additional context
        if not e.context.operation:
            e.context.operation = context.operation
        if not e.context.agent_id:
            e.context.agent_id = context.agent_id
        if not e.context.task_id:
            e.context.task_id = context.task_id
        if not e.context.integration_name:
            e.context.integration_name = context.integration_name
        raise
    except Exception as e:
        # Convert regular exceptions to Marcus errors with context
        raise ExternalServiceError(
            service_name="unknown",
            error_details=str(e),
            context=context,
            cause=e
        )


# =============================================================================
# ERROR RESPONSE FORMATTER
# =============================================================================

class ErrorResponseFormatter:
    """Formats error responses for different output formats (MCP, JSON, etc.)."""
    
    @staticmethod
    def format_for_mcp(error: MarcusBaseError, include_debug: bool = False) -> Dict[str, Any]:
        """Format error for MCP protocol response."""
        response = {
            "success": False,
            "error": error.to_dict()
        }
        
        if include_debug:
            response["error"]["debug"] = {
                "stack_trace": error.stack_trace,
                "cause": str(error.cause) if error.cause else None,
                "system_state": error.context.system_state,
                "integration_state": error.context.integration_state
            }
        
        return response
    
    @staticmethod
    def format_for_logging(error: MarcusBaseError) -> Dict[str, Any]:
        """Format error for structured logging."""
        return {
            "error_code": error.error_code,
            "message": error.message,
            "category": error.category.value,
            "severity": error.severity.value,
            "retryable": error.retryable,
            "correlation_id": error.context.correlation_id,
            "operation": error.context.operation,
            "agent_id": error.context.agent_id,
            "task_id": error.context.task_id,
            "integration_name": error.context.integration_name,
            "timestamp": error.context.timestamp.isoformat()
        }
    
    @staticmethod
    def format_user_friendly(error: MarcusBaseError) -> str:
        """Format error for user-friendly display."""
        message = error.message
        
        if error.remediation.immediate_action:
            message += f"\n\nImmediate action: {error.remediation.immediate_action}"
        
        if error.remediation.fallback_strategy:
            message += f"\nFallback: {error.remediation.fallback_strategy}"
        
        return message


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================

# Maintain backward compatibility with existing code
MarcusError = MarcusBaseError