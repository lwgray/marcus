"""User-outcome coverage check for intent fidelity (issue #449).

Given a list of :class:`UserOutcome` records (from the extractor) and a
list of :class:`Task` records (from the decomposer), this module answers:

* Which tasks address each outcome? (:func:`compute_coverage`)
* Which in-scope outcomes have no covering task? (:func:`find_gaps`)
* What fraction of in-scope outcomes are covered?
  (:func:`compute_intent_fidelity_score`)
* When gaps exist, what tasks should be added? (:func:`fill_gaps`)

Two coverage strategies are available:

* :func:`compute_coverage` — sync, requires an explicit mapper.  Use
  :func:`keyword_overlap_mapper` for offline / test scenarios.  No
  default mapper is provided because the only sync option produces
  false positives on the snake_game-v31 case (#449's motivation).
* :func:`compute_coverage_with_llm` — async, single LLM call maps
  all outcomes to all tasks.  This is the production path; the LLM
  has the global context to distinguish "supports" from "addresses".
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


def keyword_overlap_mapper(outcome: UserOutcome, task: Task) -> bool:
    """Map outcome to task via keyword overlap (FALLBACK heuristic only).

    .. warning::

        **Do not use this as the production coverage strategy.**  It is
        provably inadequate on the snake_game-v31 case (the failure
        mode that motivated #449): outcomes and internal logic tasks
        share heavy domain-noun overlap (``snake``, ``food``, ``score``)
        which produces false positives — every logic task is wrongly
        marked as "covering" the play-the-game outcome.

        Use this mapper only when:

        * No LLM client is available (smoke tests, offline tooling)
        * Writing unit tests that exercise :func:`compute_coverage`
          mechanics and need a deterministic, sync mapper

        For production decomposer integration use
        :func:`compute_coverage_with_llm` instead — it issues a single
        LLM call that maps all outcomes to all tasks at once.

    Returns ``True`` when the lower-cased, stopword-filtered token sets
    of ``(outcome.action + outcome.success_signal)`` and
    ``(task.name + task.description)`` share at least one token.

    Parameters
    ----------
    outcome : UserOutcome
        The user-visible capability under check.
    task : Task
        The candidate task.

    Returns
    -------
    bool
        ``True`` if the token sets overlap.  This is necessary but not
        sufficient evidence that the task addresses the outcome — see
        the warning above.
    """
    outcome_tokens = _tokens(outcome.action + " " + outcome.success_signal)
    task_tokens = _tokens(task.name + " " + (task.description or ""))
    return bool(outcome_tokens & task_tokens)


def compute_coverage(
    outcomes: Iterable[UserOutcome],
    tasks: Iterable[Task],
    mapper: Callable[[UserOutcome, Task], bool],
) -> Dict[str, List[str]]:
    """Map every outcome (by id) to the task ids that address it.

    The ``mapper`` argument is **required**.  There is no implicit
    default because the only sync mapper in this module
    (:func:`keyword_overlap_mapper`) produces false positives on the
    snake_game-v31 case the whole module exists to catch — a
    contributor importing :func:`compute_coverage` without thinking
    about which mapper to use would silently re-introduce the v31
    regression.

    Parameters
    ----------
    outcomes : iterable of UserOutcome
        The outcomes extracted from the spec.  Order is preserved in
        the returned dict via insertion order.
    tasks : iterable of Task
        Decomposer-generated tasks to test.
    mapper : callable
        ``(outcome, task) -> bool`` predicate.  Pass
        :func:`keyword_overlap_mapper` for fallback / testing only;
        production callers should use :func:`compute_coverage_with_llm`
        instead, which performs the mapping with a single LLM call.

    Returns
    -------
    dict
        ``{outcome.id: [task.id, ...]}``.  Every outcome appears as a
        key; the list is empty when no task covers it.
    """
    task_list = list(tasks)
    coverage: Dict[str, List[str]] = {}
    for outcome in outcomes:
        coverage[outcome.id] = [task.id for task in task_list if mapper(outcome, task)]
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


_LLM_COVERAGE_PROMPT = """\
You are evaluating whether each user-visible outcome is addressed by
at least one task in a decomposed task graph.

A task "addresses" an outcome only when finishing it would contribute
in a user-observable way to the outcome.  Internal logic that only
maintains state, validates input, or supports another task does NOT
address a user outcome unless it produces something the user sees,
hears, or otherwise observes.

Example (the snake_game-v31 case):
- Outcome: "user can play the snake game" (signal: snake visibly
  moves on a board)
- Task "Snake state machine" (track snake body) — does NOT address
  the outcome (no rendering)
- Task "Render snake to canvas" (draw snake/food/score) — DOES
  address the outcome (produces user-visible movement)

Outcomes:
{outcomes_block}

Tasks:
{tasks_block}

Return strict JSON of the form:

{{
  "coverage": {{
    "<outcome_id>": ["<task_id>", "<task_id>", ...]
  }}
}}

Rules:
- Every outcome.id must appear as a key, even if the list is empty.
- Only include task ids that genuinely address the outcome — false
  positives are worse than false negatives because they hide gaps.
- Do not invent task ids.  Use exactly the ids from the input.
- Respond with ONLY the JSON object — no preamble, no markdown fences.
"""


async def compute_coverage_with_llm(
    outcomes: Iterable[UserOutcome],
    tasks: Iterable[Task],
    llm_client: Any,
    max_tokens: int = 2000,
) -> Dict[str, List[str]]:
    """Compute outcome → task coverage via a single LLM call.

    Production decomposer integration uses this function rather than
    :func:`compute_coverage` with a sync mapper.  One LLM call evaluates
    all outcomes against all tasks at once — cheaper than per-pair calls,
    and the LLM has the global context to distinguish "supports" from
    "addresses" (the keyword mapper cannot).

    Parameters
    ----------
    outcomes : iterable of UserOutcome
        Outcomes extracted from the spec.
    tasks : iterable of Task
        Tasks produced by the decomposer.
    llm_client : Any
        Async client exposing ``analyze(prompt, context)``.  Mocked in
        tests.
    max_tokens : int, optional
        Token budget for the LLM call.  Larger task graphs may need
        more headroom.

    Returns
    -------
    dict
        ``{outcome.id: [task.id, ...]}`` — same shape as
        :func:`compute_coverage`.  Every outcome appears as a key;
        unknown outcome ids in the LLM response are dropped, missing
        outcome ids are filled with empty lists.

    Raises
    ------
    ValueError
        On malformed JSON or a missing ``coverage`` key.
    """
    outcome_list = list(outcomes)
    task_list = list(tasks)

    if not outcome_list:
        return {}
    if not task_list:
        return {o.id: [] for o in outcome_list}

    outcomes_block = "\n".join(
        f"- {o.id}: {o.action} (signal: {o.success_signal})" for o in outcome_list
    )
    tasks_block = "\n".join(
        f"- {t.id}: {t.name} — {t.description or '(no description)'}" for t in task_list
    )
    prompt = _LLM_COVERAGE_PROMPT.format(
        outcomes_block=outcomes_block, tasks_block=tasks_block
    )

    raw = await llm_client.analyze(prompt, _MaxTokensContext(max_tokens))
    raw_text = str(raw) if raw is not None else ""

    try:
        payload = parse_ai_json_response(raw_text)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"LLM coverage: malformed JSON: {exc}") from exc

    raw_coverage = payload.get("coverage")
    if not isinstance(raw_coverage, dict):
        raise ValueError("LLM coverage: response missing 'coverage' object")

    valid_outcome_ids = {o.id for o in outcome_list}
    valid_task_ids = {t.id for t in task_list}
    coverage: Dict[str, List[str]] = {oid: [] for oid in valid_outcome_ids}
    for outcome_id, task_ids in raw_coverage.items():
        if outcome_id not in valid_outcome_ids:
            continue
        if not isinstance(task_ids, list):
            continue
        coverage[outcome_id] = [
            tid for tid in task_ids if isinstance(tid, str) and tid in valid_task_ids
        ]
    return coverage


_GAP_FILL_PROMPT_HEADER = """\
The following user-visible outcomes are required by the specification
but the current task graph does not cover them.  Generate the minimum
set of tasks that would address each gap.

Specification:
{spec}

Uncovered outcomes:
{gap_list}

Existing tasks already in the graph (so you can ground ``requires``
references in real upstream task names instead of inventing labels):

{existing_tasks_block}
"""

_GAP_FILL_PROMPT_CONTRACT_SECTION = """\

Existing contract artifacts already generated for this project.  When
your synthesized task consumes or implements one of these interfaces,
quote the exact field names and contract identifiers from below — do
NOT invent contract names.  This is the same contract context that
the decomposer's original tasks were built against; gap-fill tasks
must integrate with that contract surface.

{contract_block}
"""

_GAP_FILL_PROMPT_SCHEMA_NO_CONTRACT = """\

Return strict JSON of the form:

{{
  "tasks": [
    {{
      "name": "<short task name>",
      "description": "<what to build, including how downstream agents will consume it>",
      "provides": "<interface this task makes available, or null>",
      "requires": "<interface this task consumes from upstream, or null>"
    }}
  ]
}}

Rules:
- One or more tasks per gap is allowed.
- Task names must be concrete (e.g. ``"Render snake to canvas"``) not
  generic (``"implement feature"``).
- Descriptions must say WHAT to build, not HOW.  No library choices.
- ``provides`` names an interface this task makes available to the
  rest of the graph.  Use ``null`` when the task is a pure
  user-visible endpoint with no downstream consumer.
- ``requires`` names an interface this task consumes from an existing
  task in the graph.  Use ``null`` when the task is self-contained.
- Return ONLY the JSON object — no preamble, no markdown fences.
"""

_GAP_FILL_PROMPT_SCHEMA_WITH_CONTRACT = """\

Return strict JSON of the form:

{{
  "tasks": [
    {{
      "name": "<short task name>",
      "description": "<what to build, including how downstream agents will consume it>",
      "provides": "<interface this task makes available, or null>",
      "requires": "<interface this task consumes from upstream, or null>",
      "responsibility": "<contract interface this task OWNS, or null>"
    }}
  ]
}}

Rules:
- One or more tasks per gap is allowed.
- Task names must be concrete (e.g. ``"Render snake to canvas"``) not
  generic (``"implement feature"``).
- Descriptions must say WHAT to build, not HOW.  No library choices.
- ``provides`` and ``requires`` MUST quote names that exist in the
  contract artifacts above when the task consumes or produces a
  contract-defined interface.  Use ``null`` only for tasks with no
  contract-side relationship.
- ``responsibility`` names the specific contract interface this task
  owns (the canonical "build this side of the contract" framing).
  Format: ``"implements <InterfaceName> from <relative_path>"``.  Use
  ``null`` when the task is purely a consumer.
- Return ONLY the JSON object — no preamble, no markdown fences.
"""


class _MaxTokensContext:
    """Minimal context wrapper passed to LLM clients that expect one."""

    def __init__(self, max_tokens: int) -> None:
        self.max_tokens = max_tokens


def _format_existing_tasks_block(existing_tasks: List[Task]) -> str:
    """Render the existing-tasks portion of the gap-fill prompt."""
    if not existing_tasks:
        return "(no tasks in the graph yet)"
    return "\n".join(
        f"- {t.id}: {t.name} — {t.description or '(no description)'}"
        for t in existing_tasks
    )


def _format_contract_block(contract_artifacts: Dict[str, Any]) -> str:
    """Render the contract-artifacts portion of the gap-fill prompt.

    ``contract_artifacts`` is the structure produced by
    ``_generate_contracts_by_domain`` in ``advanced_parser.py``: a
    domain-keyed dict where each value has an ``"artifacts"`` list,
    each artifact having ``filename`` / ``content`` /
    ``relative_path``.
    """
    sections: List[str] = []
    for domain, payload in contract_artifacts.items():
        if not payload:
            continue
        artifacts = payload.get("artifacts") if isinstance(payload, dict) else None
        if not isinstance(artifacts, list):
            continue
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            filename = (
                artifact.get("filename") or artifact.get("relative_path") or "<unknown>"
            )
            content = artifact.get("content") or ""
            sections.append(
                f"### Domain: {domain}\n### File: {filename}\n```\n{content}\n```"
            )
    if not sections:
        return "(no usable contract artifacts)"
    return "\n\n".join(sections)


async def fill_gaps(
    spec: str,
    gaps: List[UserOutcome],
    existing_tasks: List[Task],
    llm_client: Any,
    *,
    contract_artifacts: Optional[Dict[str, Any]] = None,
    max_tokens: int = 2000,
) -> List[Dict[str, Any]]:
    """Generate replacement tasks for uncovered outcomes via a single LLM call.

    The LLM sees the existing task graph (so it can ground its
    ``requires`` references in real task names) and, when available,
    the contract artifacts the decomposer used (so its ``provides`` /
    ``requires`` / ``responsibility`` fields name real contract
    interfaces rather than inventing labels).  This is what fixes the
    PR #454-era failure mode where gap-fill tasks shipped with
    ungrounded contract metadata that nothing else in the graph could
    consume.

    No call is made when ``gaps`` is empty.

    Parameters
    ----------
    spec : str
        Project specification, included verbatim so the LLM can
        respect scope language.
    gaps : list of UserOutcome
        Outcomes the decomposer missed.  Out-of-scope outcomes have
        already been filtered out by the caller.
    existing_tasks : list of Task
        Tasks already in the graph.  Required — the LLM uses these to
        ground its ``requires`` references in real task names instead
        of inventing labels.  Pass an empty list only when the graph
        truly has no tasks yet (rare; coverage check would not have
        produced gaps in that case).
    llm_client : Any
        Async client exposing ``analyze(prompt, context)``.
    contract_artifacts : Optional[Dict[str, Any]], keyword-only
        The contract artifacts produced by
        ``_generate_contracts_by_domain``.  When provided, the prompt
        includes a contract section and asks for a ``responsibility``
        field on each task; when ``None`` (feature-based path), the
        contract section and responsibility field are omitted.
    max_tokens : int, keyword-only, default 2000
        Token budget for the LLM call.

    Returns
    -------
    list of dict
        Each dict has:

        - ``name`` (str): short task name
        - ``description`` (str): what to build
        - ``provides`` (str | None): interface this task exposes
        - ``requires`` (str | None): interface this task consumes
        - ``responsibility`` (str | None): contract interface this
          task owns (only present when ``contract_artifacts`` was
          supplied; ``None`` for purely-consumer tasks)

    Raises
    ------
    ValueError
        On malformed JSON, missing ``tasks`` key, missing required
        ``name`` / ``description``, or any contract field with a
        non-string-or-null value.
    """
    if not gaps:
        return []

    gap_lines = "\n".join(
        f"- {gap.id}: {gap.action} (success: {gap.success_signal})" for gap in gaps
    )
    existing_block = _format_existing_tasks_block(existing_tasks)

    contracts_present = contract_artifacts is not None and bool(contract_artifacts)
    if contracts_present:
        contract_block = _format_contract_block(contract_artifacts or {})
        contract_section = _GAP_FILL_PROMPT_CONTRACT_SECTION.format(
            contract_block=contract_block
        )
        schema_section = _GAP_FILL_PROMPT_SCHEMA_WITH_CONTRACT
    else:
        contract_section = ""
        schema_section = _GAP_FILL_PROMPT_SCHEMA_NO_CONTRACT

    prompt = (
        _GAP_FILL_PROMPT_HEADER.format(
            spec=spec, gap_list=gap_lines, existing_tasks_block=existing_block
        )
        + contract_section
        + schema_section
    )

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

    # Optional contract fields.  ``responsibility`` is only meaningful
    # when contracts were supplied — for feature-based gap-fill, it is
    # omitted from the output entirely.
    optional_contract_fields: tuple[str, ...] = ("provides", "requires")
    if contracts_present:
        optional_contract_fields = optional_contract_fields + ("responsibility",)

    validated: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw_tasks):
        if not isinstance(item, dict):
            raise ValueError(f"Outcome gap-fill: task at index {idx} is not an object")

        # Required fields: name, description must be strings.  Reject
        # null / non-string rather than coerce — str(None) becomes the
        # literal string "None" which would silently pass the
        # empty-string checks below.
        for required_field in ("name", "description"):
            value = item.get(required_field)
            if not isinstance(value, str):
                raise ValueError(
                    f"Outcome gap-fill: task at index {idx} field "
                    f"{required_field!r} must be a string, got "
                    f"{type(value).__name__}: {value!r}"
                )

        # Optional contract fields must be string or null.  Anything
        # else is malformed.
        for optional_field in optional_contract_fields:
            if optional_field in item:
                value = item[optional_field]
                if value is not None and not isinstance(value, str):
                    raise ValueError(
                        f"Outcome gap-fill: task at index {idx} field "
                        f"{optional_field!r} must be a string or null, got "
                        f"{type(value).__name__}: {value!r}"
                    )

        name = item["name"].strip()
        description = item["description"].strip()
        if not name:
            raise ValueError(f"Outcome gap-fill: task at index {idx} missing 'name'")
        if not description:
            raise ValueError(
                f"Outcome gap-fill: task at index {idx} missing 'description'"
            )

        provides_raw = item.get("provides")
        requires_raw = item.get("requires")
        provides = provides_raw.strip() if isinstance(provides_raw, str) else None
        requires = requires_raw.strip() if isinstance(requires_raw, str) else None

        result_dict: Dict[str, Any] = {
            "name": name,
            "description": description,
            "provides": provides if provides else None,
            "requires": requires if requires else None,
        }

        if contracts_present:
            responsibility_raw = item.get("responsibility")
            responsibility = (
                responsibility_raw.strip()
                if isinstance(responsibility_raw, str)
                else None
            )
            result_dict["responsibility"] = responsibility if responsibility else None

        validated.append(result_dict)

    return validated
