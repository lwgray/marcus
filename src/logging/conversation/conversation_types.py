"""
Conversation type definitions for the Marcus logging system.

This module defines the enumeration of different conversation types
that occur between components in the Marcus ecosystem.
"""

from enum import Enum


class ConversationType(Enum):
    """
    Enumeration of conversation types in the Marcus system.

    This enum defines the different categories of interactions and communications
    that occur between components in the Marcus ecosystem. Each type represents
    a specific communication pattern that requires different handling and analysis.

    Attributes
    ----------
    WORKER_TO_PM : str
        Communications from worker agents to the PM agent, including status
        updates, task completion reports, and blocker notifications.
    PM_TO_WORKER : str
        Communications from PM agent to worker agents, including task assignments,
        instructions, and guidance.
    PM_TO_KANBAN : str
        Communications from PM agent to kanban board system for task management,
        board updates, and status synchronization.
    KANBAN_TO_PM : str
        Communications from kanban board to PM agent, including board state
        changes, task updates, and system notifications.
    INTERNAL_THINKING : str
        Internal reasoning and decision-making processes within agents,
        used for debugging and optimization analysis.
    DECISION : str
        Formal decisions made by the PM agent, including rationale,
        alternatives considered, and confidence scores.
    ERROR : str
        Error conditions, exceptions, and failure scenarios across
        all system components.

    Examples
    --------
    >>> conv_type = ConversationType.WORKER_TO_PM
    >>> print(conv_type.value)
    'worker_to_pm'

    >>> if conversation_type == ConversationType.DECISION:
    ...     # Handle decision logging with additional metadata
    ...     pass

    Notes
    -----
    These conversation types are used for filtering, analysis, and
    visualization of system interactions. Each type may have different
    metadata requirements and processing patterns.
    """

    WORKER_TO_PM = "worker_to_pm"
    PM_TO_WORKER = "pm_to_worker"
    PM_TO_KANBAN = "pm_to_kanban"
    KANBAN_TO_PM = "kanban_to_pm"
    INTERNAL_THINKING = "internal_thinking"
    DECISION = "decision"
    ERROR = "error"
