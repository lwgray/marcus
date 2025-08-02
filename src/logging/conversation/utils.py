"""
Utility functions for conversation logging.

This module provides convenience functions for quick logging without
needing to directly interact with the ConversationLogger class.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import structlog

from .logger import ConversationLogger

# Global logger instance
_conversation_logger: Optional[ConversationLogger] = None
# Create default instance for backward compatibility
conversation_logger = ConversationLogger()


def get_conversation_logger() -> ConversationLogger:
    """Get or create the global conversation logger instance."""
    global _conversation_logger
    if _conversation_logger is None:
        _conversation_logger = ConversationLogger()
    return _conversation_logger


def log_conversation(
    sender: str, receiver: str, message: str, metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Convenience function for quick conversation logging between system components.

    Provides a simplified interface for logging conversations without needing
    to directly interact with the ConversationLogger class. Automatically
    determines the appropriate conversation type and routing based on sender
    and receiver identifiers.

    Parameters
    ----------
    sender : str
        Identifier of the message sender. Common patterns:
        - 'worker_{type}_{id}': Worker agents (e.g., 'worker_backend_1')
        - 'marcus': Marcus system
        - 'kanban': Kanban board system
        - 'system': System-level messages
    receiver : str
        Identifier of the message receiver, following same patterns as sender.
    message : str
        The conversation message content to be logged.
    metadata : Optional[Dict[str, Any]], default=None
        Additional context and structured data for the conversation:
        - action: Specific action being performed
        - task_id: Associated task identifier
        - priority: Message or task priority level
        - timestamp: Custom timestamp if different from log time
        - status: Current status information

    Examples
    --------
    Worker reporting to Marcus:

    >>> log_conversation(
    ...     sender="worker_backend_1",
    ...     receiver="marcus",
    ...     message="Task TASK-123 completed successfully",
    ...     metadata={"task_id": "TASK-123", "completion_time": "2024-01-15T16:30:00Z"}
    ... )

    Marcus communicating with worker:

    >>> log_conversation(
    ...     sender="marcus",
    ...     receiver="worker_frontend_2",
    ...     message="New high-priority UI task assigned",
    ...     metadata={"task_id": "TASK-456", "priority": "high", "deadline": "2024-01-18"}
    ... )

    Marcus updating Kanban board:

    >>> log_conversation(
    ...     sender="marcus",
    ...     receiver="kanban",
    ...     message="Updating task status to completed",
    ...     metadata={"action": "update_task", "task_id": "TASK-789", "new_status": "Done"}
    ... )

    Kanban board notifying Marcus:

    >>> log_conversation(
    ...     sender="kanban",
    ...     receiver="marcus",
    ...     message="Board state synchronized, 3 new tasks added",
    ...     metadata={"action": "sync_complete", "new_tasks": 3, "total_tasks": 47}
    ... )

    Notes
    -----
    This function uses the global conversation_logger instance.
    Message routing is determined automatically from sender/receiver patterns.
    All conversations are timestamped automatically.
    Invalid sender/receiver patterns will log as general debug information.

    See Also
    --------
    ConversationLogger.log_worker_message : Direct worker message logging
    log_thinking : Convenience function for internal reasoning logs
    """
    logger = get_conversation_logger()

    if sender.startswith("worker"):
        logger.log_worker_message(sender, "to_pm", message, metadata)
    elif receiver.startswith("worker"):
        logger.log_worker_message(receiver, "from_pm", message, metadata)
    # Note: Kanban interactions would need to be added when that module is created
    else:
        # Log as general debug info for unsupported patterns
        debug_logger = logging.getLogger(__name__)
        debug_logger.debug(
            f"Conversation from {sender} to {receiver}: {message}",
            extra={"metadata": metadata},
        )


def log_thinking(
    component: str, thought: str, context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Convenience function for logging internal reasoning and decision processes.

    Provides a simplified interface for capturing internal thought processes,
    analysis steps, and reasoning chains across different system components.
    Enables debugging and optimization of AI and algorithmic decision-making.

    Parameters
    ----------
    component : str
        Identifier of the component doing the thinking:
        - 'marcus': Marcus reasoning and decision-making
        - 'worker_{type}_{id}': Worker agent internal processing
        - 'kanban': Kanban board processing and analysis
        - 'system': System-level analysis and monitoring
        - 'scheduler': Task scheduling and optimization
        - 'analyzer': Performance and pattern analysis
    thought : str
        Description of the internal thought, analysis, or reasoning step.
        Should be clear and detailed enough for debugging and optimization.
    context : Optional[Dict[str, Any]], default=None
        Additional context surrounding the thought process:
        - current_state: Relevant system or component state
        - input_data: Data being analyzed or processed
        - decision_factors: Factors being considered
        - analysis_results: Results of analysis or computation
        - confidence_level: Confidence in the reasoning
        - alternatives: Alternative approaches considered

    Examples
    --------
    Marcus task assignment reasoning:

    >>> log_thinking(
    ...     component="marcus",
    ...     thought="Evaluating worker capacity and skills for urgent security task",
    ...     context={
    ...         "available_workers": 5,
    ...         "task_requirements": ["security", "nodejs", "immediate_availability"],
    ...         "worker_scores": {"worker_1": 0.9, "worker_2": 0.7, "worker_3": 0.8},
    ...         "decision_factors": ["expertise", "availability", "current_load"],
    ...         "confidence_level": 0.85
    ...     }
    ... )

    Worker agent problem-solving process:

    >>> log_thinking(
    ...     component="worker_backend_1",
    ...     thought="Analyzing database performance issue, considering indexing strategies",
    ...     context={
    ...         "query_performance": "slow",
    ...         "affected_tables": ["users", "orders", "products"],
    ...         "potential_solutions": ["add_indexes", "optimize_queries", "partition_tables"],
    ...         "estimated_impact": {"add_indexes": "high", "optimize_queries": "medium"},
    ...         "implementation_complexity": {"add_indexes": "low", "optimize_queries": "medium"}
    ...     }
    ... )

    System analyzer pattern recognition:

    >>> log_thinking(
    ...     component="analyzer",
    ...     thought="Detecting recurring bottleneck pattern in task assignments",
    ...     context={
    ...         "pattern_type": "bottleneck",
    ...         "frequency": "daily_14:00-16:00",
    ...         "affected_workers": ["worker_1", "worker_3"],
    ...         "root_cause_hypothesis": "lunch_break_scheduling_conflict",
    ...         "confidence": 0.78,
    ...         "suggested_action": "stagger_break_times"
    ...     }
    ... )

    Scheduler optimization reasoning:

    >>> log_thinking(
    ...     component="scheduler",
    ...     thought="Optimizing task order to minimize dependency delays",
    ...     context={
    ...         "total_tasks": 24,
    ...         "dependency_chains": 6,
    ...         "critical_path_length": 12,
    ...         "optimization_strategy": "dependency_first",
    ...         "expected_improvement": "15%_faster_completion",
    ...         "alternative_strategies": ["priority_first", "worker_balanced"]
    ...     }
    ... )

    Notes
    -----
    Thinking logs are typically recorded at DEBUG level.
    Marcus thoughts use specialized logging for enhanced analysis.
    Other components use general structured logging with component identification.
    Context should include data that influenced the reasoning process.
    These logs are essential for AI/algorithm debugging and optimization.

    See Also
    --------
    ConversationLogger.log_pm_thinking : Direct Marcus thinking logs
    ConversationLogger.log_pm_decision : Log formal decisions
    log_conversation : Convenience function for inter-component communication
    """
    logger = get_conversation_logger()

    if component == "marcus":
        logger.log_pm_thinking(thought, context)
    else:
        # Log as general debug info using structlog if available
        try:
            struct_logger = structlog.get_logger(component)
            struct_logger.debug(
                "thinking",
                thought=thought,
                context=context or {},
                timestamp=datetime.now().isoformat(),
            )
        except:
            # Fallback to standard logging
            debug_logger = logging.getLogger(component)
            debug_logger.debug(f"Thinking: {thought}", extra={"context": context})
