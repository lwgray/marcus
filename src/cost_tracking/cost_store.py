"""
SQLite-backed event store for Marcus token usage and cost data.

Stores one row per LLM call (planner or worker) with full agent/task/model
attribution. Pricing lives in a versioned ``model_prices`` table and cost is
computed at query time via the ``v_event_cost`` view, so changing prices
never rewrites history.

Schema
------
- ``experiments``    : registry of runs (project, model, totals)
- ``token_events``   : one row per LLM call (immutable token counts)
- ``model_prices``   : versioned by ``effective_from``; edited by Cato UI
- ``v_event_cost``   : view joining events × the price active at each
                      event's timestamp, exposing ``cost_usd``

This module exposes a thin :class:`CostStore` wrapper. Aggregation queries
live in ``cost_aggregator.py``; this file only handles inserts and schema.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL: str = """
CREATE TABLE IF NOT EXISTS experiments (
  experiment_id    TEXT PRIMARY KEY,
  project_id       TEXT NOT NULL,
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
CREATE INDEX IF NOT EXISTS idx_exp_project ON experiments(project_id);

CREATE TABLE IF NOT EXISTS token_events (
  event_id              INTEGER PRIMARY KEY AUTOINCREMENT,
  experiment_id         TEXT NOT NULL,
  project_id            TEXT NOT NULL,
  agent_id              TEXT NOT NULL,
  agent_role            TEXT NOT NULL,
  parent_agent_id       TEXT,
  task_id               TEXT,
  subtask_id            TEXT,
  operation             TEXT NOT NULL,
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
CREATE INDEX IF NOT EXISTS idx_te_exp       ON token_events(experiment_id);
CREATE INDEX IF NOT EXISTS idx_te_project   ON token_events(project_id);
CREATE INDEX IF NOT EXISTS idx_te_agent     ON token_events(experiment_id, agent_id);
CREATE INDEX IF NOT EXISTS idx_te_task      ON token_events(task_id);
CREATE INDEX IF NOT EXISTS idx_te_op_model  ON token_events(operation, model);
CREATE INDEX IF NOT EXISTS idx_te_timestamp ON token_events(timestamp);

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
    experiment_id : str
        Marcus experiment ID.
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

    experiment_id: str
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
    latency_ms: Optional[int] = None
    session_id: Optional[str] = None
    turn_index: Optional[int] = None
    request_id: Optional[str] = None
    status: str = "ok"
    error_type: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class Experiment:
    """Experiment registry row."""

    experiment_id: str
    project_id: str
    started_at: datetime
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
        self._init_schema()

    def _init_schema(self) -> None:
        """Run schema DDL. Idempotent thanks to IF NOT EXISTS guards."""
        self.conn.executescript(SCHEMA_SQL)
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
            INSERT INTO token_events (
                experiment_id, project_id, agent_id, agent_role,
                parent_agent_id, task_id, subtask_id, operation,
                provider, model, input_tokens, cache_creation_tokens,
                cache_read_tokens, output_tokens, latency_ms, session_id,
                turn_index, request_id, status, error_type, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      COALESCE(?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')))
            """,
            (
                event.experiment_id,
                event.project_id,
                event.agent_id,
                event.agent_role,
                event.parent_agent_id,
                event.task_id,
                event.subtask_id,
                event.operation,
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
        event_id = cur.lastrowid
        if event_id is None:  # pragma: no cover - sqlite3 always returns rowid
            raise RuntimeError("sqlite3 did not return lastrowid")
        return event_id

    def record_experiment(self, exp: Experiment) -> None:
        """Upsert one ``experiments`` row keyed by ``experiment_id``."""
        self.conn.execute(
            """
            INSERT INTO experiments (
                experiment_id, project_id, board_id, project_name, decomposer,
                complexity, provider, model, num_agents, started_at, ended_at,
                total_tasks, completed_tasks, blocked_tasks, budget_usd, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(experiment_id) DO UPDATE SET
                project_id=excluded.project_id,
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
                exp.experiment_id,
                exp.project_id,
                exp.board_id,
                exp.project_name,
                exp.decomposer,
                exp.complexity,
                exp.provider,
                exp.model,
                exp.num_agents,
                exp.started_at.isoformat(),
                exp.ended_at.isoformat() if exp.ended_at else None,
                exp.total_tasks,
                exp.completed_tasks,
                exp.blocked_tasks,
                exp.budget_usd,
                exp.notes,
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
