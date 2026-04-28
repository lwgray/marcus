"""
Unit tests for user-outcome extraction (issue #449).

The decomposer treats specs as flat feature lists, missing the user-visible
outcomes the product must satisfy.  ``extract_user_outcomes`` produces a
list of ``UserOutcome`` records that downstream stages use as decomposition
constraints and as the basis for the ``intent_fidelity_score`` metric.

These tests exercise the extractor in isolation; the LLM is always mocked.
"""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.ai.advanced.prd.outcome_extractor import (
    UserOutcome,
    extract_user_outcomes,
)

pytestmark = pytest.mark.unit


class TestUserOutcomeDataclass:
    """``UserOutcome`` is a strict dataclass — invalid values raise."""

    def test_has_required_fields(self) -> None:
        """All four required fields are accepted as keyword args."""
        outcome = UserOutcome(
            id="outcome_play_game",
            action="user can play the snake game in their browser",
            success_signal="snake visibly moves, food appears, score updates",
            scope="in_scope",
        )
        assert outcome.id == "outcome_play_game"
        assert outcome.action.startswith("user can")
        assert outcome.success_signal
        assert outcome.scope == "in_scope"

    def test_action_must_express_user_capability(self) -> None:
        """An action without 'user can' / 'user is able to' is rejected.

        The whole point is to capture user-visible outcomes; bare feature
        descriptions like "implement rendering" are exactly the failure
        mode this prevents.
        """
        with pytest.raises(ValueError, match="user can"):
            UserOutcome(
                id="outcome_render",
                action="implement rendering",
                success_signal="canvas draws snake",
                scope="in_scope",
            )

    def test_action_rejects_vague_capability(self) -> None:
        """'user can use the app' is too vague and rejected."""
        with pytest.raises(ValueError, match="too vague"):
            UserOutcome(
                id="outcome_vague",
                action="user can use the app",
                success_signal="the app works",
                scope="in_scope",
            )

    def test_scope_must_be_known_value(self) -> None:
        """Scope must be 'in_scope' or 'out_of_scope'."""
        with pytest.raises(ValueError, match="scope"):
            UserOutcome(
                id="outcome_x",
                action="user can do X",
                success_signal="X is observable",
                scope="maybe",
            )

    def test_success_signal_required_non_empty(self) -> None:
        """An empty success_signal makes coverage unverifiable — reject it."""
        with pytest.raises(ValueError, match="success_signal"):
            UserOutcome(
                id="outcome_x",
                action="user can do X",
                success_signal="",
                scope="in_scope",
            )

    def test_id_must_be_non_empty(self) -> None:
        """An empty id breaks coverage mapping — reject it."""
        with pytest.raises(ValueError, match="id"):
            UserOutcome(
                id="",
                action="user can do X",
                success_signal="X is observable",
                scope="in_scope",
            )


class TestExtractUserOutcomes:
    """``extract_user_outcomes`` queries the LLM and validates each result."""

    @pytest.fixture
    def llm_returning(self) -> Any:
        """Build an AsyncMock LLM client that returns the given JSON string."""

        def _build(payload: str) -> AsyncMock:
            mock = AsyncMock()
            mock.analyze = AsyncMock(return_value=payload)
            return mock

        return _build

    @pytest.mark.asyncio
    async def test_visual_spec_yields_render_outcome(self, llm_returning: Any) -> None:
        """Snake game spec must produce an outcome about playing/seeing the game.

        This is the v31-snake regression: ``"build a snake game"`` previously
        produced a task graph with no rendering task because the decomposer
        treated rendering as implicit.  The outcome layer makes it explicit.
        """
        llm = llm_returning(
            '{"outcomes": ['
            '{"id": "outcome_play_game",'
            ' "action": "user can play the snake game in their browser",'
            ' "success_signal": "snake visibly moves on a board, food appears,'
            ' score updates after each food eaten",'
            ' "scope": "in_scope"}'
            "]}"
        )

        outcomes = await extract_user_outcomes(
            spec="build a snake game", llm_client=llm
        )

        assert len(outcomes) == 1
        assert outcomes[0].id == "outcome_play_game"
        assert "play the snake game" in outcomes[0].action
        assert outcomes[0].scope == "in_scope"

    @pytest.mark.asyncio
    async def test_api_spec_yields_endpoint_invocation_outcome(
        self, llm_returning: Any
    ) -> None:
        """API spec must produce outcomes about calling the endpoints."""
        llm = llm_returning(
            '{"outcomes": ['
            '{"id": "outcome_get_user",'
            ' "action": "user can call GET /users/:id and receive JSON",'
            ' "success_signal": "200 status, body contains id and name",'
            ' "scope": "in_scope"}'
            "]}"
        )

        outcomes = await extract_user_outcomes(
            spec="user management service exposing CRUD endpoints",
            llm_client=llm,
        )

        assert len(outcomes) == 1
        assert "call GET" in outcomes[0].action

    @pytest.mark.asyncio
    async def test_scope_inheritance_from_spec(self, llm_returning: Any) -> None:
        """Outcomes the spec excludes must be tagged out_of_scope, not dropped.

        Out-of-scope retention is important so the audit trail preserves
        what the LLM considered and rejected — debuggable when an outcome
        looks missing.
        """
        llm = llm_returning(
            '{"outcomes": ['
            '{"id": "outcome_play",'
            ' "action": "user can play the snake game",'
            ' "success_signal": "game is visible and interactive",'
            ' "scope": "in_scope"},'
            '{"id": "outcome_login",'
            ' "action": "user can log in with a password",'
            ' "success_signal": "credentials accepted, session cookie set",'
            ' "scope": "out_of_scope"}'
            "]}"
        )

        outcomes = await extract_user_outcomes(
            spec="build a snake game (no auth, no accounts)",
            llm_client=llm,
        )

        in_scope = [o for o in outcomes if o.scope == "in_scope"]
        out_scope = [o for o in outcomes if o.scope == "out_of_scope"]
        assert len(in_scope) == 1
        assert len(out_scope) == 1
        assert "log in" in out_scope[0].action

    @pytest.mark.asyncio
    async def test_vague_outcomes_are_rejected_at_extraction(
        self, llm_returning: Any
    ) -> None:
        """If the LLM returns a vague outcome, extraction raises rather than
        silently passing it downstream."""
        llm = llm_returning(
            '{"outcomes": ['
            '{"id": "outcome_use",'
            ' "action": "user can use the application",'
            ' "success_signal": "it works",'
            ' "scope": "in_scope"}'
            "]}"
        )

        with pytest.raises(ValueError, match="too vague"):
            await extract_user_outcomes(spec="anything", llm_client=llm)

    @pytest.mark.asyncio
    async def test_malformed_llm_response_raises(self, llm_returning: Any) -> None:
        """Non-JSON / missing 'outcomes' key surfaces a clear error."""
        llm = llm_returning("totally not json")
        with pytest.raises(ValueError, match="JSON"):
            await extract_user_outcomes(spec="anything", llm_client=llm)

    @pytest.mark.asyncio
    async def test_empty_outcome_list_raises(self, llm_returning: Any) -> None:
        """An LLM that produces no outcomes is a failure, not a clean result.

        Every project spec implies at least one user-visible outcome; if the
        extractor gets back zero, the LLM ignored the prompt.  Surface it.
        """
        llm = llm_returning('{"outcomes": []}')
        with pytest.raises(ValueError, match="no outcomes"):
            await extract_user_outcomes(spec="build something", llm_client=llm)
