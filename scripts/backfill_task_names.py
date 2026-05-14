#!/usr/bin/env python3
"""
One-shot backfill of ``task_names`` from ``marcus.db::task_metadata``.

Marcus's `marcus.db` (collection ``task_metadata`` inside the
key-value ``persistence`` table) is the source of truth for task
names. The cost-tracking dashboard reads from `costs.db::task_names`.
After Marcus #530 added the snapshot path, new tasks land in both
DBs at creation time. Historical tasks created before #530 only
exist in `marcus.db`; the dashboard renders their opaque hex IDs.

This script reads every row in the ``task_metadata`` collection,
extracts ``(task_id, name)``, and calls
:meth:`CostStore.record_task_name` for each. The store's UPSERT
makes the operation idempotent — re-running is safe and a no-op
when nothing has changed.

Usage
-----
.. code-block:: console

    $ python scripts/backfill_task_names.py
    Backfilled 287 task names from /Users/.../data/marcus.db
    Skipped 5 rows (malformed JSON or missing name)

Pass ``--marcus-db PATH`` to point at a non-default Marcus DB.
Pass ``--costs-db PATH`` to override the cost-store path (defaults
to ``~/.marcus/costs.db``).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Tuple

# Allow running directly from the repo root without installing.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from src.cost_tracking.cost_store import CostStore  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--marcus-db",
        type=Path,
        default=_REPO_ROOT / "data" / "marcus.db",
        help="Path to Marcus's marcus.db (default: ./data/marcus.db).",
    )
    parser.add_argument(
        "--costs-db",
        type=Path,
        default=Path.home() / ".marcus" / "costs.db",
        help="Path to costs.db (default: ~/.marcus/costs.db).",
    )
    return parser.parse_args()


def backfill(marcus_db: Path, costs_db: Path) -> Tuple[int, int, int]:
    """Copy ``(task_id, name)`` from ``marcus.db`` into ``costs.db``.

    Two passes:

    1. **Parent tasks.** Read every row in ``marcus.db::task_metadata``
       and snapshot its ``(task_id, name)`` into ``task_names``.
    2. **Subtasks.** Marcus decomposes some tasks into subtasks with
       IDs like ``<parent_hex>_sub_1`` / ``_sub_2``. Those IDs land in
       ``token_events.task_id`` but never appear in ``task_metadata``
       (only parents do). Walk every distinct ``_sub_N`` ID in
       ``token_events``, look up the parent's snapshotted name, and
       write a derived label (``"<parent name> — subtask N"``) so the
       dashboard surfaces something readable instead of a hex tail.

    Returns
    -------
    (parents, subtasks, skipped) : tuple of int
        Counts for parent-task names recorded, subtask-derived names
        recorded, and rows skipped (malformed JSON, missing name).
    """
    import sqlite3

    if not marcus_db.exists():
        raise FileNotFoundError(f"marcus.db not found at {marcus_db}")

    store = CostStore(db_path=costs_db)

    src = sqlite3.connect(str(marcus_db))
    rows = src.execute(
        "SELECT key, data FROM persistence WHERE collection = 'task_metadata'"
    ).fetchall()
    src.close()

    # Pass 1: parent-task names from marcus.db.
    parents = 0
    skipped = 0
    for key, raw in rows:
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, ValueError, TypeError):
            skipped += 1
            continue

        if not isinstance(parsed, dict):
            skipped += 1
            continue

        task_id = parsed.get("task_id") or key
        name = parsed.get("name")
        if not isinstance(task_id, str) or not isinstance(name, str) or not name:
            skipped += 1
            continue

        store.record_task_name(task_id, name)
        parents += 1

    # Pass 2: subtask derived names. Look for ``_sub_N`` task_ids that
    # appear in token_events but have no entry in task_names yet, and
    # synthesize a label from the parent's snapshotted name.
    subtasks = 0
    sub_rows = store.conn.execute("""
        SELECT DISTINCT te.task_id
        FROM token_events te
        LEFT JOIN task_names tn USING (task_id)
        WHERE te.task_id IS NOT NULL
          AND tn.task_id IS NULL
          AND instr(te.task_id, '_sub_') > 0
        """).fetchall()
    for (sub_id,) in sub_rows:
        suffix_at = sub_id.find("_sub_")
        parent_id = sub_id[:suffix_at]
        suffix = sub_id[suffix_at + len("_sub_") :]
        parent_name = store.get_task_name(parent_id)
        if not parent_name:
            continue
        store.record_task_name(sub_id, f"{parent_name} — subtask {suffix}")
        subtasks += 1

    return parents, subtasks, skipped


def main() -> int:
    """Parse CLI args, run the backfill, and print a short summary."""
    args = _parse_args()
    parents, subtasks, skipped = backfill(args.marcus_db, args.costs_db)
    print(f"Backfilled {parents} parent task names from {args.marcus_db}")
    if subtasks > 0:
        print(f"Backfilled {subtasks} subtask names derived from parents")
    if skipped > 0:
        print(f"Skipped {skipped} rows (malformed JSON or missing name)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
