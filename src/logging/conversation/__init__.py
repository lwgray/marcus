"""
Structured conversation logging for Marcus system.

This module provides a comprehensive structured logging system designed to capture
all conversations, decisions, and interactions between Workers, Marcus, and
Kanban Board components.
"""

# Core exports
from .conversation_types import ConversationType
from .logger import ConversationLogger
from .utils import conversation_logger, log_conversation, log_thinking

__all__ = [
    "ConversationType",
    "ConversationLogger",
    "conversation_logger",
    "log_conversation",
    "log_thinking",
]
