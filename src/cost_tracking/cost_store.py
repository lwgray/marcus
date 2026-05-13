"""
SQLite-backed event store for Marcus token usage and cost data.

Stores one row per LLM call (planner or worker) with full agent/task/model
attribution. Pricing lives in a versioned ``model_prices`` table and cost is
computed at query time via the ``v_event_cost`` view, so changing prices
never rewrites history.

Schema
------
- ``runs``           : registry of project runs (project, path, totals)
- ``token_events``   : one row per LLM call (immutable token counts)
- ``model_prices``   : versioned by ``effective_from``; edited by Cato UI
- ``v_event_cost``   : view joining events × the price active at each
                      event's timestamp, exposing ``cost_usd``

Terminology note
----------------
Marcus's cost-tracking layer talks about **runs** — one row per
end-to-end traversal of a project (create → decompose → agents work
→ stop). Each cost ``token_events`` row carries a ``run_id``
identifying which run produced it.

This concept used to be named ``experiment`` / ``experiment_id``.
The rename happened because the name clashed with MLflow's
*operational* experiment concept (the ``start_experiment`` MCP tool
in ``src/marcus_mcp/tools/experiments.py``), which is unrelated:
MLflow tracks task assignments, completions, and blockers for
``/marcus`` and Posidonius runs; the cost-tracking layer tracks
LLM token spend grouped by run. They share nothing besides a
historical name collision.

The ``runs.path`` column captures *which entry point produced
this run*: ``"direct"`` (a human MCP user), ``"marcus"`` (the
``/marcus`` meta-runner), or ``"posidonius"`` (the automated
research runner). Defaults to ``"unknown"`` for rows created
before the discriminator existed.

This module exposes a thin :class:`CostStore` wrapper. Aggregation queries
live in ``cost_aggregator.py``; this file only handles inserts and schema.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL: str = """
CREATE TABLE IF NOT EXISTS runs (
  run_id           TEXT PRIMARY KEY,
  project_id       TEXT NOT NULL,
  -- Entry point that produced this run. One of:
  --   'direct'     - human MCP user (e.g., Claude Code calling create_project)
  --   'marcus'     - /marcus meta-runner via experiments/spawn_agents.py
  --   'posidonius' - Posidonius automated research runner via spawn_agents.py
  --   'unknown'    - legacy rows from before the discriminator existed
  path             TEXT NOT NULL DEFAULT 'unknown',
  board_id         TEXT,
  project_name     TEXT,
  decomposer       TEXT,
  complexity       TEXT,
  provider         TEXT,
  model            TEXT,
  num_agents       INTEGER,
  started_at       TIMESTAMP NOT NULL,
  ended_at         TIMESTAMP,
  total_tasks      INTEGER,
  completed_tasks  INTEGER,
  blocked_tasks    INTEGER,
  budget_usd       REAL,
  notes            TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_id);
CREATE INDEX IF NOT EXISTS idx_runs_path    ON runs(path);

CREATE TABLE IF NOT EXISTS token_events (
  event_id              INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id                TEXT NOT NULL,
  project_id            TEXT NOT NULL,
  agent_id              TEXT NOT NULL,
  agent_role            TEXT NOT NULL,
  parent_agent_id       TEXT,
  task_id               TEXT,
  subtask_id            TEXT,
  operation             TEXT NOT NULL,
  -- ``tool_intent`` (Marcus #527 Phase 2): which Claude Code tool the
  -- agent invoked on this turn. Populated by ``worker_intent.py`` from
  -- the JSONL ``message.content`` tool_use blocks. NULL on planner
  -- rows and on legacy worker rows from before the parser landed.
  -- Values: worker_marcus_call / worker_mcp_call / worker_edit /
  -- worker_bash / worker_search / worker_read / worker_text / unknown.
  tool_intent           TEXT,
  provider              TEXT NOT NULL,
  model                 TEXT NOT NULL,
  input_tokens          INTEGER NOT NULL DEFAULT 0,
  cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
  cache_read_tokens     INTEGER NOT NULL DEFAULT 0,
  output_tokens         INTEGER NOT NULL DEFAULT 0,
  total_tokens          INTEGER GENERATED ALWAYS AS
                          (input_tokens + cache_creation_tokens
                           + cache_read_tokens + output_tokens) STORED,
  latency_ms            INTEGER,
  session_id            TEXT,
  turn_index            INTEGER,
  request_id            TEXT,
  status                TEXT NOT NULL DEFAULT 'ok',
  error_type            TEXT,
  -- ISO-8601 with millisecond precision and trailing 'Z' so text
  -- comparison in v_event_cost matches Python datetime.isoformat() output
  -- used by record_price(). SQLite's bare CURRENT_TIMESTAMP produces
  -- 'YYYY-MM-DD HH:MM:SS' (space separator) which sorts BEFORE
  -- 'YYYY-MM-DDT...' and would silently drop same-day events from cost
  -- aggregations (Codex P2 on PR #497).
  timestamp             TIMESTAMP NOT NULL
                        DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_te_run       ON token_events(run_id);
CREATE INDEX IF NOT EXISTS idx_te_project   ON token_events(project_id);
CREATE INDEX IF NOT EXISTS idx_te_run_agent ON token_events(run_id, agent_id);
CREATE INDEX IF NOT EXISTS idx_te_task      ON token_events(task_id);
CREATE INDEX IF NOT EXISTS idx_te_op_model  ON token_events(operation, model);
CREATE INDEX IF NOT EXISTS idx_te_intent    ON token_events(tool_intent);
CREATE INDEX IF NOT EXISTS idx_te_timestamp ON token_events(timestamp);
-- Partial unique index for dedup. Worker JSONL ingestion may sweep the
-- same session files repeatedly (e.g. Cato's 30s dashboard poll re-runs
-- run_ingest with a fresh ingester whose in-memory ``_seen_uuids`` set
-- is empty). Without DB-level dedup, every poll re-inserts every event
-- and token counts double silently. ``request_id`` is Claude Code's
-- per-call ID — unique per real LLM call. Partial WHERE clause keeps
-- the NULL case (older rows, non-Claude providers) unconstrained.
CREATE UNIQUE INDEX IF NOT EXISTS ux_te_request_id
    ON token_events(request_id) WHERE request_id IS NOT NULL;

-- Persistent project-name snapshot. Cost data outlives the Marcus
-- project registry — registries get deleted, but token_events
-- attributed to those projects stay. To keep the dashboard from
-- showing opaque hex IDs after a project is deleted, Marcus snapshots
-- the human-readable name into this table whenever a PlannerContext
-- is pushed (or a worker JSONL is ingested with a known name). Cato
-- reads from here first, then falls back to projects.json.
CREATE TABLE IF NOT EXISTS project_names (
  project_id    TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  first_seen    TIMESTAMP NOT NULL
                DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  last_seen     TIMESTAMP NOT NULL
                DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Project-level budget caps. Set by the dashboard so users can compare
-- spend against a target without needing MLflow experiments. Stored in
-- the cost DB (not ProjectRegistry) because the cap is a cost concept,
-- and keeps the write path under Cato's control without touching
-- Marcus's project metadata. One row per project_id; subsequent writes
-- update budget_usd in place.
CREATE TABLE IF NOT EXISTS project_budgets (
  project_id    TEXT PRIMARY KEY,
  budget_usd    REAL NOT NULL,
  set_at        TIMESTAMP NOT NULL
                DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  note          TEXT
);

CREATE TABLE IF NOT EXISTS model_prices (
  model                       TEXT NOT NULL,
  provider                    TEXT NOT NULL,
  effective_from              TIMESTAMP NOT NULL,
  input_per_million            REAL NOT NULL,
  cache_creation_per_million   REAL,
  cache_read_per_million       REAL,
  output_per_million           REAL NOT NULL,
  source                       TEXT,
  PRIMARY KEY (model, provider, effective_from)
);

CREATE VIEW IF NOT EXISTS v_event_cost AS
SELECT t.*,
       (t.input_tokens          * p.input_per_million          / 1e6
      + t.cache_creation_tokens * COALESCE(p.cache_creation_per_million, 0) / 1e6
      + t.cache_read_tokens     * COALESCE(p.cache_read_per_million, 0)     / 1e6
      + t.output_tokens         * p.output_per_million         / 1e6) AS cost_usd
FROM token_events t
JOIN model_prices p
  ON t.model = p.model AND t.provider = p.provider
 AND p.effective_from = (
       SELECT MAX(effective_from) FROM model_prices
       WHERE model = t.model AND provider = t.provider
         AND effective_from <= t.timestamp
     );

-- Same as v_event_cost but LEFT JOINs prices instead of INNER JOIN.
-- v_event_cost drops events whose (model, provider) has no matching
-- model_prices row (e.g., '<synthetic>' planner artifacts, local Qwen
-- models without a seed price). Aggregator queries that want true
-- event/token counts must read from this view; cost_usd is 0 for
-- unpriced rows so SUM still works (Codex P2 on PR #513).
CREATE VIEW IF NOT EXISTS v_event_cost_inclusive AS
SELECT t.*,
       COALESCE(
           t.input_tokens          * p.input_per_million          / 1e6
         + t.cache_creation_tokens * COALESCE(p.cache_creation_per_million, 0) / 1e6
         + t.cache_read_tokens     * COALESCE(p.cache_read_per_million, 0)     / 1e6
         + t.output_tokens         * p.output_per_million         / 1e6,
         0
       ) AS cost_usd
FROM token_events t
LEFT JOIN model_prices p
  ON t.model = p.model AND t.provider = p.provider
 AND p.effective_from = (
       SELECT MAX(effective_from) FROM model_prices
       WHERE model = t.model AND provider = t.provider
         AND effective_from <= t.timestamp
     );
"""

# Default seed prices loaded on first use unless caller provides their own.
# Values pulled from the official Anthropic pricing page on _SEED_DATE
# (see the populating block below). Tweaking these is harmless — Cato
# can override at runtime via the Pricing tab, which inserts new
# ``model_prices`` rows with a fresh ``effective_from``.
DEFAULT_SEED: List["ModelPrice"] = []  # populated below after dataclass def


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TokenEvent:
    """One LLM call (planner or worker).

    Parameters
    ----------
    run_id : str
        Run identifier — ties this event to one row in the ``runs``
        table. See :class:`Run` for the rationale on the rename
        from the legacy ``experiment_id``.
    project_id : str
        Marcus project ID this event belongs to (denormalized for fast filter).
    agent_id : str
        Stable agent identifier (``'planner'``, ``'agent_unicorn_1'``, etc).
    agent_role : str
        One of ``'planner'``, ``'creator'``, ``'worker'``, ``'monitor'``,
        ``'subagent'``.
    operation : str
        High-level operation name (``'parse_prd'``, ``'turn'``, ...).
    provider : str
        ``'anthropic'``, ``'cloud'``, ``'local'``, ``'openai'``.
    model : str
        Model identifier as reported by the provider.
    input_tokens : int
        Non-cached input tokens.
    cache_creation_tokens : int
        Tokens written to the prompt cache (priced at 1.25× input).
    cache_read_tokens : int
        Tokens served from the prompt cache (priced at 0.10× input).
    output_tokens : int
        Generated tokens.
    parent_agent_id, task_id, subtask_id, latency_ms, session_id,
    turn_index, request_id, status, error_type, timestamp : optional
        Drill-down context. ``timestamp`` defaults to ``CURRENT_TIMESTAMP``
        in SQLite when not supplied.
    """

    run_id: str
    project_id: str
    agent_id: str
    agent_role: str
    operation: str
    provider: str
    model: str
    input_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    output_tokens: int = 0
    parent_agent_id: Optional[str] = None
    task_id: Optional[str] = None
    subtask_id: Optional[str] = None
    tool_intent: Optional[str] = None
    latency_ms: Optional[int] = None
    session_id: Optional[str] = None
    turn_index: Optional[int] = None
    request_id: Optional[str] = None
    status: str = "ok"
    error_type: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class Run:
    """Run registry row — one project traversal end-to-end.

    Each row in the ``runs`` table represents a single execution of
    a project from ``create_project`` through agent work. The
    ``path`` field records which entry point produced the run; see
    the schema header for the allowed values.

    Renamed from ``Experiment`` (and the table from ``experiments``)
    to disambiguate from MLflow's separate experiment concept. See
    Simon decision ``7ed3074d`` for the full rationale.
    """

    run_id: str
    project_id: str
    started_at: datetime
    path: str = "unknown"
    board_id: Optional[str] = None
    project_name: Optional[str] = None
    decomposer: Optional[str] = None
    complexity: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    num_agents: Optional[int] = None
    ended_at: Optional[datetime] = None
    total_tasks: Optional[int] = None
    completed_tasks: Optional[int] = None
    blocked_tasks: Optional[int] = None
    budget_usd: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class ModelPrice:
    """One pricing row (a single (model, provider, effective_from) tuple)."""

    model: str
    provider: str
    effective_from: datetime
    input_per_million: float
    output_per_million: float
    cache_creation_per_million: Optional[float] = None
    cache_read_per_million: Optional[float] = None
    source: str = "default"


# Populate DEFAULT_SEED after the dataclass is defined.
# Effective_from date for the seed rows: the day we read the official
# pricing page (2026-05-11). We don't know the actual day each rate
# became effective on Anthropic's side, only that these are current
# values as of that date. Users who need historically-accurate cost
# for earlier experiments can insert versioned overrides via Cato.
_SEED_DATE = datetime(2026, 5, 11, tzinfo=timezone.utc)
# Authoritative Anthropic prices sourced from the official pricing page
# (claude.com/pricing, captured 2026-05-11). Per the spec, prices are:
#   input | 5m cache write (1.25× input) | 1h cache write (2× input, NOT stored —
#   our schema has one cache-write column representing the common 5m case) |
#   cache read (0.1× input) | output
#
# Our schema's cache_creation_per_million column maps to the 5-minute cache
# write multiplier. Cato displays the 5m rate; users who need 1h pricing
# can insert a versioned override via Cato's pricing form. See #409 docs.
#
# Tuple order for the positional constructor:
#   (model, provider, effective_from, input, output,
#    cache_creation, cache_read, source)
DEFAULT_SEED.extend(
    [
        # ── Claude Opus 4.5–4.7 (cheaper than 4.0–4.1!) ──
        ModelPrice(
            "claude-opus-4-7", "anthropic", _SEED_DATE, 5.0, 25.0, 6.25, 0.50, "default"
        ),
        ModelPrice(
            "claude-opus-4-6", "anthropic", _SEED_DATE, 5.0, 25.0, 6.25, 0.50, "default"
        ),
        ModelPrice(
            "claude-opus-4-5", "anthropic", _SEED_DATE, 5.0, 25.0, 6.25, 0.50, "default"
        ),
        # ── Claude Opus 4.0–4.1 (legacy higher pricing) ──
        ModelPrice(
            "claude-opus-4-1",
            "anthropic",
            _SEED_DATE,
            15.0,
            75.0,
            18.75,
            1.50,
            "default",
        ),
        ModelPrice(
            "claude-opus-4-1-20250805",
            "anthropic",
            _SEED_DATE,
            15.0,
            75.0,
            18.75,
            1.50,
            "default",
        ),
        ModelPrice(
            "claude-opus-4-20250514",
            "anthropic",
            _SEED_DATE,
            15.0,
            75.0,
            18.75,
            1.50,
            "default",
        ),
        # ── Claude Sonnet 4 family (4.0, 4.5, 4.6 all share pricing) ──
        ModelPrice(
            "claude-sonnet-4-6",
            "anthropic",
            _SEED_DATE,
            3.0,
            15.0,
            3.75,
            0.30,
            "default",
        ),
        ModelPrice(
            "claude-sonnet-4-5",
            "anthropic",
            _SEED_DATE,
            3.0,
            15.0,
            3.75,
            0.30,
            "default",
        ),
        ModelPrice(
            "claude-sonnet-4-20250514",
            "anthropic",
            _SEED_DATE,
            3.0,
            15.0,
            3.75,
            0.30,
            "default",
        ),
        # ── Claude Haiku 4.5 ──
        ModelPrice(
            "claude-haiku-4-5", "anthropic", _SEED_DATE, 1.0, 5.0, 1.25, 0.10, "default"
        ),
        ModelPrice(
            "claude-haiku-4-5-20251001",
            "anthropic",
            _SEED_DATE,
            1.0,
            5.0,
            1.25,
            0.10,
            "default",
        ),
        # ── Legacy Claude 3.x family ──
        # Marcus's default config (anthropic_provider.py:71) still uses
        # claude-3-haiku-20240307; spawn_agents docs reference
        # claude-3-5-sonnet-20241022. Sonnet 3.7 + Opus 3 are formally
        # deprecated but still appear on the pricing page.
        ModelPrice(
            "claude-3-7-sonnet-20250219",
            "anthropic",
            _SEED_DATE,
            3.0,
            15.0,
            3.75,
            0.30,
            "default",
        ),
        ModelPrice(
            "claude-3-5-sonnet-20241022",
            "anthropic",
            _SEED_DATE,
            3.0,
            15.0,
            3.75,
            0.30,
            "default",
        ),
        # Marcus's built-in default config (src/config/settings.py:111,
        # config/pm_agent_config.json:57) sets model to this non-canonical
        # identifier. Keep a compat seed so v_event_cost's inner join
        # doesn't drop events that record_usage stamped with the literal
        # configured string. Priced as Sonnet 3.5 (Codex P2 on PR #510).
        ModelPrice(
            "claude-3-sonnet-20241022",
            "anthropic",
            _SEED_DATE,
            3.0,
            15.0,
            3.75,
            0.30,
            "default",
        ),
        ModelPrice(
            "claude-3-5-haiku-20241022",
            "anthropic",
            _SEED_DATE,
            1.0,
            5.0,
            1.25,
            0.10,
            "default",
        ),
        ModelPrice(
            "claude-3-opus-20240229",
            "anthropic",
            _SEED_DATE,
            15.0,
            75.0,
            18.75,
            1.50,
            "default",
        ),
        ModelPrice(
            "claude-3-haiku-20240307",
            "anthropic",
            _SEED_DATE,
            0.25,
            1.25,
            0.30,
            0.03,
            "default",
        ),
        # ── OpenAI (kept as a starting point; users override via Cato) ──
        ModelPrice("gpt-4o", "openai", _SEED_DATE, 5.0, 15.0, None, None, "default"),
    ]
)


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class CostStore:
    """SQLite-backed token-event store.

    Parameters
    ----------
    db_path : Path
        File path for the SQLite database. Parent directory is created if
        missing. Use ``":memory:"`` (as a Path or str) for ephemeral tests
        via the alternate ``CostStore.in_memory()`` constructor.

    Notes
    -----
    The connection is opened with ``check_same_thread=False`` so background
    ingesters can write from a different thread than queries. Callers are
    responsible for serializing writes if multi-threaded access is needed;
    SQLite's WAL mode gives concurrent readers + one writer for free.
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        if str(db_path) != ":memory:":
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        # Wait up to 5s for the lock on startup DDL / contended writes
        # before raising OperationalError. Cato polls run_ingest every
        # 30s; bare 0ms timeout caused Marcus startup to die immediately
        # when Cato held the WAL.
        self.conn.execute("PRAGMA busy_timeout=5000")
        self._init_schema()

    def _init_schema(self) -> None:
        """Run schema DDL. Idempotent thanks to IF NOT EXISTS guards.

        Two ordered one-shot migrations run before ``executescript``
        so that the DDL can assume the new schema:

        1. :meth:`_runs_rename_migration` renames the legacy
           ``experiments`` table to ``runs`` and the
           ``experiment_id`` column to ``run_id`` (in both ``runs``
           and ``token_events``), then adds the new ``path`` column
           for entry-point discrimination. See the function's
           docstring for the rationale.
        2. :meth:`_dedup_pre_index_migration` removes duplicate
           ``request_id`` rows before the partial UNIQUE index lands.
        """
        self._runs_rename_migration()
        self._dedup_pre_index_migration()
        self._tool_intent_migration()
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def _runs_rename_migration(self) -> None:
        """One-shot migration: ``experiments`` → ``runs`` + add ``path``.

        Before this rename, the cost-tracking layer used
        ``experiments`` and ``experiment_id`` as its terminology. That
        clashed with MLflow's *operational* experiment concept (the
        ``start_experiment`` MCP tool), causing real architectural
        confusion — see Simon decision ``7ed3074d``. The rename
        clarifies that these are two unrelated systems with a
        historical name collision.

        Operations performed (idempotent):

        1. Detect legacy schema via the presence of the
           ``experiments`` table and absence of the ``runs`` table.
        2. ``ALTER TABLE experiments RENAME TO runs``
        3. ``ALTER TABLE runs RENAME COLUMN experiment_id TO run_id``
        4. ``ALTER TABLE token_events RENAME COLUMN experiment_id TO run_id``
        5. Drop the old index names so SCHEMA_SQL's
           ``CREATE INDEX IF NOT EXISTS`` builds fresh ones with
           descriptive names (``idx_runs_*`` / ``idx_te_run*``).
        6. ``ALTER TABLE runs ADD COLUMN path TEXT NOT NULL
           DEFAULT 'unknown'``.

        Requires SQLite 3.25+ for ``RENAME COLUMN``. Python's bundled
        sqlite3 module ships with much newer versions; Marcus's
        supported Python (3.10+) is fine.

        Skipped on three cases:

        - Fresh install (no ``experiments`` table) — SCHEMA_SQL
          creates the new layout directly.
        - Already-migrated DB (``runs`` table present) — no-op.
        - DB with neither table (unreachable in practice, but kept
          defensive) — no-op.
        """
        has_experiments = self.conn.execute(
            "SELECT 1 FROM sqlite_master " "WHERE type='table' AND name='experiments'"
        ).fetchone()
        has_runs = self.conn.execute(
            "SELECT 1 FROM sqlite_master " "WHERE type='table' AND name='runs'"
        ).fetchone()

        if has_runs:
            # Already migrated, or fresh install will create directly.
            return
        if not has_experiments:
            # Fresh install — nothing to rename.
            return

        # Legacy schema present. Execute the rename.
        self.conn.execute("ALTER TABLE experiments RENAME TO runs")
        self.conn.execute("ALTER TABLE runs RENAME COLUMN experiment_id TO run_id")
        self.conn.execute(
            "ALTER TABLE token_events RENAME COLUMN experiment_id TO run_id"
        )
        # Drop the indices that referenced the old names. SCHEMA_SQL's
        # ``CREATE INDEX IF NOT EXISTS`` will rebuild them with the
        # new descriptive names against the renamed columns. SQLite
        # auto-updates index DDL to track column renames, so the old
        # indices still work — but we drop them so the index name
        # vocabulary matches the new schema vocabulary.
        for old_index in ("idx_exp_project", "idx_te_exp", "idx_te_agent"):
            self.conn.execute(f"DROP INDEX IF EXISTS {old_index}")
        # Add the new path column for entry-point discrimination.
        self.conn.execute(
            "ALTER TABLE runs ADD COLUMN path TEXT NOT NULL " "DEFAULT 'unknown'"
        )
        self.conn.commit()

    def _tool_intent_migration(self) -> None:
        """Add ``token_events.tool_intent`` to existing DBs (Marcus #527 Phase 2).

        Fresh installs get the column via SCHEMA_SQL. For an existing
        cost DB the column doesn't exist; this migration adds it as
        nullable so old rows survive with NULL until a backfill runs.
        Idempotent: detects the column via ``PRAGMA table_info`` and
        skips when already present.

        Designed to be cheap and lock-friendly: a single ``ALTER TABLE
        ADD COLUMN`` is a metadata-only operation in SQLite, so it
        doesn't rewrite the table even on a multi-million-row
        ``token_events``.
        """
        cols = {
            row[1]
            for row in self.conn.execute("PRAGMA table_info(token_events)").fetchall()
        }
        if "token_events" not in {
            r[0]
            for r in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }:
            # Fresh install — SCHEMA_SQL will create the column.
            return
        if "tool_intent" in cols:
            return
        self.conn.execute("ALTER TABLE token_events ADD COLUMN tool_intent TEXT")
        self.conn.commit()

    def _dedup_pre_index_migration(self) -> None:
        """Compact duplicate ``request_id`` rows before the index lands.

        Keeps the lowest ``event_id`` per ``request_id``. Duplicates are
        byte-identical re-inserts of the same payload, so any winner is
        correct; ``MIN(event_id)`` is just a stable choice.

        Skipped on three cases:
        - Fresh install (token_events absent) — nothing to dedup.
        - Already-migrated DB (ux_te_request_id present) — by construction
          there are no duplicates, and the DELETE would still take a write
          lock that conflicts with concurrent Cato polling. This makes the
          migration truly no-op on every Marcus restart after the first.
        """
        table_exists = self.conn.execute(
            "SELECT 1 FROM sqlite_master " "WHERE type='table' AND name='token_events'"
        ).fetchone()
        if not table_exists:
            return
        index_exists = self.conn.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type='index' AND name='ux_te_request_id'"
        ).fetchone()
        if index_exists:
            return
        self.conn.execute("""
            DELETE FROM token_events
             WHERE request_id IS NOT NULL
               AND event_id NOT IN (
                 SELECT MIN(event_id) FROM token_events
                  WHERE request_id IS NOT NULL
                  GROUP BY request_id
               )
            """)
        self.conn.commit()

    # -- writes ------------------------------------------------------------

    def record_event(self, event: TokenEvent) -> int:
        """Insert one ``token_events`` row.

        Parameters
        ----------
        event : TokenEvent
            Event payload. Token counts default to 0 if not supplied.

        Returns
        -------
        int
            The auto-incremented ``event_id``.
        """
        cur = self.conn.execute(
            """
            INSERT OR IGNORE INTO token_events (
                run_id, project_id, agent_id, agent_role,
                parent_agent_id, task_id, subtask_id, operation, tool_intent,
                provider, model, input_tokens, cache_creation_tokens,
                cache_read_tokens, output_tokens, latency_ms, session_id,
                turn_index, request_id, status, error_type, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      COALESCE(?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')))
            """,
            (
                event.run_id,
                event.project_id,
                event.agent_id,
                event.agent_role,
                event.parent_agent_id,
                event.task_id,
                event.subtask_id,
                event.operation,
                event.tool_intent,
                event.provider,
                event.model,
                event.input_tokens,
                event.cache_creation_tokens,
                event.cache_read_tokens,
                event.output_tokens,
                event.latency_ms,
                event.session_id,
                event.turn_index,
                event.request_id,
                event.status,
                event.error_type,
                event.timestamp.isoformat() if event.timestamp else None,
            ),
        )
        self.conn.commit()
        if cur.rowcount == 0:
            # INSERT OR IGNORE skipped a duplicate ``request_id``. Return
            # the existing row's event_id so callers see idempotent behavior.
            row = self.conn.execute(
                "SELECT event_id FROM token_events WHERE request_id = ?",
                (event.request_id,),
            ).fetchone()
            if row is None:  # pragma: no cover - rowcount==0 implies match exists
                raise RuntimeError("INSERT OR IGNORE skipped but no matching row")
            return int(row[0])
        event_id = cur.lastrowid
        if event_id is None:  # pragma: no cover - sqlite3 always returns rowid
            raise RuntimeError("sqlite3 did not return lastrowid")
        return event_id

    def update_attribution(
        self,
        request_id: str,
        *,
        task_id: Optional[str] = None,
        tool_intent: Optional[str] = None,
    ) -> int:
        """Backfill ``task_id`` and/or ``tool_intent`` on an existing row.

        Used by the worker JSONL backfill path (Marcus #527 Phase 1.5
        + 2): historical rows were written before the ingester knew
        how to populate these fields. A re-walk of the JSONL files
        runs the parser and calls this helper to fill in the gaps.

        Idempotent and side-effect-light: only updates columns whose
        current value is NULL, so re-running on already-backfilled
        rows is a no-op. Returns the number of rows updated (0 or 1)
        so callers can report progress.

        Parameters
        ----------
        request_id : str
            The Claude Code per-call ID used as the upsert key.
        task_id : str, optional
            New ``task_id``. Only written if the row's current
            ``task_id`` is NULL.
        tool_intent : str, optional
            New ``tool_intent``. Only written if the row's current
            ``tool_intent`` is NULL.

        Returns
        -------
        int
            ``cur.rowcount`` from the UPDATE — 0 if no row matched
            the ``request_id``, 1 if a row was updated. Note: SQLite
            still reports 1 when the WHERE clause matched but the
            COALESCE guards left every column unchanged.
        """
        cur = self.conn.execute(
            """
            UPDATE token_events
               SET task_id     = COALESCE(task_id, ?),
                   tool_intent = COALESCE(tool_intent, ?)
             WHERE request_id = ?
            """,
            (task_id, tool_intent, request_id),
        )
        self.conn.commit()
        return cur.rowcount

    def record_run(self, run: Run) -> None:
        """Upsert one ``runs`` row keyed by ``run_id``.

        Renamed from ``record_experiment`` in the rename of
        ``experiments`` → ``runs``. See Simon decision ``7ed3074d``.
        """
        self.conn.execute(
            """
            INSERT INTO runs (
                run_id, project_id, path, board_id, project_name,
                decomposer, complexity, provider, model, num_agents,
                started_at, ended_at, total_tasks, completed_tasks,
                blocked_tasks, budget_usd, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                project_id=excluded.project_id,
                path=excluded.path,
                board_id=excluded.board_id,
                project_name=excluded.project_name,
                decomposer=excluded.decomposer,
                complexity=excluded.complexity,
                provider=excluded.provider,
                model=excluded.model,
                num_agents=excluded.num_agents,
                started_at=excluded.started_at,
                ended_at=excluded.ended_at,
                total_tasks=excluded.total_tasks,
                completed_tasks=excluded.completed_tasks,
                blocked_tasks=excluded.blocked_tasks,
                budget_usd=excluded.budget_usd,
                notes=excluded.notes
            """,
            (
                run.run_id,
                run.project_id,
                run.path,
                run.board_id,
                run.project_name,
                run.decomposer,
                run.complexity,
                run.provider,
                run.model,
                run.num_agents,
                run.started_at.isoformat(),
                run.ended_at.isoformat() if run.ended_at else None,
                run.total_tasks,
                run.completed_tasks,
                run.blocked_tasks,
                run.budget_usd,
                run.notes,
            ),
        )
        self.conn.commit()

    def record_price(self, price: ModelPrice) -> None:
        """Insert one ``model_prices`` row.

        Raises
        ------
        sqlite3.IntegrityError
            If a row with the same ``(model, provider, effective_from)``
            already exists. Use a different ``effective_from`` to update.
        """
        self.conn.execute(
            """
            INSERT INTO model_prices (
                model, provider, effective_from, input_per_million,
                cache_creation_per_million, cache_read_per_million,
                output_per_million, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                price.model,
                price.provider,
                price.effective_from.isoformat(),
                price.input_per_million,
                price.cache_creation_per_million,
                price.cache_read_per_million,
                price.output_per_million,
                price.source,
            ),
        )
        self.conn.commit()

    def upsert_project_name(self, project_id: str, name: str) -> None:
        """Snapshot a project's human-readable name into cost storage.

        Called whenever Marcus knows both the project_id and its name —
        most importantly at PlannerContext push and at WorkerJSONLIngester
        binding resolution. Idempotent: same (project_id, name) is a no-op
        after the first call; a name change updates in place and bumps
        ``last_seen``.

        The cost dashboard reads from this table as the primary name
        source so deleted projects still render with their real name.
        """
        if not project_id or not name:
            return
        self.conn.execute(
            """
            INSERT INTO project_names (project_id, name)
            VALUES (?, ?)
            ON CONFLICT(project_id) DO UPDATE SET
                name = excluded.name,
                last_seen = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            """,
            (project_id, name),
        )
        self.conn.commit()

    def get_project_name(self, project_id: str) -> Optional[str]:
        """Return the snapshotted name for ``project_id``, or None."""
        row = self.conn.execute(
            "SELECT name FROM project_names WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        return row[0] if row else None

    def rebind_project_id(self, *, from_id: str, to_id: str) -> int:
        """Re-attribute every token_events row from one project to another.

        Used by the ``create_project`` flow: the tool pushes a placeholder
        PlannerContext at entry so the heavy decomposition LLM calls land
        with attribution. Once the tool returns the real project_id, this
        method UPDATEs every row that carries the placeholder so the
        spend ends up on the new project's books, not the 'unassigned'
        bucket.

        Also drops the placeholder row from ``project_names`` so we
        don't leak an orphan name entry indexed by ``pending:<hex>``
        for every project creation (Kaia review on #515).

        Returns the number of token_events rows reattributed.
        """
        if not from_id or not to_id or from_id == to_id:
            return 0
        cur = self.conn.execute(
            "UPDATE token_events SET project_id = ? WHERE project_id = ?",
            (to_id, from_id),
        )
        self.conn.execute(
            "DELETE FROM project_names WHERE project_id = ?",
            (from_id,),
        )
        self.conn.commit()
        return cur.rowcount or 0

    def set_project_budget(
        self,
        project_id: str,
        budget_usd: float,
        note: Optional[str] = None,
    ) -> None:
        """Upsert a project-level budget cap.

        Project budgets live in the cost DB rather than Marcus's
        ProjectRegistry because the cap is a cost concept, and keeping
        it here lets Cato own the write path without touching project
        metadata. Re-calling with the same ``project_id`` updates the
        cap in place; ``set_at`` is refreshed automatically.

        Parameters
        ----------
        project_id : str
            Marcus project_id. Caller is responsible for normalizing to
            the canonical (dashless) form — see
            :func:`src.cost_tracking.cost_recorder.canonical_project_id`.
        budget_usd : float
            USD ceiling. Negative or zero means "no cap" (the row is
            removed instead so the dashboard's "no budget set" hint
            shows).
        note : str, optional
            Free-text annotation (e.g., "PoC budget", "Q2 cap").
        """
        if budget_usd <= 0:
            self.conn.execute(
                "DELETE FROM project_budgets WHERE project_id = ?",
                (project_id,),
            )
        else:
            self.conn.execute(
                """
                INSERT INTO project_budgets (project_id, budget_usd, note)
                VALUES (?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    budget_usd=excluded.budget_usd,
                    note=excluded.note,
                    set_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                """,
                (project_id, budget_usd, note),
            )
        self.conn.commit()

    def get_project_budget(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Return the budget row for a project, or None if no cap is set.

        Returns
        -------
        dict or None
            ``{budget_usd, set_at, note}`` when a cap exists.
        """
        row = self.conn.execute(
            """
            SELECT budget_usd, set_at, note FROM project_budgets
            WHERE project_id = ?
            """,
            (project_id,),
        ).fetchone()
        if row is None:
            return None
        return {"budget_usd": row[0], "set_at": row[1], "note": row[2]}

    def load_seed_prices(self, prices: Optional[List[ModelPrice]] = None) -> None:
        """Insert default pricing rows if not already present.

        Parameters
        ----------
        prices : list of ModelPrice, optional
            Override the built-in defaults. Useful for tests.

        Notes
        -----
        Idempotent: rows whose ``(model, provider, effective_from)`` already
        exist are skipped (``INSERT OR IGNORE``).
        """
        rows = prices if prices is not None else DEFAULT_SEED
        self.conn.executemany(
            """
            INSERT OR IGNORE INTO model_prices (
                model, provider, effective_from, input_per_million,
                cache_creation_per_million, cache_read_per_million,
                output_per_million, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    p.model,
                    p.provider,
                    p.effective_from.isoformat(),
                    p.input_per_million,
                    p.cache_creation_per_million,
                    p.cache_read_per_million,
                    p.output_per_million,
                    p.source,
                )
                for p in rows
            ],
        )
        self.conn.commit()

    # -- lifecycle ---------------------------------------------------------

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self.conn.close()
