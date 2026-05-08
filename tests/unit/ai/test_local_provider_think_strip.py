"""
Unit tests for ``<think>...</think>`` reasoning-block stripping.

Reasoning-distilled models (deepseek-r1, qwq, etc.) emit chain-of-thought
prefixes that Marcus's JSON parsers cannot consume.  ``_strip_reasoning_blocks``
removes well-formed blocks before the response is returned to the caller.

Reproducer evidence: trial5-snake-game-deepsekk-r1-q5-mcp run on
2026-05-07 emitted a 7051-char response starting with ``<think>``; the PRD
parser failed with "Expected JSON object, got list" and contract_first
fell back to feature_based.
"""

import pytest

from src.ai.providers.local_provider import _strip_reasoning_blocks

pytestmark = pytest.mark.unit


class TestStripReasoningBlocks:
    """``_strip_reasoning_blocks`` removes well-formed reasoning prefixes."""

    def test_strips_well_formed_block(self) -> None:
        """A complete ``<think>...</think>`` followed by JSON is stripped."""
        content = (
            "<think>\nOkay, let me analyze this PRD carefully.\n"
            "Step 1: identify domains.\n</think>\n"
            '{"tasks": [{"id": "t1", "name": "Setup"}]}'
        )
        result = _strip_reasoning_blocks(content)
        assert result == '{"tasks": [{"id": "t1", "name": "Setup"}]}'

    def test_preserves_response_when_no_think_block(self) -> None:
        """Plain JSON responses pass through unchanged (after .strip())."""
        content = '{"tasks": [{"id": "t1", "name": "Setup"}]}'
        assert _strip_reasoning_blocks(content) == content

    def test_strips_multiple_leading_blocks(self) -> None:
        """Consecutive reasoning blocks at the start are all stripped."""
        content = (
            "<think>first thought</think>\n"
            "<think>second thought</think>\n"
            '{"part": 2}'
        )
        result = _strip_reasoning_blocks(content)
        assert result == '{"part": 2}'

    def test_preserves_tags_inside_payload(self) -> None:
        """
        Codex P2: tags embedded inside the response payload must NOT be
        stripped.

        A response like ``<think>reasoning</think>{"task": "handle <think>
        blocks"}`` would, under a global-substitution strip, lose the
        legitimate string content "handle ".  Anchoring the regex to the
        leading prefix preserves embedded tags inside the structured
        output.
        """
        content = (
            "<think>brief reasoning</think>\n"
            '{"task": "describe how to parse <think>...</think> blocks"}'
        )
        result = _strip_reasoning_blocks(content)
        # Leading reasoning is gone
        assert not result.startswith("<think>")
        # But the payload's quoted tags are preserved
        assert "<think>...</think>" in result
        assert "describe how to parse" in result

    def test_preserves_payload_when_no_leading_block(self) -> None:
        """Embedded tags with no leading reasoning prefix are untouched."""
        content = '{"description": "model emits <think>X</think> on errors"}'
        assert _strip_reasoning_blocks(content) == content

    def test_strips_block_spanning_many_newlines(self) -> None:
        """``re.DOTALL`` lets the pattern span newlines (default behavior)."""
        content = (
            "<think>\nLine 1\nLine 2\nLine 3\nLine 4\n</think>" '\n{"result": "ok"}'
        )
        result = _strip_reasoning_blocks(content)
        assert result == '{"result": "ok"}'

    def test_leaves_unclosed_think_tag_alone(self) -> None:
        """
        Malformed (unclosed) ``<think>`` blocks are NOT stripped.

        We deliberately do not try to recover from a stuck-open think block —
        better to surface the failure in the parser than silently strip an
        unbounded prefix that might also contain valid JSON.
        """
        content = "<think>\nReasoning never closed and JSON never came..."
        result = _strip_reasoning_blocks(content)
        assert result.startswith("<think>")

    def test_handles_case_insensitive_tags(self) -> None:
        """Some models emit ``<THINK>`` or mixed case — strip those too."""
        content = "<THINK>thought</THINK>\n{}"
        result = _strip_reasoning_blocks(content)
        assert result == "{}"

    def test_strips_surrounding_whitespace(self) -> None:
        """After stripping the block, leading/trailing whitespace is trimmed."""
        content = "   <think>x</think>\n\n   {}\n   "
        result = _strip_reasoning_blocks(content)
        assert result == "{}"

    def test_handles_empty_think_block(self) -> None:
        """An empty ``<think></think>`` block is removed cleanly."""
        content = '<think></think>{"ok": true}'
        result = _strip_reasoning_blocks(content)
        assert result == '{"ok": true}'

    def test_preserves_json_array_response(self) -> None:
        """
        A response that is a JSON array (no think block) passes through.

        This is the "got list" parser failure case the user observed —
        the strip should not affect it; the wrapper-shape mismatch is a
        separate concern handled by the parser layer.
        """
        content = '[{"id": "t1"}, {"id": "t2"}]'
        assert _strip_reasoning_blocks(content) == content


# ---------------------------------------------------------------------------
# max_tokens propagation
# ---------------------------------------------------------------------------
#
# Before this fix:
#   - LLMAbstraction.analyze hardcoded max_tokens=2000 when context had no
#     max_tokens attribute
#   - LocalLLMProvider.complete defaulted max_tokens=2000
#   The net effect: ``config.ai.max_tokens`` (default 4096) was silently
#   ignored on the PRD-parser path, capping every call at 2000 tokens.
#
#   For reasoning-distilled models whose ``<think>`` blocks frequently exceed
#   1500 tokens, this caused mid-reasoning truncation before any JSON could
#   be emitted.
#
# After this fix:
#   - When the caller does not explicitly supply max_tokens, the provider's
#     ``self.max_tokens`` (from config) takes effect.
#   - Explicit caller overrides still work.


class TestMaxTokensPropagation:
    """``self.max_tokens`` from config is the default, not 2000."""

    def test_complete_uses_self_max_tokens_when_not_specified(self) -> None:
        """``complete(prompt)`` without max_tokens uses ``self.max_tokens``."""
        from unittest.mock import AsyncMock, patch

        from src.ai.providers.local_provider import LocalLLMProvider

        with patch("src.config.marcus_config.get_config") as mock_cfg:
            mock_cfg.return_value.ai.local_url = "http://localhost:11434/v1"
            mock_cfg.return_value.ai.local_key = "none"
            mock_cfg.return_value.ai.max_tokens = 8192
            mock_cfg.return_value.ai.temperature = 0.7

            provider = LocalLLMProvider("test-model")
            assert provider.max_tokens == 8192

            # Spy on _call_local_llm to verify what max_tokens it receives
            provider._call_local_llm = AsyncMock(return_value="ok")  # type: ignore[method-assign]

            import asyncio

            asyncio.run(provider.complete("prompt"))

            call_kwargs = provider._call_local_llm.call_args
            # Positional: prompt, max_tokens, temperature
            passed_max_tokens = call_kwargs.args[1]
            assert passed_max_tokens == 8192, (
                f"complete() must propagate self.max_tokens (8192) when no "
                f"explicit override is given. Got {passed_max_tokens}"
            )

    def test_complete_respects_explicit_max_tokens(self) -> None:
        """Explicit ``max_tokens=N`` override is preserved."""
        from unittest.mock import AsyncMock, patch

        from src.ai.providers.local_provider import LocalLLMProvider

        with patch("src.config.marcus_config.get_config") as mock_cfg:
            mock_cfg.return_value.ai.local_url = "http://localhost:11434/v1"
            mock_cfg.return_value.ai.local_key = "none"
            mock_cfg.return_value.ai.max_tokens = 8192
            mock_cfg.return_value.ai.temperature = 0.7

            provider = LocalLLMProvider("test-model")
            provider._call_local_llm = AsyncMock(return_value="ok")  # type: ignore[method-assign]

            import asyncio

            asyncio.run(provider.complete("prompt", max_tokens=500))

            passed_max_tokens = provider._call_local_llm.call_args.args[1]
            assert passed_max_tokens == 500, (
                f"Explicit max_tokens override must be preserved. "
                f"Got {passed_max_tokens}"
            )
