"""Unit tests for the validation escalation atomicity path.

Regression coverage for the post-Codex review of PR #337 (validator
hallucination fixes). When the MAX_VALIDATION_RETRIES ceiling is
hit, the task falls through to the normal completion pipeline
instead of short-circuiting out of the failure handler. If the
completion pipeline raises partway through, the outer except block
must still surface the escalation context — otherwise the agent
sees a generic error and has no idea the task had been escalated,
breaking the observability guarantee the ceiling was meant to
provide.
"""

import pytest

from src.marcus_mcp.tools.task import (
    MAX_VALIDATION_RETRIES,
    _build_escalation_error_response,
)


@pytest.mark.unit
class TestEscalationErrorResponse:
    """
    ``_build_escalation_error_response`` merges the escalation
    payload into the error response returned by the outer except
    handler in ``report_task_progress``.
    """

    def test_preserves_escalation_flag(self) -> None:
        """The merged response must carry validation_escalated=True."""
        payload = {
            "status": "validation_escalated",
            "escalated": True,
            "attempt_count": MAX_VALIDATION_RETRIES + 1,
            "issues": [{"issue": "x"}],
            "message": "original escalation message",
        }
        exc = RuntimeError("kanban update failed")

        response = _build_escalation_error_response(exc, payload)

        assert response["success"] is False
        assert response["validation_escalated"] is True
        assert response["escalation_pipeline_error"] is True

    def test_surfaces_pipeline_error_string(self) -> None:
        """The exception's string form must be in the error field."""
        exc = RuntimeError("kanban.update_task timed out")
        response = _build_escalation_error_response(exc, {"status": "x"})

        assert "kanban.update_task timed out" in response["error"]

    def test_merges_escalation_payload_fields(self) -> None:
        """
        Every field of the original escalation payload must appear
        in the merged response — downstream observers rely on the
        same fields whether the pipeline succeeded or failed.
        """
        payload = {
            "status": "validation_escalated",
            "escalated": True,
            "attempt_count": 4,
            "issues": [
                {"issue": "empty file", "severity": "critical"},
                {"issue": "missing call", "severity": "major"},
            ],
        }
        exc = ValueError("subtask rollup failed")

        response = _build_escalation_error_response(exc, payload)

        assert response["status"] == "validation_escalated"
        assert response["escalated"] is True
        assert response["attempt_count"] == 4
        assert len(response["issues"]) == 2

    def test_message_mentions_escalation_and_pipeline_failure(self) -> None:
        """
        The human-readable message must tell the caller BOTH that
        validation was escalated AND that the pipeline failed, so
        a coordinator can tell this state apart from a plain retry
        ceiling hit.
        """
        exc = RuntimeError("lease cleanup exploded")
        response = _build_escalation_error_response(
            exc, {"status": "validation_escalated"}
        )

        message = response["message"]
        assert "escalated" in message.lower()
        assert "pipeline failed" in message.lower()
        assert "lease cleanup exploded" in message

    def test_next_completion_retry_semantics_documented(self) -> None:
        """
        The message must guide the caller to retry completion so
        the pipeline re-runs. This is the documented recovery path
        for partial kanban state.
        """
        response = _build_escalation_error_response(
            RuntimeError("pipeline"), {"status": "validation_escalated"}
        )
        assert "retry completion" in response["message"].lower()

    def test_does_not_require_message_in_payload(self) -> None:
        """
        The helper must work even if the escalation payload omits
        its own ``message`` key — the merged response's ``message``
        is set by the helper itself, not copied from the payload.
        Protects against the helper accidentally passing through a
        stale pre-pipeline message.
        """
        response = _build_escalation_error_response(
            RuntimeError("x"), {"status": "validation_escalated"}
        )
        assert response["message"] is not None
        assert "pipeline failed" in response["message"].lower()
