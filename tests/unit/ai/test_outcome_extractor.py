"""
Unit tests for user-outcome extraction (issue #449).

The decomposer treats specs as flat feature lists, missing the user-visible
outcomes the product must satisfy.  ``extract_user_outcomes`` produces a
list of ``UserOutcome`` records that downstream stages use as decomposition
constraints and as the basis for the ``intent_fidelity_score`` metric.

These tests exercise the extractor in isolation; both LLM calls
(extraction and the verifiability self-check) are mocked.
"""

from typing import Any, Sequence
from unittest.mock import AsyncMock

import pytest

from src.ai.advanced.prd.outcome_extractor import (
    UserOutcome,
    extract_user_outcomes,
    filter_to_verifiable_capabilities,
)

pytestmark = pytest.mark.unit


# Filter response that approves a single play-game outcome.  Used by
# extraction tests where the spec produces exactly one outcome.
_FILTER_APPROVES_PLAY = (
    '{"verdicts": {"outcome_play_game": '
    '{"verifiable": true, "reason": "concrete user-visible action"}}}'
)


def _llm_with_responses(*responses: str) -> AsyncMock:
    """Build an AsyncMock LLM that returns each response in sequence.

    extract_user_outcomes makes two LLM calls (extraction + filter), so
    most extraction tests need to provide both payloads in order.
    """
    mock = AsyncMock()
    mock.analyze = AsyncMock(side_effect=list(responses))
    return mock


class TestUserOutcomeDataclass:
    """``UserOutcome`` enforces structural invariants only.

    Semantic invariants (positive capability, no negations, no vague
    phrasings) are enforced by :func:`filter_to_verifiable_capabilities`
    via an LLM self-check, NOT by pattern matching here.  The dataclass
    only checks types and non-emptiness.
    """

    def test_has_required_fields(self) -> None:
        """All four required fields are accepted as keyword args."""
        outcome = UserOutcome(
            id="outcome_play_game",
            action="user can play the snake game in their browser",
            success_signal="snake visibly moves, food appears, score updates",
            scope="in_scope",
        )
        assert outcome.id == "outcome_play_game"
        assert outcome.scope == "in_scope"

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

    def test_action_must_be_non_empty(self) -> None:
        """Empty action means nothing for downstream coverage to address."""
        with pytest.raises(ValueError, match="action"):
            UserOutcome(
                id="outcome_x",
                action="   ",
                success_signal="X is observable",
                scope="in_scope",
            )

    def test_dataclass_does_not_enforce_semantic_constraints(self) -> None:
        """Constructing a 'bad' outcome at the dataclass layer succeeds.

        This is the design point: the dataclass validates SHAPE only.
        Semantic checks (vague phrasings, negations, non-capability
        actions) happen in :func:`filter_to_verifiable_capabilities`
        via an LLM call.  We test that the LLM filter catches these
        elsewhere.  The dataclass should not be enforcing language rules.
        """
        # All of these would have raised under the old pattern-matching
        # validation.  Now they construct cleanly because the LLM filter
        # is the right place to evaluate them.
        UserOutcome(
            id="outcome_render",
            action="implement rendering",
            success_signal="canvas draws snake",
            scope="in_scope",
        )
        UserOutcome(
            id="outcome_negate",
            action="user cannot log in",
            success_signal="login fails",
            scope="in_scope",
        )
        UserOutcome(
            id="outcome_vague",
            action="user can use the app",
            success_signal="the app works",
            scope="in_scope",
        )


class TestExtractUserOutcomes:
    """``extract_user_outcomes`` queries the LLM and validates each result."""

    @pytest.fixture
    def llm_returning(self) -> Any:
        """Build an AsyncMock LLM client that returns the given JSON string.

        Single-payload variant — useful for tests that only get as far
        as the extraction call (e.g. malformed-JSON tests).  For tests
        that exercise the full pipeline, use ``_llm_with_responses``
        directly with both extraction + filter payloads.
        """

        def _build(payload: str) -> AsyncMock:
            mock = AsyncMock()
            mock.analyze = AsyncMock(return_value=payload)
            return mock

        return _build

    @pytest.mark.asyncio
    async def test_visual_spec_yields_render_outcome(self) -> None:
        """Snake game spec must produce an outcome about playing/seeing the game.

        This is the v31-snake regression: ``"build a snake game"`` previously
        produced a task graph with no rendering task because the decomposer
        treated rendering as implicit.  The outcome layer makes it explicit.
        """
        llm = _llm_with_responses(
            '{"outcomes": ['
            '{"id": "outcome_play_game",'
            ' "action": "user can play the snake game in their browser",'
            ' "success_signal": "snake visibly moves on a board, food appears,'
            ' score updates after each food eaten",'
            ' "scope": "in_scope"}'
            "]}",
            _FILTER_APPROVES_PLAY,
        )

        outcomes = await extract_user_outcomes(
            spec="build a snake game", llm_client=llm
        )

        assert len(outcomes) == 1
        assert outcomes[0].id == "outcome_play_game"
        assert "play the snake game" in outcomes[0].action
        assert outcomes[0].scope == "in_scope"

    @pytest.mark.asyncio
    async def test_api_spec_yields_endpoint_invocation_outcome(self) -> None:
        """API spec must produce outcomes about calling the endpoints."""
        llm = _llm_with_responses(
            '{"outcomes": ['
            '{"id": "outcome_get_user",'
            ' "action": "user can call GET /users/:id and receive JSON",'
            ' "success_signal": "200 status, body contains id and name",'
            ' "scope": "in_scope"}'
            "]}",
            '{"verdicts": {"outcome_get_user": '
            '{"verifiable": true, "reason": "concrete API call"}}}',
        )

        outcomes = await extract_user_outcomes(
            spec="user management service exposing CRUD endpoints",
            llm_client=llm,
        )

        assert len(outcomes) == 1
        assert "call GET" in outcomes[0].action

    @pytest.mark.asyncio
    async def test_scope_inheritance_from_spec(self) -> None:
        """Outcomes the spec excludes must be tagged out_of_scope, not dropped.

        Out-of-scope retention is important so the audit trail preserves
        what the LLM considered and rejected — debuggable when an outcome
        looks missing.
        """
        llm = _llm_with_responses(
            '{"outcomes": ['
            '{"id": "outcome_play",'
            ' "action": "user can play the snake game",'
            ' "success_signal": "game is visible and interactive",'
            ' "scope": "in_scope"},'
            '{"id": "outcome_login",'
            ' "action": "user can log in with a password",'
            ' "success_signal": "credentials accepted, session cookie set",'
            ' "scope": "out_of_scope"}'
            "]}",
            '{"verdicts": {'
            '"outcome_play": {"verifiable": true, "reason": "concrete"},'
            '"outcome_login": {"verifiable": true, "reason": "concrete"}'
            "}}",
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
    async def test_vague_outcomes_are_rejected_by_llm_filter(self) -> None:
        """LLM filter pass drops vague outcomes — replaces the old denylist.

        The extractor LLM produces a vague outcome ("user can use the
        application").  The filter LLM pass evaluates it as
        verifiable=False and drops it.  Since it was the only outcome,
        extract_user_outcomes raises rather than silently returning an
        empty list — every spec implies at least one good outcome.
        """
        llm = _llm_with_responses(
            '{"outcomes": ['
            '{"id": "outcome_use",'
            ' "action": "user can use the application",'
            ' "success_signal": "it works",'
            ' "scope": "in_scope"}'
            "]}",
            '{"verdicts": {"outcome_use": '
            '{"verifiable": false, "reason": "vague — no concrete user action"}}}',
        )

        with pytest.raises(ValueError, match="failed the verifiability"):
            await extract_user_outcomes(spec="anything", llm_client=llm)

    @pytest.mark.asyncio
    async def test_negation_outcomes_are_rejected_by_llm_filter(self) -> None:
        """LLM filter drops negations — replaces denylist regex matching."""
        llm = _llm_with_responses(
            '{"outcomes": ['
            '{"id": "outcome_negate",'
            ' "action": "user cannot bypass the paywall",'
            ' "success_signal": "paywall blocks access",'
            ' "scope": "in_scope"}'
            "]}",
            '{"verdicts": {"outcome_negate": '
            '{"verifiable": false, "reason": "negation, not a positive capability"}}}',
        )

        with pytest.raises(ValueError, match="failed the verifiability"):
            await extract_user_outcomes(spec="paywall app", llm_client=llm)

    @pytest.mark.asyncio
    async def test_malformed_llm_response_raises(self, llm_returning: Any) -> None:
        """Non-JSON / missing 'outcomes' key surfaces a clear error."""
        llm = llm_returning("totally not json")
        with pytest.raises(ValueError, match="JSON"):
            await extract_user_outcomes(spec="anything", llm_client=llm)

    @pytest.mark.asyncio
    async def test_null_id_field_is_rejected(self, llm_returning: Any) -> None:
        """LLM null for required field raises — must not coerce to 'None'.

        Codex P1 regression (PR #453): the original ``str(item.get(...))``
        coercion turned ``None`` into the literal string ``"None"`` which
        is non-empty and silently passed validation, polluting outcome
        ids used by ``compute_coverage``.
        """
        llm = llm_returning(
            '{"outcomes": ['
            '{"id": null,'
            ' "action": "user can play",'
            ' "success_signal": "snake moves",'
            ' "scope": "in_scope"}'
            "]}"
        )
        with pytest.raises(ValueError, match=r"'id'.*string"):
            await extract_user_outcomes(spec="x", llm_client=llm)

    @pytest.mark.asyncio
    async def test_null_success_signal_is_rejected(self, llm_returning: Any) -> None:
        llm = llm_returning(
            '{"outcomes": ['
            '{"id": "o1",'
            ' "action": "user can play",'
            ' "success_signal": null,'
            ' "scope": "in_scope"}'
            "]}"
        )
        with pytest.raises(ValueError, match=r"'success_signal'.*string"):
            await extract_user_outcomes(spec="x", llm_client=llm)

    @pytest.mark.asyncio
    async def test_non_string_field_is_rejected(self, llm_returning: Any) -> None:
        """An integer where a string is expected also raises."""
        llm = llm_returning(
            '{"outcomes": ['
            '{"id": 42,'
            ' "action": "user can play",'
            ' "success_signal": "snake moves",'
            ' "scope": "in_scope"}'
            "]}"
        )
        with pytest.raises(ValueError, match=r"'id'.*string"):
            await extract_user_outcomes(spec="x", llm_client=llm)

    @pytest.mark.asyncio
    async def test_empty_outcome_list_raises(self, llm_returning: Any) -> None:
        """An LLM that produces no outcomes is a failure, not a clean result.

        Every project spec implies at least one user-visible outcome; if the
        extractor gets back zero, the LLM ignored the prompt.  Surface it.
        """
        llm = llm_returning('{"outcomes": []}')
        with pytest.raises(ValueError, match="no outcomes"):
            await extract_user_outcomes(spec="build something", llm_client=llm)


def _outcome(
    out_id: str = "o1",
    action: str = "user can play the snake game",
    signal: str = "snake visibly moves",
    scope: str = "in_scope",
) -> UserOutcome:
    """Build a structurally-valid UserOutcome for filter tests."""
    return UserOutcome(id=out_id, action=action, success_signal=signal, scope=scope)


class TestFilterToVerifiableCapabilities:
    """LLM self-check pass replaces hand-curated denylists.

    Catches negations, vague phrasings, internal/non-user-facing
    actions, and any other antipattern an LLM understands semantically
    — without us maintaining a list of bad strings.
    """

    @staticmethod
    def _llm(payload: str) -> AsyncMock:
        mock = AsyncMock()
        mock.analyze = AsyncMock(return_value=payload)
        return mock

    @pytest.mark.asyncio
    async def test_keeps_outcomes_marked_verifiable(self) -> None:
        outcomes = [
            _outcome("o_play", "user can play snake", "snake moves"),
            _outcome("o_score", "user can see score", "score visible in DOM"),
        ]
        llm = self._llm(
            '{"verdicts": {'
            '"o_play": {"verifiable": true, "reason": "concrete"},'
            '"o_score": {"verifiable": true, "reason": "concrete"}'
            "}}"
        )
        kept = await filter_to_verifiable_capabilities(outcomes, llm)
        assert [o.id for o in kept] == ["o_play", "o_score"]

    @pytest.mark.asyncio
    async def test_drops_outcomes_marked_not_verifiable(self) -> None:
        """LLM marks vague/negation outcomes as not verifiable; they drop."""
        outcomes = [
            _outcome("o_good", "user can play snake", "snake moves"),
            _outcome("o_vague", "user can use the app", "app works"),
            _outcome("o_negate", "user cannot register", "registration fails"),
        ]
        llm = self._llm(
            '{"verdicts": {'
            '"o_good": {"verifiable": true, "reason": "concrete"},'
            '"o_vague": {"verifiable": false, "reason": "too vague"},'
            '"o_negate": {"verifiable": false, "reason": "negation"}'
            "}}"
        )
        kept = await filter_to_verifiable_capabilities(outcomes, llm)
        assert [o.id for o in kept] == ["o_good"]

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty_without_llm_call(self) -> None:
        """No outcomes means no LLM call — saves cost."""
        mock = AsyncMock()
        mock.analyze = AsyncMock()
        kept = await filter_to_verifiable_capabilities([], mock)
        assert kept == []
        mock.analyze.assert_not_called()

    @pytest.mark.asyncio
    async def test_outcome_missing_from_llm_response_is_kept(self) -> None:
        """A missing verdict defaults to keep, with a logged warning.

        Dropping a structurally-valid outcome because the filter LLM
        forgot it would be silent loss.  A coverage gap downstream is
        recoverable; a missing outcome is not.
        """
        outcomes = [
            _outcome("o_evaluated", "user can play", "moves"),
            _outcome("o_forgotten", "user can score", "score visible"),
        ]
        llm = self._llm(
            '{"verdicts": {'
            '"o_evaluated": {"verifiable": true, "reason": "concrete"}'
            "}}"
        )
        kept = await filter_to_verifiable_capabilities(outcomes, llm)
        assert [o.id for o in kept] == ["o_evaluated", "o_forgotten"]

    @pytest.mark.asyncio
    async def test_malformed_response_raises(self) -> None:
        outcomes = [_outcome()]
        llm = self._llm("not json")
        with pytest.raises(ValueError, match="malformed JSON"):
            await filter_to_verifiable_capabilities(outcomes, llm)

    @pytest.mark.asyncio
    async def test_missing_verdicts_key_raises(self) -> None:
        outcomes = [_outcome()]
        llm = self._llm('{"wrong_key": {}}')
        with pytest.raises(ValueError, match="verdicts"):
            await filter_to_verifiable_capabilities(outcomes, llm)

    @pytest.mark.asyncio
    async def test_non_boolean_verifiable_raises(self) -> None:
        """A verdict with non-boolean ``verifiable`` is malformed."""
        outcomes = [_outcome("o1")]
        llm = self._llm('{"verdicts": {"o1": {"verifiable": "yes", "reason": "x"}}}')
        with pytest.raises(ValueError, match="verifiable"):
            await filter_to_verifiable_capabilities(outcomes, llm)

    @pytest.mark.asyncio
    async def test_extract_raises_when_filter_drops_everything(self) -> None:
        """If the filter drops every outcome, extraction surfaces the failure.

        End-to-end coverage of the extractor's "every spec implies at
        least one good outcome" invariant via the new filter step.
        """
        responses: Sequence[str] = (
            '{"outcomes": ['
            '{"id": "outcome_bad",'
            ' "action": "user can use the app",'
            ' "success_signal": "it works",'
            ' "scope": "in_scope"}'
            "]}",
            '{"verdicts": {"outcome_bad": '
            '{"verifiable": false, "reason": "vague"}}}',
        )
        llm = _llm_with_responses(*responses)
        with pytest.raises(ValueError, match="failed the verifiability"):
            await extract_user_outcomes(spec="x", llm_client=llm)
