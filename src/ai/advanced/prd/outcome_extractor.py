"""User-outcome extraction for intent fidelity coverage (issue #449).

The decomposer historically treats specs as flat feature lists and never
verifies that the union of features yields a usable product.  v31 of the
snake-game experiment shipped a perfectly-tested engine with no rendering
because no task said "render the snake" — the spec implied it but the
decomposer had no representation of what "done" means to a user.

This module produces a list of :class:`UserOutcome` records from a spec.
Each outcome is a concrete user action ("user can play the snake game")
paired with an observable success signal.  Downstream stages use the
list as decomposition constraints (every in-scope outcome must map to
at least one task) and to compute the ``intent_fidelity_score`` metric.

Two LLM calls happen here:

1. :func:`extract_user_outcomes` — turns a spec into outcome records.
2. :func:`filter_to_verifiable_capabilities` — a second LLM pass that
   acts as a quality gate, dropping outcomes that fail the
   :data:`_USER_OUTCOME_CRITERIA` self-check.

Both prompts share a single positive definition of what a user
outcome MUST be (:data:`_USER_OUTCOME_CRITERIA`), rather than each
prompt enumerating its own list of bad phrasings.  Defining success
generalizes; enumerating failure modes is the band-aid pattern that
:mod:`advanced_parser.py` accumulated as ``frontend`` /
``e-commerce`` / ``UI/UX`` guards.

The extractor itself is a thin wrapper around the LLM calls; validation
in :class:`UserOutcome` is purely structural (types, non-empty fields,
scope enum).  Semantic correctness is the LLM filter's job.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, List

logger = logging.getLogger(__name__)

_VALID_SCOPES: frozenset[str] = frozenset({"in_scope", "out_of_scope"})


# The single source of truth for what a user outcome must be.
#
# Both prompts reference this constant.  The three properties are
# defined positively — what a good outcome IS, not what bad outcomes
# look like — so the LLM evaluates against properties rather than
# pattern-matching against an enumerated list of bad phrasings.
# That is the architectural difference from the prior denylist
# implementation: properties generalize, lists do not.
_USER_OUTCOME_CRITERIA = """\
A user outcome must satisfy ALL THREE of these properties:

1. CONCRETE — names specific user-visible behavior such that an
   observer running the product can point at what they see, hear,
   or otherwise sense.

2. POSITIVE — names a capability the user gains, framed as
   something they CAN do.  An absence, restriction, or prohibition
   is not a capability.

3. VERIFIABLE — its satisfaction is decidable from observing the
   running product.  Evidence either appears or it does not.
"""


@dataclass
class UserOutcome:
    """A user-visible outcome the product must satisfy.

    Parameters
    ----------
    id : str
        Stable identifier used to map outcomes to tasks during the
        coverage check.  Convention: ``outcome_<short_action_verb>``.
    action : str
        Concrete user capability statement (e.g. ``"user can play the
        snake game in their browser"``).  Validated only structurally
        here — non-empty after stripping.  Semantic checks (positive
        capability, concreteness, no negation) happen in
        :func:`filter_to_verifiable_capabilities` via an LLM call,
        not via pattern matching against denylists in this module.
    success_signal : str
        Observable evidence that the outcome is satisfied.  Drives the
        Integration Verification gate (Stage 5, deferred): a Playwright
        DOM check, curl assertion, or CLI invocation must produce
        evidence matching this signal.
    scope : str
        ``"in_scope"`` or ``"out_of_scope"``.  Out-of-scope outcomes
        are retained (not dropped) so the audit trail records what the
        extractor considered and rejected based on spec language.

    Raises
    ------
    ValueError
        If any field violates a structural invariant.  Validation runs
        in ``__post_init__`` so malformed outcomes never enter the
        pipeline.  Semantic invariants (action is a positive capability,
        not vague, not a negation) are enforced separately by
        :func:`filter_to_verifiable_capabilities`.
    """

    id: str
    action: str
    success_signal: str
    scope: str

    def __post_init__(self) -> None:
        """Validate structural invariants only — types and non-emptiness."""
        if not self.id:
            raise ValueError("UserOutcome.id must be a non-empty string")

        if not self.action.strip():
            raise ValueError("UserOutcome.action must be a non-empty string")

        if not self.success_signal:
            raise ValueError(
                "UserOutcome.success_signal must be non-empty — without "
                "an observable signal the outcome cannot be verified"
            )

        if self.scope not in _VALID_SCOPES:
            raise ValueError(
                f"UserOutcome.scope must be one of {sorted(_VALID_SCOPES)}, "
                f"got {self.scope!r}"
            )


_EXTRACTION_PROMPT_TEMPLATE = """\
You are extracting user-visible outcomes from a project specification.

{criteria}

Format ``action`` as a positive user-capability statement.  The
canonical phrasing is ``"user can <verb> <object> <observable
detail>"`` (e.g. ``"user can play the snake game in their browser"``)
— but the surface form matters less than the three properties above.

Return strict JSON of the form:

{{
  "outcomes": [
    {{
      "id": "outcome_<short_verb>",
      "action": "<positive user-capability statement>",
      "success_signal": "<observable evidence>",
      "scope": "in_scope" | "out_of_scope"
    }}
  ]
}}

Rules:
- Outcomes the spec explicitly excludes must still be listed but
  tagged ``out_of_scope`` so the audit trail records what was
  considered and rejected based on spec language.
- Every project implies at least one outcome — never return an empty
  list.
- Provide a success_signal even for out_of_scope outcomes.

Specification:
{spec}

Respond with ONLY the JSON object — no preamble, no markdown fences.
"""

# Substitute the criteria block at module load time.  ``replace``
# leaves the ``{spec}`` placeholder intact for ``.format()`` later.
_EXTRACTION_PROMPT = _EXTRACTION_PROMPT_TEMPLATE.replace(
    "{criteria}", _USER_OUTCOME_CRITERIA
)


async def extract_user_outcomes(
    spec: str, llm_client: Any, max_tokens: int = 1500
) -> List[UserOutcome]:
    """Extract a list of :class:`UserOutcome` records from a project spec.

    Parameters
    ----------
    spec : str
        The raw project specification.  Passed to the LLM verbatim — the
        extractor inherits scope language ("no auth", "no accounts")
        from the spec itself rather than re-deriving it.
    llm_client : Any
        Any client exposing ``async analyze(prompt, context)`` and
        returning a string.  Mocked in unit tests.
    max_tokens : int, optional
        Token budget for the LLM call (default ``1500``).  Outcomes are
        small; the budget is generous to avoid truncation in
        many-feature specs.

    Returns
    -------
    list of UserOutcome
        Validated outcomes, in the order the LLM produced them.  Both
        in-scope and out-of-scope outcomes are returned; the coverage
        check filters by scope.

    Raises
    ------
    ValueError
        If the LLM returns malformed JSON, an empty outcome list, or
        any individual outcome fails :class:`UserOutcome` validation.
    """
    prompt = _EXTRACTION_PROMPT.format(spec=spec)
    from src.utils.structured_llm import safe_structured_call

    try:
        payload = await safe_structured_call(
            llm=llm_client,
            prompt=prompt,
            operation="extract_outcomes",
            initial_max_tokens=max_tokens,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"User-outcome extractor: LLM returned malformed JSON: {exc}"
        ) from exc

    # parse_ai_json_response normalizes to a dict; the prompt asks for an
    # object with an "outcomes" key.  Missing key = prompt ignored: hard fail.
    raw_outcomes = payload.get("outcomes")
    if raw_outcomes is None:
        raise ValueError("User-outcome extractor: LLM JSON missing 'outcomes' key")
    if not isinstance(raw_outcomes, list):
        raise ValueError("User-outcome extractor: 'outcomes' must be a JSON array")

    if not raw_outcomes:
        raise ValueError(
            "User-outcome extractor: LLM returned no outcomes — every spec "
            "implies at least one user-visible capability"
        )

    outcomes: List[UserOutcome] = []
    for idx, item in enumerate(raw_outcomes):
        if not isinstance(item, dict):
            raise ValueError(
                f"User-outcome extractor: outcome at index {idx} is not "
                f"an object: {item!r}"
            )

        # Reject null / non-string fields rather than coerce.  str(None)
        # is the string "None" which is non-empty and would silently
        # bypass UserOutcome's empty-string checks, polluting outcome ids
        # used by compute_coverage.
        for required_field in ("id", "action", "success_signal", "scope"):
            value = item.get(required_field)
            if not isinstance(value, str):
                raise ValueError(
                    f"User-outcome extractor: outcome at index {idx} "
                    f"field {required_field!r} must be a string, got "
                    f"{type(value).__name__}: {value!r}"
                )

        try:
            outcomes.append(
                UserOutcome(
                    id=str(item.get("id", "")).strip(),
                    action=str(item.get("action", "")).strip(),
                    success_signal=str(item.get("success_signal", "")).strip(),
                    scope=str(item.get("scope", "")).strip(),
                )
            )
        except ValueError as exc:
            raise ValueError(
                f"User-outcome extractor: outcome at index {idx} invalid: " f"{exc}"
            ) from exc

    # Reject ID collisions — they would silently overwrite each other in
    # the coverage map.
    seen_ids: set[str] = set()
    for outcome in outcomes:
        if outcome.id in seen_ids:
            raise ValueError(
                f"User-outcome extractor: duplicate outcome id {outcome.id!r}"
            )
        seen_ids.add(outcome.id)

    # Quality gate: a second LLM pass drops outcomes that aren't
    # concrete positive verifiable user capabilities.  This replaces
    # hand-curated denylists for negations and vague phrasings — the
    # LLM understands "user is forbidden from", "user shall avoid",
    # "user has zero capacity to", and any other phrasing we never
    # listed.
    outcomes = await filter_to_verifiable_capabilities(outcomes, llm_client)

    if not outcomes:
        raise ValueError(
            "User-outcome extractor: every extracted outcome failed the "
            "verifiability self-check — the spec produced no concrete "
            "positive user capabilities"
        )

    return outcomes


_FILTER_PROMPT_TEMPLATE = """\
You are a quality reviewer for user-outcome statements.

{criteria}

For each outcome below, return ``verifiable: true`` if it satisfies
ALL THREE properties, ``verifiable: false`` otherwise.  Provide a
short ``reason`` either way — the reason will be logged for debug
visibility when an outcome is dropped.

Outcomes:
{outcomes_block}

Return strict JSON of the form:

{{
  "verdicts": {{
    "<outcome_id>": {{
      "verifiable": true,
      "reason": "<one short sentence>"
    }}
  }}
}}

Every outcome.id from the input must appear as a key in verdicts.
Respond with ONLY the JSON object — no preamble, no markdown fences.
"""

# Substitute the criteria block at module load time.  ``replace``
# leaves ``{outcomes_block}`` intact for ``.format()`` at call time.
_FILTER_PROMPT = _FILTER_PROMPT_TEMPLATE.replace("{criteria}", _USER_OUTCOME_CRITERIA)


async def filter_to_verifiable_capabilities(
    outcomes: List[UserOutcome], llm_client: Any, max_tokens: int = 1500
) -> List[UserOutcome]:
    """Drop outcomes that are not concrete positive verifiable capabilities.

    Single LLM call evaluates every outcome and returns YES/NO verdicts.
    Outcomes marked NO are dropped from the returned list and logged at
    INFO level for debug visibility.

    This is the structural alternative to maintaining hand-curated
    denylists for negations, vague phrasings, and capability-pattern
    matching.  An LLM understands every phrasing we'd otherwise need
    to enumerate — "user is forbidden from", "user has zero ability
    to", "users shall avoid" — without us listing them.

    Parameters
    ----------
    outcomes : list of UserOutcome
        Structurally-validated outcomes from
        :func:`extract_user_outcomes`.  Empty list is allowed and
        returns immediately without an LLM call.
    llm_client : Any
        Async client exposing ``analyze(prompt, context)``.
    max_tokens : int, optional
        Token budget for the LLM call.

    Returns
    -------
    list of UserOutcome
        Outcomes the LLM judged verifiable, in original order.

    Raises
    ------
    ValueError
        On malformed JSON, missing ``verdicts`` key, or any verdict
        with a non-boolean ``verifiable`` field.
    """
    if not outcomes:
        return []

    outcomes_block = "\n".join(
        f"- {o.id}: {o.action} (signal: {o.success_signal}, scope: {o.scope})"
        for o in outcomes
    )
    prompt = _FILTER_PROMPT.format(outcomes_block=outcomes_block)
    from src.utils.structured_llm import safe_structured_call

    try:
        payload = await safe_structured_call(
            llm=llm_client,
            prompt=prompt,
            operation="filter_outcomes",
            initial_max_tokens=max_tokens,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"User-outcome filter: LLM returned malformed JSON: {exc}"
        ) from exc

    raw_verdicts = payload.get("verdicts")
    if not isinstance(raw_verdicts, dict):
        raise ValueError("User-outcome filter: response missing 'verdicts' object")

    kept: List[UserOutcome] = []
    for outcome in outcomes:
        verdict = raw_verdicts.get(outcome.id)
        if not isinstance(verdict, dict):
            # Missing verdict = treat as ambiguous; default to KEEPING
            # the outcome.  Dropping a structurally-valid outcome
            # because the filter LLM forgot to evaluate it is worse
            # than keeping a borderline one — a downstream coverage
            # gap is recoverable, a vanished outcome is silent loss.
            logger.warning(
                "User-outcome filter: no verdict for %s — keeping by default",
                outcome.id,
            )
            kept.append(outcome)
            continue

        verifiable = verdict.get("verifiable")
        if not isinstance(verifiable, bool):
            raise ValueError(
                f"User-outcome filter: verdict for {outcome.id!r} "
                f"missing or non-boolean 'verifiable' field: {verdict!r}"
            )

        if verifiable:
            kept.append(outcome)
        else:
            reason = str(verdict.get("reason", "(no reason given)"))
            logger.info("User-outcome filter: dropped %s — %s", outcome.id, reason)

    return kept
