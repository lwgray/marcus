"""Unit tests for the resilience event helpers (Stage 4 of #9).

Four events:

- ``fire_lease_expired``       — task lease expired without completion
- ``fire_validator_retry``     — planner validation retry
- ``fire_structured_llm_retry``— planner truncation retry (PR #542)
- ``fire_error_occurred``      — Marcus error monitoring

All carry **type only**, never message text or stack traces.  This
matches the privacy contract in ``docs/telemetry.md``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("MARCUS_TELEMETRY", raising=False)
    monkeypatch.delenv("MARCUS_POSTHOG_API_KEY", raising=False)
    return tmp_path


@pytest.fixture
def mock_client(monkeypatch: pytest.MonkeyPatch) -> Any:
    client = MagicMock()
    monkeypatch.setattr(
        "src.telemetry.events.get_telemetry_client", lambda: client
    )
    return client


class TestFireLeaseExpired:
    def test_event_name_and_keys(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        from src.telemetry.events import fire_lease_expired

        fire_lease_expired(
            task_held_minutes=45,
            progress_pct_at_expiry=60,
            recovered=True,
        )
        args, _ = mock_client.capture.call_args
        assert args[0] == "lease_expired"
        assert args[1] == {
            "task_held_minutes": 45,
            "progress_pct_at_expiry": 60,
            "recovered": True,
        }

    def test_swallows_exceptions(
        self, isolated_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from src.telemetry.events import fire_lease_expired

        broken = MagicMock()
        broken.capture.side_effect = RuntimeError("simulated")
        monkeypatch.setattr(
            "src.telemetry.events.get_telemetry_client", lambda: broken
        )
        fire_lease_expired(
            task_held_minutes=1, progress_pct_at_expiry=0, recovered=False
        )  # Must not raise.


class TestFireValidatorRetry:
    def test_event_name_and_keys(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        from src.telemetry.events import fire_validator_retry

        fire_validator_retry(
            retry_count=2,
            final_result="pass",
            validation_type="task_completeness",
        )
        args, _ = mock_client.capture.call_args
        assert args[0] == "validator_retry"
        assert args[1] == {
            "retry_count": 2,
            "final_result": "pass",
            "validation_type": "task_completeness",
        }

    def test_swallows_exceptions(
        self, isolated_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from src.telemetry.events import fire_validator_retry

        broken = MagicMock()
        broken.capture.side_effect = RuntimeError("simulated")
        monkeypatch.setattr(
            "src.telemetry.events.get_telemetry_client", lambda: broken
        )
        fire_validator_retry(
            retry_count=1, final_result="fail", validation_type="x"
        )  # Must not raise.


class TestFireStructuredLLMRetry:
    def test_event_name_and_keys(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        from src.telemetry.events import fire_structured_llm_retry

        fire_structured_llm_retry(
            operation="parse_prd",
            retry_count=1,
            reason="truncation",
            final="ok",
        )
        args, _ = mock_client.capture.call_args
        assert args[0] == "structured_llm_retry"
        assert args[1] == {
            "operation": "parse_prd",
            "retry_count": 1,
            "reason": "truncation",
            "final": "ok",
        }

    def test_swallows_exceptions(
        self, isolated_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from src.telemetry.events import fire_structured_llm_retry

        broken = MagicMock()
        broken.capture.side_effect = RuntimeError("simulated")
        monkeypatch.setattr(
            "src.telemetry.events.get_telemetry_client", lambda: broken
        )
        fire_structured_llm_retry(
            operation="x", retry_count=0, reason="x", final="ok"
        )  # Must not raise.


class TestFireErrorOccurred:
    def test_event_name_and_keys(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        from src.telemetry.events import fire_error_occurred

        fire_error_occurred(error_type="KanbanIntegrationError")
        args, _ = mock_client.capture.call_args
        assert args[0] == "error_occurred"
        assert args[1] == {"error_type": "KanbanIntegrationError"}

    def test_only_type_no_message_no_stack(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        """Even if a caller tries to pass a message/stack, the helper
        accepts only ``error_type`` — the function signature is the
        regression net.  The disclosure says: "The error type is
        shipped. The error message and stack trace are never shipped."
        """
        import inspect

        from src.telemetry.events import fire_error_occurred

        sig = inspect.signature(fire_error_occurred)
        # Single positional/kw param — error_type.
        assert list(sig.parameters.keys()) == ["error_type"]

    def test_swallows_exceptions(
        self, isolated_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from src.telemetry.events import fire_error_occurred

        broken = MagicMock()
        broken.capture.side_effect = RuntimeError("simulated")
        monkeypatch.setattr(
            "src.telemetry.events.get_telemetry_client", lambda: broken
        )
        fire_error_occurred(error_type="x")  # Must not raise.
