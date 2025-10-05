"""
Minimal stub for pattern learning initialization.

The actual pattern learning API has been moved to Seneca.
This stub maintains backwards compatibility for Marcus core.
"""

from typing import Any, Optional


def init_pattern_learning_components(
    kanban_client: Optional[Any] = None, ai_engine: Optional[Any] = None
) -> None:
    """
    Stub for pattern learning component initialization.

    Parameters
    ----------
    kanban_client : Optional[Any], optional
        Kanban client instance (ignored), by default None
    ai_engine : Optional[Any], optional
        AI engine instance (ignored), by default None
    """
    # No-op stub - pattern learning functionality moved to Seneca
    pass
