"""
Unit tests for Marcus Error Framework

Tests the core error handling framework including custom exceptions,
error context, and error response formatting.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.core.error_framework import (  # Transient errors; Configuration errors; Business logic errors; Integration errors; Security errors; System errors
    AIProviderError,
    AuthenticationError,
    AuthorizationError,
    BusinessLogicError,
    ConfigurationError,
    CorruptedStateError,
    CriticalDependencyError,
    DatabaseError,
    EnvironmentError,
    ErrorCategory,
    ErrorContext,
    ErrorSeverity,
    ExternalServiceError,
    IntegrationError,
    InvalidConfigurationError,
    KanbanIntegrationError,
    MarcusBaseError,
    MissingCredentialsError,
    MissingDependencyError,
    NetworkTimeoutError,
    PermissionError,
    RateLimitError,
    RemediationSuggestion,
    ResourceExhaustionError,
    SecurityError,
    ServiceUnavailableError,
    StateConflictError,
    SystemError,
    TaskAssignmentError,
    TemporaryResourceError,
    TransientError,
    ValidationError,
    WorkflowViolationError,
    WorkspaceSecurityError,
    error_context,
)
from tests.unit.test_helpers import create_test_context, create_test_remediation


class TestErrorContext:
    """Test suite for ErrorContext"""

    def test_error_context_creation(self):
        """Test creating error context with default values"""
        context = ErrorContext()

        assert context.operation == ""
        assert context.operation_id is not None
        assert context.agent_id is None
        assert context.task_id is None
        assert context.correlation_id is not None
        assert isinstance(context.timestamp, datetime)
        assert context.custom_context is None

    def test_error_context_with_values(self):
        """Test creating error context with specific values"""
        context = create_test_context(custom_context={"key": "value"})

        assert context.operation == "test_operation"
        assert context.agent_id == "agent_123"
        assert context.task_id == "task_456"
        assert context.custom_context == {"key": "value"}


class TestRemediationSuggestion:
    """Test suite for RemediationSuggestion"""

    def test_remediation_creation(self):
        """Test creating remediation suggestion"""
        remediation = RemediationSuggestion(
            immediate_action="Retry operation",
            long_term_solution="Fix configuration",
            fallback_strategy="Use cached data",
        )

        assert remediation.immediate_action == "Retry operation"
        assert remediation.long_term_solution == "Fix configuration"
        assert remediation.fallback_strategy == "Use cached data"


class TestMarcusBaseError:
    """Test suite for MarcusBaseError"""

    @patch("src.core.error_framework.logger")
    def test_base_error_creation(self, mock_logger):
        """Test creating base Marcus error"""
        context = create_test_context(operation="test_op")
        error = MarcusBaseError(
            message="Test error",
            error_code="TEST_ERROR",
            context=context,
            severity=ErrorSeverity.HIGH,
        )

        assert error.message == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.context.operation == "test_op"
        assert error.severity == ErrorSeverity.HIGH
        assert error.retryable is False
        assert error.category == ErrorCategory.SYSTEM  # Default category

        # Verify logging was called
        mock_logger.error.assert_called_once()

    def test_error_to_dict(self):
        """Test converting error to dictionary"""
        context = create_test_context(operation="test_op", correlation_id="corr_123")
        remediation = create_test_remediation(
            immediate_action="Retry", fallback_strategy="Use fallback"
        )

        error = MarcusBaseError(
            message="Test error",
            error_code="TEST_ERROR",
            context=context,
            remediation=remediation,
            severity=ErrorSeverity.MEDIUM,
        )

        error_dict = error.to_dict()

        assert error_dict["code"] == "TEST_ERROR"
        assert error_dict["message"] == "Test error"
        assert error_dict["type"] == "MarcusBaseError"
        assert error_dict["severity"] == "medium"
        assert error_dict["retryable"] is False
        assert error_dict["context"]["operation"] == "test_op"
        assert error_dict["context"]["agent_id"] == "agent_123"
        assert error_dict["remediation"]["immediate"] == "Retry"
        assert error_dict["remediation"]["fallback"] == "Use fallback"


class TestTransientErrors:
    """Test suite for transient error types"""

    def test_network_timeout_error(self):
        """Test NetworkTimeoutError creation"""
        error = NetworkTimeoutError(service_name="test_service", timeout_seconds=30)

        assert "test_service" in error.message
        assert "30s" in error.message
        assert error.retryable is True
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.category == ErrorCategory.TRANSIENT
        assert "Retry connection" in error.remediation.immediate_action

    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError creation"""
        error = ServiceUnavailableError(service_name="kanban_service")

        assert "kanban_service" in error.message
        assert error.retryable is True
        assert error.category == ErrorCategory.TRANSIENT
        assert "Wait and retry" in error.remediation.immediate_action

    def test_rate_limit_error(self):
        """Test RateLimitError creation"""
        error = RateLimitError(service_name="api_service", retry_after=60)

        assert "api_service" in error.message
        assert "60s" in error.message
        assert error.retryable is True
        assert "Wait 60 seconds" in error.remediation.immediate_action


class TestConfigurationErrors:
    """Test suite for configuration error types"""

    def test_missing_credentials_error(self):
        """Test MissingCredentialsError creation"""
        error = MissingCredentialsError(
            service_name="github", credential_type="API token"
        )

        assert "API token" in error.message
        assert "github" in error.message
        assert error.retryable is False
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.CONFIGURATION

    def test_invalid_configuration_error(self):
        """Test InvalidConfigurationError creation"""
        error = InvalidConfigurationError(
            config_key="database_url", expected_format="postgresql://..."
        )

        assert "database_url" in error.message
        assert "postgresql://" in error.message
        assert error.category == ErrorCategory.CONFIGURATION

    def test_missing_dependency_error(self):
        """Test MissingDependencyError creation"""
        error = MissingDependencyError(dependency_name="redis")

        assert "redis" in error.message
        assert error.category == ErrorCategory.CONFIGURATION


class TestBusinessLogicErrors:
    """Test suite for business logic error types"""

    def test_task_assignment_error(self):
        """Test TaskAssignmentError creation"""
        error = TaskAssignmentError(
            task_id="task_123", agent_id="agent_456", reason="Agent unavailable"
        )

        assert "task_123" in error.message
        assert "agent_456" in error.message
        assert "Agent unavailable" in error.message
        assert error.category == ErrorCategory.BUSINESS_LOGIC
        assert error.severity == ErrorSeverity.MEDIUM

    def test_workflow_violation_error(self):
        """Test WorkflowViolationError creation"""
        error = WorkflowViolationError(workflow_rule="Cannot assign completed task")

        assert "Cannot assign completed task" in error.message
        assert error.category == ErrorCategory.BUSINESS_LOGIC

    def test_validation_error(self):
        """Test ValidationError creation"""
        error = ValidationError(
            field_name="email", validation_rule="must be valid email format"
        )

        assert "email" in error.message
        assert "must be valid email format" in error.message
        assert error.category == ErrorCategory.BUSINESS_LOGIC


class TestIntegrationErrors:
    """Test suite for integration error types"""

    def test_kanban_integration_error(self):
        """Test KanbanIntegrationError creation"""
        error = KanbanIntegrationError(board_name="test_board", operation="create_task")

        assert "test_board" in error.message
        assert "create_task" in error.message
        assert error.category == ErrorCategory.INTEGRATION
        assert error.retryable is True

    def test_ai_provider_error(self):
        """Test AIProviderError creation"""
        error = AIProviderError(provider_name="openai", operation="text_generation")

        assert "openai" in error.message
        assert "text_generation" in error.message
        assert error.category == ErrorCategory.INTEGRATION

    def test_authentication_error(self):
        """Test AuthenticationError creation"""
        error = AuthenticationError(service_name="github")

        assert "github" in error.message
        assert error.severity == ErrorSeverity.HIGH
        assert error.retryable is False
        assert error.category == ErrorCategory.INTEGRATION


class TestSecurityErrors:
    """Test suite for security error types"""

    def test_authorization_error(self):
        """Test AuthorizationError creation"""
        error = AuthorizationError(
            resource="sensitive_data", required_permission="admin"
        )

        assert "sensitive_data" in error.message
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.retryable is False
        assert error.category == ErrorCategory.SECURITY

    def test_workspace_security_error(self):
        """Test WorkspaceSecurityError creation"""
        error = WorkspaceSecurityError(
            path="/restricted/path", violation_type="unauthorized_access"
        )

        assert "/restricted/path" in error.message
        assert "unauthorized_access" in error.message
        assert error.category == ErrorCategory.SECURITY


class TestSystemErrors:
    """Test suite for system error types"""

    def test_resource_exhaustion_error(self):
        """Test ResourceExhaustionError creation"""
        error = ResourceExhaustionError(resource_type="memory", current_usage="95%")

        assert "memory" in error.message
        assert "95%" in error.message
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.category == ErrorCategory.SYSTEM

    def test_database_error(self):
        """Test DatabaseError creation"""
        error = DatabaseError(operation="INSERT", table="tasks")

        assert "INSERT" in error.message
        assert "tasks" in error.message
        assert error.category == ErrorCategory.SYSTEM

    def test_critical_dependency_error(self):
        """Test CriticalDependencyError creation"""
        error = CriticalDependencyError(
            dependency_name="message_queue", failure_reason="Connection refused"
        )

        assert "message_queue" in error.message
        assert "Connection refused" in error.message
        assert error.severity == ErrorSeverity.CRITICAL


class TestErrorContextManager:
    """Test suite for error context manager"""

    def test_error_context_manager_success(self):
        """Test error context manager with successful operation"""
        with error_context("test_operation", agent_id="agent_123") as context:
            assert context.operation == "test_operation"
            assert context.agent_id == "agent_123"
            # No exception should be raised

    def test_error_context_manager_with_marcus_error(self):
        """Test error context manager with Marcus error"""
        with pytest.raises(TaskAssignmentError) as exc_info:
            with error_context("assign_task", agent_id="agent_123", task_id="task_456"):
                raise TaskAssignmentError(
                    task_id="original_task", agent_id="original_agent"
                )

        error = exc_info.value
        # Context should be enhanced with additional info
        assert error.context.operation == "assign_task"
        assert error.context.agent_id == "agent_123"
        assert error.context.task_id == "task_456"

    def test_error_context_manager_with_regular_exception(self):
        """Test error context manager with regular exception"""
        with pytest.raises(ExternalServiceError) as exc_info:
            with error_context("test_operation", agent_id="agent_123"):
                raise ValueError("Regular exception")

        error = exc_info.value
        # Regular exception should be converted to Marcus error
        assert error.context.operation == "test_operation"
        assert error.context.agent_id == "agent_123"
        assert "Regular exception" in str(error.cause)


class TestErrorProperties:
    """Test suite for error properties and categorization"""

    @pytest.mark.parametrize(
        "error_class,expected_category",
        [
            (NetworkTimeoutError, ErrorCategory.TRANSIENT),
            (MissingCredentialsError, ErrorCategory.CONFIGURATION),
            (TaskAssignmentError, ErrorCategory.BUSINESS_LOGIC),
            (KanbanIntegrationError, ErrorCategory.INTEGRATION),
            (AuthorizationError, ErrorCategory.SECURITY),
            (DatabaseError, ErrorCategory.SYSTEM),
        ],
    )
    def test_error_categories(self, error_class, expected_category):
        """Test that errors have correct categories"""
        # Create error with minimal required args
        if error_class in [NetworkTimeoutError, ServiceUnavailableError]:
            error = error_class("test")
        elif error_class == MissingCredentialsError:
            error = error_class("test")
        else:
            error = error_class()

        assert error.category == expected_category

    @pytest.mark.parametrize(
        "error_class,expected_retryable",
        [
            # Transient errors should be retryable
            (NetworkTimeoutError, True),
            (ServiceUnavailableError, True),
            # Configuration errors should not be retryable
            (MissingCredentialsError, False),
            (InvalidConfigurationError, False),
            # Business logic errors should not be retryable
            (TaskAssignmentError, False),
            (ValidationError, False),
            # Integration errors should be retryable
            (KanbanIntegrationError, True),
            (AIProviderError, True),
            # Security errors should not be retryable
            (AuthorizationError, False),
            (WorkspaceSecurityError, False),
            # System errors should not be retryable
            (DatabaseError, False),
            (ResourceExhaustionError, False),
        ],
    )
    def test_retryable_defaults(self, error_class, expected_retryable):
        """Test default retryable settings"""
        # Create error with minimal required args
        if error_class in [NetworkTimeoutError, ServiceUnavailableError]:
            error = error_class("test")
        elif error_class == MissingCredentialsError:
            error = error_class("test")
        elif error_class == InvalidConfigurationError:
            error = error_class("test")
        else:
            error = error_class()

        assert error.retryable == expected_retryable

    @pytest.mark.parametrize(
        "error_class,expected_severity",
        [
            # Transient errors should be medium severity
            (NetworkTimeoutError, ErrorSeverity.MEDIUM),
            # Configuration errors should be high severity
            (MissingCredentialsError, ErrorSeverity.HIGH),
            # Business logic errors should be medium severity
            (TaskAssignmentError, ErrorSeverity.MEDIUM),
            # Integration errors should be medium severity
            (KanbanIntegrationError, ErrorSeverity.MEDIUM),
            # Security errors should be critical severity
            (AuthorizationError, ErrorSeverity.CRITICAL),
            # System errors should be critical severity
            (DatabaseError, ErrorSeverity.CRITICAL),
        ],
    )
    def test_severity_defaults(self, error_class, expected_severity):
        """Test default severity settings"""
        # Create error with minimal required args
        if error_class in [NetworkTimeoutError]:
            error = error_class("test")
        elif error_class == MissingCredentialsError:
            error = error_class("test")
        else:
            error = error_class()

        assert error.severity == expected_severity


class TestErrorSerialization:
    """Test suite for error serialization and JSON compatibility"""

    def test_error_dict_serialization(self):
        """Test that error dictionaries are JSON serializable"""
        error = TaskAssignmentError(
            task_id="task_123", agent_id="agent_456", reason="Test reason"
        )

        error_dict = error.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(error_dict)

        # Should be able to parse back
        parsed_dict = json.loads(json_str)

        assert parsed_dict["code"] == error.error_code
        assert parsed_dict["message"] == error.message
        assert parsed_dict["type"] == "TaskAssignmentError"

    def test_error_context_serialization(self):
        """Test that error context is properly serialized"""
        context = create_test_context()

        error = MarcusBaseError(message="Test error", context=context)

        error_dict = error.to_dict()
        context_dict = error_dict["context"]

        assert context_dict["operation"] == "test_operation"
        assert context_dict["agent_id"] == "agent_123"
        assert context_dict["task_id"] == "task_456"
        assert "timestamp" in context_dict
        assert "correlation_id" in context_dict


@pytest.mark.asyncio
class TestAsyncErrorHandling:
    """Test suite for async error handling scenarios"""

    async def test_async_error_context(self):
        """Test error context with async operations"""

        async def async_operation():
            raise ValueError("Async error")

        with pytest.raises(ExternalServiceError):
            with error_context("async_op", agent_id="agent_123"):
                await async_operation()

    async def test_async_marcus_error(self):
        """Test async operations with Marcus errors"""

        async def async_operation():
            raise NetworkTimeoutError(service_name="test_service")

        with pytest.raises(NetworkTimeoutError) as exc_info:
            await async_operation()

        error = exc_info.value
        assert error.retryable is True
        assert "test_service" in error.message
