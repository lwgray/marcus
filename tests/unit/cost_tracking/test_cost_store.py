"""
Unit tests for src.cost_tracking.cost_store.

Validates schema creation, seed loading, event/experiment writes, and the
v_event_cost view's price-versioning behavior.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.cost_tracking.cost_store import (
    CostStore,
    Experiment,
    ModelPrice,
    TokenEvent,
)


@pytest.fixture
def store(tmp_path: Path) -> CostStore:
    """Provide a fresh CostStore backed by a tmp SQLite file."""
    db = tmp_path / "costs.db"
    return CostStore(db_path=db)


@pytest.fixture
def seeded_store(store: CostStore) -> CostStore:
    """CostStore with a single default model_prices row for tests."""
    store.record_price(
        ModelPrice(
            model="claude-sonnet-4-6",
            provider="anthropic",
            effective_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
            input_per_million=3.0,
            cache_creation_per_million=3.75,
            cache_read_per_million=0.30,
            output_per_million=15.0,
            source="default",
        )
    )
    return store


@pytest.fixture
def base_event() -> TokenEvent:
    """Reusable TokenEvent for happy-path tests."""
    return TokenEvent(
        experiment_id="exp_1",
        project_id="proj_1",
        agent_id="planner",
        agent_role="planner",
        operation="parse_prd",
        provider="anthropic",
        model="claude-sonnet-4-6",
        input_tokens=1000,
        cache_creation_tokens=2000,
        cache_read_tokens=4000,
        output_tokens=500,
    )


class TestSchemaInitialization:
    """Schema and view creation."""

    def test_init_creates_all_tables(self, store: CostStore) -> None:
        """All four schema objects exist after construction."""
        names = {
            row[0]
            for row in store.conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
            )
        }
        assert {"experiments", "token_events", "model_prices", "v_event_cost"} <= names

    def test_init_enables_wal_mode(self, store: CostStore) -> None:
        """WAL mode enabled for safe concurrent reads during writes."""
        mode = store.conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"

    def test_token_events_total_tokens_is_generated(
        self, seeded_store: CostStore, base_event: TokenEvent
    ) -> None:
        """total_tokens column auto-sums the four input fields."""
        seeded_store.record_event(base_event)
        row = seeded_store.conn.execute(
            "SELECT total_tokens FROM token_events"
        ).fetchone()
        assert row[0] == 1000 + 2000 + 4000 + 500


class TestRecordEvent:
    """token_events insert behavior."""

    def test_records_event_returns_event_id(
        self, seeded_store: CostStore, base_event: TokenEvent
    ) -> None:
        """record_event returns the auto-incremented PK."""
        event_id = seeded_store.record_event(base_event)
        assert isinstance(event_id, int) and event_id > 0

    def test_records_event_persists_all_fields(
        self, seeded_store: CostStore, base_event: TokenEvent
    ) -> None:
        """Every TokenEvent field round-trips through the DB."""
        seeded_store.record_event(base_event)
        row = seeded_store.conn.execute(
            "SELECT experiment_id, agent_id, agent_role, operation, "
            "input_tokens, cache_creation_tokens, cache_read_tokens, "
            "output_tokens FROM token_events"
        ).fetchone()
        assert row == (
            "exp_1",
            "planner",
            "planner",
            "parse_prd",
            1000,
            2000,
            4000,
            500,
        )

    def test_default_status_is_ok(
        self, seeded_store: CostStore, base_event: TokenEvent
    ) -> None:
        """status defaults to 'ok' when not provided."""
        seeded_store.record_event(base_event)
        status = seeded_store.conn.execute(
            "SELECT status FROM token_events"
        ).fetchone()[0]
        assert status == "ok"

    def test_duplicate_request_id_is_ignored(
        self, seeded_store: CostStore, base_event: TokenEvent
    ) -> None:
        """Re-inserting an event with the same request_id is idempotent.

        Cato's dashboard polls run_ingest every 30s with a fresh ingester
        whose in-memory dedup set is empty. Without DB-level dedup, every
        poll re-inserts every event and counts double silently. The
        partial UNIQUE index on request_id plus INSERT OR IGNORE
        guarantees idempotency regardless of process boundaries.
        """
        base_event.request_id = "req_dup_1"
        first_id = seeded_store.record_event(base_event)
        second_id = seeded_store.record_event(base_event)

        assert first_id == second_id
        count = seeded_store.conn.execute(
            "SELECT COUNT(*) FROM token_events WHERE request_id = 'req_dup_1'"
        ).fetchone()[0]
        assert count == 1

    def test_init_dedups_preexisting_duplicates(self, tmp_path: Path) -> None:
        """Opening a dirty DB compacts duplicates before adding the index.

        Simulates a pre-PR-#511 install: build a DB without the partial
        UNIQUE index, hand-insert duplicate request_id rows (which the
        old INSERT path allowed), then re-open via CostStore. The
        constructor's migration must dedup so CREATE UNIQUE INDEX
        succeeds and Marcus starts.
        """
        db = tmp_path / "dirty.db"
        conn = sqlite3.connect(str(db))
        conn.executescript("""
            CREATE TABLE token_events (
              event_id     INTEGER PRIMARY KEY AUTOINCREMENT,
              experiment_id TEXT NOT NULL,
              project_id    TEXT NOT NULL,
              agent_id      TEXT NOT NULL,
              agent_role    TEXT NOT NULL,
              parent_agent_id TEXT,
              task_id       TEXT,
              subtask_id    TEXT,
              operation     TEXT NOT NULL,
              provider      TEXT NOT NULL,
              model         TEXT NOT NULL,
              input_tokens  INTEGER NOT NULL DEFAULT 0,
              cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
              cache_read_tokens     INTEGER NOT NULL DEFAULT 0,
              output_tokens INTEGER NOT NULL DEFAULT 0,
              total_tokens  INTEGER GENERATED ALWAYS AS
                              (input_tokens + cache_creation_tokens
                               + cache_read_tokens + output_tokens) STORED,
              latency_ms    INTEGER,
              session_id    TEXT,
              turn_index    INTEGER,
              request_id    TEXT,
              status        TEXT NOT NULL DEFAULT 'ok',
              error_type    TEXT,
              timestamp     TIMESTAMP NOT NULL DEFAULT '2026-05-11T00:00:00.000Z'
            );
            """)
        for _ in range(3):
            conn.execute(
                "INSERT INTO token_events "
                "(experiment_id, project_id, agent_id, agent_role, operation, "
                " provider, model, request_id) VALUES "
                "('e','p','a','planner','op','anthropic','m','req_dup')"
            )
        for _ in range(2):
            conn.execute(
                "INSERT INTO token_events "
                "(experiment_id, project_id, agent_id, agent_role, operation, "
                " provider, model, request_id) VALUES "
                "('e','p','a','planner','op','anthropic','m', NULL)"
            )
        conn.commit()
        conn.close()

        store = CostStore(db_path=db)

        dup_count = store.conn.execute(
            "SELECT COUNT(*) FROM token_events WHERE request_id = 'req_dup'"
        ).fetchone()[0]
        assert dup_count == 1
        null_count = store.conn.execute(
            "SELECT COUNT(*) FROM token_events WHERE request_id IS NULL"
        ).fetchone()[0]
        assert null_count == 2
        with pytest.raises(sqlite3.IntegrityError):
            store.conn.execute(
                "INSERT INTO token_events "
                "(experiment_id, project_id, agent_id, agent_role, operation, "
                " provider, model, request_id) VALUES "
                "('e','p','a','planner','op','anthropic','m','req_dup')"
            )

    def test_null_request_id_allows_multiple_rows(
        self, seeded_store: CostStore, base_event: TokenEvent
    ) -> None:
        """NULL request_id is exempt from the unique constraint.

        Older rows and non-Claude providers may lack a request_id; the
        partial WHERE clause keeps them unconstrained so multiple NULLs
        can coexist.
        """
        assert base_event.request_id is None
        seeded_store.record_event(base_event)
        seeded_store.record_event(base_event)
        count = seeded_store.conn.execute(
            "SELECT COUNT(*) FROM token_events WHERE request_id IS NULL"
        ).fetchone()[0]
        assert count == 2


class TestRecordExperiment:
    """experiments table upsert behavior."""

    def test_records_new_experiment(self, store: CostStore) -> None:
        """A fresh experiment_id inserts a row."""
        store.record_experiment(
            Experiment(
                experiment_id="exp_1",
                project_id="proj_1",
                started_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
                project_name="hangman",
            )
        )
        row = store.conn.execute(
            "SELECT project_id, project_name FROM experiments"
        ).fetchone()
        assert row == ("proj_1", "hangman")

    def test_upserts_existing_experiment(self, store: CostStore) -> None:
        """Re-recording the same experiment_id updates fields, doesn't duplicate."""
        started = datetime(2026, 5, 10, tzinfo=timezone.utc)
        store.record_experiment(
            Experiment(experiment_id="exp_1", project_id="p", started_at=started)
        )
        store.record_experiment(
            Experiment(
                experiment_id="exp_1",
                project_id="p",
                started_at=started,
                completed_tasks=5,
            )
        )
        rows = store.conn.execute("SELECT COUNT(*) FROM experiments").fetchone()
        assert rows[0] == 1
        completed = store.conn.execute(
            "SELECT completed_tasks FROM experiments WHERE experiment_id='exp_1'"
        ).fetchone()[0]
        assert completed == 5


class TestRecordPrice:
    """model_prices versioning."""

    def test_records_price(self, store: CostStore) -> None:
        """A single price row inserts cleanly."""
        store.record_price(
            ModelPrice(
                model="m",
                provider="p",
                effective_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
                input_per_million=1.0,
                output_per_million=2.0,
                source="default",
            )
        )
        row = store.conn.execute("SELECT COUNT(*) FROM model_prices").fetchone()
        assert row[0] == 1

    def test_versioned_prices_coexist(self, store: CostStore) -> None:
        """Two prices for the same (model, provider) at different effective_from coexist."""
        for ef in (
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 1, tzinfo=timezone.utc),
        ):
            store.record_price(
                ModelPrice(
                    model="m",
                    provider="p",
                    effective_from=ef,
                    input_per_million=1.0,
                    output_per_million=2.0,
                    source="default",
                )
            )
        count = store.conn.execute("SELECT COUNT(*) FROM model_prices").fetchone()[0]
        assert count == 2

    def test_duplicate_effective_from_rejected(self, store: CostStore) -> None:
        """Same (model, provider, effective_from) twice raises IntegrityError."""
        ef = datetime(2025, 1, 1, tzinfo=timezone.utc)
        price = ModelPrice(
            model="m",
            provider="p",
            effective_from=ef,
            input_per_million=1.0,
            output_per_million=2.0,
            source="default",
        )
        store.record_price(price)
        with pytest.raises(sqlite3.IntegrityError):
            store.record_price(price)


class TestEventCostView:
    """v_event_cost computes cost using the price active at event timestamp."""

    def test_cost_uses_active_price(
        self, seeded_store: CostStore, base_event: TokenEvent
    ) -> None:
        """1000 in + 2000 cache_create + 4000 cache_read + 500 out at default price."""
        seeded_store.record_event(base_event)
        cost = seeded_store.conn.execute(
            "SELECT cost_usd FROM v_event_cost"
        ).fetchone()[0]
        # 1000*3/1e6 + 2000*3.75/1e6 + 4000*0.30/1e6 + 500*15/1e6
        # = 0.003 + 0.0075 + 0.0012 + 0.0075 = 0.0192
        assert cost == pytest.approx(0.0192, rel=1e-6)

    def test_cost_uses_historical_price_when_event_predates_new_one(
        self, store: CostStore
    ) -> None:
        """Event at t=2025-06 uses 2025-01 price even if 2026-01 price exists."""
        old = datetime(2025, 1, 1, tzinfo=timezone.utc)
        new = datetime(2026, 1, 1, tzinfo=timezone.utc)
        store.record_price(
            ModelPrice(
                model="m",
                provider="p",
                effective_from=old,
                input_per_million=1.0,
                output_per_million=1.0,
                source="default",
            )
        )
        store.record_price(
            ModelPrice(
                model="m",
                provider="p",
                effective_from=new,
                input_per_million=10.0,
                output_per_million=10.0,
                source="default",
            )
        )
        # Event in mid-2025 should use old price
        store.record_event(
            TokenEvent(
                experiment_id="e",
                project_id="proj",
                agent_id="a",
                agent_role="planner",
                operation="op",
                provider="p",
                model="m",
                input_tokens=1_000_000,
                output_tokens=0,
                timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            )
        )
        cost = store.conn.execute("SELECT cost_usd FROM v_event_cost").fetchone()[0]
        assert cost == pytest.approx(1.0, rel=1e-6)


class TestCodexP1LegacyModelSeeds:
    """Regression: out-of-box Anthropic models must seed (Codex P1 on PR #497).

    Marcus's default config uses ``claude-3-haiku-20240307`` and the historic
    settings default ``claude-3-sonnet-20241022``. Without seed rows, the
    inner join in ``v_event_cost`` drops every event for those models from
    aggregations.
    """

    def test_default_anthropic_model_has_seed_price(self, store: CostStore) -> None:
        """The model anthropic_provider.py defaults to is in DEFAULT_SEED."""
        store.load_seed_prices()
        models = {
            row[0]
            for row in store.conn.execute(
                "SELECT model FROM model_prices WHERE provider='anthropic'"
            )
        }
        assert "claude-3-haiku-20240307" in models
        assert "claude-3-sonnet-20241022" in models

    def test_event_for_legacy_model_appears_in_cost_view(
        self, store: CostStore
    ) -> None:
        """Event for claude-3-haiku-20240307 produces a v_event_cost row."""
        store.load_seed_prices()
        store.record_event(
            TokenEvent(
                experiment_id="e",
                project_id="p",
                agent_id="planner",
                agent_role="planner",
                operation="parse_prd",
                provider="anthropic",
                model="claude-3-haiku-20240307",
                input_tokens=1_000_000,
                output_tokens=0,
            )
        )
        cost = store.conn.execute("SELECT cost_usd FROM v_event_cost").fetchone()
        assert cost is not None  # would be None if INNER JOIN dropped the event
        assert cost[0] == pytest.approx(0.25, rel=1e-6)


class TestCodexP2TimestampFormat:
    """Regression: same-day price must apply to events lacking explicit ts.

    Codex P2 on PR #497: SQLite's bare CURRENT_TIMESTAMP defaults to
    ``YYYY-MM-DD HH:MM:SS`` (space separator) while ``record_price``
    stores ISO format with a ``T`` separator. Lexical comparison in
    ``v_event_cost`` would silently drop events whose default timestamp
    sorts before any price row for the same model.
    """

    def test_event_with_default_timestamp_joins_iso_priced_row(
        self, store: CostStore
    ) -> None:
        """Insert price first, then event without a timestamp; v_event_cost row exists."""
        store.record_price(
            ModelPrice(
                model="m",
                provider="p",
                effective_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
                input_per_million=1.0,
                output_per_million=1.0,
                source="default",
            )
        )
        store.record_event(
            TokenEvent(
                experiment_id="e",
                project_id="p",
                agent_id="planner",
                agent_role="planner",
                operation="op",
                provider="p",
                model="m",
                input_tokens=1_000_000,
                output_tokens=0,
                # timestamp deliberately omitted — uses SQLite default
            )
        )
        row = store.conn.execute("SELECT cost_usd FROM v_event_cost").fetchone()
        assert row is not None, "default timestamp format must allow join"
        assert row[0] == pytest.approx(1.0, rel=1e-6)

    def test_default_timestamp_uses_iso_t_separator(self, store: CostStore) -> None:
        """Stored default timestamp has the 'T' separator, not a space."""
        store.load_seed_prices()
        store.record_event(
            TokenEvent(
                experiment_id="e",
                project_id="p",
                agent_id="planner",
                agent_role="planner",
                operation="op",
                provider="anthropic",
                model="claude-3-haiku-20240307",
                input_tokens=1,
                output_tokens=1,
            )
        )
        ts = store.conn.execute("SELECT timestamp FROM token_events").fetchone()[0]
        assert (
            "T" in ts and " " not in ts
        ), f"expected ISO format with T separator, got {ts!r}"


class TestSeedLoader:
    """load_seed_prices idempotency."""

    def test_load_seed_inserts_default_prices(self, store: CostStore) -> None:
        """Calling load_seed_prices populates the default Anthropic / OpenAI rows."""
        store.load_seed_prices()
        models = {
            row[0]
            for row in store.conn.execute(
                "SELECT model FROM model_prices WHERE source='default'"
            )
        }
        # At least the headline Anthropic + OpenAI defaults should be there
        assert "claude-sonnet-4-6" in models
        assert "claude-haiku-4-5" in models

    def test_load_seed_idempotent(self, store: CostStore) -> None:
        """Running load_seed_prices twice doesn't duplicate rows."""
        store.load_seed_prices()
        first_count = store.conn.execute(
            "SELECT COUNT(*) FROM model_prices"
        ).fetchone()[0]
        store.load_seed_prices()
        second_count = store.conn.execute(
            "SELECT COUNT(*) FROM model_prices"
        ).fetchone()[0]
        assert first_count == second_count
