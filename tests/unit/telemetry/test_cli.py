"""Unit tests for :func:`src.telemetry.cli.handle_telemetry_cli`.

The CLI is the user's primary path to disable telemetry.  It must
work even when the rest of Marcus is in a broken state — opting out
should never require a working MCP server.  Tests pin:

- Help text is shown when no subcommand is given.
- ``status`` prints current state.
- ``enable`` / ``disable`` round-trip through the config layer.
- ``purge`` removes the anonymous UUID, outbound log, and notice
  marker.  Idempotent — running twice succeeds cleanly.
- Unknown subcommands exit non-zero.
- Output goes to stdout (CLI is interactive; not subject to the
  MCP stdio invariant — that only applies to the server path).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ``~`` to ``tmp_path`` for per-test config isolation."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("MARCUS_TELEMETRY", raising=False)

    resolved_home = Path.home()
    assert resolved_home == tmp_path, (
        f"isolated_home fixture failed: Path.home() resolved to "
        f"{resolved_home!r}, expected {tmp_path!r}"
    )
    return tmp_path


class TestHandleTelemetryCli:
    """Top-level dispatch + help behavior."""

    def test_no_args_prints_help_zero_exit(
        self, isolated_home: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``marcus telemetry`` (no subcommand) prints help, exits 0."""
        from src.telemetry.cli import handle_telemetry_cli

        rc = handle_telemetry_cli([])

        assert rc == 0
        captured = capsys.readouterr()
        # argparse's help text includes the program name and at least
        # the four subcommand names.
        out = captured.out + captured.err
        assert "telemetry" in out.lower()
        for cmd in ("status", "enable", "disable", "purge"):
            assert cmd in out

    def test_unknown_subcommand_exits_nonzero(self, isolated_home: Path) -> None:
        """Argparse rejects unknown subcommands with non-zero exit."""
        from src.telemetry.cli import handle_telemetry_cli

        with pytest.raises(SystemExit) as exc_info:
            handle_telemetry_cli(["nonexistent"])

        assert exc_info.value.code != 0


class TestDisable:
    """``marcus telemetry disable`` turns telemetry off + reports."""

    def test_disable_writes_false_to_config(
        self, isolated_home: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """After ``disable``, ``is_telemetry_enabled()`` returns False."""
        from src.telemetry.cli import handle_telemetry_cli
        from src.telemetry.config import is_telemetry_enabled

        rc = handle_telemetry_cli(["disable"])

        assert rc == 0
        assert is_telemetry_enabled() is False

    def test_disable_prints_confirmation(
        self, isolated_home: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """User sees confirmation that telemetry is now disabled."""
        from src.telemetry.cli import handle_telemetry_cli

        handle_telemetry_cli(["disable"])

        captured = capsys.readouterr()
        assert "disabled" in captured.out.lower()


class TestEnable:
    """``marcus telemetry enable`` turns telemetry on + reports."""

    def test_enable_after_disable_round_trips(self, isolated_home: Path) -> None:
        """disable → enable → is_telemetry_enabled() returns True."""
        from src.telemetry.cli import handle_telemetry_cli
        from src.telemetry.config import is_telemetry_enabled

        handle_telemetry_cli(["disable"])
        assert is_telemetry_enabled() is False

        rc = handle_telemetry_cli(["enable"])
        assert rc == 0
        assert is_telemetry_enabled() is True

    def test_enable_prints_confirmation(
        self, isolated_home: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from src.telemetry.cli import handle_telemetry_cli

        handle_telemetry_cli(["enable"])

        captured = capsys.readouterr()
        assert "enabled" in captured.out.lower()


class TestStatus:
    """``marcus telemetry status`` prints current state without modifying."""

    def test_status_shows_enabled_when_default(
        self, isolated_home: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Fresh install — status reports enabled (opt-in default)."""
        from src.telemetry.cli import handle_telemetry_cli

        rc = handle_telemetry_cli(["status"])

        assert rc == 0
        out = capsys.readouterr().out.lower()
        assert "enabled" in out

    def test_status_shows_disabled_after_disable(
        self, isolated_home: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """After disable, status reports disabled."""
        from src.telemetry.cli import handle_telemetry_cli

        handle_telemetry_cli(["disable"])
        capsys.readouterr()  # drain disable output

        rc = handle_telemetry_cli(["status"])

        assert rc == 0
        out = capsys.readouterr().out.lower()
        assert "disabled" in out

    def test_status_includes_config_paths(
        self, isolated_home: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Status output names the files state lives in.

        Without paths, a user who runs ``marcus telemetry status``
        and wants to inspect what's been sent has no breadcrumb to
        ``~/.marcus/telemetry_outbound.jsonl``.  The "audit your
        own data" disclosure promise needs this.
        """
        from src.telemetry.cli import handle_telemetry_cli

        handle_telemetry_cli(["status"])

        out = capsys.readouterr().out
        # At least the config and outbound-log paths should appear.
        assert "config" in out.lower()
        assert "telemetry_outbound.jsonl" in out

    def test_status_does_not_modify_state(self, isolated_home: Path) -> None:
        """``status`` is read-only — does not flip telemetry."""
        from src.telemetry.cli import handle_telemetry_cli
        from src.telemetry.config import is_telemetry_enabled

        # Default is enabled; status should leave it enabled.
        assert is_telemetry_enabled() is True
        handle_telemetry_cli(["status"])
        assert is_telemetry_enabled() is True

        # Disabled stays disabled.
        handle_telemetry_cli(["disable"])
        assert is_telemetry_enabled() is False
        handle_telemetry_cli(["status"])
        assert is_telemetry_enabled() is False


class TestPurge:
    """``marcus telemetry purge`` removes identifying artifacts."""

    def test_purge_disables_telemetry(self, isolated_home: Path) -> None:
        """Purge implies disable."""
        from src.telemetry.cli import handle_telemetry_cli
        from src.telemetry.config import is_telemetry_enabled

        rc = handle_telemetry_cli(["purge"])

        assert rc == 0
        assert is_telemetry_enabled() is False

    def test_purge_removes_uuid_file(self, isolated_home: Path) -> None:
        """Anonymous UUID file is deleted."""
        from src.telemetry.cli import (
            get_telemetry_id_path,
            handle_telemetry_cli,
        )

        uuid_path = get_telemetry_id_path()
        # Seed a fake UUID file.
        uuid_path.parent.mkdir(parents=True, exist_ok=True)
        uuid_path.write_text("00000000-0000-0000-0000-000000000000\n")
        assert uuid_path.exists()

        handle_telemetry_cli(["purge"])

        assert not uuid_path.exists()

    def test_purge_removes_outbound_log(self, isolated_home: Path) -> None:
        """Local outbound-event log is deleted."""
        from src.telemetry.cli import (
            get_outbound_log_path,
            handle_telemetry_cli,
        )

        log_path = get_outbound_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text('{"event":"test"}\n')
        assert log_path.exists()

        handle_telemetry_cli(["purge"])

        assert not log_path.exists()

    def test_purge_removes_notice_marker(self, isolated_home: Path) -> None:
        """First-run notice marker is deleted so re-enable restores notice."""
        from src.telemetry.cli import handle_telemetry_cli
        from src.telemetry.client import get_marker_path

        marker = get_marker_path()
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
        assert marker.exists()

        handle_telemetry_cli(["purge"])

        assert not marker.exists()

    def test_purge_is_idempotent(self, isolated_home: Path) -> None:
        """Running purge twice succeeds cleanly with no errors.

        After the first purge, identity files are gone.  The second
        call must not crash trying to delete missing files.
        Critical for users who run purge defensively without
        knowing prior state.

        Falsification recipe: replace ``path.unlink(missing_ok=True)``
        in ``_cmd_purge`` with bare ``path.unlink()`` and confirm
        this test fails with FileNotFoundError on the second call.
        """
        from src.telemetry.cli import handle_telemetry_cli

        rc1 = handle_telemetry_cli(["purge"])
        rc2 = handle_telemetry_cli(["purge"])

        assert rc1 == 0
        assert rc2 == 0

    def test_purge_succeeds_on_clean_install(self, isolated_home: Path) -> None:
        """Purge before any identity files exist still succeeds."""
        from src.telemetry.cli import handle_telemetry_cli

        rc = handle_telemetry_cli(["purge"])

        assert rc == 0
