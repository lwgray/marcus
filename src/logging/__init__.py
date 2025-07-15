"""
Logging package for Marcus system.

This package provides comprehensive logging capabilities for the Marcus system,
including structured conversation logging, decision tracking, and system state
monitoring. The logging system is designed to capture all interactions between
workers, PM agents, and kanban boards for real-time visualization and analysis.

Modules
-------
conversation_logger : module
    Main logging module containing ConversationLogger class and utility functions
    for structured logging of system interactions and decisions.

Classes
-------
ConversationLogger : class
    Primary logging class for capturing structured conversations and events.
ConversationType : enum
    Enumeration of different conversation types in the system.

Functions
---------
log_conversation : function
    Convenience function for quickly logging conversations between components.
log_thinking : function
    Utility function for logging internal thinking processes and decision-making.

Examples
--------
Basic usage for logging conversations:

>>> from marcus.logging import log_conversation, log_thinking
>>> log_conversation("worker_1", "marcus", "Task completed", {"task_id": "123"})
>>> log_thinking("marcus", "Analyzing task assignment priorities")

Using the main logger class:

>>> from marcus.logging import ConversationLogger
>>> logger = ConversationLogger(log_dir="custom_logs")
>>> logger.log_pm_decision("Assign task to worker_2", "Best skills match")

Notes
-----
All logs are structured in JSON format for easy parsing and analysis.
Log files are automatically rotated with timestamps for organization.
The logging system supports real-time visualization and replay capabilities.
"""

from typing import TYPE_CHECKING

from .conversation_logger import (
    ConversationLogger,
    ConversationType,
    conversation_logger,
    log_conversation,
    log_thinking,
)

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any, Dict, List, Optional

__all__ = [
    "ConversationLogger",
    "ConversationType",
    "conversation_logger",
    "log_conversation",
    "log_thinking",
]
