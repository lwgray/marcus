"""Unit tests for retry tracking functionality.

Tests the RetryTracker class which detects when agents retry validation
with the same issues (indicating they're stuck).
"""

from datetime import datetime, timedelta

import pytest

from src.ai.validation.retry_tracker import RetryTracker
from src.ai.validation.validation_models import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)


class TestRetryTracker:
    """Test suite for RetryTracker."""

    @pytest.fixture
    def tracker(self) -> RetryTracker:
        """Create a RetryTracker instance for testing."""
        return RetryTracker(cleanup_hours=24)

    @pytest.fixture
    def passing_result(self) -> ValidationResult:
        """Create a passing validation result."""
        return ValidationResult(passed=True, issues=[], ai_reasoning="All criteria met")

    @pytest.fixture
    def failing_result(self) -> ValidationResult:
        """Create a failing validation result with issues."""
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                issue="Missing phone validation",
                evidence="validation.js has no validatePhone function",
                remediation="Add validatePhone() function",
                criterion="Fields are properly validated",
            ),
            ValidationIssue(
                severity=ValidationSeverity.MAJOR,
                issue="Empty CSS file",
                evidence="styles.css is 0 bytes",
                remediation="Add styling rules",
                criterion="Professional CSS styling applied",
            ),
        ]
        return ValidationResult(
            passed=False, issues=issues, ai_reasoning="Missing features"
        )

    def test_record_first_attempt(
        self, tracker: RetryTracker, failing_result: ValidationResult
    ) -> None:
        """Test recording first validation attempt."""
        task_id = "task-123"

        record = tracker.record_attempt(task_id, failing_result)

        assert record.task_id == task_id
        assert record.attempt_number == 1
        assert record.result == failing_result
        assert isinstance(record.timestamp, datetime)

    def test_record_multiple_attempts(
        self, tracker: RetryTracker, failing_result: ValidationResult
    ) -> None:
        """Test recording multiple validation attempts increments count."""
        task_id = "task-456"

        record1 = tracker.record_attempt(task_id, failing_result)
        record2 = tracker.record_attempt(task_id, failing_result)
        record3 = tracker.record_attempt(task_id, failing_result)

        assert record1.attempt_number == 1
        assert record2.attempt_number == 2
        assert record3.attempt_number == 3
        assert tracker.get_attempt_count(task_id) == 3

    def test_is_retry_with_same_issues_first_attempt(
        self, tracker: RetryTracker, failing_result: ValidationResult
    ) -> None:
        """Test is_retry_with_same_issues returns False for first attempt."""
        task_id = "task-789"

        is_retry = tracker.is_retry_with_same_issues(task_id, failing_result)

        assert is_retry is False

    def test_is_retry_with_same_issues_detects_retry(
        self, tracker: RetryTracker, failing_result: ValidationResult
    ) -> None:
        """Test detecting retry with exact same issues."""
        task_id = "task-101"

        # First attempt
        tracker.record_attempt(task_id, failing_result)

        # Second attempt with SAME issues
        is_retry = tracker.is_retry_with_same_issues(task_id, failing_result)

        assert is_retry is True

    def test_is_retry_with_different_issues(
        self, tracker: RetryTracker, failing_result: ValidationResult
    ) -> None:
        """Test that different issues are not flagged as retry."""
        task_id = "task-202"

        # First attempt
        tracker.record_attempt(task_id, failing_result)

        # Second attempt with DIFFERENT issues
        different_result = ValidationResult(
            passed=False,
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    issue="Database connection failed",
                    evidence="Connection timeout",
                    remediation="Check database config",
                    criterion="Database integration works",
                )
            ],
            ai_reasoning="Different problem",
        )

        is_retry = tracker.is_retry_with_same_issues(task_id, different_result)

        assert is_retry is False

    def test_is_retry_after_passing(
        self,
        tracker: RetryTracker,
        passing_result: ValidationResult,
        failing_result: ValidationResult,
    ) -> None:
        """Test that failure after pass is not flagged as retry."""
        task_id = "task-303"

        # First attempt passes
        tracker.record_attempt(task_id, passing_result)

        # Second attempt fails (new issues introduced)
        is_retry = tracker.is_retry_with_same_issues(task_id, failing_result)

        assert is_retry is False

    def test_get_attempts(
        self, tracker: RetryTracker, failing_result: ValidationResult
    ) -> None:
        """Test retrieving all attempts for a task."""
        task_id = "task-404"

        tracker.record_attempt(task_id, failing_result)
        tracker.record_attempt(task_id, failing_result)
        tracker.record_attempt(task_id, failing_result)

        attempts = tracker.get_attempts(task_id)

        assert len(attempts) == 3
        assert all(a.task_id == task_id for a in attempts)
        # Verify ordering (oldest to newest)
        assert attempts[0].attempt_number == 1
        assert attempts[1].attempt_number == 2
        assert attempts[2].attempt_number == 3

    def test_get_attempts_empty(self, tracker: RetryTracker) -> None:
        """Test retrieving attempts for task with no history."""
        task_id = "task-nonexistent"

        attempts = tracker.get_attempts(task_id)

        assert attempts == []

    def test_get_attempt_count_zero(self, tracker: RetryTracker) -> None:
        """Test getting count for task with no attempts."""
        task_id = "task-none"

        count = tracker.get_attempt_count(task_id)

        assert count == 0

    def test_clear_task(
        self, tracker: RetryTracker, failing_result: ValidationResult
    ) -> None:
        """Test clearing all attempts for a task."""
        task_id = "task-505"

        tracker.record_attempt(task_id, failing_result)
        tracker.record_attempt(task_id, failing_result)

        tracker.clear_task(task_id)

        assert tracker.get_attempt_count(task_id) == 0
        assert tracker.get_attempts(task_id) == []

    def test_cleanup_stale_attempts(
        self, tracker: RetryTracker, failing_result: ValidationResult
    ) -> None:
        """Test automatic cleanup of stale attempts."""
        task_id = "task-606"

        # Create tracker with 1 hour cleanup threshold
        short_tracker = RetryTracker(cleanup_hours=1)

        # Record attempt
        short_tracker.record_attempt(task_id, failing_result)

        # Manually set timestamp to 2 hours ago (stale)
        short_tracker._attempts[task_id][0].timestamp = datetime.utcnow() - timedelta(
            hours=2
        )

        # Record new attempt (triggers cleanup)
        short_tracker.record_attempt(task_id, failing_result)

        # Only new attempt should remain
        attempts = short_tracker.get_attempts(task_id)
        assert len(attempts) == 1
        assert attempts[0].attempt_number == 1  # Renumbered after cleanup

    def test_multiple_tasks_isolation(
        self, tracker: RetryTracker, failing_result: ValidationResult
    ) -> None:
        """Test that attempts for different tasks are isolated."""
        task_1 = "task-701"
        task_2 = "task-702"

        tracker.record_attempt(task_1, failing_result)
        tracker.record_attempt(task_1, failing_result)
        tracker.record_attempt(task_2, failing_result)

        assert tracker.get_attempt_count(task_1) == 2
        assert tracker.get_attempt_count(task_2) == 1

        # Clearing one task doesn't affect the other
        tracker.clear_task(task_1)
        assert tracker.get_attempt_count(task_1) == 0
        assert tracker.get_attempt_count(task_2) == 1

    def test_issue_fingerprint_stability(self) -> None:
        """Test that issue fingerprints are stable across identical issues."""
        issue1 = ValidationIssue(
            severity=ValidationSeverity.CRITICAL,
            issue="Missing validation",
            evidence="No function found",
            remediation="Add function",
            criterion="Validation works",
        )

        # Same issue with different evidence/remediation
        issue2 = ValidationIssue(
            severity=ValidationSeverity.CRITICAL,
            issue="Missing validation",
            evidence="DIFFERENT evidence",
            remediation="DIFFERENT remediation",
            criterion="Validation works",
        )

        # Fingerprints should match (based on severity + issue + criterion only)
        assert issue1.get_fingerprint() == issue2.get_fingerprint()

    def test_issue_fingerprint_changes_with_content(self) -> None:
        """Test that issue fingerprints change when issue content changes."""
        issue1 = ValidationIssue(
            severity=ValidationSeverity.CRITICAL,
            issue="Missing validation",
            evidence="No function",
            remediation="Add function",
            criterion="Validation works",
        )

        issue2 = ValidationIssue(
            severity=ValidationSeverity.CRITICAL,
            issue="DIFFERENT issue",  # Changed
            evidence="No function",
            remediation="Add function",
            criterion="Validation works",
        )

        # Fingerprints should differ
        assert issue1.get_fingerprint() != issue2.get_fingerprint()
