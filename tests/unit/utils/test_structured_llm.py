"""Unit tests for :mod:`src.utils.structured_llm`.

Covers:

* The closing-brace truncation heuristic (the only signal the helper
  uses to distinguish "ran out of tokens" from "schema drift").
* Retry escalation (budget doubling, ceiling enforcement, attempt count).
* Bail-out on schema drift so we don't burn tokens chasing a problem
  more tokens won't fix.
* Prompt-length sanity check.

The helper itself is small — these tests guard the policy, since the
helper is the resilience layer that other modules depend on.
"""

from __future__ import annotations

import json
from typing import Any, List
from unittest.mock import AsyncMock

import pytest

from src.utils import structured_llm
from src.utils.structured_llm import (
    DEFAULT_MAX_TOKENS,
    MAX_OUTPUT_TOKENS,
    MAX_PROMPT_CHARS,
    _looks_truncated,
    safe_structured_call,
)


class TestLooksTruncated:
    """Heuristic used to decide whether a parse failure should retry."""

    def test_empty_response_treated_as_truncated(self) -> None:
        assert _looks_truncated("") is True

    def test_clean_object_not_truncated(self) -> None:
        assert _looks_truncated('{"x": 1}') is False

    def test_clean_array_not_truncated(self) -> None:
        assert _looks_truncated("[1, 2, 3]") is False

    def test_markdown_fenced_object_not_truncated(self) -> None:
        """Models often wrap JSON in ```json...``` fences; helper strips
        trailing backticks before checking the closing brace."""
        assert _looks_truncated('```json\n{"x": 1}\n```') is False

    def test_object_with_trailing_whitespace_not_truncated(self) -> None:
        assert _looks_truncated('{"x": 1}\n\n  ') is False

    def test_mid_string_cutoff_is_truncated(self) -> None:
        """The actual failure mode: response ends mid-string value."""
        assert _looks_truncated('{"x": "hello wor') is True

    def test_mid_array_cutoff_is_truncated(self) -> None:
        assert _looks_truncated('{"items": [1, 2,') is True

    def test_trailing_prose_after_complete_json_not_truncated(self) -> None:
        """Some models append a polite closing — parse_ai_json_response
        already strips trailing prose. The closing-brace heuristic
        deliberately treats this as truncated (so retry fires when
        the parser fails), but in practice the parser succeeds first.
        We assert the heuristic's actual behavior here, not what the
        end-to-end flow does."""
        assert _looks_truncated('{"x": 1}\n\nHope this helps!') is True


class TestSafeStructuredCall:
    """End-to-end behavior of the retry-on-truncation policy."""

    @pytest.mark.asyncio
    async def test_first_attempt_succeeds(self) -> None:
        llm = AsyncMock()
        llm.analyze = AsyncMock(return_value='{"ok": true}')
        result = await safe_structured_call(llm=llm, prompt="p", operation="op")
        assert result == {"ok": True}
        assert llm.analyze.await_count == 1

    @pytest.mark.asyncio
    async def test_initial_budget_passed_to_first_call(self) -> None:
        llm = AsyncMock()
        llm.analyze = AsyncMock(return_value='{"ok": true}')
        await safe_structured_call(
            llm=llm,
            prompt="p",
            operation="op",
            initial_max_tokens=2048,
        )
        ctx = llm.analyze.await_args.kwargs["context"]
        assert ctx.max_tokens == 2048

    @pytest.mark.asyncio
    async def test_truncated_response_triggers_retry_with_doubled_budget(
        self,
    ) -> None:
        truncated = '{"items": ["a", "b'
        complete = '{"items": ["a", "b", "c"]}'
        llm = AsyncMock()
        llm.analyze = AsyncMock(side_effect=[truncated, complete])

        result = await safe_structured_call(
            llm=llm,
            prompt="p",
            operation="op",
            initial_max_tokens=2048,
        )
        assert result == {"items": ["a", "b", "c"]}
        assert llm.analyze.await_count == 2
        # Second call should have run with doubled budget.
        second_ctx = llm.analyze.await_args_list[1].kwargs["context"]
        assert second_ctx.max_tokens == 4096

    @pytest.mark.asyncio
    async def test_retry_emits_structured_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        truncated = '{"x": "hel'
        complete = '{"x": "hello"}'
        llm = AsyncMock()
        llm.analyze = AsyncMock(side_effect=[truncated, complete])

        with caplog.at_level("WARNING", logger="src.utils.structured_llm"):
            await safe_structured_call(
                llm=llm,
                prompt="p",
                operation="my_op",
                initial_max_tokens=4096,
            )

        retry_records = [
            r for r in caplog.records if r.message == "structured_llm.retry"
        ]
        assert len(retry_records) == 1
        rec = retry_records[0]
        # Structured fields are mounted via ``extra=`` so Cato can graph
        # retry frequency per operation.
        assert getattr(rec, "operation") == "my_op"
        assert getattr(rec, "attempt") == 1
        assert getattr(rec, "attempted_budget") == 4096
        assert getattr(rec, "retry_budget") == 8192

    @pytest.mark.asyncio
    async def test_schema_drift_bails_immediately_no_retry(self) -> None:
        """Well-formed JSON that doesn't match expectations should NOT
        retry — more tokens won't fix a wrong-shape response."""
        # An array — parse_ai_json_response only accepts objects.
        bad_shape = "[1, 2, 3]"
        llm = AsyncMock()
        llm.analyze = AsyncMock(return_value=bad_shape)

        with pytest.raises(ValueError):
            await safe_structured_call(llm=llm, prompt="p", operation="op")
        # Exactly one call — bailout, no retry.
        assert llm.analyze.await_count == 1

    @pytest.mark.asyncio
    async def test_exhausts_retries_then_raises(self) -> None:
        """All attempts truncated → raise after final attempt."""
        truncated = '{"items": ["incomplete'
        llm = AsyncMock()
        llm.analyze = AsyncMock(return_value=truncated)

        with pytest.raises((ValueError, json.JSONDecodeError)):
            await safe_structured_call(
                llm=llm,
                prompt="p",
                operation="op",
                initial_max_tokens=2048,
                max_retries=2,
            )
        # initial + 2 retries = 3 attempts total.
        assert llm.analyze.await_count == 3

    @pytest.mark.asyncio
    async def test_budget_caps_at_max_output_tokens(self) -> None:
        """Escalation must not request more than the Claude ceiling."""
        truncated = '{"items": ["incomplete'
        llm = AsyncMock()
        llm.analyze = AsyncMock(return_value=truncated)

        with pytest.raises((ValueError, json.JSONDecodeError)):
            await safe_structured_call(
                llm=llm,
                prompt="p",
                operation="op",
                # Start near the ceiling so a single double would
                # exceed MAX_OUTPUT_TOKENS — escalation must clamp.
                initial_max_tokens=MAX_OUTPUT_TOKENS // 2,
                max_retries=3,
            )
        budgets = [
            call.kwargs["context"].max_tokens for call in llm.analyze.await_args_list
        ]
        # No budget exceeds the ceiling.
        assert max(budgets) <= MAX_OUTPUT_TOKENS

    @pytest.mark.asyncio
    async def test_no_retry_when_already_at_ceiling(self) -> None:
        """Doubling can't go higher than ceiling — give up immediately."""
        truncated = '{"items": ["incomplete'
        llm = AsyncMock()
        llm.analyze = AsyncMock(return_value=truncated)

        with pytest.raises((ValueError, json.JSONDecodeError)):
            await safe_structured_call(
                llm=llm,
                prompt="p",
                operation="op",
                initial_max_tokens=MAX_OUTPUT_TOKENS,
                max_retries=3,
            )
        # First attempt is at ceiling; doubling would not help; raise.
        assert llm.analyze.await_count == 1

    @pytest.mark.asyncio
    async def test_prompt_too_long_rejected_before_llm_call(self) -> None:
        """Hard-cap prompt size to bound runaway cost."""
        llm = AsyncMock()
        llm.analyze = AsyncMock(return_value='{"ok": true}')

        oversized = "x" * (MAX_PROMPT_CHARS + 1)
        with pytest.raises(ValueError, match="caps at"):
            await safe_structured_call(llm=llm, prompt=oversized, operation="op")
        # No LLM call happens — sanity check runs first.
        assert llm.analyze.await_count == 0

    @pytest.mark.asyncio
    async def test_default_budget_is_4x_legacy_haiku_3_cap(self) -> None:
        """Sanity check on the documented constant — Haiku 3 capped at
        4096; the new default is 4x that to absorb 4-domain projects
        without a retry round-trip."""
        assert DEFAULT_MAX_TOKENS == 16_384


class TestRetryEndToEndThroughAIAnalysisEngine:
    """Exercise the retry path through the public entry point that
    Marcus actually uses for contract decomposition.

    The other tests prove safe_structured_call's policy in isolation.
    These prove the wiring: when contract decomposition truncates,
    AIAnalysisEngine.generate_structured_response retries, escalates
    the budget, and ultimately returns the parsed JSON.  The original
    bug bypassed all this — the parse failed, control flow fell back
    to feature_based, and the planner intent was silently lost."""

    @pytest.mark.asyncio
    async def test_generate_structured_response_retries_on_truncation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The originally-failing call path — contract decomposition —
        now recovers from a truncated first response and returns the
        complete JSON on retry."""
        from src.integrations.ai_analysis_engine import AIAnalysisEngine

        truncated = '{"tasks": [{"name": "Build snake mov'
        complete = (
            '{"tasks": [{"name": "Build snake movement", '
            '"description": "Owns grid movement contract"}]}'
        )
        mock_analyze = AsyncMock(side_effect=[truncated, complete])

        class _MockLLM:
            analyze = mock_analyze

        # generate_structured_response does ``from src.ai.providers.
        # llm_abstraction import LLMAbstraction`` lazily inside the
        # function, so we patch the source module — same import path
        # the function will resolve.
        monkeypatch.setattr(
            "src.ai.providers.llm_abstraction.LLMAbstraction",
            lambda: _MockLLM(),
        )

        engine = AIAnalysisEngine()
        result = await engine.generate_structured_response(
            prompt="Decompose this PRD into contract-owned tasks.",
            operation="generate_contracts",
        )

        assert result["tasks"][0]["name"] == "Build snake movement"
        assert mock_analyze.await_count == 2
        # Second call must have escalated the budget.
        first_budget = mock_analyze.await_args_list[0].kwargs["context"].max_tokens
        second_budget = mock_analyze.await_args_list[1].kwargs["context"].max_tokens
        assert second_budget == first_budget * 2
