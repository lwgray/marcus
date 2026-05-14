"""Unit tests for :func:`src.telemetry.client.print_first_run_notice_if_needed`.

The notice is the user's first user-facing touchpoint with telemetry.
It must be:

- Idempotent (prints once per install via a marker file).
- stderr-only (Marcus runs in MCP stdio mode where stdout is reserved
  for JSON-RPC; any non-protocol bytes on stdout corrupt the channel).
- Honoring ``MARCUS_TELEMETRY=off`` as a suppression switch that does
  NOT create the marker (so re-enabling restores the notice).
- Crash-safe on read-only home directories.

Tests in this module are the privacy contract regression net for the
disclosure document at ``docs/telemetry.md``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ``~`` to ``tmp_path`` so the marker file lives in a tmp dir.

    Each test gets a clean ``~/.marcus/`` to operate on. Forwards
    ``Path.home()`` resolution by setting the platform-appropriate env
    vars. Also clears ``MARCUS_TELEMETRY`` so tests don't inherit the
    developer's environment.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("MARCUS_TELEMETRY", raising=False)
    return tmp_path


class TestFirstRunNotice:
    """The first-run notice prints once, to stderr, idempotently."""

    def test_prints_notice_on_first_call(
        self,
        isolated_home: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Notice text appears on stderr the first time the function runs."""
        from src.telemetry.client import print_first_run_notice_if_needed

        print_first_run_notice_if_needed()

        captured = capsys.readouterr()
        assert "Marcus Telemetry" in captured.err
        assert "anonymous" in captured.err
        assert "marcus telemetry disable" in captured.err

    def test_writes_to_stderr_never_stdout(
        self,
        isolated_home: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """stdout MUST be empty.

        Marcus runs in MCP stdio mode where stdout is the JSON-RPC
        protocol channel. Any non-protocol bytes on stdout corrupt
        the channel and break Claude Desktop / Cursor integration
        silently. This is the privacy + protocol regression net.

        Falsification recipe: change the ``print(...)`` call in
        ``client.py`` to use ``file=sys.stdout`` (or omit ``file=``
        which defaults to stdout) and confirm this test fails.
        """
        from src.telemetry.client import print_first_run_notice_if_needed

        print_first_run_notice_if_needed()

        captured = capsys.readouterr()
        assert captured.out == "", (
            f"stdout must be empty (MCP stdio mode invariant); got: "
            f"{captured.out!r}"
        )

    def test_creates_marker_file_on_first_call(
        self,
        isolated_home: Path,
    ) -> None:
        """Marker file exists at ~/.marcus/.telemetry_notice_shown after first call."""
        from src.telemetry.client import (
            TELEMETRY_NOTICE_MARKER,
            print_first_run_notice_if_needed,
        )

        assert not TELEMETRY_NOTICE_MARKER.exists()
        print_first_run_notice_if_needed()
        assert TELEMETRY_NOTICE_MARKER.exists()

    def test_skipped_when_marker_exists(
        self,
        isolated_home: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Second call is a no-op — marker file suppresses the notice."""
        from src.telemetry.client import (
            TELEMETRY_NOTICE_MARKER,
            print_first_run_notice_if_needed,
        )

        # Pre-create the marker (simulating a previous run).
        TELEMETRY_NOTICE_MARKER.parent.mkdir(parents=True, exist_ok=True)
        TELEMETRY_NOTICE_MARKER.touch()

        print_first_run_notice_if_needed()

        captured = capsys.readouterr()
        assert captured.err == "", (
            "Marker file should suppress the notice; instead saw: " + captured.err
        )

    def test_skipped_when_marcus_telemetry_off(
        self,
        isolated_home: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """MARCUS_TELEMETRY=off suppresses notice AND does NOT create marker.

        Critical: the env var must not create the marker, so that
        re-enabling telemetry (clearing the env var) restores the
        notice on the next run. Without this, users who run
        ``MARCUS_TELEMETRY=off marcus`` once would lose the notice
        forever even if they later want to opt back in.
        """
        from src.telemetry.client import (
            TELEMETRY_NOTICE_MARKER,
            print_first_run_notice_if_needed,
        )

        monkeypatch.setenv("MARCUS_TELEMETRY", "off")

        print_first_run_notice_if_needed()

        captured = capsys.readouterr()
        assert captured.err == ""
        assert captured.out == ""
        assert not TELEMETRY_NOTICE_MARKER.exists(), (
            "Marker must NOT be created when MARCUS_TELEMETRY=off; "
            "otherwise re-enabling telemetry loses the notice forever."
        )

    def test_marcus_telemetry_off_case_insensitive(
        self,
        isolated_home: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """MARCUS_TELEMETRY=OFF / Off / oFf all suppress the notice."""
        from src.telemetry.client import print_first_run_notice_if_needed

        for value in ("OFF", "Off", "oFf"):
            monkeypatch.setenv("MARCUS_TELEMETRY", value)
            capsys.readouterr()  # drain anything from prior iteration
            print_first_run_notice_if_needed()
            captured = capsys.readouterr()
            assert (
                captured.err == ""
            ), f"MARCUS_TELEMETRY={value!r} should suppress; saw: {captured.err!r}"

    def test_marcus_telemetry_on_does_not_suppress(
        self,
        isolated_home: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Any value other than 'off' lets the notice fire.

        Set to 'on' explicitly — the function should treat this as
        "telemetry not actively suppressed" and print the notice as
        normal.
        """
        from src.telemetry.client import print_first_run_notice_if_needed

        monkeypatch.setenv("MARCUS_TELEMETRY", "on")
        print_first_run_notice_if_needed()
        captured = capsys.readouterr()
        assert "Marcus Telemetry" in captured.err

    def test_idempotent_back_to_back(
        self,
        isolated_home: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Calling twice in one session prints once total."""
        from src.telemetry.client import print_first_run_notice_if_needed

        print_first_run_notice_if_needed()
        first = capsys.readouterr().err
        assert "Marcus Telemetry" in first

        print_first_run_notice_if_needed()
        second = capsys.readouterr().err
        assert second == ""

    def test_disclosure_url_in_notice(
        self,
        isolated_home: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Notice must contain a clickable URL to the full disclosure.

        Regression net: if the disclosure doc moves, this test forces
        us to update the notice in lockstep. The URL is the user's
        only programmatic path to "see what's being sent."
        """
        from src.telemetry.client import print_first_run_notice_if_needed

        print_first_run_notice_if_needed()
        captured = capsys.readouterr()
        assert "https://github.com/lwgray/marcus" in captured.err
        assert "telemetry.md" in captured.err
