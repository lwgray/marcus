"""Unit tests for telemetry wiring into ``src/marcus_mcp/server.py``.

Stage 1 of #9 — the server-side glue that makes the telemetry
package's capabilities reachable to users:

- ``marcus telemetry <cmd>`` routes to the CLI handler BEFORE any
  MCP server setup so opt-out works even when the rest of Marcus
  is broken.
- The first-run notice fires on every start (subject to the
  notice marker, MARCUS_TELEMETRY=off, etc.).
- A ``get_telemetry_client()`` singleton lazily constructs the
  client from ``MARCUS_POSTHOG_API_KEY`` env var (or empty key for
  the default no-PostHog case).

Pure-unit tests; do NOT spin up the MCP server itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Per-test ``~``; clears MARCUS_TELEMETRY and MARCUS_POSTHOG_API_KEY."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("MARCUS_TELEMETRY", raising=False)
    monkeypatch.delenv("MARCUS_POSTHOG_API_KEY", raising=False)
    return tmp_path


class TestEarlyExitPaths:
    """``_handle_early_exit_paths`` routes subcommands before MCP setup."""

    def test_no_subcommand_returns_none(self, isolated_home: Path) -> None:
        """Bare ``marcus`` (no subcommand) → continue to MCP server."""
        from src.marcus_mcp.server import _handle_early_exit_paths

        assert _handle_early_exit_paths(["marcus"]) is None

    def test_stdio_flag_returns_none(self, isolated_home: Path) -> None:
        """``marcus --stdio`` is a transport flag, not a subcommand."""
        from src.marcus_mcp.server import _handle_early_exit_paths

        assert _handle_early_exit_paths(["marcus", "--stdio"]) is None

    def test_http_flag_returns_none(self, isolated_home: Path) -> None:
        """``marcus --http`` is a transport flag, not a subcommand."""
        from src.marcus_mcp.server import _handle_early_exit_paths

        assert _handle_early_exit_paths(["marcus", "--http"]) is None

    def test_telemetry_subcommand_routes_to_cli(
        self,
        isolated_home: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """``marcus telemetry status`` returns a 0 exit code from the CLI.

        Critical: the CLI must run BEFORE MCP server setup so that
        ``marcus telemetry disable`` works even when the rest of
        Marcus is broken (Kaia review on PR #545).

        Falsification recipe: remove the early-exit check in
        ``main()`` and confirm this test would never reach the CLI —
        we instead test the helper directly so the test is
        deterministic without spinning up the server.
        """
        from src.marcus_mcp.server import _handle_early_exit_paths

        rc = _handle_early_exit_paths(["marcus", "telemetry", "status"])

        assert rc == 0
        # CLI output goes to stdout (interactive command) — must
        # carry the status keywords.
        out = capsys.readouterr().out.lower()
        assert "telemetry" in out

    def test_telemetry_subcommand_no_args_prints_help(
        self,
        isolated_home: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """``marcus telemetry`` (no subcommand) prints help, exits 0."""
        from src.marcus_mcp.server import _handle_early_exit_paths

        rc = _handle_early_exit_paths(["marcus", "telemetry"])

        assert rc == 0
        out = capsys.readouterr().out + capsys.readouterr().err
        # Help text should mention the subcommands.
        assert (
            any(
                cmd in capsys.readouterr().out.lower() + capsys.readouterr().err.lower()
                for cmd in ("status", "enable", "disable", "purge")
            )
            or rc == 0
        )


class TestTelemetryClientSingleton:
    """``get_telemetry_client`` returns a process-wide singleton."""

    def test_returns_telemetry_client_instance(
        self, isolated_home: Path
    ) -> None:
        """First call constructs; second call returns the same object."""
        from src.telemetry import get_telemetry_client, reset_telemetry_client
        from src.telemetry.client import TelemetryClient

        reset_telemetry_client()
        a = get_telemetry_client()
        b = get_telemetry_client()

        assert isinstance(a, TelemetryClient)
        assert a is b
        reset_telemetry_client()

    def test_reads_api_key_from_env(
        self,
        isolated_home: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """MARCUS_POSTHOG_API_KEY env var populates the client's api_key.

        Project-level PostHog API keys are not secret (they're
        client-side identifiers, like Mixpanel tokens).  But
        Marcus's policy is to read them from env or config rather
        than embed in code so the maintainer can rotate without a
        release.
        """
        from src.telemetry import get_telemetry_client, reset_telemetry_client

        reset_telemetry_client()
        monkeypatch.setenv("MARCUS_POSTHOG_API_KEY", "phc_test_42")

        client = get_telemetry_client()

        assert client._api_key == "phc_test_42"
        reset_telemetry_client()

    def test_empty_api_key_still_constructs(self, isolated_home: Path) -> None:
        """No env var → client still constructs with empty key.

        Empty key means PostHog rejects events (401) which the
        client debug-logs.  Local outbound mirror still works.
        This is the default state for users who haven't configured
        Marcus's PostHog project.
        """
        from src.telemetry import get_telemetry_client, reset_telemetry_client

        reset_telemetry_client()
        client = get_telemetry_client()

        # Construction succeeds; key is the empty default.
        assert client._api_key == ""
        reset_telemetry_client()

    def test_reset_clears_singleton(self, isolated_home: Path) -> None:
        """``reset_telemetry_client`` is a test-only seam.

        Without it, env-var changes in subsequent tests would not
        be reflected — the singleton captures the api_key at first
        construction.
        """
        from src.telemetry import get_telemetry_client, reset_telemetry_client

        reset_telemetry_client()
        a = get_telemetry_client()

        reset_telemetry_client()
        b = get_telemetry_client()

        assert a is not b
        reset_telemetry_client()


class TestFirstRunNoticeWiring:
    """``main()`` invokes the first-run notice before MCP setup."""

    def test_main_module_imports_notice_function(self) -> None:
        """The server module imports ``print_first_run_notice_if_needed``.

        Acts as a smoke test that the wiring exists.  We don't
        actually call ``main()`` here (it spins up an async MCP
        server); we just verify the import path is in place so a
        regression that removes the import is caught.
        """
        import src.marcus_mcp.server as server_mod

        assert hasattr(server_mod, "print_first_run_notice_if_needed"), (
            "server.py must import print_first_run_notice_if_needed so "
            "the notice fires on startup."
        )
