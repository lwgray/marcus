"""
Communication Module for Marcus.

This module provides multi-channel communication capabilities for the Marcus system.
It enables coordinated notifications and messaging across different platforms to keep
agents and managers informed about task assignments, blockers, and project status.

The main component is the CommunicationHub class which manages notifications across:
- Kanban board comments
- Slack messaging
- Email notifications

Key Features
------------
- Asynchronous message delivery
- Channel-specific message formatting
- Agent communication preferences
- Escalation workflows
- Daily work plan distribution

Classes
-------
CommunicationHub
    Main communication coordinator handling multi-channel notifications

Examples
--------
>>> from src.communication import CommunicationHub
>>> hub = CommunicationHub()
>>> await hub.notify_task_assignment("agent-001", assignment)
"""

from .communication_hub import CommunicationHub

__all__ = ["CommunicationHub"]
