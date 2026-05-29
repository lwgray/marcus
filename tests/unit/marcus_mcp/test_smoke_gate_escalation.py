"""
Unit tests for the smoke-gate missing-verifications retry ceiling (issue #676).

When an integration task carries in-scope outcomes but the agent reports
completion without declaring ``verifications``, the product smoke gate
rejects with ``error="verifications_required_but_missing"``. Before this
fix that rejection had NO ceiling: the agent could re-send the same
incomplete report forever, the gate rejected each time, and the run
eventually froze into gridlock (snake-pr667-5: 6 identical rejections).

The fix converts the rejection into a TERMINAL escalation after a small
number of identical attempts, so the agent stops retrying and the failure
is surfaced (with the same remediation payload) instead of looping.
"""

import pytest

from src.marcus_mcp.tools.task import (
    MAX_SMOKE_MISSING_VERIFICATION_ATTEMPTS,
    _clear_smoke_attempts,
    _escalate_missing_verifications_response,
    _record_missing_verification_attempt,
)

pytestmark = pytest.mark.unit


def _missing_verifications_rejection() -> dict:
    """A representative missing-verifications rejection from the smoke gate."""
    return {
        "success": False,
        "status": "smoke_verification_failed",
        "error": "verifications_required_but_missing",
        "agent_id": "agent-1",
        "task_id": "task-int",
        "blocker": "## Verifications required ...",
        "missing_outcome_ids": ["outcome_play", "outcome_restart"],
        "required_outcome_ids": ["outcome_play", "outcome_restart"],
    }


class TestMissingVerificationAttemptCounter:
    """The per-task attempt counter increments and clears."""

    def test_record_increments_per_task(self) -> None:
        _clear_smoke_attempts("t-count")
        assert _record_missing_verification_attempt("t-count") == 1
        assert _record_missing_verification_attempt("t-count") == 2
        assert _record_missing_verification_attempt("t-count") == 3

    def test_counters_are_independent_per_task(self) -> None:
        _clear_smoke_attempts("t-a")
        _clear_smoke_attempts("t-b")
        _record_missing_verification_attempt("t-a")
        _record_missing_verification_attempt("t-a")
        assert _record_missing_verification_attempt("t-b") == 1

    def test_clear_resets_count(self) -> None:
        _record_missing_verification_attempt("t-clear")
        _clear_smoke_attempts("t-clear")
        assert _record_missing_verification_attempt("t-clear") == 1


class TestEscalationResponse:
    """The terminal escalation preserves remediation but stops retries."""

    def test_marks_terminal_and_escalated(self) -> None:
        out = _escalate_missing_verifications_response(
            _missing_verifications_rejection()
        )
        assert out["terminal"] is True
        assert out["escalated"] is True
        assert out["success"] is False

    def test_uses_a_distinct_error_so_it_is_not_a_retry_signal(self) -> None:
        out = _escalate_missing_verifications_response(
            _missing_verifications_rejection()
        )
        # Must NOT keep the retryable error code, or the agent treats it as
        # "fix and retry" rather than "stop, escalated".
        assert out["error"] != "verifications_required_but_missing"
        assert out["error"] == "verifications_required_escalated"

    def test_preserves_remediation_payload(self) -> None:
        out = _escalate_missing_verifications_response(
            _missing_verifications_rejection()
        )
        assert out["missing_outcome_ids"] == ["outcome_play", "outcome_restart"]
        assert "blocker" in out
        # original is not mutated
        src = _missing_verifications_rejection()
        _escalate_missing_verifications_response(src)
        assert src["error"] == "verifications_required_but_missing"


class TestCeilingDecision:
    """Attempts at/under the ceiling stay retryable; beyond it escalates."""

    def test_first_attempts_under_ceiling(self) -> None:
        _clear_smoke_attempts("t-ceil")
        for i in range(1, MAX_SMOKE_MISSING_VERIFICATION_ATTEMPTS + 1):
            assert (
                _record_missing_verification_attempt("t-ceil")
                <= MAX_SMOKE_MISSING_VERIFICATION_ATTEMPTS
            )

    def test_attempt_beyond_ceiling_triggers_escalation(self) -> None:
        _clear_smoke_attempts("t-ceil2")
        last = 0
        for _ in range(MAX_SMOKE_MISSING_VERIFICATION_ATTEMPTS + 1):
            last = _record_missing_verification_attempt("t-ceil2")
        assert last > MAX_SMOKE_MISSING_VERIFICATION_ATTEMPTS
