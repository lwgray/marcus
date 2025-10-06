"""
Coordinator module for Marcus.

Handles task decomposition, subtask management, and task assignment coordination.
"""

from src.marcus_mcp.coordinator.decomposer import (
    decompose_task,
    should_decompose,
)
from src.marcus_mcp.coordinator.subtask_manager import (
    Subtask,
    SubtaskManager,
    SubtaskMetadata,
)

__all__ = [
    "Subtask",
    "SubtaskManager",
    "SubtaskMetadata",
    "should_decompose",
    "decompose_task",
]
