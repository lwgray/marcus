"""
Read-only aggregator over the Marcus cost store.

Provides the query helpers that power the Cato ``/api/cost/*`` endpoints
described in #409. Aggregator never writes; it only reads from
:class:`src.cost_tracking.cost_store.CostStore` and returns dicts shaped
like the documented API responses, so the Cato backend can pass them
through with minimal transformation.

All methods are synchronous (sqlite3 is sync). The aggregator is safe to
share across threads because it relies on the underlying connection's
WAL mode for concurrent readers.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from src.cost_tracking.cost_store import CostStore


class CostAggregator:
    """Read-only query layer over a :class:`CostStore`.

    Parameters
    ----------
    store : CostStore
        The backing store. Aggregator does not own the connection; the
        caller is responsible for the store's lifecycle.
    """

    def __init__(self, store: CostStore) -> None:
        self.store = store
        # Allow row access by column name for convenience in helpers.
        self.store.conn.row_factory = sqlite3.Row

    # -- helpers -----------------------------------------------------------

    def _rows(self, sql: str, params: tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        """Run a query and return rows as plain dicts."""
        cur = self.store.conn.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]

    def _row(self, sql: str, params: tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
        """Run a query that returns at most one row."""
        cur = self.store.conn.execute(sql, params)
        r = cur.fetchone()
        return dict(r) if r is not None else None

    # -- public queries ---------------------------------------------------

    def list_experiments(
        self,
        *,
        project_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List experiments with token + cost totals attached.

        Parameters
        ----------
        project_id : str, optional
            Restrict to one project.
        limit : int, default 100
            Cap result set.

        Returns
        -------
        list of dict
            Each row carries experiment metadata plus ``total_tokens``
            and ``total_cost_usd`` aggregated from ``v_event_cost_inclusive``
            (LEFT-joined to ``model_prices``) so events whose model has no
            seeded price still count toward token totals.
        """
        sql = """
            SELECT e.*,
                   COALESCE(SUM(c.total_tokens), 0) AS total_tokens,
                   COALESCE(SUM(c.cost_usd), 0)     AS total_cost_usd
            FROM experiments e
            LEFT JOIN v_event_cost_inclusive c USING (experiment_id)
            WHERE (? IS NULL OR e.project_id = ?)
            GROUP BY e.experiment_id
            ORDER BY e.started_at DESC
            LIMIT ?
        """
        return self._rows(sql, (project_id, project_id, limit))

    def experiment_summary(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Full per-experiment summary used by Cato's drill-in view.

        Returns
        -------
        dict or None
            Shaped like the example response in #409 (``summary``,
            ``by_role``, ``by_agent``, ``by_task``, ``by_operation``,
            ``by_model``). Returns ``None`` if the experiment does not
            exist.
        """
        meta = self._row(
            "SELECT * FROM experiments WHERE experiment_id = ?",
            (experiment_id,),
        )
        if meta is None:
            return None

        totals = (
            self._row(
                """
            SELECT
                COUNT(*)                                    AS total_events,
                COALESCE(SUM(total_tokens), 0)              AS total_tokens,
                COALESCE(SUM(input_tokens), 0)              AS input_tokens,
                COALESCE(SUM(cache_creation_tokens), 0)     AS cache_creation_tokens,
                COALESCE(SUM(cache_read_tokens), 0)         AS cache_read_tokens,
                COALESCE(SUM(output_tokens), 0)             AS output_tokens,
                COALESCE(SUM(cost_usd), 0)                  AS total_cost_usd
            FROM v_event_cost_inclusive
            WHERE experiment_id = ?
            """,
                (experiment_id,),
            )
            or {}
        )

        cacheable = (
            (totals.get("input_tokens") or 0)
            + (totals.get("cache_creation_tokens") or 0)
            + (totals.get("cache_read_tokens") or 0)
        )
        hit_rate = (
            (totals.get("cache_read_tokens") or 0) / cacheable if cacheable > 0 else 0.0
        )
        totals["cache_hit_rate"] = hit_rate

        by_role = self._rows(
            """
            SELECT agent_role AS role,
                   COUNT(*)                          AS events,
                   COALESCE(SUM(total_tokens), 0)    AS tokens,
                   COALESCE(SUM(cost_usd), 0)        AS cost_usd
            FROM v_event_cost_inclusive
            WHERE experiment_id = ?
            GROUP BY agent_role
            """,
            (experiment_id,),
        )

        by_agent = self._rows(
            """
            SELECT agent_id, agent_role AS role,
                   COUNT(*)                                   AS events,
                   COALESCE(SUM(total_tokens), 0)             AS tokens,
                   COALESCE(SUM(cost_usd), 0)                 AS cost_usd,
                   COUNT(DISTINCT task_id)                    AS tasks_worked,
                   COUNT(DISTINCT session_id)                 AS sessions,
                   COALESCE(SUM(CASE WHEN turn_index IS NOT NULL THEN 1 ELSE 0 END), 0)
                                                              AS turns
            FROM v_event_cost_inclusive
            WHERE experiment_id = ?
            GROUP BY agent_id, agent_role
            ORDER BY cost_usd DESC
            """,
            (experiment_id,),
        )

        by_task = self._rows(
            """
            SELECT task_id,
                   COUNT(*)                          AS events,
                   COALESCE(SUM(total_tokens), 0)    AS tokens,
                   COALESCE(SUM(cost_usd), 0)        AS cost_usd
            FROM v_event_cost_inclusive
            WHERE experiment_id = ? AND task_id IS NOT NULL
            GROUP BY task_id
            ORDER BY cost_usd DESC
            """,
            (experiment_id,),
        )

        by_operation = self._rows(
            """
            SELECT operation,
                   COUNT(*)                          AS events,
                   COALESCE(SUM(total_tokens), 0)    AS tokens,
                   COALESCE(SUM(cost_usd), 0)        AS cost_usd
            FROM v_event_cost_inclusive
            WHERE experiment_id = ?
            GROUP BY operation
            ORDER BY cost_usd DESC
            """,
            (experiment_id,),
        )

        by_model = self._rows(
            """
            SELECT model, provider,
                   COUNT(*)                          AS events,
                   COALESCE(SUM(total_tokens), 0)    AS tokens,
                   COALESCE(SUM(cost_usd), 0)        AS cost_usd
            FROM v_event_cost_inclusive
            WHERE experiment_id = ?
            GROUP BY model, provider
            ORDER BY cost_usd DESC
            """,
            (experiment_id,),
        )

        return {
            **meta,
            "summary": totals,
            "by_role": by_role,
            "by_agent": by_agent,
            "by_task": by_task,
            "by_operation": by_operation,
            "by_model": by_model,
        }

    def session_turns(self, session_id: str) -> List[Dict[str, Any]]:
        """Per-turn cost trajectory for one Claude Code session.

        Used to find runaway loops and visualize cost growth across a
        single agent session.
        """
        return self._rows(
            """
            SELECT turn_index, total_tokens, cost_usd, timestamp
            FROM v_event_cost_inclusive
            WHERE session_id = ?
            ORDER BY turn_index
            """,
            (session_id,),
        )

    def cache_hit_rate_by_agent(self, experiment_id: str) -> List[Dict[str, Any]]:
        """Per-agent cache hit rate within one experiment.

        Returns
        -------
        list of dict
            Each row: ``{agent_id, cacheable_tokens, cache_read_tokens,
            cache_hit_rate}``. ``cache_hit_rate`` is 0.0 when no tokens
            were cacheable.
        """
        rows = self._rows(
            """
            SELECT agent_id,
                   COALESCE(SUM(input_tokens), 0)
                     + COALESCE(SUM(cache_creation_tokens), 0)
                     + COALESCE(SUM(cache_read_tokens), 0)         AS cacheable_tokens,
                   COALESCE(SUM(cache_read_tokens), 0)             AS cache_read_tokens
            FROM token_events
            WHERE experiment_id = ?
            GROUP BY agent_id
            """,
            (experiment_id,),
        )
        for r in rows:
            r["cache_hit_rate"] = (
                r["cache_read_tokens"] / r["cacheable_tokens"]
                if r["cacheable_tokens"] > 0
                else 0.0
            )
        return rows

    def list_projects(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List every project_id that has cost events, sorted by spend desc.

        The primary source of truth is ``token_events.project_id`` — every
        row is derived from recorded events. The query then enriches each
        project row with a human-readable ``project_name`` from the
        ``experiments`` table as a best-effort label; this is NULL for
        projects whose runs never called ``start_experiment``, and the
        dashboard falls back to the raw ``project_id`` in that case.

        Each row carries event count, token total, cost, and first/last
        activity timestamps so the dashboard can show "active in the last
        hour" without a second query.

        Parameters
        ----------
        limit : int
            Cap result set. Default 100.

        Returns
        -------
        list of dict
            One row per project_id. Excludes the ``'unassigned'`` bucket;
            it's surfaced separately via ``unassigned_totals`` so it
            doesn't get mistaken for a real project.
        """
        # LEFT JOIN to experiments to pull a human-readable project_name
        # when one exists. The experiments table is only populated when a
        # run opts into MLflow tracking (start_experiment), so many
        # projects will have NULL here.
        #
        # JOIN-safety invariant: this query relies on
        # ``experiments.experiment_id`` being unique (it's the primary
        # key, see cost_store.SCHEMA_SQL). If a future migration relaxes
        # that — e.g. adds a versioning column — the LEFT JOIN will fan
        # out and inflate every token / cost total. Revisit this query
        # if the experiments PK ever changes.
        #
        # MAX(project_name) picks the lexically latest name to keep the
        # GROUP BY deterministic when the same project_id has multiple
        # experiments with conflicting names. This is masking-not-fixing
        # behavior: a name conflict usually means data drift (rename,
        # spawn registry bug). Intentional drift detection is a separate
        # follow-up; today we just stay deterministic.
        return self._rows(
            """
            SELECT t.project_id,
                   MAX(e.project_name)                  AS project_name,
                   COUNT(*)                             AS events,
                   COUNT(DISTINCT t.experiment_id)      AS experiments,
                   COUNT(DISTINCT t.agent_id)           AS agents,
                   COALESCE(SUM(t.total_tokens), 0)     AS total_tokens,
                   COALESCE(SUM(t.cost_usd), 0)         AS total_cost_usd,
                   MIN(t.timestamp)                     AS first_event_at,
                   MAX(t.timestamp)                     AS last_event_at
            FROM v_event_cost_inclusive t
            LEFT JOIN experiments e USING (experiment_id)
            WHERE t.project_id != 'unassigned'
            GROUP BY t.project_id
            ORDER BY total_cost_usd DESC
            LIMIT ?
            """,
            (limit,),
        )

    def unassigned_totals(self) -> Dict[str, Any]:
        """Cost of LLM calls made without an active PlannerContext.

        These are events Marcus recorded before ``project_id`` was known —
        usually because a code path makes an LLM call outside the MCP
        request lifecycle. Surfacing them separately keeps the project
        list clean while making the gap visible so we can fix the
        upstream caller.
        """
        return (
            self._row(
                """
            SELECT COUNT(*)                             AS events,
                   COALESCE(SUM(total_tokens), 0)       AS total_tokens,
                   COALESCE(SUM(cost_usd), 0)           AS total_cost_usd
            FROM v_event_cost_inclusive
            WHERE project_id = 'unassigned'
            """,
            )
            or {"events": 0, "total_tokens": 0, "total_cost_usd": 0.0}
        )

    def project_totals(self, project_id: str) -> Dict[str, Any]:
        """Roll up all token and cost data for one project across experiments."""
        return (
            self._row(
                """
            SELECT
                COUNT(DISTINCT experiment_id)        AS experiments,
                COUNT(*)                             AS events,
                COALESCE(SUM(total_tokens), 0)       AS total_tokens,
                COALESCE(SUM(cost_usd), 0)           AS total_cost_usd
            FROM v_event_cost_inclusive
            WHERE project_id = ?
            """,
                (project_id,),
            )
            or {
                "experiments": 0,
                "events": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
            }
        )

    def project_summary(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Full per-project summary used by Cato's drill-in view.

        Mirrors :meth:`experiment_summary` but scoped to ``project_id``,
        because Marcus's coordination model identifies work by project,
        not by MLflow experiment. Most Marcus runs never call
        ``start_experiment`` and therefore have no row in the
        ``experiments`` table — but they still produce token events
        attributed to a project. This method drives the project-first
        dashboard surface.

        Returns
        -------
        dict or None
            ``{summary, by_role, by_agent, by_task, by_operation,
            by_model, project_id, first_event_at, last_event_at}``.
            ``None`` only if the project has zero events.
        """
        totals = self._row(
            """
            SELECT
                COUNT(*)                                    AS total_events,
                COUNT(DISTINCT experiment_id)               AS experiments,
                COUNT(DISTINCT agent_id)                    AS agents,
                COUNT(DISTINCT session_id)                  AS sessions,
                COALESCE(SUM(total_tokens), 0)              AS total_tokens,
                COALESCE(SUM(input_tokens), 0)              AS input_tokens,
                COALESCE(SUM(cache_creation_tokens), 0)     AS cache_creation_tokens,
                COALESCE(SUM(cache_read_tokens), 0)         AS cache_read_tokens,
                COALESCE(SUM(output_tokens), 0)             AS output_tokens,
                COALESCE(SUM(cost_usd), 0)                  AS total_cost_usd,
                MIN(timestamp)                              AS first_event_at,
                MAX(timestamp)                              AS last_event_at
            FROM v_event_cost_inclusive
            WHERE project_id = ?
            """,
            (project_id,),
        )

        if not totals or (totals.get("total_events") or 0) == 0:
            return None

        cacheable = (
            (totals.get("input_tokens") or 0)
            + (totals.get("cache_creation_tokens") or 0)
            + (totals.get("cache_read_tokens") or 0)
        )
        hit_rate = (
            (totals.get("cache_read_tokens") or 0) / cacheable if cacheable > 0 else 0.0
        )
        totals["cache_hit_rate"] = hit_rate

        by_role = self._rows(
            """
            SELECT agent_role AS role,
                   COUNT(*)                          AS events,
                   COALESCE(SUM(total_tokens), 0)    AS tokens,
                   COALESCE(SUM(cost_usd), 0)        AS cost_usd
            FROM v_event_cost_inclusive
            WHERE project_id = ?
            GROUP BY agent_role
            """,
            (project_id,),
        )

        by_agent = self._rows(
            """
            SELECT agent_id, agent_role AS role,
                   COUNT(*)                                   AS events,
                   COALESCE(SUM(total_tokens), 0)             AS tokens,
                   COALESCE(SUM(cost_usd), 0)                 AS cost_usd,
                   COUNT(DISTINCT task_id)                    AS tasks_worked,
                   COUNT(DISTINCT session_id)                 AS sessions,
                   COALESCE(SUM(CASE WHEN turn_index IS NOT NULL THEN 1 ELSE 0 END), 0)
                                                              AS turns
            FROM v_event_cost_inclusive
            WHERE project_id = ?
            GROUP BY agent_id, agent_role
            ORDER BY cost_usd DESC
            """,
            (project_id,),
        )

        by_task = self._rows(
            """
            SELECT task_id,
                   COUNT(*)                          AS events,
                   COALESCE(SUM(total_tokens), 0)    AS tokens,
                   COALESCE(SUM(cost_usd), 0)        AS cost_usd
            FROM v_event_cost_inclusive
            WHERE project_id = ? AND task_id IS NOT NULL
            GROUP BY task_id
            ORDER BY cost_usd DESC
            """,
            (project_id,),
        )

        # by_operation: enriched with the full token-type split + per-op
        # cache hit rate so users can see where prompts are heavy and
        # where the cache is (or isn't) helping. Sorted by total tokens
        # so the most-spent-on operation surfaces first — that's the
        # one to focus prompt-tightening work on.
        by_operation = self._rows(
            """
            SELECT operation,
                   COUNT(*)                                AS events,
                   COALESCE(SUM(total_tokens), 0)          AS tokens,
                   COALESCE(SUM(input_tokens), 0)          AS input_tokens,
                   COALESCE(SUM(cache_creation_tokens), 0) AS cache_creation_tokens,
                   COALESCE(SUM(cache_read_tokens), 0)     AS cache_read_tokens,
                   COALESCE(SUM(output_tokens), 0)         AS output_tokens,
                   COALESCE(SUM(cost_usd), 0)              AS cost_usd,
                   CASE
                     WHEN SUM(input_tokens) + SUM(cache_creation_tokens)
                        + SUM(cache_read_tokens) > 0
                     THEN CAST(SUM(cache_read_tokens) AS REAL) /
                          (SUM(input_tokens) + SUM(cache_creation_tokens)
                           + SUM(cache_read_tokens))
                     ELSE 0
                   END                                     AS cache_hit_rate
            FROM v_event_cost_inclusive
            WHERE project_id = ?
            GROUP BY operation
            ORDER BY tokens DESC
            """,
            (project_id,),
        )

        # Same split for by_model so users can see whether a given
        # provider/model is actually benefiting from prompt caching, or
        # whether all input is unique each call.
        by_model = self._rows(
            """
            SELECT model, provider,
                   COUNT(*)                                AS events,
                   COALESCE(SUM(total_tokens), 0)          AS tokens,
                   COALESCE(SUM(input_tokens), 0)          AS input_tokens,
                   COALESCE(SUM(cache_creation_tokens), 0) AS cache_creation_tokens,
                   COALESCE(SUM(cache_read_tokens), 0)     AS cache_read_tokens,
                   COALESCE(SUM(output_tokens), 0)         AS output_tokens,
                   COALESCE(SUM(cost_usd), 0)              AS cost_usd,
                   CASE
                     WHEN SUM(input_tokens) + SUM(cache_creation_tokens)
                        + SUM(cache_read_tokens) > 0
                     THEN CAST(SUM(cache_read_tokens) AS REAL) /
                          (SUM(input_tokens) + SUM(cache_creation_tokens)
                           + SUM(cache_read_tokens))
                     ELSE 0
                   END                                     AS cache_hit_rate
            FROM v_event_cost_inclusive
            WHERE project_id = ?
            GROUP BY model, provider
            ORDER BY tokens DESC
            """,
            (project_id,),
        )

        return {
            "project_id": project_id,
            "summary": totals,
            "by_role": by_role,
            "by_agent": by_agent,
            "by_task": by_task,
            "by_operation": by_operation,
            "by_model": by_model,
        }
