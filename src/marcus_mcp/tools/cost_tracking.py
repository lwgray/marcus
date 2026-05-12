"""
MCP tools for the Marcus cost tracking dashboard (#409).

Exposes :func:`get_cost_summary` so agents and external clients (notably
the Cato dashboard) can query the cost store without direct DB access.

The tool dispatches to :class:`src.cost_tracking.cost_aggregator.CostAggregator`
and returns dicts shaped like the API responses documented in #409.

Terminology
-----------
This module talks about **runs** (one project traversal end-to-end),
not "experiments." The legacy name clashed with MLflow's unrelated
experiment concept (Simon ``7ed3074d`` for the rationale).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.types import Tool

from src.cost_tracking.cost_aggregator import CostAggregator


async def get_cost_summary(
    run_id: Optional[str] = None,
    project_id: Optional[str] = None,
    state: Any = None,
) -> Dict[str, Any]:
    """Return a cost summary keyed by run or project.

    Parameters
    ----------
    run_id : str, optional
        Run identifier. When provided, returns a full per-run
        breakdown (``summary`` + ``by_role`` + ``by_agent`` +
        ``by_task`` + ``by_operation`` + ``by_model``).
    project_id : str, optional
        Marcus project ID. When provided, returns project totals
        plus a list of run summaries belonging to the project. Used
        by Cato when drilling from a project view into its runs.
    state : Any
        Marcus server state. Must expose ``cost_store`` (set up at
        server init, see
        :class:`src.marcus_mcp.server.MarcusServer.__init__`).

    Returns
    -------
    dict
        Either the run-summary shape (when ``run_id`` is passed),
        the project-rollup shape (when ``project_id`` is passed),
        or an error envelope ``{success: False, error: ...}`` if
        the caller didn't provide either or the store is
        unavailable.

    Notes
    -----
    Read-only. Never raises; argument and lookup errors are returned
    as ``{success: False, error: ...}`` dicts so MCP clients get a
    friendly payload rather than a stack trace.
    """
    if run_id is None and project_id is None:
        return {
            "success": False,
            "error": "Provide either run_id or project_id.",
        }

    cost_store = getattr(state, "cost_store", None)
    if cost_store is None:
        return {
            "success": False,
            "error": "Cost store not available on server state.",
        }

    aggregator = CostAggregator(store=cost_store)

    if run_id is not None:
        summary = aggregator.run_summary(run_id)
        if summary is None:
            return {
                "success": False,
                "error": f"Run '{run_id}' not found.",
            }
        return summary

    # project_id was provided
    assert project_id is not None  # for mypy
    return {
        "project_id": project_id,
        "totals": aggregator.project_totals(project_id),
        "runs": aggregator.list_runs(project_id=project_id),
    }


# Tool definition registered in handlers.py.
COST_SUMMARY_TOOL = Tool(
    name="get_cost_summary",
    description=(
        "Return per-run or per-project token + cost breakdown from "
        "the Marcus cost store. Pass run_id for a full drill-in "
        "(summary, by_role, by_agent, by_task, by_operation, "
        "by_model). Pass project_id for project totals plus a list "
        "of run summaries. Read-only."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "run_id": {
                "type": "string",
                "description": (
                    "Run identifier. Returns a full per-run "
                    "breakdown if matched. Renamed from "
                    "experiment_id; the legacy name clashed with "
                    "MLflow's separate experiment concept."
                ),
            },
            "project_id": {
                "type": "string",
                "description": (
                    "Marcus project ID. Returns project totals plus "
                    "a list of run summaries belonging to the "
                    "project."
                ),
            },
        },
    },
)
