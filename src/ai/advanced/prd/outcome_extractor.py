"""User-outcome extraction for intent fidelity coverage (issue #449).

The decomposer historically treats specs as flat feature lists and never
verifies that the union of features yields a usable product.  v31 of the
snake-game experiment shipped a perfectly-tested engine with no rendering
because no task said "render the snake" — the spec implied it but the
decomposer had no representation of what "done" means to a user.

This module produces a list of :class:`UserOutcome` records from a spec.
Each outcome is a concrete user action ("user can play the snake game")
paired with an observable success signal.  Downstream stages use the list
as decomposition constraints (every in-scope outcome must map to at least
one task) and to compute the ``intent_fidelity_score`` metric.

The extractor itself is a thin wrapper around an LLM call that validates
the result against the schema — the validation is what makes the
abstraction useful, not the call itself.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, List

from src.utils.json_parser import parse_ai_json_response

# Patterns that mark a real user-capability action.  Word-boundary
# regex (not substring) so that ``"user cannot ..."`` and ``"user
# can't ..."`` do NOT match — those are negations and contradict the
# positive-capability invariant.  The lookahead ``(?!')`` rejects the
# ``"can't"`` contraction.
_USER_CAPABILITY_PATTERNS: tuple["re.Pattern[str]", ...] = (
    re.compile(r"\busers? can\b(?!')", re.IGNORECASE),
    re.compile(r"\busers? (?:is|are) able to\b", re.IGNORECASE),
    re.compile(r"\busers? must be able to\b", re.IGNORECASE),
)

# Negation markers — even if a positive pattern also matches, presence
# of any of these phrases means the action is NOT a positive capability
# (e.g. ``"user cannot play"`` or ``"user can never log in"``).
_NEGATION_PATTERNS: tuple["re.Pattern[str]", ...] = (
    re.compile(r"\bcannot\b", re.IGNORECASE),
    re.compile(r"\bcan ?not\b", re.IGNORECASE),
    re.compile(r"\bcan't\b", re.IGNORECASE),
    re.compile(r"\bunable\b", re.IGNORECASE),
    re.compile(r"\bnever\b", re.IGNORECASE),
    re.compile(r"\bwon't\b", re.IGNORECASE),
    re.compile(r"\bwill not\b", re.IGNORECASE),
)

# Vague verbs / phrases that pass the "user can" check but carry no
# observable meaning.  These are rejected to keep the outcome list useful
# as a coverage gate.
#
# .. warning::
#
#     **DO NOT EXPAND THIS LIST.**  Maintaining a hand-curated denylist
#     of vague phrasings is a band-aid that recreates the
#     project-type-specific guard pattern this module was built to
#     replace (see ``advanced_parser.py`` ``frontend`` / ``e-commerce``
#     / ``UI/UX`` band-aids — that growth pattern was the original sin).
#
#     The structural fix is an LLM specificity self-check: after
#     extraction, run a second LLM pass that scores each outcome's
#     observability and rejects low-scoring ones.  That generalizes
#     across phrasings without requiring this list to grow.
#
#     The current denylist is the minimum viable catch for the most
#     common LLM failure modes ("user can use the app" was the v31
#     antipattern).  When you find a new vague phrasing slipping
#     through, add the LLM self-check, do not extend this tuple.
_VAGUE_PHRASES: tuple[str, ...] = (
    "use the app",
    "use the application",
    "use the product",
    "use it",
    "interact with the app",
    "interact with the application",
    "do stuff",
    "do things",
)

_VALID_SCOPES: frozenset[str] = frozenset({"in_scope", "out_of_scope"})


@dataclass
class UserOutcome:
    """A user-visible outcome the product must satisfy.

    Parameters
    ----------
    id : str
        Stable identifier used to map outcomes to tasks during the
        coverage check.  Convention: ``outcome_<short_action_verb>``.
    action : str
        Concrete user capability statement.  Must contain a phrase
        from :data:`_USER_CAPABILITY_PATTERNS` (word-boundary regex).
        Vague phrasings such as "user can use the app" are rejected;
        negations such as "user cannot ..." or "user can't ..." are
        also rejected via :data:`_NEGATION_PATTERNS`.
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
        If any field violates its invariant.  Validation runs in
        ``__post_init__`` so invalid outcomes can never reach the
        coverage check.
    """

    id: str
    action: str
    success_signal: str
    scope: str

    def __post_init__(self) -> None:
        """Validate all fields; reject vague, malformed, or negated outcomes."""
        if not self.id:
            raise ValueError("UserOutcome.id must be a non-empty string")

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

        # Reject negations FIRST — "user cannot play" contains "user can"
        # as a substring, so word-boundary positive matching alone is not
        # enough.  An action with a negation marker is never a positive
        # capability regardless of whether a positive pattern also matches.
        if any(p.search(self.action) for p in _NEGATION_PATTERNS):
            raise ValueError(
                "UserOutcome.action contains a negation (cannot / can't / "
                "unable / never / won't / will not) — outcomes must "
                f"express positive capabilities; got {self.action!r}"
            )

        if not any(p.search(self.action) for p in _USER_CAPABILITY_PATTERNS):
            raise ValueError(
                "UserOutcome.action must express a user capability "
                "(e.g. 'user can <verb>', 'users are able to <verb>'); "
                f"got {self.action!r}"
            )

        action_lc = self.action.lower()
        if any(vague in action_lc for vague in _VAGUE_PHRASES):
            raise ValueError(
                f"UserOutcome.action is too vague to be verifiable: "
                f"{self.action!r}.  Replace with a concrete user-visible "
                "capability (e.g. 'user can play the snake game')."
            )


_EXTRACTION_PROMPT = """\
You are extracting user-visible outcomes from a project specification.

A user outcome is a concrete capability the user must have when the
product is finished — phrased as "user can <verb> <object> <observable
detail>". Each outcome must be verifiable: an observer running the
finished product must be able to tell yes/no whether it is satisfied.

Return strict JSON of the form:

{{
  "outcomes": [
    {{
      "id": "outcome_<short_verb>",
      "action": "user can <verb> <object> ...",
      "success_signal": "<observable evidence>",
      "scope": "in_scope" | "out_of_scope"
    }}
  ]
}}

Rules:
- Every action must contain "user can" (or "users can" / "is able to").
- "user can use the app" is too vague — reject this phrasing. Use
  concrete actions tied to the product domain.
- Outcomes the spec explicitly excludes (e.g. "no auth", "no accounts")
  must still be listed but tagged "out_of_scope" so the audit trail is
  preserved.
- Every project has at least one outcome — never return an empty list.
- Provide a success_signal even for out-of-scope outcomes.

Specification:
{spec}

Respond with ONLY the JSON object — no preamble, no markdown fences.
"""


class _MaxTokensContext:
    """Minimal context wrapper passed to LLM clients that expect one."""

    def __init__(self, max_tokens: int) -> None:
        self.max_tokens = max_tokens


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
    raw = await llm_client.analyze(prompt, _MaxTokensContext(max_tokens))
    raw_text = str(raw) if raw is not None else ""

    try:
        payload = parse_ai_json_response(raw_text)
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

    return outcomes
