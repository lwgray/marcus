"""Resilient structured-JSON calls to the planner LLM.

Why
---
Marcus's planner LLM (PRD analysis, contract decomposition, outcome
extraction, domain discovery, foundation synthesis) emits structured
JSON. The model's ``max_tokens`` cap is hard to size statically: a
4-domain project needs more tokens than a 2-domain project. When the
cap is too low, the JSON truncates mid-string and downstream parsing
fails — the silent fallback to ``feature_based`` decomposition is
visible only as a log warning, and the planner's intent is lost.

This module centralizes the per-call policy so every structured-JSON
caller gets the same defense:

* Start at a sensible default (``16384`` — 4x the Haiku-3-era 4096
  that was scattered through the codebase).
* Detect mid-stream truncation via a closing-brace heuristic on the
  raw text.
* Auto-retry with doubled budget up to ``MAX_OUTPUT_TOKENS`` (64K —
  Claude Haiku 4.5 ceiling).
* Bail out fast on schema drift / non-truncation parse failures —
  more tokens won't fix those.
* Emit a structured warning when retry triggers so Cato can graph
  retry frequency per operation.
* Hard-cap prompt length to bound cost on runaway inputs.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from src.utils.json_parser import parse_ai_json_response

logger = logging.getLogger(__name__)

# Hard cap on prompt length. ~200K chars ≈ 50K input tokens — generous
# but bounds runaway cost from someone passing a giant PRD or context.
MAX_PROMPT_CHARS = 200_000

# Output token ceiling. Claude Haiku 4.5 supports 64K output; this
# matches. Older Haiku 3 capped at 4096, which is what the legacy
# scattered defaults were sized for.
MAX_OUTPUT_TOKENS = 65_536

# Default starting budget. 4x the legacy 4096 covers the realistic
# upper bound of contract-first decomposition output for 4-domain
# projects without needing a retry round-trip.
DEFAULT_MAX_TOKENS = 16_384


class _Ctx:
    """Minimal context passed to LLMAbstraction.analyze with max_tokens."""

    def __init__(self, max_tokens: int) -> None:
        self.max_tokens = max_tokens


def _looks_truncated(raw: str) -> bool:
    """Return True if ``raw`` looks like the model ran out of tokens mid-emit.

    A complete JSON document — even when the model wrapped it in
    markdown fences or appended a polite "let me know if you need
    changes" — strips back to something that ends with ``}`` or
    ``]``. Anything else suggests the stream cut off mid-string,
    mid-array, or mid-key, which is the failure mode that more tokens
    fixes.

    Schema drift (wrong field names, missing required fields) still
    produces well-formed JSON that ends correctly — retrying won't
    help those, so this heuristic deliberately lets them fall through
    to the caller as a hard failure.

    Future work
    -----------
    The authoritative truncation signal is the provider's
    ``stop_reason``/``finish_reason`` field (``max_tokens`` on
    Anthropic, ``length`` on OpenAI/Fireworks).  Plumbing that
    through ``LLMAbstraction.analyze`` requires changing the return
    type from ``str`` to a typed response object across all four
    provider implementations and their callers.  For now this
    heuristic is sufficient: Claude truncates mid-string, which is
    the case the suffix check catches reliably; the change-of-return-
    type refactor can land separately when its blast radius is worth
    paying for.
    """
    if not raw:
        return True
    tail = raw.rstrip().rstrip("`").rstrip()
    return not tail.endswith(("}", "]"))


async def safe_structured_call(
    *,
    llm: Any,
    prompt: str,
    operation: str,
    initial_max_tokens: int = DEFAULT_MAX_TOKENS,
    max_retries: int = 2,
) -> Dict[str, Any]:
    """Run an LLM call expecting structured JSON, with truncation retry.

    Parameters
    ----------
    llm : Any
        A client exposing async ``analyze(prompt, context, operation)``.
        Typically :class:`src.ai.providers.llm_abstraction.LLMAbstraction`.
    prompt : str
        The full prompt (system + user + schema instructions). Caller
        composes this; the helper does not add extra wrapping.
    operation : str
        Cost-event operation key (see
        :mod:`src.cost_tracking.operations`).  Forwarded to the
        provider and used as the retry-event tag.
    initial_max_tokens : int, default :data:`DEFAULT_MAX_TOKENS`
        Starting token budget for the first attempt.  Callers that
        know their output is small (e.g. yes/no classifier, domain
        discovery) may pass a smaller value; the retry path will
        still escalate up to :data:`MAX_OUTPUT_TOKENS` on truncation.
    max_retries : int, default 2
        Additional attempts after the first if the response looks
        truncated. Budget doubles each attempt, capped at
        :data:`MAX_OUTPUT_TOKENS`.

    Returns
    -------
    dict
        Parsed JSON response.

    Raises
    ------
    ValueError
        Prompt exceeds :data:`MAX_PROMPT_CHARS`, or the LLM returned a
        non-JSON / schema-drift response that retrying cannot fix.
    json.JSONDecodeError
        Final attempt still failed to parse (truncation kept exceeding
        the doubled budget — should not happen in practice).
    """
    if len(prompt) > MAX_PROMPT_CHARS:
        raise ValueError(
            f"Prompt is {len(prompt)} chars; safe_structured_call "
            f"caps at {MAX_PROMPT_CHARS} to bound cost. Trim the "
            f"input or split the call."
        )

    max_tokens = initial_max_tokens
    raw_text = ""
    last_err: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        result = await llm.analyze(
            prompt=prompt,
            context=_Ctx(max_tokens),
            operation=operation,
        )
        raw_text = str(result) if result is not None else ""

        try:
            return parse_ai_json_response(raw_text)
        except (ValueError, json.JSONDecodeError) as exc:
            last_err = exc
            if attempt == max_retries or not _looks_truncated(raw_text):
                raise
            next_budget = min(max_tokens * 2, MAX_OUTPUT_TOKENS)
            if next_budget == max_tokens:
                # Already at ceiling; doubling won't help.
                raise
            logger.warning(
                "structured_llm.retry",
                extra={
                    "event": "structured_llm.retry",
                    "operation": operation,
                    "attempt": attempt + 1,
                    "initial_budget": initial_max_tokens,
                    "attempted_budget": max_tokens,
                    "retry_budget": next_budget,
                    "raw_chars": len(raw_text),
                    "prompt_chars": len(prompt),
                },
            )
            max_tokens = next_budget

    # Defensive — loop only exits via return or raise.
    assert last_err is not None
    raise last_err
