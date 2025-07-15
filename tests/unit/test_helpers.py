"""
Shared test utilities for unit tests
"""

from src.core.error_framework import ErrorContext, RemediationSuggestion


def create_test_context(
    operation="test_operation",
    agent_id="agent_123",
    task_id="task_456",
    correlation_id="corr_789",
    custom_context=None,
):
    """
    Create a test error context with default values.

    Parameters
    ----------
    operation : str, optional
        The operation name, by default "test_operation"
    agent_id : str, optional
        The agent ID, by default "agent_123"
    task_id : str, optional
        The task ID, by default "task_456"
    correlation_id : str, optional
        The correlation ID, by default "corr_789"
    custom_context : dict, optional
        Custom context data, by default None

    Returns
    -------
    ErrorContext
        The created error context
    """
    return ErrorContext(
        operation=operation,
        agent_id=agent_id,
        task_id=task_id,
        correlation_id=correlation_id,
        custom_context=custom_context,
    )


def create_test_remediation(
    immediate_action="Retry operation",
    fallback_strategy="Use cached data",
    long_term_solution="Fix configuration",
    retry_strategy="Exponential backoff",
):
    """
    Create a test remediation suggestion with default values.

    Parameters
    ----------
    immediate_action : str, optional
        The immediate action to take, by default "Retry operation"
    fallback_strategy : str, optional
        The fallback strategy, by default "Use cached data"
    long_term_solution : str, optional
        The long-term solution, by default "Fix configuration"
    retry_strategy : str, optional
        The retry strategy, by default "Exponential backoff"

    Returns
    -------
    RemediationSuggestion
        The created remediation suggestion
    """
    return RemediationSuggestion(
        immediate_action=immediate_action,
        fallback_strategy=fallback_strategy,
        long_term_solution=long_term_solution,
        retry_strategy=retry_strategy,
    )
