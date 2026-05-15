"""Marcus telemetry event helpers (Marcus #416, Stage 2 of #9).

Each public function in this module corresponds to one event in the
schema documented at ``docs/telemetry.md``.  The function gathers
properties (with NO PII / source code / secrets), then forwards to
:class:`src.telemetry.client.TelemetryClient.capture`.

Every helper is wrapped in a top-level ``try/except Exception``
that swallows errors at debug log level — telemetry must never
raise into the MCP tool path.

These helpers live in the telemetry package (not the tool modules)
so the privacy contract is co-located with the disclosure document.
A single grep over ``src/telemetry/events.py`` answers "what do we
actually ship?" — the contract surface is one file.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from src.telemetry import get_telemetry_client

__all__ = [
    "classify_blocker_type",
    "extract_task_phase",
    "fire_experiment_completed",
    "fire_experiment_started",
    "fire_project_created",
    "fire_task_blocked",
    "fire_task_completed",
]


logger = logging.getLogger(__name__)


#: Runner default used by both ``session_started`` and ``experiment_started``.
#: Kept in sync with the value in ``src/marcus_mcp/server.py``.
_RUNNER_DEFAULT: str = "mcp_direct"


#: Fixed task-phase taxonomy.  Tasks carry labels (free-form strings);
#: we map each label to one of these buckets and ship only the bucket
#: label.  Unknown labels collapse to ``"unknown"``.
_TASK_PHASE_BUCKETS: frozenset[str] = frozenset(
    {
        "backend",
        "frontend",
        "design",
        "integration",
        "testing",
        "deployment",
        "documentation",
        "foundation",
    }
)


#: Fixed blocker-type taxonomy.  See :func:`classify_blocker_type`.
#: The keyword tuples are checked in order — first match wins.  Adjust
#: the order if a tighter prefix should win over a looser keyword (e.g.
#: ``timeout`` is more specific than ``timed out``).
_BLOCKER_TYPE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("dependency_not_ready", ("depend", "blocked by", "waiting for")),
    ("timeout", ("timeout", "timed out")),
    ("missing_credential", ("api key", "api_key", "credential", "auth")),
    ("tool_error", ("tool", "command failed", "permission denied", "exit code")),
    ("ambiguous_requirement", ("unclear", "ambiguous", "don't know", "do not know")),
    ("async_failure", ("async", "race condition")),
)


# -- project_created ----------------------------------------------------------


def fire_project_created(
    result: Dict[str, Any],
    options: Optional[Dict[str, Any]],
    actual_decomposer: Optional[str],
) -> None:
    """Emit the ``project_created`` event after a successful ``create_project``.

    Best-effort: all errors are swallowed at debug-log level.  Does
    NOT fire when ``result["success"]`` is falsy — failed creates
    are not creates.

    Parameters
    ----------
    result : dict
        The ``create_project`` return value.  Reads ``success`` and
        ``tasks_created`` only.
    options : dict, optional
        The ``options`` arg passed to ``create_project``.  Reads
        ``complexity`` only; never reads keys that could carry
        secrets (``anthropic_api_key``, etc.).
    actual_decomposer : str, optional
        The decomposer strategy that actually ran (may differ from
        the requested one — contract_first can fall back to
        feature_based under certain conditions).
    """
    try:
        if not result or not result.get("success"):
            return

        options = options or {}
        properties = {
            "task_count": result.get("tasks_created"),
            "complexity_mode": options.get("complexity", "standard"),
            "decomposer_strategy": actual_decomposer or "unknown",
            # Populated by Task #7 once the planner output is
            # extended to emit these.  Honest placeholder until then.
            "structural_category": "unknown",
            "domain": "unknown",
        }
        get_telemetry_client().capture("project_created", properties)
    except Exception as exc:  # noqa: BLE001 - never crash the tool path
        logger.debug("fire_project_created failed: %s", exc)


# -- experiment_started -------------------------------------------------------


def fire_experiment_started(agent_count: int) -> None:
    """Emit the ``experiment_started`` event after ``start_experiment`` succeeds.

    Best-effort: all errors are swallowed.

    Parameters
    ----------
    agent_count : int
        Number of agents registered with the experiment at start time.
        May be 0 if the experiment starts before any agents register —
        agents typically register after.
    """
    try:
        properties = {
            "agent_count": agent_count,
            "runner": os.environ.get("MARCUS_RUNNER", _RUNNER_DEFAULT),
        }
        get_telemetry_client().capture("experiment_started", properties)
    except Exception as exc:  # noqa: BLE001
        logger.debug("fire_experiment_started failed: %s", exc)


# -- experiment_completed -----------------------------------------------------


def fire_experiment_completed(result: Dict[str, Any]) -> None:
    """Emit the ``experiment_completed`` event after ``end_experiment``.

    Reads aggregate metrics from ``result['final_metrics']``.  Best-
    effort; swallows all errors.  Does NOT fire when ``result['success']``
    is falsy.

    Parameters
    ----------
    result : dict
        The ``end_experiment`` return value.  Expects:

        - ``success``  : bool
        - ``final_metrics`` : dict with the following sub-keys
          (all optional, defaulted to 0 when absent):

          - ``total_tasks`` : int
          - ``total_task_completions`` : int
          - ``total_blockers`` : int
          - ``total_registered_agents`` : int
          - ``duration_seconds`` : float
    """
    try:
        if not result or not result.get("success"):
            return

        metrics = result.get("final_metrics") or {}
        total_tasks = int(metrics.get("total_tasks") or 0)
        completed = int(metrics.get("total_task_completions") or 0)
        blockers = int(metrics.get("total_blockers") or 0)
        agents = int(metrics.get("total_registered_agents") or 0)
        duration_s = float(metrics.get("duration_seconds") or 0)

        completion_pct = (completed / total_tasks * 100) if total_tasks else 0
        blocker_rate = (blockers / total_tasks) if total_tasks else 0

        properties = {
            "total_tasks": total_tasks,
            "completion_pct": round(completion_pct, 2),
            "duration_minutes": int(duration_s // 60),
            "agent_count": agents,
            "blocker_rate": round(blocker_rate, 4),
        }
        get_telemetry_client().capture("experiment_completed", properties)
    except Exception as exc:  # noqa: BLE001
        logger.debug("fire_experiment_completed failed: %s", exc)


# -- task_completed -----------------------------------------------------------


def extract_task_phase(labels: Optional[list]) -> str:
    """Map a task's labels to one of the fixed :data:`_TASK_PHASE_BUCKETS`.

    First matching label wins.  Comparison is case-insensitive.
    Returns ``"unknown"`` if no label is in the taxonomy.

    Parameters
    ----------
    labels : list of str, optional
        The ``task.labels`` list.  May be ``None`` or empty.

    Returns
    -------
    str
        One of the bucket names, or ``"unknown"``.
    """
    if not labels:
        return "unknown"
    for label in labels:
        if not isinstance(label, str):
            continue
        normalized = label.lower()
        if normalized in _TASK_PHASE_BUCKETS:
            return normalized
    return "unknown"


def fire_task_completed(task: Any) -> None:
    """Emit the ``task_completed`` event when a task moves to DONE.

    Reads only the task's ``labels`` field for the phase bucket.
    Task ``name``, ``description``, and any other free-text fields
    are NOT touched — they never leave the machine.

    Best-effort.  Errors swallowed at debug-log level.

    Parameters
    ----------
    task : Task-like
        Marcus Task object.  Must expose ``labels``.  Other
        attributes (``id``, ``name``) are intentionally ignored.

    Notes
    -----
    ``had_blocker`` and ``duration_minutes`` are part of the
    ``docs/telemetry.md`` § task_completed schema but their
    capture sites do not exist yet (they need the
    ``task_lifecycle`` table from Sub-issue A #547 and the
    ``blockers`` table from Sub-issue E #551).  We ship ``None``
    for them today — honest placeholder; populated in v0.3.8+.
    """
    try:
        labels = getattr(task, "labels", None) if task is not None else None
        properties = {
            "task_phase": extract_task_phase(labels),
            # Populated in v0.3.8 once Sub-issues A (#547) and
            # E (#551) land — task_lifecycle table + blockers table.
            "had_blocker": None,
            "duration_minutes": None,
        }
        get_telemetry_client().capture("task_completed", properties)
    except Exception as exc:  # noqa: BLE001
        logger.debug("fire_task_completed failed: %s", exc)


# -- task_blocked -------------------------------------------------------------


def classify_blocker_type(description: str) -> str:
    """Bucket a free-text blocker description into a fixed type.

    Local keyword bucketing — the description text itself never
    leaves the machine.  Only the returned bucket label ships in
    the ``task_blocked`` event.  See ``docs/telemetry.md`` §
    task_blocked: "The blocker type is shipped. The blocker
    message is never shipped."

    Parameters
    ----------
    description : str
        Free-text blocker description from ``report_blocker``.
        May be empty or ``None``.

    Returns
    -------
    str
        One of: ``dependency_not_ready``, ``timeout``,
        ``missing_credential``, ``tool_error``,
        ``ambiguous_requirement``, ``async_failure``, ``unknown``.

    Notes
    -----
    Keyword order in :data:`_BLOCKER_TYPE_KEYWORDS` is load-bearing.
    More specific buckets should appear before more general ones
    so the first match is the most-precise classification.
    """
    text = (description or "").lower()
    if not text:
        return "unknown"
    for bucket, keywords in _BLOCKER_TYPE_KEYWORDS:
        if any(k in text for k in keywords):
            return bucket
    return "unknown"


def fire_task_blocked(severity: str, blocker_description: str) -> None:
    """Emit the ``task_blocked`` event.

    Ships ``blocker_type`` (keyword-classified from the description)
    and ``severity`` (passthrough).  Does NOT ship the description
    itself.

    Best-effort.  Errors swallowed at debug-log level.

    Parameters
    ----------
    severity : str
        ``"low"``, ``"medium"``, or ``"high"`` from ``report_blocker``.
    blocker_description : str
        The free-text description.  Used only by
        :func:`classify_blocker_type` to derive a bucket label; the
        text itself is never put on the wire.
    """
    try:
        properties = {
            "blocker_type": classify_blocker_type(blocker_description),
            "severity": severity,
        }
        get_telemetry_client().capture("task_blocked", properties)
    except Exception as exc:  # noqa: BLE001
        logger.debug("fire_task_blocked failed: %s", exc)
