"""Marcus telemetry package (Marcus #416).

Public surface:

- :func:`get_telemetry_client` — process-wide singleton accessor.
  Lazily constructs a :class:`TelemetryClient` from the
  ``MARCUS_POSTHOG_API_KEY`` env var, falling back to the embedded
  PostHog project key (:data:`_DEFAULT_POSTHOG_API_KEY`).
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


#: Marcus's PostHog **project** API key.
#:
#: This is a write-only ingest key — PostHog designs project keys to
#: be public and ships them in client-side JavaScript.  It cannot read
#: project data and cannot administer the project, so embedding it in
#: Marcus's source is the intended use, not a leak.  (The secret kind
#: is a *personal* key, ``phx_…`` — never embed one of those.)
#:
#: End users never configure this: opting telemetry in or out is their
#: only control, and the destination project is Marcus's, not theirs.
#: ``MARCUS_POSTHOG_API_KEY`` overrides it for development or for a
#: self-hosted PostHog instance.
_DEFAULT_POSTHOG_API_KEY: str = (
    "phc_w5fzah2FLTCzZhcVHGCnEYbfFSALjUufj3qqEfSsMuFG"  # pragma: allowlist secret
)


def get_telemetry_client() -> TelemetryClient:
    """Return the process-wide :class:`TelemetryClient` instance.

    Lazy construction on first call.  The PostHog API key is resolved
    as ``MARCUS_POSTHOG_API_KEY`` (env override, for development or a
    self-hosted PostHog) falling back to the embedded project key
    :data:`_DEFAULT_POSTHOG_API_KEY`.  The key is always non-empty in
    a normal install, so opted-in events reach PostHog without the
    user configuring anything.

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
        api_key = os.environ.get("MARCUS_POSTHOG_API_KEY") or _DEFAULT_POSTHOG_API_KEY
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
