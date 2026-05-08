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

    def test_strips_multiple_blocks(self) -> None:
        """Multiple reasoning blocks are all removed."""
        content = (
            "<think>first thought</think>\n"
            '{"part": 1}\n'
            "<think>second thought</think>\n"
            '{"part": 2}'
        )
        result = _strip_reasoning_blocks(content)
        assert "<think>" not in result
        assert "</think>" not in result
        assert '"part": 1' in result
        assert '"part": 2' in result

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
