"""Marcus telemetry client (Marcus #416).

Provides the first-run notice plus (in subsequent commits) the
``TelemetryClient`` that ships anonymous usage events to PostHog.

The first-run notice is the user's earliest user-facing touchpoint
with telemetry.  It is intentionally minimal and stderr-only so it
never corrupts the MCP JSON-RPC channel on stdout.

See ``docs/telemetry.md`` for the full disclosure of what is and is
not collected.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

__all__ = [
    "FIRST_RUN_NOTICE",
    "TELEMETRY_NOTICE_MARKER",
    "print_first_run_notice_if_needed",
]


# -- Public constants ---------------------------------------------------------


def _telemetry_notice_marker() -> Path:
    """Resolve the marker path lazily so HOME monkeypatching in tests works.

    Returns
    -------
    Path
        ``~/.marcus/.telemetry_notice_shown``.  Resolved at call time
        rather than module-import time so unit tests that patch
        ``HOME``/``USERPROFILE`` via ``monkeypatch.setenv`` get an
        isolated marker path per test.
    """
    return Path.home() / ".marcus" / ".telemetry_notice_shown"


class _MarkerProxy:
    """A ``Path``-like object that re-resolves ``Path.home()`` on every call.

    Tests that ``monkeypatch.setenv("HOME", tmp)`` need
    ``TELEMETRY_NOTICE_MARKER.exists()`` and ``TELEMETRY_NOTICE_MARKER.touch()``
    to operate on the per-test home directory.  A module-level
    ``Path.home() / ...`` resolves once at import time and ignores the
    monkeypatch.  This proxy forwards each attribute access to a fresh
    resolution.

    The proxy is internal — :data:`TELEMETRY_NOTICE_MARKER` is the
    public name.  Treat it as a ``Path`` for all practical purposes.
    """

    def __fspath__(self) -> str:
        return str(_telemetry_notice_marker())

    def __getattr__(self, name: str) -> object:
        return getattr(_telemetry_notice_marker(), name)

    def __repr__(self) -> str:
        return repr(_telemetry_notice_marker())

    def __eq__(self, other: object) -> bool:
        return _telemetry_notice_marker() == other

    def __hash__(self) -> int:
        return hash(_telemetry_notice_marker())


#: Path to the marker file that records the notice has been shown.
#: When this file exists, the notice does not print again.  Lazy
#: resolution so tests can isolate ``HOME``.
TELEMETRY_NOTICE_MARKER: Path = _MarkerProxy()  # type: ignore[assignment]


#: The first-run notice text printed to stderr.  Format chosen to
#: stay readable in a typical 80-column terminal.
FIRST_RUN_NOTICE: str = """\
============================================================
 Marcus Telemetry (anonymous, opt-in)
============================================================

Marcus collects anonymous usage data to improve the tool.

What we collect:
  - Marcus version, OS, Python version
  - Run duration, task counts, completion rate
  - Bucket labels for project type (e.g. "web app", "fintech")
  - Error types (not messages or stack traces)
  - Cost summary (tokens, dollars per run)

What we never collect:
  - Source code, file contents, API keys
  - Project names, task descriptions, PRD text
  - IP addresses, email, hostnames

Anonymous UUID at: ~/.marcus/telemetry_id
Local copy of sent events: ~/.marcus/telemetry_outbound.jsonl

Disable any time:
  marcus telemetry disable

Full disclosure:
  https://github.com/lwgray/marcus/blob/main/docs/telemetry.md

(This notice prints once.)
============================================================
"""


def print_first_run_notice_if_needed() -> None:
    """Print the telemetry notice exactly once per Marcus installation.

    Side effects
    ------------
    - Prints :data:`FIRST_RUN_NOTICE` to ``sys.stderr`` if the marker
      file does not exist.
    - Creates the marker file as a side effect of printing.
      Subsequent calls are no-ops.

    Honored environment variables
    -----------------------------
    ``MARCUS_TELEMETRY``
        If set to ``"off"`` (case-insensitive), the notice is skipped
        AND the marker is *not* created.  This makes the env var a
        true suppression switch — turning it off and then back on
        later restores first-run notice behavior.

    Notes
    -----
    - This function never prints to ``sys.stdout``.  Marcus runs in
      MCP stdio mode where stdout is reserved for the JSON-RPC
      protocol; any non-protocol bytes on stdout corrupt the channel.
      Always stderr.
    - The function swallows ``OSError`` on marker creation so a
      read-only home directory cannot crash Marcus on first run.  The
      cost is that users on read-only homes see the notice every run
      — better than a crash.
    """
    if os.environ.get("MARCUS_TELEMETRY", "").lower() == "off":
        return

    marker = _telemetry_notice_marker()
    if marker.exists():
        return

    # Print before touching the filesystem so a write failure does not
    # silently swallow the notice on first run.
    print(FIRST_RUN_NOTICE, file=sys.stderr, flush=True)

    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
    except OSError:
        # Read-only home or permission issue.  We've already printed
        # the notice; not being able to write the marker just means
        # we'll print it again next run.  Acceptable — never crash
        # Marcus over a marker file.
        pass
