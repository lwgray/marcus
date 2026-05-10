"""
MCP tools for the Marcus cost tracking dashboard (#409).

Exposes :func:`get_cost_summary` so agents and external clients (notably
the Cato dashboard) can query the cost store without direct DB access.

The tool dispatches to :class:`src.cost_tracking.cost_aggregator.CostAggregator`
and returns dicts shaped like the API responses documented in #409.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.types import Tool

from src.cost_tracking.cost_aggregator import CostAggregator


async def get_cost_summary(
    experiment_id: Optional[str] = None,
    project_id: Optional[str] = None,
    state: Any = None,
) -> Dict[str, Any]:
    """Return a cost summary keyed by experiment or project.

    Parameters
    ----------
    experiment_id : str, optional
        Marcus experiment ID. When provided, returns a full per-experiment
        breakdown (``summary`` + ``by_role`` + ``by_agent`` + ``by_task``
        + ``by_operation`` + ``by_model``).
    project_id : str, optional
        Marcus project ID. When provided, returns project totals plus a
        list of experiment summaries belonging to the project. Used by
        Cato when drilling from a project view into its runs.
    state : Any
        Marcus server state. Must expose ``cost_store`` (set up at server
        init, see :class:`src.marcus_mcp.server.MarcusServer.__init__`).

    Returns
    -------
    dict
        Either the experiment-summary shape (when ``experiment_id`` is
        passed), the project-rollup shape (when ``project_id`` is passed),
        or an error envelope ``{success: False, error: ...}`` if the
        caller didn't provide either or the store is unavailable.

    Notes
    -----
    Read-only. Never raises; argument and lookup errors are returned as
    ``{success: False, error: ...}`` dicts so MCP clients get a friendly
    payload rather than a stack trace.
    """
    if experiment_id is None and project_id is None:
        return {
            "success": False,
            "error": "Provide either experiment_id or project_id.",
        }

    cost_store = getattr(state, "cost_store", None)
    if cost_store is None:
        return {
            "success": False,
            "error": "Cost store not available on server state.",
        }

    aggregator = CostAggregator(store=cost_store)

    if experiment_id is not None:
        summary = aggregator.experiment_summary(experiment_id)
        if summary is None:
            return {
                "success": False,
                "error": f"Experiment '{experiment_id}' not found.",
            }
        return summary

    # project_id was provided
    assert project_id is not None  # for mypy
    return {
        "project_id": project_id,
        "totals": aggregator.project_totals(project_id),
        "experiments": aggregator.list_experiments(project_id=project_id),
    }


# Tool definition registered in handlers.py.
COST_SUMMARY_TOOL = Tool(
    name="get_cost_summary",
    description=(
        "Return per-experiment or per-project token + cost breakdown from "
        "the Marcus cost store. Pass experiment_id for a full drill-in "
        "(summary, by_role, by_agent, by_task, by_operation, by_model). "
        "Pass project_id for project totals plus a list of experiment "
        "summaries. Read-only."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "experiment_id": {
                "type": "string",
                "description": (
                    "Marcus experiment ID. Returns a full per-experiment "
                    "breakdown if matched."
                ),
            },
            "project_id": {
                "type": "string",
                "description": (
                    "Marcus project ID. Returns project totals plus a list "
                    "of experiment summaries belonging to the project."
                ),
            },
        },
    },
)
