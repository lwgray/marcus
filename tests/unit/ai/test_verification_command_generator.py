"""
Unit tests for :mod:`src.ai.advanced.prd.verification_command_generator`.

Background
----------
Issue #636 Phase A: Marcus generates verification commands per
:class:`UserOutcome` at setup time so the smoke gate can run
contract-authored commands at completion time instead of trusting
agent-authored ones (Invariant #2 v2 in ``CLAUDE.md``).

These tests cover the generator module:

- :class:`ContractVerification` dataclass serialization round-trips
- :func:`generate_verification_command` LLM contract (success, null,
  malformed JSON, missing fields)
- :func:`generate_verification_commands` fan-out semantics (parallelism,
  partial-failure handling)
"""

from __future__ import annotations

import json
from typing import List
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.ai.advanced.prd.outcome_extractor import UserOutcome
from src.ai.advanced.prd.verification_command_generator import (
    ContractVerification,
    generate_verification_command,
    generate_verification_commands,
)

pytestmark = pytest.mark.unit


def _outcome(
    id_: str = "outcome_play",
    action: str = "user can play the game",
    success_signal: str = "snake responds to arrow keys",
    scope: str = "in_scope",
) -> UserOutcome:
    """Build a UserOutcome with defaults sufficient for generator tests."""
    return UserOutcome(
        id=id_,
        action=action,
        success_signal=success_signal,
        scope=scope,
    )


def _stub_llm(response: str) -> MagicMock:
    """Return a mock LLM client that yields ``response`` from ``analyze``.

    Mirrors the contract :func:`safe_structured_call` expects: an async
    ``analyze(prompt, context)`` method returning a string.
    """
    client = MagicMock()
    client.analyze = AsyncMock(return_value=response)
    return client


# ---------------------------------------------------------------------------
# ContractVerification dataclass — round-trips and validation
# ---------------------------------------------------------------------------


class TestContractVerification:
    """Round-trip + validation semantics for the dataclass."""

    def test_to_dict_includes_required_fields(self):
        """``to_dict`` always emits the three required fields."""
        cv = ContractVerification(
            signal_id="outcome_play",
            command="npm test",
            description="run the test suite",
        )
        d = cv.to_dict()
        assert d == {
            "signal_id": "outcome_play",
            "command": "npm test",
            "description": "run the test suite",
        }

    def test_to_dict_omits_readiness_probe_when_none(self):
        """``readiness_probe`` is absent from the dict when not provided.

        Matches the existing agent-authored verification schema where
        the probe is opt-in.
        """
        cv = ContractVerification(
            signal_id="a",
            command="x",
            description="y",
            readiness_probe=None,
        )
        assert "readiness_probe" not in cv.to_dict()

    def test_to_dict_includes_readiness_probe_when_provided(self):
        """When the probe is set, it appears in the serialized dict."""
        cv = ContractVerification(
            signal_id="a",
            command="vite dev",
            description="dev server",
            readiness_probe="curl -f http://localhost:5173",
        )
        assert cv.to_dict()["readiness_probe"] == "curl -f http://localhost:5173"

    def test_from_dict_round_trips(self):
        """``from_dict(to_dict(x)) == x`` for any valid record."""
        original = ContractVerification(
            signal_id="outcome_a",
            command="npm test",
            description="run tests",
            readiness_probe="curl -f http://localhost:3000",
        )
        round_tripped = ContractVerification.from_dict(original.to_dict())
        assert round_tripped == original

    def test_from_dict_rejects_missing_required_field(self):
        """Missing a required field raises ValueError, not silent default."""
        with pytest.raises(ValueError, match="signal_id"):
            ContractVerification.from_dict({"command": "x", "description": "y"})

    def test_from_dict_rejects_non_string_required_field(self):
        """Required fields must be strings; ints / None raise ValueError."""
        with pytest.raises(ValueError, match="command"):
            ContractVerification.from_dict(
                {"signal_id": "a", "command": 42, "description": "y"}
            )

    def test_from_dict_rejects_empty_string_required_field(self):
        """Empty strings are rejected — they're a malformed contract."""
        with pytest.raises(ValueError, match="description"):
            ContractVerification.from_dict(
                {"signal_id": "a", "command": "x", "description": "   "}
            )

    def test_from_dict_rejects_non_string_readiness_probe(self):
        """A non-string probe value is rejected; None is allowed."""
        with pytest.raises(ValueError, match="readiness_probe"):
            ContractVerification.from_dict(
                {
                    "signal_id": "a",
                    "command": "x",
                    "description": "y",
                    "readiness_probe": 99,
                }
            )


# ---------------------------------------------------------------------------
# generate_verification_command — single-outcome LLM contract
# ---------------------------------------------------------------------------


class TestGenerateVerificationCommand:
    """The single-outcome generator's LLM contract."""

    @pytest.mark.asyncio
    async def test_returns_populated_verification_on_well_formed_llm_response(self):
        """The happy path: LLM returns a valid JSON object → ContractVerification."""
        llm = _stub_llm(
            json.dumps(
                {
                    "command": "npm test -- --grep arrow-keys",
                    "readiness_probe": None,
                    "description": "exercise keyboard input",
                }
            )
        )
        result = await generate_verification_command(
            _outcome(),
            project_description="A snake game built with vanilla JavaScript and Vite.",
            llm_client=llm,
        )
        assert result is not None
        assert isinstance(result, ContractVerification)
        assert result.signal_id == "outcome_play"
        assert result.command == "npm test -- --grep arrow-keys"
        assert result.description == "exercise keyboard input"
        assert result.readiness_probe is None

    @pytest.mark.asyncio
    async def test_returns_none_when_llm_returns_null_command(self):
        """LLM signals 'cannot verify with the available stack' → None."""
        llm = _stub_llm(
            json.dumps(
                {
                    "command": None,
                    "readiness_probe": None,
                    "description": "skipped",
                }
            )
        )
        result = await generate_verification_command(
            _outcome(), project_description="bare-bones project", llm_client=llm
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_strips_whitespace_from_command_and_description(self):
        """Leading/trailing whitespace in LLM output is normalized away."""
        llm = _stub_llm(
            json.dumps(
                {
                    "command": "   npm test   ",
                    "description": "  run tests  ",
                }
            )
        )
        result = await generate_verification_command(
            _outcome(), project_description="x", llm_client=llm
        )
        assert result is not None
        assert result.command == "npm test"
        assert result.description == "run tests"

    @pytest.mark.asyncio
    async def test_includes_readiness_probe_when_llm_provides_one(self):
        """Server-mode commands carry the probe through to the dataclass."""
        llm = _stub_llm(
            json.dumps(
                {
                    "command": "vite dev",
                    "readiness_probe": "curl -f http://localhost:5173",
                    "description": "boot dev server",
                }
            )
        )
        result = await generate_verification_command(
            _outcome(), project_description="vite app", llm_client=llm
        )
        assert result is not None
        assert result.readiness_probe == "curl -f http://localhost:5173"

    @pytest.mark.asyncio
    async def test_falls_back_to_success_signal_when_description_absent(self):
        """A missing description field uses the outcome's success_signal."""
        llm = _stub_llm(json.dumps({"command": "x"}))
        result = await generate_verification_command(
            _outcome(success_signal="snake responds to arrows"),
            project_description="x",
            llm_client=llm,
        )
        assert result is not None
        assert result.description == "snake responds to arrows"

    @pytest.mark.asyncio
    async def test_rejects_empty_string_command(self):
        """Empty command is malformed — strict-fail with ValueError."""
        llm = _stub_llm(json.dumps({"command": "   "}))
        with pytest.raises(ValueError, match="command"):
            await generate_verification_command(
                _outcome(), project_description="x", llm_client=llm
            )

    @pytest.mark.asyncio
    async def test_rejects_non_string_command(self):
        """Non-string command is malformed — strict-fail with ValueError."""
        llm = _stub_llm(json.dumps({"command": 42}))
        with pytest.raises(ValueError, match="command"):
            await generate_verification_command(
                _outcome(), project_description="x", llm_client=llm
            )

    @pytest.mark.asyncio
    async def test_rejects_non_string_readiness_probe(self):
        """Non-string readiness_probe — strict-fail with ValueError."""
        llm = _stub_llm(json.dumps({"command": "x", "readiness_probe": 99}))
        with pytest.raises(ValueError, match="readiness_probe"):
            await generate_verification_command(
                _outcome(), project_description="x", llm_client=llm
            )

    @pytest.mark.asyncio
    async def test_rejects_malformed_llm_json(self):
        """Garbage from the LLM raises ValueError with outcome id in message."""
        llm = _stub_llm("not json at all")
        with pytest.raises(ValueError, match="outcome_play"):
            await generate_verification_command(
                _outcome(), project_description="x", llm_client=llm
            )


# ---------------------------------------------------------------------------
# generate_verification_commands — fan-out semantics
# ---------------------------------------------------------------------------


class TestGenerateVerificationCommands:
    """Fan-out generator's parallelism + partial-failure handling."""

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty_list_without_llm_call(self):
        """No outcomes → no LLM calls fired."""
        llm = MagicMock()
        llm.analyze = AsyncMock(side_effect=AssertionError("must not call"))
        result = await generate_verification_commands(
            outcomes=[], project_description="x", llm_client=llm
        )
        assert result == []
        llm.analyze.assert_not_called()

    @pytest.mark.asyncio
    async def test_generates_one_verification_per_outcome(self):
        """N outcomes → N LLM calls → N verifications when all succeed."""
        # Each call returns the same shape; test asserts the count.
        llm = _stub_llm(json.dumps({"command": "npm test", "description": "tests"}))
        outcomes = [
            _outcome(id_=f"outcome_{i}", action=f"do thing {i}") for i in range(3)
        ]
        result = await generate_verification_commands(
            outcomes=outcomes,
            project_description="any",
            llm_client=llm,
        )
        assert len(result) == 3
        assert llm.analyze.call_count == 3
        assert [v.signal_id for v in result] == [
            "outcome_0",
            "outcome_1",
            "outcome_2",
        ]

    @pytest.mark.asyncio
    async def test_drops_outcomes_for_which_llm_returns_null_command(self):
        """LLM-null command for one outcome → that outcome is omitted."""
        # First call returns null; second returns a real command.
        responses = [
            json.dumps({"command": None}),
            json.dumps({"command": "npm test", "description": "tests"}),
        ]
        llm = MagicMock()
        llm.analyze = AsyncMock(side_effect=responses)

        outcomes = [
            _outcome(id_="unverifiable"),
            _outcome(id_="verifiable"),
        ]
        result = await generate_verification_commands(
            outcomes=outcomes,
            project_description="x",
            llm_client=llm,
        )

        assert len(result) == 1
        assert result[0].signal_id == "verifiable"

    @pytest.mark.asyncio
    async def test_partial_llm_failure_is_isolated_per_outcome(self, caplog):
        """One bad LLM call drops that outcome but keeps the rest (P2-2).

        Pre-P2-2, ``asyncio.gather`` defaulted to ``return_exceptions=False``
        and a single bad LLM response would raise out of the whole batch
        — losing ALL N verifications because the caller in nlp_tools.py
        caught the exception and fell back to ``None``. With
        ``return_exceptions=True``, failures are per-outcome: log a
        warning and drop just the failing one.
        """
        import logging

        # First call: well-formed. Second: parses but fails validation
        # (non-string command → strict-fail in single-outcome generator).
        responses = [
            json.dumps({"command": "ok"}),
            json.dumps({"command": 42}),
        ]
        llm = MagicMock()
        llm.analyze = AsyncMock(side_effect=responses)
        outcomes = [_outcome(id_="good"), _outcome(id_="bad")]

        with caplog.at_level(logging.WARNING):
            result = await generate_verification_commands(
                outcomes=outcomes,
                project_description="x",
                llm_client=llm,
            )

        # The good outcome survived; the bad one was dropped.
        assert len(result) == 1
        assert result[0].signal_id == "good"

        # And the failing outcome's id appears in a warning log line so
        # operators can see WHY a contract is incomplete.
        assert any(
            "bad" in rec.message and rec.levelno == logging.WARNING
            for rec in caplog.records
        )
