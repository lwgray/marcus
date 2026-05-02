r"""Subtask-to-agent distribution analysis.

Answers: for a given project, when a parent task has N subtasks, how many
DISTINCT agents touched those subtasks?  If the answer is "1 per parent" the
codebase has implicit stickiness.  If it's "N", subtasks are fanning out as
``find_next_available_subtask`` claims to.

Reads parents + assignment data from ``data/kanban.db`` (SQLite kanban
backend) and subtasks from ``data/marcus_state/subtasks.json``
(SubtaskManager's JSON state file).  Subtasks do NOT live in kanban.db —
they're transient SubtaskManager state migrated into ``project_tasks`` at
request time.  Run with no args to analyze the most recently updated
project; pass ``--project <name>`` to target a specific one or ``--list``
to enumerate recent projects.

Examples
--------
.. code-block:: bash

    # Analyze most recent project
    python dev-tools/experiments/analysis/analyze_subtask_agent_distribution.py

    # Analyze snake-game-v37 specifically
    python dev-tools/experiments/analysis/analyze_subtask_agent_distribution.py \\
        --project snake-game-v37

    # List candidate projects
    python dev-tools/experiments/analysis/analyze_subtask_agent_distribution.py --list

Background
----------
Filed during the v0.3.6.post1 release window (2026-04-29).  User
hypothesized that "single parent's subtasks are kept with a single agent"
based on visual DAG inspection.  Code in
``src/marcus_mcp/coordinator/subtask_assignment.py:144-148`` claims to
fan out across parents.  This script measures the actual behavior in
the kanban data.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_DB = Path(__file__).resolve().parents[3] / "data" / "kanban.db"
DEFAULT_SUBTASKS_JSON = (
    Path(__file__).resolve().parents[3] / "data" / "marcus_state" / "subtasks.json"
)


def list_recent_projects(con: sqlite3.Connection, limit: int = 15) -> None:
    """Print recent projects sorted by most-recently-updated task."""
    cur = con.execute(
        """
        SELECT project_name, project_id,
               COUNT(*)                      AS task_count,
               SUM(CASE WHEN is_subtask THEN 1 ELSE 0 END) AS subtask_count,
               MAX(updated_at)               AS last_update
          FROM tasks
         WHERE project_name IS NOT NULL AND project_name != ''
         GROUP BY project_id
         ORDER BY last_update DESC
         LIMIT ?
        """,
        (limit,),
    )
    print(f"{'project_name':<32} {'tasks':>6} {'subtasks':>9}  last_update")
    print("-" * 80)
    for name, _pid, n, sub, last in cur:
        print(f"{name[:32]:<32} {n:>6} {sub:>9}  {last}")


def load_subtasks_json(
    path: Path, project_parent_ids: set[str]
) -> Dict[str, List[Dict[str, Any]]]:
    """Load subtasks from SubtaskManager's JSON state file.

    Returns a ``{parent_task_id: [subtask_dict, ...]}`` mapping, scoped to
    parent ids that belong to the project under analysis.

    Schema of ``subtasks.json``:

    .. code-block:: json

        {
          "subtasks": {"<subtask_id>": {<fields>}, ...},
          "parent_to_subtasks": {"<parent_id>": ["<subtask_id>", ...], ...},
          "metadata": {...}
        }
    """
    if not path.exists():
        return {}
    with path.open() as f:
        data = json.load(f)
    all_subs = data.get("subtasks", {})
    parent_map = data.get("parent_to_subtasks", {})
    out: Dict[str, List[Dict[str, Any]]] = {}
    for pid in project_parent_ids:
        sub_ids = parent_map.get(pid, [])
        out[pid] = [all_subs[sid] for sid in sub_ids if sid in all_subs]
    return out


def find_most_recent_project(
    con: sqlite3.Connection,
) -> Optional[Tuple[str, str]]:
    """Return most-recently-updated project from the kanban DB.

    Returns ``(project_name, project_id)`` tuple, or None if no projects found.
    """
    cur = con.execute("""
        SELECT project_name, project_id, MAX(updated_at) AS last_update
          FROM tasks
         WHERE project_name IS NOT NULL AND project_name != ''
         GROUP BY project_id
         ORDER BY last_update DESC
         LIMIT 1
        """)
    row = cur.fetchone()
    return (row[0], row[1]) if row else None


def find_project_by_name(
    con: sqlite3.Connection, name: str
) -> Optional[Tuple[str, str]]:
    """Return the most recent project matching ``name``.

    Returns ``(project_name, project_id)`` keyed on latest updated_at,
    or None if not found.
    """
    cur = con.execute(
        """
        SELECT project_name, project_id, MAX(updated_at)
          FROM tasks
         WHERE project_name = ?
         GROUP BY project_id
         ORDER BY MAX(updated_at) DESC
         LIMIT 1
        """,
        (name,),
    )
    row = cur.fetchone()
    return (row[0], row[1]) if row else None


def load_project_tasks(
    con: sqlite3.Connection, project_id: str
) -> List[Dict[str, Any]]:
    """Load all tasks (parents + subtasks) for a project."""
    cur = con.execute(
        """
        SELECT id, name, status, assigned_to, is_subtask, parent_task_id,
               subtask_index, completed_at, source_type
          FROM tasks
         WHERE project_id = ?
         ORDER BY parent_task_id, subtask_index
        """,
        (project_id,),
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def analyze(
    project_name: str,
    project_id: str,
    tasks: List[Dict[str, Any]],
    subtasks_from_json: Dict[str, List[Dict[str, Any]]],
) -> None:
    """Print subtask-to-agent distribution for this project.

    Parents come from the kanban DB.  Subtasks come from
    ``subtasks.json`` because SubtaskManager doesn't persist subtasks to
    the kanban DB (they're loaded into ``project_tasks`` at request time
    via migrate_to_unified_storage).
    """
    parents = {t["id"]: t for t in tasks if not t["is_subtask"]}
    subtasks_by_parent: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    # Prefer kanban-backed subtasks (post-migration); fall back to JSON.
    for t in tasks:
        if t["is_subtask"] and t["parent_task_id"]:
            subtasks_by_parent[t["parent_task_id"]].append(t)
    for pid, subs in subtasks_from_json.items():
        if pid not in subtasks_by_parent:  # only add if kanban didn't have it
            for s in subs:
                # Normalize JSON shape into the same dict shape kanban uses.
                subtasks_by_parent[pid].append(
                    {
                        "id": s.get("id", ""),
                        "name": s.get("name", ""),
                        "status": s.get("status", "todo"),
                        "assigned_to": s.get("assigned_to"),
                        "is_subtask": True,
                        "parent_task_id": pid,
                        "subtask_index": s.get("order", 0),
                    }
                )

    if not subtasks_by_parent:
        print(f"\nProject '{project_name}' ({project_id[:8]}) has no subtasks.")
        print("Either subtasks weren't enabled for this run, or the project")
        print("uses parent-only task assignment.")
        return

    print(f"\nProject: {project_name}  ({project_id})")
    print(
        f"  {len(parents)} parent task(s), "
        f"{sum(len(s) for s in subtasks_by_parent.values())} subtask(s) "
        f"across {len(subtasks_by_parent)} parent(s) with subtasks"
    )
    print()

    # Per-parent distribution
    print(f"{'parent':<40} {'#sub':>5} {'#agents':>8}  agents")
    print("-" * 90)

    one_agent_count = 0
    multi_agent_count = 0
    unassigned_count = 0

    for parent_id, subs in sorted(
        subtasks_by_parent.items(),
        key=lambda kv: parents.get(kv[0], {}).get("name", ""),
    ):
        parent_name = parents.get(parent_id, {}).get(
            "name", f"<missing:{parent_id[:8]}>"
        )
        agents_assigned = [s["assigned_to"] for s in subs if s["assigned_to"]]
        unique_agents = sorted(set(agents_assigned))

        n_sub = len(subs)
        n_agents = len(unique_agents)

        if not agents_assigned:
            unassigned_count += 1
            agent_str = "(none assigned)"
        elif n_agents == 1:
            one_agent_count += 1
            agent_str = unique_agents[0]
        else:
            multi_agent_count += 1
            agent_str = ", ".join(unique_agents)

        print(f"{parent_name[:40]:<40} {n_sub:>5} {n_agents:>8}  {agent_str}")

    print()
    print("Distribution summary:")
    print(f"  Parents with subtasks worked by 1 agent:    {one_agent_count}")
    print(f"  Parents with subtasks worked by ≥2 agents:  {multi_agent_count}")
    print(f"  Parents with no agents assigned (TODO):     {unassigned_count}")
    print()

    # Verdict
    total_with_assignments = one_agent_count + multi_agent_count
    if total_with_assignments == 0:
        print("VERDICT: no completed assignments to analyze.  Run an experiment first.")
        return
    pct_single = 100.0 * one_agent_count / total_with_assignments
    if pct_single >= 80:
        print(
            f"VERDICT: {pct_single:.0f}% of parents had subtasks"
            " worked by exactly 1 agent."
        )
        print("  → Either the user's hypothesis (sticky assignment) is real,")
        print("    OR sibling subtasks have sequential dependencies that effectively")
        print(
            "    serialize them and only one agent happens to be free at handoff time."
        )
        print("  → Investigate: do sibling subtasks have inter-dependencies?")
    elif pct_single <= 30:
        print(f"VERDICT: {pct_single:.0f}% of parents had subtasks worked by 1 agent.")
        print("  → Subtasks DO fan out across agents as the code claims.")
        print(
            "  → No stickiness; user's perception may be projection from small samples."
        )
    else:
        print(
            f"VERDICT: mixed — {pct_single:.0f}% single-agent, "
            f"{100-pct_single:.0f}% multi-agent."
        )
        print("  → Behavior depends on subtask structure / agent count / timing.")
        print("  → Worth filing as an issue with this data attached.")


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Analyze subtask-to-agent distribution for a Marcus experiment. "
            "Reads data/kanban.db."
        )
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"path to kanban.db (default: {DEFAULT_DB})",
    )
    parser.add_argument(
        "--subtasks-json",
        type=Path,
        default=DEFAULT_SUBTASKS_JSON,
        help=(
            "path to SubtaskManager state JSON " f"(default: {DEFAULT_SUBTASKS_JSON})"
        ),
    )
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="project name to analyze (default: most recently updated project)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list recent projects and exit",
    )
    args = parser.parse_args()

    if not args.db.exists():
        print(f"Error: {args.db} not found.", file=sys.stderr)
        return 1

    con = sqlite3.connect(str(args.db))

    if args.list:
        list_recent_projects(con)
        return 0

    if args.project:
        proj = find_project_by_name(con, args.project)
        if not proj:
            print(f"Error: no project named '{args.project}'.", file=sys.stderr)
            print("Try --list to see candidates.", file=sys.stderr)
            return 1
    else:
        proj = find_most_recent_project(con)
        if not proj:
            print("Error: no projects with subtasks found.", file=sys.stderr)
            return 1

    project_name, project_id = proj
    tasks = load_project_tasks(con, project_id)
    parent_ids = {t["id"] for t in tasks if not t["is_subtask"]}
    subtasks_from_json = load_subtasks_json(args.subtasks_json, parent_ids)
    analyze(project_name, project_id, tasks, subtasks_from_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
