"""Minimal stubs for conversation adapter."""

from typing import Any, Dict


def log_agent_event(event_type: str, data: Dict[str, Any]) -> None:
    """
    Stub for logging agent events - delegates to conversation logger.

    Parameters
    ----------
    event_type : str
        The type of event to log.
    data : Dict[str, Any]
        Event data to be logged.
    """
    try:
        from src.logging.agent_events import log_agent_event as real_log_agent_event

        real_log_agent_event(event_type, data)
    except ImportError:
        # Fallback - just print for debugging
        pass
