"""Unit tests for the per-task event helpers (Stage 3 of #9).

Two events:

- ``fire_task_completed`` — fires when a task moves to DONE.
- ``fire_task_blocked``  — fires when ``report_blocker`` is called.

Plus the supporting helpers ``classify_blocker_type`` (keyword
bucketing of free-text blocker descriptions; the description text
never leaves the machine) and ``extract_task_phase`` (label →
phase bucket).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Per-test ``~`` + clear telemetry env vars."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("MARCUS_TELEMETRY", raising=False)
    monkeypatch.delenv("MARCUS_POSTHOG_API_KEY", raising=False)
    monkeypatch.delenv("MARCUS_RUNNER", raising=False)
    return tmp_path


@pytest.fixture
def mock_client(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Replace get_telemetry_client with a MagicMock."""
    client = MagicMock()
    monkeypatch.setattr("src.telemetry.events.get_telemetry_client", lambda: client)
    return client


class TestExtractTaskPhase:
    """``extract_task_phase`` maps labels to a fixed bucket."""

    @pytest.mark.parametrize(
        "labels,expected",
        [
            (["backend"], "backend"),
            (["BackEnd"], "backend"),  # case-insensitive
            (["frontend", "react"], "frontend"),  # first match wins
            (["design", "architecture"], "design"),
            (["testing"], "testing"),
            (["deployment"], "deployment"),
            (["documentation"], "documentation"),
            (["integration"], "integration"),
            (["foundation"], "foundation"),
            ([], "unknown"),
            (["random_label"], "unknown"),
            (None, "unknown"),
        ],
    )
    def test_label_to_phase(self, labels: List[str], expected: str) -> None:
        """Each label form maps to the documented phase bucket."""
        from src.telemetry.events import extract_task_phase

        assert extract_task_phase(labels) == expected


class TestClassifyBlockerType:
    """``classify_blocker_type`` is the local keyword classifier.

    The blocker description text NEVER leaves the machine — only
    the bucket label ships.  Tests pin the mapping and the privacy
    contract (no text in the return value).
    """

    @pytest.mark.parametrize(
        "description,expected",
        [
            ("Task is blocked by the auth service migration", "dependency_not_ready"),
            ("Waiting for the new contract to land", "dependency_not_ready"),
            ("Depends on issue #42 closing first", "dependency_not_ready"),
            ("Request timed out after 30s", "timeout"),
            ("HTTP timeout while calling the API", "timeout"),
            ("Missing ANTHROPIC_API_KEY in env", "missing_credential"),
            ("No credentials configured for Linear", "missing_credential"),
            ("Permission denied when running the script", "tool_error"),
            ("Build command failed with exit code 1", "tool_error"),
            ("Requirements are unclear and ambiguous", "ambiguous_requirement"),
            ("I don't know which library to use", "ambiguous_requirement"),
            ("Async race condition in scheduler", "async_failure"),
            ("Just stuck with no obvious reason", "unknown"),
            ("", "unknown"),
        ],
    )
    def test_description_to_type(self, description: str, expected: str) -> None:
        from src.telemetry.events import classify_blocker_type

        assert classify_blocker_type(description) == expected

    def test_returned_value_is_only_a_bucket_label(self) -> None:
        """Privacy regression net: the returned value contains only the
        bucket label, never any substring of the original description.

        Falsification recipe: return ``description`` from the
        classifier and confirm this test fails because the secret
        string appears in the output.
        """
        from src.telemetry.events import classify_blocker_type

        secret = "Customer XYZ's launch-codes API failed authentication"
        result = classify_blocker_type(secret)

        assert "Customer" not in result
        assert "XYZ" not in result
        assert "launch-codes" not in result
        assert result in {
            "dependency_not_ready",
            "timeout",
            "missing_credential",
            "tool_error",
            "ambiguous_requirement",
            "async_failure",
            "unknown",
        }


class TestFireTaskCompleted:
    """``fire_task_completed`` emits the ``task_completed`` event."""

    def test_calls_capture_with_event_name(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        from src.telemetry.events import fire_task_completed

        task = MagicMock()
        task.labels = ["backend"]

        fire_task_completed(task)

        mock_client.capture.assert_called_once()
        args, _ = mock_client.capture.call_args
        assert args[0] == "task_completed"

    def test_task_phase_from_labels(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        from src.telemetry.events import fire_task_completed

        task = MagicMock()
        task.labels = ["frontend", "react"]

        fire_task_completed(task)
        props = mock_client.capture.call_args[0][1]
        assert props["task_phase"] == "frontend"

    def test_payload_has_disclosure_keys(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        """Every key promised in docs/telemetry.md § task_completed."""
        from src.telemetry.events import fire_task_completed

        task = MagicMock()
        task.labels = []

        fire_task_completed(task)
        props = mock_client.capture.call_args[0][1]

        required = {"task_phase", "had_blocker", "duration_minutes"}
        missing = required - set(props.keys())
        assert not missing, f"task_completed missing keys: {missing}"

    def test_no_task_description_in_payload(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        """The task's description / name MUST NOT leave the machine."""
        from src.telemetry.events import fire_task_completed

        task = MagicMock()
        task.labels = ["backend"]
        task.name = "Implement the customer-XYZ wire-transfer endpoint"
        task.description = "Process inbound wire transfers from Bank Foo"

        fire_task_completed(task)
        props = mock_client.capture.call_args[0][1]
        flat = " ".join(str(v) for v in props.values()).lower()

        assert "customer" not in flat
        assert "xyz" not in flat
        assert "wire-transfer" not in flat
        assert "bank foo" not in flat

    def test_swallows_exceptions(
        self, isolated_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A broken task object cannot crash the report_task_progress path."""
        from src.telemetry.events import fire_task_completed

        broken = MagicMock()
        broken.capture.side_effect = RuntimeError("simulated")
        monkeypatch.setattr("src.telemetry.events.get_telemetry_client", lambda: broken)

        # Pass None as the task — must not raise.
        fire_task_completed(None)


class TestFireTaskBlocked:
    """``fire_task_blocked`` emits the ``task_blocked`` event."""

    def test_calls_capture_with_event_name(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        from src.telemetry.events import fire_task_blocked

        fire_task_blocked(
            severity="high",
            blocker_description="depends on issue #42",
        )

        mock_client.capture.assert_called_once()
        args, _ = mock_client.capture.call_args
        assert args[0] == "task_blocked"

    def test_payload_carries_type_and_severity(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        from src.telemetry.events import fire_task_blocked

        fire_task_blocked(
            severity="medium", blocker_description="depends on the new auth API"
        )
        props = mock_client.capture.call_args[0][1]

        assert props["blocker_type"] == "dependency_not_ready"
        assert props["severity"] == "medium"

    def test_blocker_description_is_never_in_payload(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        """The free-text description MUST NOT leave the machine.

        Privacy regression net: the disclosure document explicitly
        says "The blocker message is never shipped."
        """
        from src.telemetry.events import fire_task_blocked

        secret = "Customer XYZ's wire-transfer API returned 401 again"
        fire_task_blocked(severity="high", blocker_description=secret)

        props = mock_client.capture.call_args[0][1]
        flat = " ".join(str(v) for v in props.values()).lower()
        assert "customer" not in flat
        assert "xyz" not in flat
        assert "wire-transfer" not in flat

    def test_swallows_exceptions(
        self, isolated_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from src.telemetry.events import fire_task_blocked

        broken = MagicMock()
        broken.capture.side_effect = RuntimeError("simulated")
        monkeypatch.setattr("src.telemetry.events.get_telemetry_client", lambda: broken)

        fire_task_blocked(severity="low", blocker_description="x")  # Must not raise.
