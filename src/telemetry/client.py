"""Marcus telemetry client (Marcus #416).

Provides the first-run notice and the :class:`TelemetryClient` that
ships anonymous usage events to PostHog.

The client is the in-process surface for emitting events.  Every
hook in Marcus that wants to record an event calls
``TelemetryClient.capture(event, properties)``.  The client:

- Generates an anonymous UUID on first send and persists it at
  ``~/.marcus/telemetry_id`` so subsequent processes reuse it
  (cohort grouping without identifying anyone).
- Mirrors every sent event to ``~/.marcus/telemetry_outbound.jsonl``
  so users can audit what shipped (rotated at ~100 MB).
- Posts to ``https://us.i.posthog.com/capture/`` via ``httpx``,
  fire-and-forget — network errors are caught and dropped, never
  propagated into Marcus code paths.
- Respects ``is_telemetry_enabled()`` — when disabled, ``capture``
  is a complete no-op (no UUID generated, no log written, no
  network call).
- Never writes to ``sys.stdout`` (MCP stdio mode invariant — see
  the first-run notice docstring).

See ``docs/telemetry.md`` for the full disclosure of what is and
is not collected.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

__all__ = [
    "FIRST_RUN_NOTICE",
    "POSTHOG_CAPTURE_URL",
    "TelemetryClient",
    "get_marker_path",
    "print_first_run_notice_if_needed",
]

logger = logging.getLogger(__name__)


#: PostHog US-region capture endpoint.  EU users get the same
#: contract; we ship US-only per the v0.3.7 disclosure document.
POSTHOG_CAPTURE_URL: str = "https://us.i.posthog.com/capture/"

#: Default outbound log rotation cap (~100 MB) per Kaia review on
#: PR #545.  Live log is rotated to ``.jsonl.1`` and a fresh empty
#: live log is started when the live log exceeds this many bytes.
_DEFAULT_MAX_LOG_BYTES: int = 100 * 1024 * 1024

#: httpx POST timeout in seconds.  Short — telemetry must never
#: block Marcus.  A long timeout against a slow PostHog instance
#: would stall the calling code path.
_DEFAULT_TIMEOUT_SECONDS: float = 5.0


# -- Public API ---------------------------------------------------------------


def get_marker_path() -> Path:
    """Return the marker file path used to suppress the first-run notice.

    Resolved on every call so unit tests that ``monkeypatch.setenv("HOME",
    tmp)`` get the per-test home directory.  A module-level constant
    would resolve once at import time and ignore the monkeypatch.

    Returns
    -------
    Path
        ``~/.marcus/.telemetry_notice_shown`` — created when the
        first-run notice fires, checked on every subsequent call to
        :func:`print_first_run_notice_if_needed`.

    See Also
    --------
    print_first_run_notice_if_needed : the one production caller.
    """
    return Path.home() / ".marcus" / ".telemetry_notice_shown"


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

    marker = get_marker_path()
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


# -- TelemetryClient ----------------------------------------------------------


class TelemetryClient:
    """In-process surface for emitting anonymous telemetry events.

    Every Marcus event hook calls
    ``TelemetryClient.capture(event, properties)``.  The client
    decides on the spot whether to actually ship — honoring the
    opt-in/out config — and handles UUID lifecycle, outbound
    mirroring, and network errors transparently.

    Designed to be cheap to instantiate (no I/O in ``__init__``);
    callers typically create one per Marcus process.

    Parameters
    ----------
    api_key : str
        The PostHog project API key.  Typically read from
        ``MARCUS_POSTHOG_API_KEY`` env var or ``config.yaml``.
    capture_url : str, optional
        Override the PostHog endpoint.  Defaults to
        :data:`POSTHOG_CAPTURE_URL`.  Tests can point this at a
        local mock server.
    timeout_seconds : float, optional
        httpx timeout per request.  Short by design — telemetry
        must never block Marcus.
    _max_log_bytes : int, optional
        Outbound log rotation threshold in bytes.  Public for
        unit tests; production code should accept the default.
    _send_inline : bool, optional
        Test-only escape hatch.  When ``True``, the network send
        runs synchronously in the caller's thread instead of being
        submitted to the background executor.  Required for unit
        tests that need deterministic verification of what
        ``httpx.post`` saw without race-condition waits.  Production
        code should leave this ``False``.

    Notes
    -----
    The network send runs on a small ``ThreadPoolExecutor`` so
    ``capture`` returns immediately from the caller's perspective —
    even when called from async code paths (the MCP server's event
    loop never blocks on telemetry).  The mirror-to-outbound-log
    step still runs synchronously inside ``capture`` so the audit
    record is complete before the function returns.

    The executor uses non-daemon threads (Python default for
    ``ThreadPoolExecutor``).  At process shutdown, pending events
    finish before the process exits — worst case ~5 s if an event
    is mid-timeout when Marcus exits.  That trade-off favors "the
    last few events make it to PostHog" over "Marcus exits 5 s
    earlier on slow networks", which we judge a feature not a bug.

    The class does not expose a ``flush`` or ``shutdown`` method.
    Tests that need to wait on the executor can call
    ``client._executor.shutdown(wait=True)`` directly.
    """

    def __init__(
        self,
        api_key: str,
        *,
        capture_url: str = POSTHOG_CAPTURE_URL,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        _max_log_bytes: int = _DEFAULT_MAX_LOG_BYTES,
        _send_inline: bool = False,
    ) -> None:
        self._api_key = api_key
        self._capture_url = capture_url
        self._timeout_seconds = timeout_seconds
        self._max_log_bytes = _max_log_bytes
        self._send_inline = _send_inline
        # Lazy-created on first non-inline send so tests using
        # ``_send_inline=True`` never spin up a thread pool they
        # don't need.
        self._executor: Optional[ThreadPoolExecutor] = None

    # -- Public ---------------------------------------------------------------

    def capture(self, event: str, properties: Dict[str, Any]) -> None:
        """Emit a single telemetry event.

        Fire-and-forget: returns immediately, swallows every network
        error, never raises.  When telemetry is disabled at the
        config layer (or via ``MARCUS_TELEMETRY=off``), this method
        is a complete no-op — no UUID generated, no log written,
        no network call.

        Parameters
        ----------
        event : str
            Event name (e.g. ``"session_started"``, ``"project_created"``).
            Must match the schema in ``docs/telemetry.md``.
        properties : dict
            Event properties.  Per the privacy contract: no raw
            user text, no source code, no PII.  Callers are
            responsible for sanitization before this call.
        """
        # Late import to avoid cycles and to honor test-time
        # config changes (the config layer reads the env var on
        # every call).
        from src.telemetry.config import is_telemetry_enabled

        if not is_telemetry_enabled():
            return

        distinct_id = self._get_or_create_uuid()
        if distinct_id is None:
            return

        payload: Dict[str, Any] = {
            "api_key": self._api_key,
            "event": event,
            "distinct_id": distinct_id,
            "properties": dict(properties),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Mirror to the local outbound log BEFORE the network call.
        # If the network attempt fails, the user's audit record is
        # still complete — they can see the system tried to send.
        self._append_to_outbound_log(payload)

        # Pre-serialize the payload with ``default=str`` so non-
        # stdlib-JSON types (Path, datetime, Decimal) survive the
        # wire send.  ``httpx.post(json=payload)`` internally calls
        # ``json.dumps(payload)`` *without* a default, so a property
        # carrying a Path would silently land in the mirror (which
        # uses default=str) but raise TypeError on the wire.  Mirror
        # and wire must agree on serialization or the audit promise
        # is a lie.
        try:
            body = json.dumps(payload, default=str).encode("utf-8")
        except (TypeError, ValueError) as exc:
            logger.debug(
                "Telemetry payload serialization failed for %s: %s",
                event,
                exc,
            )
            return

        # Network send — fire-and-forget.  In production, submit to
        # the background executor so the caller (often inside an
        # asyncio event loop) returns immediately.  In tests,
        # ``_send_inline=True`` runs the send synchronously so the
        # test can assert against the mock httpx.post without
        # racing the background thread.
        if self._send_inline:
            self._send_payload_sync(event, body)
        else:
            if self._executor is None:
                self._executor = ThreadPoolExecutor(
                    max_workers=2,
                    thread_name_prefix="marcus-telemetry",
                )
            self._executor.submit(self._send_payload_sync, event, body)

    def _send_payload_sync(self, event: str, body: bytes) -> None:
        """Send a pre-serialized JSON payload.  Always swallow errors.

        Catches every plausible network / HTTP / serialization error
        and logs at debug level.  Telemetry must never raise into a
        Marcus call site, whether the call site is the worker hot
        path or the thread pool's task runner.

        Calls ``response.raise_for_status()`` so non-2xx responses
        (PostHog rate limits, invalid API key, server error) are
        treated as failures.  Without this check, a 429 response
        would silently 'succeed' from ``httpx.post``'s perspective
        and the audit log would report shipped events that PostHog
        never accepted.
        """
        try:
            response = httpx.post(
                self._capture_url,
                content=body,
                headers={"content-type": "application/json"},
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except (
            httpx.HTTPError,
            OSError,
        ) as exc:
            # ``httpx.HTTPError`` is the base of HTTPStatusError,
            # ConnectError, TimeoutException, RequestError, etc.
            # ``OSError`` catches lower-level socket failures that
            # httpx may not wrap on some platforms.
            logger.debug("Telemetry capture failed for %s: %s", event, exc)

    # -- Internals ------------------------------------------------------------

    def _get_or_create_uuid(self) -> Optional[str]:
        """Read the anonymous UUID, generating one on first send.

        Returns
        -------
        str or None
            The UUID as a string.  Returns ``None`` if the home
            directory is unwritable — caller treats this as
            "skip the send" rather than crashing.
        """
        from src.telemetry.cli import get_telemetry_id_path

        path = get_telemetry_id_path()
        try:
            if path.exists():
                value = path.read_text().strip()
                if value:
                    return value
            new_uuid = str(uuid.uuid4())
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new_uuid + "\n")
            return new_uuid
        except OSError as exc:
            logger.debug("Could not read/write telemetry UUID: %s", exc)
            return None

    def _append_to_outbound_log(self, payload: Dict[str, Any]) -> None:
        """Append ``payload`` as one JSONL line; rotate if oversized.

        Rotation: if the live log exceeds ``self._max_log_bytes``,
        it is renamed to ``<path>.1`` (overwriting any prior ``.1``)
        and a fresh empty live log is started.  Only one
        generation is kept — the rotation cap is a "do not let
        this grow unbounded" guarantee, not an archival policy.
        """
        from src.telemetry.cli import get_outbound_log_path

        path = get_outbound_log_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            # Rotation check BEFORE the append so a single huge
            # event cannot blow past the cap unbounded.
            if path.exists() and path.stat().st_size >= self._max_log_bytes:
                rotated = path.with_suffix(path.suffix + ".1")
                # Overwrite any prior rotated file.
                if rotated.exists():
                    rotated.unlink()
                path.rename(rotated)

            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, default=str) + "\n")
        except OSError as exc:
            logger.debug("Could not write outbound log entry: %s", exc)
