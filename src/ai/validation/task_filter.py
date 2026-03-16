"""Task type filtering for validation system.

This module determines which tasks should be validated based on their type.
Only implementation tasks are validated - design, planning, and documentation
tasks are skipped to respect agent autonomy for creative work.
"""

from typing import Any


def should_validate_task(task: Any) -> bool:
    """Determine if a task should undergo validation.

    Validation is applied only to implementation tasks (tasks that create
    working code). Design, planning, testing, and documentation tasks are
    skipped to respect agent autonomy for creative work.

    Parameters
    ----------
    task : Any
        Task object to evaluate (must have 'labels' attribute)

    Returns
    -------
    bool
        True if task should be validated, False otherwise

    Notes
    -----
    Implementation tasks are identified by labels like:
    - implement, build, create, develop
    - backend, frontend, api, database

    Excluded task types (never validated):
    - design, planning, architecture, research
    - testing, qa, review
    - documentation, docs, readme
    """
    if not hasattr(task, "labels") or not task.labels:
        # No labels - skip validation (can't determine type)
        return False

    # Convert labels to lowercase for case-insensitive matching
    labels_lower = [label.lower() for label in task.labels]

    # Implementation labels - tasks that create working code
    implementation_labels = {
        "implement",
        "implementation",
        "build",
        "create",
        "develop",
        "development",
        "backend",
        "frontend",
        "api",
        "database",
        "feature",
        "enhancement",
    }

    # Exclusion labels - tasks that should NOT be validated
    exclusion_labels = {
        "design",
        "planning",
        "plan",
        "architecture",
        "research",
        "investigation",
        "testing",
        "test",
        "qa",
        "review",
        "documentation",
        "docs",
        "readme",
        "refactor",  # Refactoring is creative work
        "cleanup",  # Cleanup is creative work
    }

    # Check for exclusion labels first (priority)
    if any(label in exclusion_labels for label in labels_lower):
        return False

    # Check for implementation labels
    if any(label in implementation_labels for label in labels_lower):
        return True

    # Default: don't validate if we can't clearly identify as implementation
    return False
