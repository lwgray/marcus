"""``marcus telemetry`` subcommand handler (Marcus #416).

Provides the user-facing CLI for inspecting and changing telemetry
state:

- ``marcus telemetry status``   — show current state and paths.
- ``marcus telemetry enable``   — turn telemetry on.
- ``marcus telemetry disable``  — turn telemetry off.
- ``marcus telemetry purge``    — disable + delete anonymous UUID
                                  + outbound log + notice marker.

The CLI is the user's primary path to opt out.  It must remain
functional even when the rest of Marcus is in a broken state —
opting out should never depend on a working MCP server, a working
kanban connection, or anything else beyond filesystem access to
``~/.marcus/``.

The router is :func:`handle_telemetry_cli`, intended to be
dispatched from the top of ``src/marcus_mcp/server.py:main()``
before any MCP / async setup so the disable command works in
degraded modes.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

__all__ = [
    "HELP_EPILOG",
    "get_outbound_log_path",
    "get_telemetry_id_path",
    "handle_telemetry_cli",
]


HELP_EPILOG: str = """\
Commands:
  status      Show whether telemetry is enabled and where state lives.
  enable      Turn telemetry on for this machine.
  disable     Turn telemetry off for this machine.
  purge       Disable AND delete the anonymous UUID + local outbound log.

Examples:
  marcus telemetry status
  marcus telemetry disable
  marcus telemetry purge

For a one-time disable without changing config, run Marcus with:
  MARCUS_TELEMETRY=off marcus

Full disclosure of what is and is not collected:
  https://github.com/lwgray/marcus/blob/main/docs/telemetry.md

Privacy questions or data requests:
  privacy@marcus-ai.dev
"""


# -- Path helpers -------------------------------------------------------------
#
# Each helper resolves ``Path.home()`` on every call so that test
# monkeypatching of HOME works per-test (matches the function-not-
# constant pattern from Kaia review on PR #545).  The module-level
# ``TELEMETRY_ID_FILE`` / ``OUTBOUND_LOG`` aliases below are thin
# Path-like wrappers around these helpers for the test API.


def get_telemetry_id_path() -> Path:
    """Return the anonymous UUID file path."""
    return Path.home() / ".marcus" / "telemetry_id"


def get_outbound_log_path() -> Path:
    """Return the local outbound-event log path."""
    return Path.home() / ".marcus" / "telemetry_outbound.jsonl"


# -- Entry point --------------------------------------------------------------


def handle_telemetry_cli(argv: List[str]) -> int:
    """Dispatch ``marcus telemetry <subcommand>`` and return an exit code.

    Parameters
    ----------
    argv : list of str
        Arguments after ``telemetry`` in the original command line.
        Empty list means the user typed bare ``marcus telemetry``.

    Returns
    -------
    int
        Process exit code.  Zero on success.  Non-zero exits happen
        through ``argparse`` for unknown subcommands (it raises
        ``SystemExit`` itself).
    """
    parser = argparse.ArgumentParser(
        prog="marcus telemetry",
        description="Manage Marcus's anonymous telemetry settings.",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "subcommand",
        choices=["status", "enable", "disable", "purge"],
        nargs="?",
        default=None,
        help="What to do.",
    )

    if not argv:
        parser.print_help()
        return 0

    args = parser.parse_args(argv)

    if args.subcommand == "status":
        return _cmd_status()
    if args.subcommand == "enable":
        return _cmd_enable()
    if args.subcommand == "disable":
        return _cmd_disable()
    if args.subcommand == "purge":
        return _cmd_purge()

    # Unreachable — argparse rejects unknown choices before we get
    # here, and ``nargs="?"`` falls through to ``None`` only when
    # ``argv`` is empty (handled above).
    parser.print_help()
    return 1


# -- Subcommand handlers ------------------------------------------------------


def _cmd_status() -> int:
    """Print current telemetry state to stdout.

    Read-only — does not modify configuration.
    """
    from src.telemetry.config import get_config_path, is_telemetry_enabled

    enabled = is_telemetry_enabled()
    config_path = get_config_path()
    uuid_path = get_telemetry_id_path()
    outbound_path = get_outbound_log_path()

    outbound_size = outbound_path.stat().st_size if outbound_path.exists() else 0

    print(f"Telemetry: {'enabled' if enabled else 'disabled'}")
    print(f"Config: {config_path}")
    print(
        f"Anonymous UUID: {uuid_path} "
        f"({'present' if uuid_path.exists() else 'absent'})"
    )
    print(f"Local outbound log: {outbound_path} ({outbound_size} bytes)")
    print()
    print("To disable: marcus telemetry disable")
    print("To purge identity:  marcus telemetry purge")
    print(
        "Full disclosure: "
        "https://github.com/lwgray/marcus/blob/main/docs/telemetry.md"
    )
    return 0


def _cmd_enable() -> int:
    """Set ``telemetry.enabled: true`` in the config file."""
    from src.telemetry.config import get_config_path, set_telemetry_enabled

    set_telemetry_enabled(True)
    print("Telemetry enabled.")
    print(f"Config: {get_config_path()}")
    return 0


def _cmd_disable() -> int:
    """Set ``telemetry.enabled: false`` in the config file."""
    from src.telemetry.config import get_config_path, set_telemetry_enabled

    set_telemetry_enabled(False)
    print("Telemetry disabled.")
    print(f"Config: {get_config_path()}")
    print("Existing anonymous UUID kept. To also delete it, run:")
    print("  marcus telemetry purge")
    return 0


def _cmd_purge() -> int:
    """Disable telemetry, delete UUID, outbound log, and notice marker.

    Idempotent — running purge twice succeeds cleanly.  Uses
    ``Path.unlink(missing_ok=True)`` so absent files do not raise.
    """
    from src.telemetry.client import get_marker_path
    from src.telemetry.config import set_telemetry_enabled

    set_telemetry_enabled(False)

    removed: List[str] = []
    for path in (
        get_telemetry_id_path(),
        get_outbound_log_path(),
        get_marker_path(),
    ):
        existed = path.exists()
        path.unlink(missing_ok=True)
        if existed:
            removed.append(str(path))

    print("Telemetry disabled and local identity purged.")
    if removed:
        print("Removed:")
        for entry in removed:
            print(f"  {entry}")
    else:
        print("No local identity files existed; nothing to remove.")
    return 0
