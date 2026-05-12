"""
Unit tests for the ``make_analyze_mock`` test helper.

The helper is meant to insulate tests from future ``analyze()`` kwarg
additions. These tests pin the contract.
"""

from __future__ import annotations

import pytest

from src.ai.providers.protocols import LLMAnalyzeClient
from tests.unit.conftest import make_analyze_mock


class TestMakeAnalyzeMock:
    """Verifies the helper's contract.

    The helper has three responsibilities:
    1. Accept a 2-arg sync ``(prompt, context) -> str`` side effect.
    2. Accept a 2-arg async side effect, awaiting it transparently.
    3. Absorb any extra kwargs the production signature adds —
       ``operation`` today, anything else tomorrow.
    """

    @pytest.mark.asyncio
    async def test_sync_side_effect_passthrough(self) -> None:
        """Sync side_effect runs and its return value bubbles up."""
        mock = make_analyze_mock(side_effect=lambda p, _c: f"echo:{p}")
        result = await mock(prompt="hi", context=object())
        assert result == "echo:hi"

    @pytest.mark.asyncio
    async def test_async_side_effect_passthrough(self) -> None:
        """Async side_effect is awaited transparently."""

        async def aio(prompt: str, _ctx: object) -> str:
            return f"async:{prompt}"

        mock = make_analyze_mock(side_effect=aio)
        result = await mock(prompt="hi", context=object())
        assert result == "async:hi"

    @pytest.mark.asyncio
    async def test_absorbs_operation_kwarg(self) -> None:
        """``operation`` (and any future kwarg) is silently dropped."""
        seen: list[tuple[str, object]] = []

        def capture(prompt: str, ctx: object) -> str:
            seen.append((prompt, ctx))
            return "ok"

        mock = make_analyze_mock(side_effect=capture)
        # Simulate Marcus's call: ``operation`` is the new kwarg
        await mock(prompt="hi", context=object(), operation="decompose_prd")
        assert seen == [("hi", seen[0][1])]

    @pytest.mark.asyncio
    async def test_return_value_path(self) -> None:
        """``return_value`` short-circuits without a side effect."""
        mock = make_analyze_mock(return_value="canned")
        result = await mock(prompt="anything", context=None)
        assert result == "canned"

    def test_rejects_both_side_effect_and_return_value(self) -> None:
        """Pinning both args is a programming error."""
        with pytest.raises(ValueError):
            make_analyze_mock(side_effect=lambda p, c: "", return_value="x")


class TestProtocolConformance:
    """Sanity-check that the mock satisfies the runtime-checkable Protocol."""

    def test_mock_satisfies_protocol_via_runtime_check(self) -> None:
        """Wrapping the mock in a tiny adapter satisfies ``isinstance``.

        Mocks don't implement Protocol methods directly; this test
        proves the *production* shape of an adapter (a class that
        owns an ``analyze`` attribute set to the mock) satisfies the
        runtime check. That's the realistic test-double pattern.
        """
        mock = make_analyze_mock(return_value="ok")

        class _Adapter:
            analyze = mock

        assert isinstance(_Adapter(), LLMAnalyzeClient)
