"""Marcus telemetry package (Marcus #416).

Public surface:

- :func:`get_telemetry_client` — process-wide singleton accessor.
  Lazily constructs a :class:`TelemetryClient` from
  ``MARCUS_POSTHOG_API_KEY`` env var (or empty default).
- :func:`reset_telemetry_client` — test-only seam to clear the
  singleton between tests.
- :func:`print_first_run_notice_if_needed` — re-exported from
  :mod:`src.telemetry.client` for convenience at the server
  startup site.
- :class:`TelemetryClient` — re-exported for type hints.

See ``docs/telemetry.md`` for the privacy contract.
"""

from __future__ import annotations

import os
from typing import Optional

from src.telemetry.client import (
    TelemetryClient,
    print_first_run_notice_if_needed,
)

__all__ = [
    "TelemetryClient",
    "get_telemetry_client",
    "print_first_run_notice_if_needed",
    "reset_telemetry_client",
]


#: Process-wide singleton.  ``None`` until first :func:`get_telemetry_client`
#: call.  Tests use :func:`reset_telemetry_client` to clear between cases.
_singleton: Optional[TelemetryClient] = None


def get_telemetry_client() -> TelemetryClient:
    """Return the process-wide :class:`TelemetryClient` instance.

    Lazy construction on first call.  Reads ``MARCUS_POSTHOG_API_KEY``
    from the environment; falls back to the empty string when
    unset.  An empty API key means PostHog will reject the events
    (401) but the client still mirrors locally — useful for
    development and for users who haven't configured a PostHog
    project.

    Returns
    -------
    TelemetryClient
        The singleton client.  Subsequent calls return the same
        object.

    Notes
    -----
    The singleton pattern is intentional: every event hook in
    Marcus calls into the same client so all events share one
    UUID, one outbound log, and one ThreadPoolExecutor.  A new
    client per call would defeat the cohort-grouping property
    that the anonymous UUID is meant to provide.
    """
    global _singleton
    if _singleton is None:
        api_key = os.environ.get("MARCUS_POSTHOG_API_KEY", "")
        _singleton = TelemetryClient(api_key=api_key)
    return _singleton


def reset_telemetry_client() -> None:
    """Clear the singleton.  Test-only — production code must not call.

    Without this seam, env-var changes in subsequent unit tests
    would not be reflected: the singleton captures ``api_key`` at
    first construction.  In production, the env is read once and
    the client lives for the process lifetime.
    """
    global _singleton
    _singleton = None
