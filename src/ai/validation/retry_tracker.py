"""Retry tracking for validation system.

This module tracks validation attempts and detects when agents retry with
the same issues (indicating they're stuck in a loop).
"""

from datetime import datetime, timedelta
from typing import Optional

from src.ai.validation.validation_models import (
    ValidationAttemptRecord,
    ValidationResult,
)


class RetryTracker:
    """Tracks validation attempts to detect repeated failures.

    Maintains in-memory history of validation attempts per task and
    detects when agents retry with the same issues.

    Attributes
    ----------
    _attempts : dict[str, list[ValidationAttemptRecord]]
        Validation attempts per task_id
    _cleanup_threshold : timedelta
        Auto-cleanup attempts older than this threshold
    """

    def __init__(self, cleanup_hours: int = 24) -> None:
        """Initialize retry tracker.

        Parameters
        ----------
        cleanup_hours : int, optional
            Hours after which old attempts are cleaned up, by default 24
        """
        self._attempts: dict[str, list[ValidationAttemptRecord]] = {}
        self._cleanup_threshold = timedelta(hours=cleanup_hours)

    def record_attempt(
        self, task_id: str, result: ValidationResult
    ) -> ValidationAttemptRecord:
        """Record a validation attempt for a task.

        Parameters
        ----------
        task_id : str
            Task being validated
        result : ValidationResult
            Validation result for this attempt

        Returns
        -------
        ValidationAttemptRecord
            The recorded attempt

        Notes
        -----
        Automatically cleans up stale attempts before recording.
        """
        # Clean up stale attempts first
        self._cleanup_stale_attempts(task_id)

        # Get attempt number (incremental)
        if task_id not in self._attempts:
            self._attempts[task_id] = []
        attempt_number = len(self._attempts[task_id]) + 1

        # Create and store record
        record = ValidationAttemptRecord(
            task_id=task_id,
            attempt_number=attempt_number,
            result=result,
            timestamp=datetime.utcnow(),
        )
        self._attempts[task_id].append(record)

        return record

    def is_retry_with_same_issues(self, task_id: str, result: ValidationResult) -> bool:
        """Check if this is a retry with the same issues as the last attempt.

        Compares issue fingerprints (MD5 hash of severity + criterion + issue)
        to detect if the agent is retrying without fixing the problems.

        Parameters
        ----------
        task_id : str
            Task being validated
        result : ValidationResult
            Current validation result

        Returns
        -------
        bool
            True if this is a retry with same issues, False otherwise

        Notes
        -----
        Returns False if:
        - This is the first attempt
        - Last attempt passed validation
        - Issues have changed (agent tried to fix something)
        """
        if task_id not in self._attempts or not self._attempts[task_id]:
            # First attempt - not a retry
            return False

        last_attempt = self._attempts[task_id][-1]

        # If last attempt passed, this is a new failure (not same issues)
        if last_attempt.result.passed:
            return False

        # Compare issue fingerprints
        last_fingerprints = last_attempt.get_issue_fingerprints()
        current_fingerprints = result.get_issue_fingerprints()

        # Same issues if fingerprints match exactly
        return last_fingerprints == current_fingerprints

    def get_attempts(self, task_id: str) -> list[ValidationAttemptRecord]:
        """Get all validation attempts for a task.

        Parameters
        ----------
        task_id : str
            Task to get attempts for

        Returns
        -------
        list[ValidationAttemptRecord]
            All recorded attempts (oldest to newest)
        """
        return self._attempts.get(task_id, []).copy()

    def get_attempt_count(self, task_id: str) -> int:
        """Get number of validation attempts for a task.

        Parameters
        ----------
        task_id : str
            Task to get count for

        Returns
        -------
        int
            Number of attempts recorded
        """
        return len(self._attempts.get(task_id, []))

    def clear_task(self, task_id: str) -> None:
        """Clear all attempts for a task.

        Useful when task passes validation or is abandoned.

        Parameters
        ----------
        task_id : str
            Task to clear attempts for
        """
        if task_id in self._attempts:
            del self._attempts[task_id]

    def _cleanup_stale_attempts(self, task_id: Optional[str] = None) -> None:
        """Remove attempts older than cleanup threshold.

        Parameters
        ----------
        task_id : Optional[str], optional
            If specified, only clean this task. Otherwise clean all tasks.
        """
        now = datetime.utcnow()
        cutoff = now - self._cleanup_threshold

        if task_id:
            # Clean specific task
            if task_id in self._attempts:
                self._attempts[task_id] = [
                    attempt
                    for attempt in self._attempts[task_id]
                    if attempt.timestamp >= cutoff
                ]
                # Remove task entry if no attempts remain
                if not self._attempts[task_id]:
                    del self._attempts[task_id]
        else:
            # Clean all tasks
            tasks_to_remove = []
            for tid, attempts in self._attempts.items():
                self._attempts[tid] = [
                    attempt for attempt in attempts if attempt.timestamp >= cutoff
                ]
                if not self._attempts[tid]:
                    tasks_to_remove.append(tid)

            for tid in tasks_to_remove:
                del self._attempts[tid]
