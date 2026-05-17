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
  Claude Haiku 4.5 ceiling).  Three retries by default so a tight
  initial budget (2048) still escalates all the way to 16384 before
  giving up.
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

# Import the module (not the function) so callers that
# ``patch("src.utils.json_parser.parse_ai_json_response")`` in tests
# see the patched name when this helper resolves it at call time.
# Binding the function at module load (``from json_parser import ...``)
# would freeze the reference before any patch can take effect.
from src.utils import json_parser

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


def _deployment_ceiling() -> int:
    """Return the maximum ``max_tokens`` value safe for this deployment.

    ``config.ai.max_tokens`` is a per-deployment knob the operator sets
    to match the configured model's output cap (Claude 3 Haiku caps at
    4096; Claude Haiku 4.5 supports 64K).  The helper must not escalate
    beyond it — sending more than the model allows fails with a 400
    before any retry can help.

    Falls back to :data:`DEFAULT_MAX_TOKENS` if config is unavailable
    (test harnesses, partial imports).
    """
    try:
        from src.config.marcus_config import get_config

        ceiling = int(get_config().ai.max_tokens)
        # Clamp to module hard cap so a misconfigured ai.max_tokens
        # can't blow past the Claude Haiku 4.5 limit.
        return min(ceiling, MAX_OUTPUT_TOKENS)
    except Exception:
        return DEFAULT_MAX_TOKENS


async def _analyze_as_retry(
    llm: Any, prompt: str, max_tokens: int, operation: str
) -> Any:
    """Run ``llm.analyze`` tagged as a retry for Phase 0 cost tracking.

    Wraps the call in :meth:`CostRecorder.retry_attempt` so the
    ``token_events`` row records ``was_retry`` / ``retry_reason``
    (Marcus #546).  ``reason`` is always ``"truncation"`` — the only
    condition :func:`safe_structured_call` retries on.

    If the cost recorder is unavailable (test harness, partial
    import) the call still runs; the retry tag is simply not stamped.
    The recorder lookup never blocks or breaks the LLM call.
    """
    # Acquire the retry-tagging context separately from the LLM call so
    # an exception raised by ``llm.analyze`` is never mistaken for a
    # recorder failure (which would double-invoke the call).
    retry_ctx: Any = None
    try:
        from src.cost_tracking.cost_recorder import get_recorder

        retry_ctx = get_recorder().retry_attempt("truncation")
    except Exception:  # noqa: BLE001 - recorder import/lookup failed
        retry_ctx = None

    if retry_ctx is not None:
        with retry_ctx:
            return await llm.analyze(
                prompt=prompt,
                context=_Ctx(max_tokens),
                operation=operation,
            )
    return await llm.analyze(
        prompt=prompt,
        context=_Ctx(max_tokens),
        operation=operation,
    )


async def safe_structured_call(
    *,
    llm: Any,
    prompt: str,
    operation: str,
    initial_max_tokens: int = DEFAULT_MAX_TOKENS,
    max_retries: int = 3,
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
        discovery) may pass a smaller value.  Whatever the caller
        passes, the helper clamps it to the per-deployment ceiling
        (``config.ai.max_tokens``) so older models like Claude 3 Haiku
        (4096 cap) don't get a request bigger than the API allows.
    max_retries : int, default 3
        Additional attempts after the first if the response looks
        truncated. Budget doubles each attempt, capped at the
        per-deployment ceiling.

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

    # The configured model's output cap is the real ceiling for
    # everything the helper does — first attempt and retry escalation.
    # Sending more than the model supports fails with a 400 before any
    # retry can help (Codex P1 on PR #542).
    ceiling = _deployment_ceiling()
    max_tokens = min(initial_max_tokens, ceiling)
    raw_text = ""
    last_err: Optional[Exception] = None

    # Telemetry retry counter (Marcus #416, Kaia review 3 fix).
    # Track how many retries actually fire so we can emit ONE
    # structured_llm_retry event at exit time with the real
    # final outcome — "ok" if a retry succeeded, "fail" if all
    # exhausted.  Prior implementation emitted final="pending"
    # mid-loop, which made the field useless to the dashboard.
    retries_fired = 0

    def _emit_retry_event(final_outcome: str) -> None:
        """Fire structured_llm_retry once with the known final outcome.

        Only fires when at least one retry actually happened; a
        first-attempt success produces no event.  Swallows all
        errors so it can never crash the retry path.
        """
        if retries_fired <= 0:
            return
        try:
            from src.telemetry.events import fire_structured_llm_retry

            fire_structured_llm_retry(
                operation=operation,
                retry_count=retries_fired,
                reason="truncation",
                final=final_outcome,
            )
        except Exception:  # noqa: BLE001 - never crash the retry path
            pass

    for attempt in range(max_retries + 1):
        # Attempt 0 is the first try; 1..max_retries are retries.
        # Wrap retry attempts in the recorder's retry_attempt() context
        # so their token_events rows record was_retry / retry_reason
        # for Phase 0 forecasting (Marcus #546).  Best-effort: a
        # missing/broken recorder must never block the LLM call.
        if attempt == 0:
            result = await llm.analyze(
                prompt=prompt,
                context=_Ctx(max_tokens),
                operation=operation,
            )
        else:
            result = await _analyze_as_retry(llm, prompt, max_tokens, operation)
        raw_text = str(result) if result is not None else ""

        try:
            parsed = json_parser.parse_ai_json_response(raw_text)
            # Successful parse — if we got here after one or more
            # retries, the retry helper recovered.  Emit final=ok.
            _emit_retry_event("ok")
            return parsed
        except (ValueError, json.JSONDecodeError) as exc:
            last_err = exc
            if attempt == max_retries or not _looks_truncated(raw_text):
                _emit_retry_event("fail")
                raise
            next_budget = min(max_tokens * 2, ceiling)
            if next_budget == max_tokens:
                # Already at the per-deployment ceiling; doubling won't
                # help and would just trigger an API rejection.
                _emit_retry_event("fail")
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
            retries_fired += 1
            max_tokens = next_budget

    # Defensive — loop only exits via return or raise.
    _emit_retry_event("fail")
    assert last_err is not None
    raise last_err
