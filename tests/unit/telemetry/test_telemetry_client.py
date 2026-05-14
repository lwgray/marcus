"""Unit tests for :class:`src.telemetry.client.TelemetryClient`.

The ``TelemetryClient`` is the in-process surface that emits events.
Tests pin the load-bearing invariants:

- Anonymous UUID is generated exactly once and persisted at
  ``~/.marcus/telemetry_id``.  Subsequent processes reuse the same
  UUID — that is how cohort analysis works without identifying users.
- Events are sent fire-and-forget: network failures, timeouts, and
  unreachable hosts never raise into Marcus code paths.
- Every event sent is mirrored to ``~/.marcus/telemetry_outbound.jsonl``
  so users can audit what shipped.
- The outbound log rotates at ~100 MB so it cannot grow unbounded.
- When ``is_telemetry_enabled()`` returns False, ``capture`` is a
  no-op — no network call, no UUID generated, no outbound log
  write.
- The client never prints to stdout (MCP stdio invariant).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ``~`` to ``tmp_path`` and force telemetry enabled."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("MARCUS_TELEMETRY", raising=False)

    resolved_home = Path.home()
    assert resolved_home == tmp_path, (
        f"isolated_home fixture failed: Path.home() resolved to "
        f"{resolved_home!r}, expected {tmp_path!r}"
    )
    return tmp_path


@pytest.fixture
def captured_posts(monkeypatch: pytest.MonkeyPatch) -> List[Dict[str, Any]]:
    """Capture every httpx.post call without making a real request.

    The fixture returns a list that gets one dict appended per call,
    with ``url`` and ``json`` keys.  Tests inspect the list to
    assert what would have shipped.
    """
    calls: List[Dict[str, Any]] = []

    def _fake_post(url: str, *, json: Any = None, timeout: Any = None) -> Any:
        calls.append({"url": url, "json": json, "timeout": timeout})

        class _Resp:
            status_code = 200

            def raise_for_status(self) -> None:
                return None

        return _Resp()

    monkeypatch.setattr("httpx.post", _fake_post)
    return calls


class TestAnonymousUUID:
    """Anonymous UUID lifecycle — generate once, reuse forever."""

    def test_uuid_generated_on_first_capture(
        self, isolated_home: Path, captured_posts: List[Dict[str, Any]]
    ) -> None:
        """First capture creates ~/.marcus/telemetry_id with a UUID."""
        from src.telemetry.cli import get_telemetry_id_path
        from src.telemetry.client import TelemetryClient

        uuid_path = get_telemetry_id_path()
        assert not uuid_path.exists()

        client = TelemetryClient(api_key="dummy")
        client.capture("test_event", {})

        assert uuid_path.exists()
        # Basic UUID shape — 36 chars with hyphens.
        uuid_value = uuid_path.read_text().strip()
        assert len(uuid_value) == 36
        assert uuid_value.count("-") == 4

    def test_uuid_reused_across_clients(
        self, isolated_home: Path, captured_posts: List[Dict[str, Any]]
    ) -> None:
        """Second TelemetryClient instance reads the existing UUID."""
        from src.telemetry.cli import get_telemetry_id_path
        from src.telemetry.client import TelemetryClient

        client_a = TelemetryClient(api_key="dummy")
        client_a.capture("e1", {})
        uuid_a = get_telemetry_id_path().read_text().strip()

        client_b = TelemetryClient(api_key="dummy")
        client_b.capture("e2", {})
        uuid_b = get_telemetry_id_path().read_text().strip()

        assert uuid_a == uuid_b

    def test_uuid_in_event_payload(
        self, isolated_home: Path, captured_posts: List[Dict[str, Any]]
    ) -> None:
        """Sent payload carries the anonymous UUID as ``distinct_id``.

        PostHog uses ``distinct_id`` to group events by user.  We
        ship the anonymous UUID under that key so PostHog cohort
        analysis works without us identifying anyone.
        """
        from src.telemetry.cli import get_telemetry_id_path
        from src.telemetry.client import TelemetryClient

        client = TelemetryClient(api_key="dummy")
        client.capture("test_event", {"foo": "bar"})

        assert len(captured_posts) == 1
        payload = captured_posts[0]["json"]
        uuid_on_disk = get_telemetry_id_path().read_text().strip()
        assert payload["distinct_id"] == uuid_on_disk


class TestCaptureDisabledByConfig:
    """When telemetry is disabled, capture is a no-op."""

    def test_disabled_skips_post(
        self, isolated_home: Path, captured_posts: List[Dict[str, Any]]
    ) -> None:
        """Disable + capture → no httpx call."""
        from src.telemetry.client import TelemetryClient
        from src.telemetry.config import set_telemetry_enabled

        set_telemetry_enabled(False)

        client = TelemetryClient(api_key="dummy")
        client.capture("test_event", {})

        assert captured_posts == []

    def test_disabled_does_not_create_uuid(
        self, isolated_home: Path, captured_posts: List[Dict[str, Any]]
    ) -> None:
        """Disabled capture does not generate the UUID file.

        Critical: a user who disabled telemetry should NOT see a
        ``telemetry_id`` file appear on disk just because some code
        path called ``capture()``.  The UUID is created lazily, only
        when an event is actually about to ship.
        """
        from src.telemetry.cli import get_telemetry_id_path
        from src.telemetry.client import TelemetryClient
        from src.telemetry.config import set_telemetry_enabled

        set_telemetry_enabled(False)

        client = TelemetryClient(api_key="dummy")
        client.capture("test_event", {})

        assert not get_telemetry_id_path().exists()

    def test_env_var_off_skips_post(
        self,
        isolated_home: Path,
        captured_posts: List[Dict[str, Any]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """MARCUS_TELEMETRY=off → capture is a no-op."""
        from src.telemetry.client import TelemetryClient

        monkeypatch.setenv("MARCUS_TELEMETRY", "off")

        client = TelemetryClient(api_key="dummy")
        client.capture("test_event", {})

        assert captured_posts == []


class TestOutboundLog:
    """Every captured event is mirrored locally for user audit."""

    def test_capture_writes_to_outbound_log(
        self, isolated_home: Path, captured_posts: List[Dict[str, Any]]
    ) -> None:
        """One capture → one JSONL line in ~/.marcus/telemetry_outbound.jsonl."""
        from src.telemetry.cli import get_outbound_log_path
        from src.telemetry.client import TelemetryClient

        client = TelemetryClient(api_key="dummy")
        client.capture("test_event", {"hello": "world"})

        log_path = get_outbound_log_path()
        assert log_path.exists()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["event"] == "test_event"
        assert entry["properties"]["hello"] == "world"

    def test_outbound_log_appended_not_overwritten(
        self, isolated_home: Path, captured_posts: List[Dict[str, Any]]
    ) -> None:
        """Multiple captures append; older entries are preserved."""
        from src.telemetry.cli import get_outbound_log_path
        from src.telemetry.client import TelemetryClient

        client = TelemetryClient(api_key="dummy")
        client.capture("e1", {})
        client.capture("e2", {})
        client.capture("e3", {})

        lines = get_outbound_log_path().read_text().strip().splitlines()
        assert len(lines) == 3
        events = [json.loads(line)["event"] for line in lines]
        assert events == ["e1", "e2", "e3"]

    def test_outbound_log_rotates_at_threshold(
        self, isolated_home: Path, captured_posts: List[Dict[str, Any]]
    ) -> None:
        """When the log exceeds the rotation cap, it is rotated.

        Kaia review on PR #545 — outbound log cannot grow unbounded.
        Rotation cap is 100 MB in production; for testability we
        let the client expose a ``_max_log_bytes`` knob so we can
        force rotation in a unit test.
        """
        from src.telemetry.cli import get_outbound_log_path
        from src.telemetry.client import TelemetryClient

        client = TelemetryClient(api_key="dummy", _max_log_bytes=200)

        # Each capture writes ~80 bytes of JSON; three captures
        # will cross the 200-byte cap and trigger rotation.
        client.capture("e1", {"data": "x" * 30})
        client.capture("e2", {"data": "x" * 30})
        client.capture("e3", {"data": "x" * 30})

        log = get_outbound_log_path()
        rotated = log.with_suffix(log.suffix + ".1")

        # Either the live log was rotated to .1 and a fresh one
        # started, OR the live log was truncated and the old
        # contents moved to .1.  In both cases, .1 must exist.
        assert rotated.exists(), (
            f"Outbound log did not rotate; live log is "
            f"{log.stat().st_size} bytes (cap 200)."
        )


class TestNetworkFailures:
    """Network errors never propagate to the caller."""

    def test_http_error_swallowed(
        self,
        isolated_home: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """httpx connection error in capture → no exception raised."""
        import httpx

        from src.telemetry.client import TelemetryClient

        def _raising_post(*args: Any, **kwargs: Any) -> Any:
            raise httpx.ConnectError("simulated network failure")

        monkeypatch.setattr("httpx.post", _raising_post)

        client = TelemetryClient(api_key="dummy")
        # Must not raise.
        client.capture("test_event", {})

        # And must not pollute stdout (MCP stdio invariant).
        assert capsys.readouterr().out == ""

    def test_timeout_swallowed(
        self,
        isolated_home: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """httpx timeout → no exception."""
        import httpx

        from src.telemetry.client import TelemetryClient

        def _timeout_post(*args: Any, **kwargs: Any) -> Any:
            raise httpx.TimeoutException("simulated timeout")

        monkeypatch.setattr("httpx.post", _timeout_post)

        client = TelemetryClient(api_key="dummy")
        client.capture("test_event", {})

    def test_http_failure_still_logs_outbound(
        self,
        isolated_home: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Even when the network fails, the outbound log captures the attempt.

        This is the user-audit guarantee: the disclosure promises
        users can inspect what shipped at
        ``~/.marcus/telemetry_outbound.jsonl``.  An event that
        failed to send is still an "attempted to send" that the
        user has a right to see.
        """
        import httpx

        from src.telemetry.cli import get_outbound_log_path
        from src.telemetry.client import TelemetryClient

        def _raising_post(*args: Any, **kwargs: Any) -> Any:
            raise httpx.ConnectError("simulated")

        monkeypatch.setattr("httpx.post", _raising_post)

        client = TelemetryClient(api_key="dummy")
        client.capture("test_event", {"foo": "bar"})

        assert get_outbound_log_path().exists()
        lines = get_outbound_log_path().read_text().strip().splitlines()
        assert len(lines) == 1


class TestStdioInvariant:
    """The client never writes to stdout — same invariant as the notice."""

    def test_capture_does_not_touch_stdout(
        self,
        isolated_home: Path,
        captured_posts: List[Dict[str, Any]],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Full happy-path capture → stdout stays empty.

        MCP stdio mode reserves stdout for JSON-RPC.  Any non-protocol
        bytes corrupt the channel.  This test is the privacy +
        protocol regression net for the client surface.
        """
        from src.telemetry.client import TelemetryClient

        client = TelemetryClient(api_key="dummy")
        client.capture("test_event", {"k": "v"})

        captured = capsys.readouterr()
        assert captured.out == "", (
            f"stdout must be empty (MCP stdio invariant); got: " f"{captured.out!r}"
        )


class TestPostHogEndpoint:
    """Posts go to the configured PostHog URL with the API key."""

    def test_posts_to_us_posthog_capture_endpoint(
        self, isolated_home: Path, captured_posts: List[Dict[str, Any]]
    ) -> None:
        """Default endpoint is https://us.i.posthog.com/capture/."""
        from src.telemetry.client import TelemetryClient

        client = TelemetryClient(api_key="dummy")
        client.capture("e1", {})

        assert len(captured_posts) == 1
        assert captured_posts[0]["url"] == "https://us.i.posthog.com/capture/"

    def test_api_key_in_payload(
        self, isolated_home: Path, captured_posts: List[Dict[str, Any]]
    ) -> None:
        """Payload includes ``api_key`` so PostHog accepts the event."""
        from src.telemetry.client import TelemetryClient

        client = TelemetryClient(api_key="phc_test_key_12345")
        client.capture("e1", {})

        payload = captured_posts[0]["json"]
        assert payload["api_key"] == "phc_test_key_12345"

    def test_event_name_in_payload(
        self, isolated_home: Path, captured_posts: List[Dict[str, Any]]
    ) -> None:
        """Payload includes the event name verbatim."""
        from src.telemetry.client import TelemetryClient

        client = TelemetryClient(api_key="dummy")
        client.capture("session_started", {"version": "0.3.7"})

        payload = captured_posts[0]["json"]
        assert payload["event"] == "session_started"
        assert payload["properties"]["version"] == "0.3.7"

    def test_timeout_is_short(
        self, isolated_home: Path, captured_posts: List[Dict[str, Any]]
    ) -> None:
        """httpx post uses a short timeout — telemetry must not slow Marcus.

        A long timeout means a slow PostHog blocks Marcus.  We
        cap at a few seconds maximum.
        """
        from src.telemetry.client import TelemetryClient

        client = TelemetryClient(api_key="dummy")
        client.capture("e1", {})

        timeout = captured_posts[0]["timeout"]
        # Accept any sane representation (seconds float, httpx.Timeout).
        # The invariant we pin: not None, not >10s.
        assert timeout is not None
        if hasattr(timeout, "connect"):
            # httpx.Timeout object
            assert timeout.connect <= 10
        else:
            # plain seconds float/int
            assert timeout <= 10
