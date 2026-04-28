"""User-outcome coverage check for intent fidelity (issue #449).

Given a list of :class:`UserOutcome` records (from the extractor) and a
list of :class:`Task` records (from the decomposer), this module answers:

* Which tasks address each outcome? (:func:`compute_coverage`)
* Which in-scope outcomes have no covering task? (:func:`find_gaps`)
* What fraction of in-scope outcomes are covered?
  (:func:`compute_intent_fidelity_score`)
* When gaps exist, what tasks should be added? (:func:`fill_gaps`)

The default coverage mapper is keyword-based — fast, deterministic, no
LLM cost during the check.  Tests can inject an explicit mapper to bypass
the default heuristic.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

from src.ai.advanced.prd.outcome_extractor import UserOutcome
from src.core.models import Task
from src.utils.json_parser import parse_ai_json_response

# Words too common to discriminate between outcome and task.  Stripped
# from the keyword sets before overlap is computed.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "if",
        "of",
        "in",
        "on",
        "at",
        "to",
        "for",
        "with",
        "by",
        "from",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "user",
        "users",
        "can",
        "able",
        "must",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "their",
        "there",
        "when",
        "where",
        "what",
        "who",
        "how",
        "all",
        "any",
        "some",
        "no",
        "not",
        "so",
        "than",
        "then",
        "into",
        "out",
        "up",
        "down",
        "over",
        "under",
        "again",
        "more",
        "most",
        "other",
        "such",
        "own",
        "same",
        "very",
        "will",
        "just",
        "also",
        # signal-domain noise
        "observable",
        "appears",
        "shows",
        "displays",
        "set",
        "works",
        # action verbs that almost always appear in outcomes (don't help
        # discriminate)
        "see",
        "view",
        "use",
        "make",
        "get",
        "go",
    }
)

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]+")


def _tokens(text: str) -> Set[str]:
    """Lower-cased, stopword-filtered token set for keyword overlap."""
    return {
        match.group().lower()
        for match in _TOKEN_RE.finditer(text)
        if match.group().lower() not in _STOPWORDS and len(match.group()) >= 3
    }


def _default_mapper(outcome: UserOutcome, task: Task) -> bool:
    """Map outcome to task via keyword overlap (default coverage heuristic).

    Combines ``action`` and ``success_signal`` for the outcome and
    ``name`` and ``description`` for the task, then asks whether the
    intersection (after stopword removal) is non-empty.

    The threshold is intentionally low (≥1 shared token) — tasks that
    are too narrow to share even one distinctive token with an outcome
    are very likely not addressing it.  False positives in coverage
    are recoverable (a task can address more than one outcome); false
    negatives manifest as a gap, which triggers a single LLM call to
    fill — the worst case.

    Parameters
    ----------
    outcome : UserOutcome
        The user-visible capability under check.
    task : Task
        The candidate task.

    Returns
    -------
    bool
        ``True`` if the task plausibly addresses the outcome.
    """
    outcome_tokens = _tokens(outcome.action + " " + outcome.success_signal)
    task_tokens = _tokens(task.name + " " + (task.description or ""))
    return bool(outcome_tokens & task_tokens)


def compute_coverage(
    outcomes: Iterable[UserOutcome],
    tasks: Iterable[Task],
    mapper: Optional[Callable[[UserOutcome, Task], bool]] = None,
) -> Dict[str, List[str]]:
    """Map every outcome (by id) to the task ids that address it.

    Parameters
    ----------
    outcomes : iterable of UserOutcome
        The outcomes extracted from the spec.  Order is preserved in the
        returned dict via insertion order.
    tasks : iterable of Task
        Decomposer-generated tasks to test.
    mapper : callable, optional
        Custom ``(outcome, task) -> bool`` predicate.  When ``None``,
        :func:`_default_mapper` (keyword overlap) is used.  Tests inject
        explicit mappers to control coverage deterministically.

    Returns
    -------
    dict
        ``{outcome.id: [task.id, ...]}``.  Every outcome appears as a
        key; the list is empty when no task covers it.
    """
    use_mapper = mapper or _default_mapper
    task_list = list(tasks)
    coverage: Dict[str, List[str]] = {}
    for outcome in outcomes:
        coverage[outcome.id] = [
            task.id for task in task_list if use_mapper(outcome, task)
        ]
    return coverage


def find_gaps(
    outcomes: Iterable[UserOutcome],
    coverage: Dict[str, List[str]],
) -> List[UserOutcome]:
    """Return in-scope outcomes that have no covering task.

    Out-of-scope outcomes are excluded — they are tracked in the audit
    trail but never count as gaps because the spec said not to build them.

    Parameters
    ----------
    outcomes : iterable of UserOutcome
        Outcomes to check.
    coverage : dict
        Output of :func:`compute_coverage`.

    Returns
    -------
    list of UserOutcome
        Outcomes that are in-scope and uncovered, in original order.
    """
    return [
        outcome
        for outcome in outcomes
        if outcome.scope == "in_scope" and not coverage.get(outcome.id, [])
    ]


def compute_intent_fidelity_score(
    outcomes: Iterable[UserOutcome],
    coverage: Dict[str, List[str]],
) -> float:
    """Fraction of in-scope outcomes that have at least one covering task.

    Returns ``1.0`` when there are no in-scope outcomes — vacuously
    satisfied, since there is nothing to fail.  Other choices (NaN,
    0.0, raise) all surprise consumers; treat absence as full fidelity.

    Parameters
    ----------
    outcomes : iterable of UserOutcome
        All outcomes (in-scope and out-of-scope).
    coverage : dict
        Output of :func:`compute_coverage`.

    Returns
    -------
    float
        Score in ``[0.0, 1.0]``.
    """
    in_scope = [o for o in outcomes if o.scope == "in_scope"]
    if not in_scope:
        return 1.0
    covered = sum(1 for o in in_scope if coverage.get(o.id))
    return covered / len(in_scope)


_GAP_FILL_PROMPT = """\
The following user-visible outcomes are required by the specification
but the current task graph does not cover them.  Generate the minimum
set of tasks that would address each gap.

Specification:
{spec}

Uncovered outcomes:
{gap_list}

Return strict JSON of the form:

{{
  "tasks": [
    {{
      "name": "<short task name>",
      "description": "<what to build, including how downstream agents '
      'will consume it>"
    }}
  ]
}}

Rules:
- One or more tasks per gap is allowed.
- Task names must be concrete (e.g. "Render snake to canvas") not
  generic ("implement feature").
- Descriptions must say WHAT to build, not HOW.  No library choices.
- Return ONLY the JSON object — no preamble, no markdown fences.
"""


class _MaxTokensContext:
    """Minimal context wrapper passed to LLM clients that expect one."""

    def __init__(self, max_tokens: int) -> None:
        self.max_tokens = max_tokens


async def fill_gaps(
    spec: str,
    gaps: List[UserOutcome],
    llm_client: Any,
    max_tokens: int = 1500,
) -> List[Dict[str, Any]]:
    """Generate replacement tasks for uncovered outcomes via a single LLM call.

    No call is made when ``gaps`` is empty — coverage was full and we
    save the round-trip.

    Parameters
    ----------
    spec : str
        The original project spec, included verbatim so the LLM can
        respect scope language.
    gaps : list of UserOutcome
        Outcomes the decomposer missed.  Caller is expected to have
        filtered out out-of-scope outcomes already.
    llm_client : Any
        Async client exposing ``analyze(prompt, context)``.
    max_tokens : int, optional
        Token budget for the LLM call.

    Returns
    -------
    list of dict
        Each dict has at minimum ``name`` and ``description`` keys.  The
        decomposer constructs full :class:`Task` objects from these
        dicts (synthesis hours, dependencies, labels, etc.).

    Raises
    ------
    ValueError
        On malformed JSON, missing ``tasks`` key, or any task missing
        ``name`` / ``description``.
    """
    if not gaps:
        return []

    gap_lines = "\n".join(
        f"- {gap.id}: {gap.action} (success: {gap.success_signal})" for gap in gaps
    )
    prompt = _GAP_FILL_PROMPT.format(spec=spec, gap_list=gap_lines)

    raw = await llm_client.analyze(prompt, _MaxTokensContext(max_tokens))
    raw_text = str(raw) if raw is not None else ""

    try:
        payload = parse_ai_json_response(raw_text)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"Outcome gap-fill: LLM returned malformed JSON: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError(
            "Outcome gap-fill: LLM JSON must be an object with 'tasks' key"
        )
    raw_tasks = payload.get("tasks")
    if not isinstance(raw_tasks, list):
        raise ValueError("Outcome gap-fill: 'tasks' must be a JSON array")

    validated: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw_tasks):
        if not isinstance(item, dict):
            raise ValueError(f"Outcome gap-fill: task at index {idx} is not an object")
        name = str(item.get("name", "")).strip()
        description = str(item.get("description", "")).strip()
        if not name:
            raise ValueError(f"Outcome gap-fill: task at index {idx} missing 'name'")
        if not description:
            raise ValueError(
                f"Outcome gap-fill: task at index {idx} missing 'description'"
            )
        validated.append({"name": name, "description": description})

    return validated
