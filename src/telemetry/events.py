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
    "fire_experiment_completed",
    "fire_experiment_started",
    "fire_project_created",
]


logger = logging.getLogger(__name__)


#: Runner default used by both ``session_started`` and ``experiment_started``.
#: Kept in sync with the value in ``src/marcus_mcp/server.py``.
_RUNNER_DEFAULT: str = "mcp_direct"


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
