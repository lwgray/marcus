"""
Lightweight agent event logging for Marcus

This module provides basic event logging functionality without any dependencies
on visualization libraries like NetworkX. It's designed to be fast and safe
for use in the core Marcus operations.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def log_agent_event(event_type: str, event_data: Dict[str, Any]) -> None:
    """
    Log an agent event for later visualization.

    This is a lightweight version that doesn't trigger NetworkX imports.

    Args:
        event_type: Type of event (e.g., "task_request", "worker_registration")
        event_data: Event details as a dictionary
    """
    try:
        # Create logs directory if it doesn't exist
        # Use absolute path based on Marcus root directory
        marcus_root = Path(__file__).parent.parent.parent
        log_dir = marcus_root / "logs" / "agent_events"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped event
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": event_data,
        }

        # Write to a simple JSON lines file
        log_file = log_dir / f"agent_events_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(event) + "\n")

    except Exception as e:
        # Don't let logging errors break the main functionality
        print(f"Warning: Failed to log agent event: {e}", file=sys.stderr)


# For compatibility, create an alias
def log_conversation_event(event_type: str, event_data: Dict[str, Any]) -> None:
    """Alias for log_agent_event for backward compatibility"""
    log_agent_event(event_type, event_data)
