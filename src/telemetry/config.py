"""Telemetry on/off configuration (Marcus #416).

Reads and writes the user's opt-in/out choice at
``~/.marcus/config.yaml`` under the ``telemetry.enabled`` key.

Defaults to ``True`` (opt-in by default — OSS dev-tool norm; the
disclosure document at ``docs/telemetry.md`` is the user's contract).
The ``MARCUS_TELEMETRY=off`` environment variable is a one-shot
suppression switch that does NOT modify the on-disk config — so
re-enabling telemetry is a matter of clearing the env var.

The config writer performs a true YAML upsert (read-modify-write)
so unrelated sections (``ai``, ``kanban``, etc.) are preserved when
the telemetry flag is toggled.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict

import yaml

__all__ = [
    "get_config_path",
    "is_telemetry_enabled",
    "set_telemetry_enabled",
]


logger = logging.getLogger(__name__)


# -- Path resolution ----------------------------------------------------------


def get_config_path() -> Path:
    """Return the Marcus user-level config path.

    Resolved on every call so tests that monkeypatch ``HOME`` get
    the per-test config directory.  Same pattern as
    :func:`src.telemetry.client.get_marker_path` — exposing a
    function instead of a "constant" avoids module-level
    ``Path.home()`` caching and the proxy-class gymnastics that
    would otherwise be needed (Kaia review on PR #545).
    """
    return Path.home() / ".marcus" / "config.yaml"


# -- Public API ---------------------------------------------------------------


def is_telemetry_enabled() -> bool:
    """Return whether telemetry is enabled for the current process.

    Resolution order (first match wins):

    1. ``MARCUS_TELEMETRY=off`` (case-insensitive) → returns ``False``.
       This is the one-shot suppression switch; it does not modify
       the on-disk config.
    2. ``telemetry.enabled`` in ``~/.marcus/config.yaml`` → returns
       whatever boolean is written there.
    3. Default → ``True`` (opt-in by default; see
       ``docs/telemetry.md`` for the privacy contract).

    Robust to:

    - Missing config file (returns the default).
    - Missing ``telemetry`` section in an existing config (returns
      the default).
    - Unparseable / corrupt YAML (returns the default, logs a
      warning).

    Returns
    -------
    bool
        ``True`` if telemetry should be sent for this process,
        ``False`` otherwise.
    """
    if os.environ.get("MARCUS_TELEMETRY", "").lower() == "off":
        return False

    config = _load_config()
    telemetry = config.get("telemetry", {})
    if not isinstance(telemetry, dict):
        return True
    enabled = telemetry.get("enabled", True)
    if not isinstance(enabled, bool):
        return True
    return enabled


def set_telemetry_enabled(value: bool) -> None:
    """Persist the user's telemetry choice to ``~/.marcus/config.yaml``.

    Performs a true upsert: reads the existing config, updates only
    the ``telemetry.enabled`` key, and writes the merged result back.
    Unrelated keys (``ai``, ``kanban``, anything else) are preserved
    unchanged.

    Creates ``~/.marcus/`` if it does not already exist — first-run
    scenario where the user runs ``marcus telemetry disable`` before
    any other Marcus command.

    Parameters
    ----------
    value : bool
        ``True`` to enable telemetry, ``False`` to disable.

    Raises
    ------
    OSError
        If the config directory or file cannot be written.  Callers
        that wrap this in a CLI command should surface the error to
        the user — silently swallowing write failures would leave
        the user thinking telemetry was disabled when it was not.
    """
    config = _load_config()
    telemetry_section = config.setdefault("telemetry", {})
    if not isinstance(telemetry_section, dict):
        # The existing value is something weird (a string, a list).
        # Replace it with a fresh dict.  Honest behavior: we cannot
        # preserve a malformed section meaningfully.
        telemetry_section = {}
        config["telemetry"] = telemetry_section
    telemetry_section["enabled"] = value

    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config, sort_keys=False))


# -- Internals ----------------------------------------------------------------


def _load_config() -> Dict[str, Any]:
    """Read the config file, returning an empty dict on any error.

    Logs a warning on parse failures so the user has a breadcrumb
    if their hand-edited config is malformed — but never raises.
    Crashing Marcus over a bad config file would defeat the
    "telemetry is optional and best-effort" contract.
    """
    path = get_config_path()
    if not path.exists():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        logger.warning("Could not parse %s: %s. Using telemetry defaults.", path, exc)
        return {}
    if not isinstance(loaded, dict):
        return {}
    return loaded
