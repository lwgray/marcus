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
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional, Set
from uuid import uuid4

from src.ai.advanced.prd.outcome_extractor import UserOutcome
from src.config.outcome_coverage_config import is_outcome_coverage_enabled
from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.coordinator.graph_augmentation import AugmentationResult
from src.utils.json_parser import parse_ai_json_response

if TYPE_CHECKING:
    # TYPE_CHECKING-only to avoid the runtime cycle:
    # advanced_parser imports from this module.
    from src.ai.advanced.prd.advanced_parser import PRDAnalysis

logger = logging.getLogger(__name__)

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

DEFAULT TO EMPTY.  The decomposer typically produces only internal
or structural tasks — data models, services, APIs, business logic —
in the first pass.  Most user-visible outcomes will have NO covering
task in this graph.  Returning an empty list for an outcome IS the
expected case, not a failure.  An empty result with score 0.0 is a
healthy honest signal; a falsely-full result with score 1.0 hides
real gaps and breaks downstream gap-fill.

More domain examples (the principle, applied):

  Web app with REST backend (the user is a human in a browser):
    Outcome: "user can sign up"
    - Task "Signup form page that POSTs to /api/users and renders
      success or error" → ADDRESSES (form is visible to the user;
      the rendered result is the user-observable signal)
    - Task "POST /api/users endpoint" → does NOT (backend plumbing —
      without a UI calling it, the user sees nothing; this is
      supporting work for the form task above)
    - Task "User schema validation" → does NOT (internal precondition)

  Developer-facing API product (the user IS an API consumer):
    Outcome: "developer can create a user via the API"
    - Task "POST /api/users endpoint that returns 201 with user JSON"
      → ADDRESSES (the API response IS the product surface for this
      user; the developer reads the JSON directly)
    - Task "User schema validation" → does NOT (internal precondition)

  Same task, different verdict: who the "user" is determines whether
  a backend endpoint is the surface or the plumbing.  Read the spec
  to identify the user.  When the spec says "REST API backend, web
  frontend," the user is the human in the browser and the endpoint
  is plumbing.  When the spec says "REST API for third-party
  developers," the user is a developer and the endpoint is the
  surface.  When uncertain, treat backend-only tasks as plumbing.

  File-handling:
    Outcome: "user can upload a recipe photo"
    - Task "Photo upload form with progress indicator" → ADDRESSES
      (form is shown, progress is observable)
    - Task "Image storage backend" → does NOT (internal plumbing)

  Notification:
    Outcome: "user is alerted when their post is liked"
    - Task "Send like notification to user device" → ADDRESSES
      (device notification is observable)
    - Task "Like event aggregation worker" → does NOT (internal
      counting)

  CLI:
    Outcome: "user sees results of their query"
    - Task "Print query results to stdout" → ADDRESSES (terminal
      output is observable)
    - Task "Query optimizer" → does NOT (internal performance)

The pattern across all of these: a task addresses an outcome when
COMPLETING IT PRODUCES the observable signal the user can sense.
Internal correctness, validation, storage, scheduling, contract
definition, and service plumbing do not — even when their names
sound related to the outcome.  Domains differ; the principle does
not.  Apply the same judgment to whatever domain this project is
in, not just the ones above.

Tiebreaker: when you cannot describe what user-observable evidence
the task produces, return an empty list.  When in doubt, empty
list.  False positives are worse than false negatives because they
hide gaps from the next pipeline stage.

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
- Only include a task id when you can describe what user-observable
  evidence completing that task produces (a screen shown, an HTTP
  response, a file written that the user reads, a notification
  delivered).  If the task only produces internal state, return
  an empty list for that outcome.
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


@dataclass
class OutcomeCoverageResult:
    """Result of running the full outcome coverage pipeline.

    Returned by :func:`apply_outcome_coverage`.  Each decomposer
    converts ``synthesized_tasks`` (gap-fill output dicts) into proper
    :class:`Task` objects in its own conventions — feature-based
    tasks get default fields; contract-first tasks get
    ``responsibility`` set from the dict.

    Attributes
    ----------
    synthesized_tasks : list of dict
        Gap-fill output dicts (same shape as :func:`fill_gaps`
        returns).  Empty when coverage was full or when no outcomes
        were supplied.
    intent_fidelity_score : float
        Final score on the augmented graph (post gap-fill).  In
        ``[0.0, 1.0]``.  ``1.0`` when there are no in-scope outcomes
        (vacuously satisfied).
    coverage_before_fill : dict
        ``{outcome.id: [task.id, ...]}`` from the initial coverage
        check, before any gap-fill ran.  Useful for logging /
        debugging the original task graph's coverage.
    gaps : list of UserOutcome
        In-scope outcomes that had no covering task in the initial
        graph.  These are the inputs to :func:`fill_gaps`.  Empty
        when coverage was full.
    """

    synthesized_tasks: List[Dict[str, Any]]
    intent_fidelity_score: float
    coverage_before_fill: Dict[str, List[str]] = field(default_factory=dict)
    coverage_after_fill: Optional[Dict[str, List[str]]] = None
    gaps: List[UserOutcome] = field(default_factory=list)


# Public so tests don't have to hardcode the literal in mock LLM
# responses.  The prefix marks task IDs we synthesize internally for
# the recoverage check; the caller's task_factory replaces them with
# proper IDs (gap_fill_<uuid> or kanban-backed) before the augmented
# graph reaches downstream consumers.
STUB_TASK_ID_PREFIX: str = "_synth_for_coverage_"


def _normalize_gap_task_name(name: str) -> str:
    """Convert ``snake_case`` LLM slug to a readable task name.

    Weak local models occasionally ignore the prompt instruction to
    produce concrete human-readable names (e.g. ``"Render snake to
    canvas"``) and instead return Python-style slugs such as
    ``"render_snake_to_canvas"``.  This normalizer detects the slug
    pattern — underscores present, no spaces — and converts it to
    Title Case.  Already-readable names pass through unchanged.

    Parameters
    ----------
    name : str
        Raw name from the gap-fill LLM response.

    Returns
    -------
    str
        Human-readable name; empty string when input is blank.

    Examples
    --------
    >>> _normalize_gap_task_name("render_game_board")
    'Render Game Board'
    >>> _normalize_gap_task_name("Render game board")
    'Render game board'
    >>> _normalize_gap_task_name("")
    ''
    """
    name = name.strip()
    if not name:
        return name
    # Slug detection: underscores present AND no spaces
    if "_" in name and " " not in name:
        return " ".join(word.capitalize() for word in name.split("_"))
    return name


def _build_recoverage_description(gap_dict: Dict[str, Any]) -> str:
    """Render a description that surfaces contract metadata for the recheck.

    The post-fill coverage check is an LLM call that scores tasks by
    name + description only.  When gap-fill emits a task with
    ``provides`` / ``requires`` / ``responsibility``, those fields
    carry semantic load — the LLM should see them when judging
    whether the synthesized task actually covers an outcome.

    For example, a task whose description says only "draw on canvas"
    is ambiguous; appending ``(provides=RenderingAgent.draw)`` makes
    the contract surface visible to the recheck LLM, raising the
    odds it scores the task as covering the play-the-game outcome.
    """
    base = str(gap_dict["description"])
    parts: List[str] = []
    provides = gap_dict.get("provides")
    requires = gap_dict.get("requires")
    responsibility = gap_dict.get("responsibility")
    if provides:
        parts.append(f"provides={provides}")
    if requires:
        parts.append(f"requires={requires}")
    if responsibility:
        parts.append(f"responsibility={responsibility}")
    if not parts:
        return base
    return f"{base}\n\nContract: " + ", ".join(parts)


def _make_stub_task_for_coverage(idx: int, gap_dict: Dict[str, Any]) -> Task:
    """Build a stub :class:`Task` for the post-fill coverage recheck.

    :func:`compute_coverage_with_llm` only reads ``id`` / ``name`` /
    ``description`` from each task when rendering its prompt, so the
    other Task fields can be filler.  The description is enriched
    with contract metadata via :func:`_build_recoverage_description`
    so the recheck LLM has full signal when scoring.

    Real task construction (with sibling-inherited estimated_hours,
    project_id, contract responsibility, etc.) happens in the
    caller's task_factory after :func:`apply_outcome_coverage`
    returns.
    """
    now = datetime.now(timezone.utc)
    return Task(
        id=f"{STUB_TASK_ID_PREFIX}{idx}",
        name=_normalize_gap_task_name(gap_dict["name"]),
        description=_build_recoverage_description(gap_dict),
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=1.0,
    )


async def apply_outcome_coverage(
    *,
    spec: str,
    outcomes: List[UserOutcome],
    tasks: List[Task],
    llm_client: Any,
    contract_artifacts: Optional[Dict[str, Any]] = None,
) -> OutcomeCoverageResult:
    """Run the full intent-fidelity coverage pipeline.

    Both decomposers (``parse_prd_to_tasks`` and
    ``decompose_by_contract``) call this internally after producing
    their initial task graph.  Each decomposer then converts
    ``result.synthesized_tasks`` into proper :class:`Task` objects in
    its own conventions and appends to its output.

    Pipeline:

    1. Coverage check on the initial task graph (1 LLM call)
    2. Identify gaps among in-scope outcomes
    3. If gaps exist:
       a. Gap-fill with full context (1 LLM call) — sees the
          existing task graph and, when supplied, the contract
          artifacts so its provides/requires/responsibility quote
          real interface names
       b. Recompute coverage on the augmented graph (1 LLM call) —
          gap-fill is an LLM call that might produce tasks that
          don't actually cover; the score reflects measured coverage
          on the augmented graph, not assumed
    4. Score = covered_in_scope / total_in_scope from the final coverage

    Total LLM cost: 1 call when no gaps; 3 calls when gaps exist.

    Parameters
    ----------
    spec : str
        Project specification, passed to :func:`fill_gaps` for
        context.
    outcomes : list of UserOutcome
        Outcomes extracted from the spec.  Empty list returns a
        vacuous-success result with no LLM calls.
    tasks : list of Task
        The initial task graph the decomposer just produced.
    llm_client : Any
        Async client exposing ``analyze(prompt, context)``.
    contract_artifacts : Optional[Dict[str, Any]], keyword-only
        Contract artifacts from ``_generate_contracts_by_domain``.
        When provided, gap-fill emits a ``responsibility`` field
        per synthesized task (contract-first path).  When ``None``,
        gap-fill omits ``responsibility`` (feature-based path).

    Returns
    -------
    OutcomeCoverageResult
        Synthesized tasks + score + audit-trail fields.

    Raises
    ------
    ValueError
        From :func:`compute_coverage_with_llm` or :func:`fill_gaps`
        when an LLM call returns malformed JSON.  Callers
        (decomposers) should catch and downgrade to a warning rather
        than fail the whole project — the legacy "no coverage check"
        path is the always-available fallback.
    """
    if not outcomes:
        return OutcomeCoverageResult(
            synthesized_tasks=[],
            intent_fidelity_score=1.0,
        )

    coverage_before = await compute_coverage_with_llm(
        outcomes=outcomes,
        tasks=tasks,
        llm_client=llm_client,
    )
    gaps = find_gaps(outcomes, coverage_before)

    if not gaps:
        # No gap-fill needed.  Score from the initial coverage map.
        return OutcomeCoverageResult(
            synthesized_tasks=[],
            intent_fidelity_score=compute_intent_fidelity_score(
                outcomes, coverage_before
            ),
            coverage_before_fill=coverage_before,
            gaps=[],
        )

    synthesized_dicts = await fill_gaps(
        spec=spec,
        gaps=gaps,
        existing_tasks=tasks,
        llm_client=llm_client,
        contract_artifacts=contract_artifacts,
    )

    if not synthesized_dicts:
        # Gap-fill produced nothing — degraded LLM behavior, but the
        # function did not raise.  Score from coverage_before since
        # the graph is unchanged.
        return OutcomeCoverageResult(
            synthesized_tasks=[],
            intent_fidelity_score=compute_intent_fidelity_score(
                outcomes, coverage_before
            ),
            coverage_before_fill=coverage_before,
            gaps=gaps,
        )

    # Build stubs for the recoverage check; the real Task
    # construction (with proper hours / project_id / responsibility)
    # happens in the caller's task_factory after this returns.
    stubs = [
        _make_stub_task_for_coverage(idx, d) for idx, d in enumerate(synthesized_dicts)
    ]
    augmented_tasks = list(tasks) + stubs
    coverage_after = await compute_coverage_with_llm(
        outcomes=outcomes,
        tasks=augmented_tasks,
        llm_client=llm_client,
    )

    return OutcomeCoverageResult(
        synthesized_tasks=synthesized_dicts,
        intent_fidelity_score=compute_intent_fidelity_score(outcomes, coverage_after),
        coverage_before_fill=coverage_before,
        coverage_after_fill=coverage_after,
        gaps=gaps,
    )


# ---------------------------------------------------------------------------
# Graph-level adapters (issue #456 Stage 5)
#
# These functions take/return Task graphs (not just outcome data) and
# adapt the lower-level :func:`apply_outcome_coverage` into the
# :class:`AugmentationResult` shape that the augmenter chain consumes.
#
# Pre-#456-Stage-5 these lived as private methods on
# ``AdvancedPRDParser``.  Lifting them to public module functions
# decouples ``OutcomeCoverageAugmenter`` from the parser's private API
# (Kaia review #3, Simon ``4453bd2c``) — the augmenter now constructs
# with ``llm_client`` only and dispatches to these by name.
# ---------------------------------------------------------------------------


def _build_feature_gap_fill_task(
    *,
    idx: int,
    gap_dict: Dict[str, Any],
    sibling_tasks: List[Task],
) -> Task:
    """Convert a feature-based gap-fill output dict into a Task.

    Inherits defaults from sibling tasks so synthesized tasks fit
    naturally into the existing graph:

    - ``estimated_hours``: median of sibling estimates (4.0 fallback)
    - ``priority``: ``Priority.MEDIUM``
    - ``project_id`` / ``project_name``: copied from any sibling
    - ``status``: ``TaskStatus.TODO``
    - ``provides`` / ``requires``: from the gap-fill dict so downstream
      wiring integrates synthesized tasks via the existing contract
      mechanism
    - ``labels``: ``["gap_fill", "intent_fidelity"]`` so audits can
      identify synthesized tasks distinctly
    """
    now = datetime.now(timezone.utc)

    sibling_hours = sorted(
        t.estimated_hours for t in sibling_tasks if t.estimated_hours > 0
    )
    median = sibling_hours[len(sibling_hours) // 2] if sibling_hours else 4.0

    project_id = next((t.project_id for t in sibling_tasks if t.project_id), None)
    project_name = next((t.project_name for t in sibling_tasks if t.project_name), None)

    return Task(
        id=f"gap_fill_{uuid4().hex[:12]}",
        name=_normalize_gap_task_name(gap_dict["name"]),
        description=gap_dict["description"],
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=median,
        labels=["gap_fill", "intent_fidelity"],
        project_id=project_id,
        project_name=project_name,
        provides=gap_dict.get("provides"),
        requires=gap_dict.get("requires"),
    )


def _build_contract_gap_fill_task(
    *,
    idx: int,
    gap_dict: Dict[str, Any],
    sibling_tasks: List[Task],
) -> Task:
    """Convert a contract-first gap-fill dict into a full Task.

    Differs from :func:`_build_feature_gap_fill_task` by setting
    ``Task.responsibility`` from the gap-fill output's
    ``responsibility`` field — that's how contract-first tasks carry
    the "build this side of the contract" framing in the agent prompt
    at ``build_tiered_instructions`` time.

    The ``"contract"`` label is added ONLY when ``responsibility`` is
    present.  When the gap-fill helper falls back to feature-based
    output (because contract artifacts were filtered to empty),
    responsibility is None and the task is no different from a
    feature-based gap-fill — labeling it ``"contract"`` would lie
    about the synthesis context.

    ``source_context["contract_file"]`` is parsed from the
    canonical ``"implements <Iface> from <path>"`` responsibility
    string when the regex matches a path-separator-bearing token, so
    Layer 1.3 of :func:`build_tiered_instructions` can render the full
    "Read() the contract file at..." prompt.
    """
    now = datetime.now(timezone.utc)

    sibling_hours = sorted(
        t.estimated_hours for t in sibling_tasks if t.estimated_hours > 0
    )
    median = sibling_hours[len(sibling_hours) // 2] if sibling_hours else 4.0

    project_id = next((t.project_id for t in sibling_tasks if t.project_id), None)
    project_name = next((t.project_name for t in sibling_tasks if t.project_name), None)

    responsibility = gap_dict.get("responsibility")

    labels = ["gap_fill", "intent_fidelity"]
    if responsibility:
        labels.append("contract")

    # Best-effort parse of contract_file from the responsibility
    # string; the gap-fill prompt requests
    # ``"implements <Iface> from <relative_path>"``.  The path-separator
    # guard rejects method names ("from RenderingAgent.draw") and
    # dotted namespaces ("from src.module.thing") — a real relative
    # path will always contain '/' or '\\'.
    source_context: Dict[str, Any] = {}
    if isinstance(responsibility, str):
        match = re.search(r"\bfrom\s+(\S+\.\S+)\b", responsibility)
        if match:
            candidate = match.group(1)
            if "/" in candidate or "\\" in candidate:
                source_context["contract_file"] = candidate
        # Belt-and-braces: stash responsibility itself so providers
        # that don't round-trip Task.responsibility (Planka) still
        # surface the contract framing.
        source_context["responsibility"] = responsibility

    # Embed MARCUS_CONTRACT_FIRST marker so contract metadata
    # survives round-trip through providers that don't persist
    # Task.responsibility OR source_context.  Mirrors the native
    # contract-first task path; ``_parse_contract_metadata`` reads
    # this marker as priority-3 fallback.
    description = gap_dict["description"]
    if isinstance(responsibility, str) and responsibility:
        contract_file_for_marker = source_context.get("contract_file", "")
        marker_lines = [
            "<!-- MARCUS_CONTRACT_FIRST",
            f"responsibility: {responsibility}",
            f"contract_file: {contract_file_for_marker}",
            "-->",
        ]
        description = f"{description}\n\n" + "\n".join(marker_lines)

    return Task(
        id=f"gap_fill_{uuid4().hex[:12]}",
        name=_normalize_gap_task_name(gap_dict["name"]),
        description=description,
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=median,
        labels=labels,
        project_id=project_id,
        project_name=project_name,
        provides=gap_dict.get("provides"),
        requires=gap_dict.get("requires"),
        responsibility=responsibility,
        source_type="gap_fill_contract",
        source_context=source_context if source_context else None,
    )


def _coverage_to_telemetry(
    coverage: OutcomeCoverageResult,
) -> Dict[str, Any]:
    """Flatten an OutcomeCoverageResult into PLANNING_INTENT_FIDELITY shape.

    Keys are pinned to the event payload at
    ``src/integrations/nlp_tools.py:396-399``:
    ``intent_fidelity_score``, ``coverage_before_fill``,
    ``coverage_after_fill``, ``gap_filled_outcomes``.  Cato consumers
    read this slice via ``result.telemetry["outcome_coverage"]``.
    """
    return {
        "intent_fidelity_score": coverage.intent_fidelity_score,
        "coverage_before_fill": coverage.coverage_before_fill,
        "coverage_after_fill": coverage.coverage_after_fill,
        "gap_filled_outcomes": [g.id for g in coverage.gaps],
    }


async def apply_outcome_coverage_to_feature_graph(
    *,
    prd_analysis: "PRDAnalysis",
    tasks: List[Task],
    llm_client: Any,
) -> AugmentationResult:
    """Run the outcome-coverage check on a feature-based task graph.

    Issue #449 + #456.  Returns the canonical
    :class:`AugmentationResult` shape so the chain orchestrator can
    consume it directly without a parser-side wrapper.

    Returns an :class:`AugmentationResult` with empty telemetry when:

    - The flag is off (``MARCUS_OUTCOME_COVERAGE`` unset/false)
    - No outcomes were extracted (extraction failed earlier or no
      in-scope outcomes in the PRD)
    - The coverage pipeline raised (LLM error)

    Otherwise carries the augmented task list (originals + any
    synthesized gap-fill tasks), ``synthesized_ids`` of the new tasks,
    and ``telemetry`` with the canonical event-payload keys.

    Failures degrade gracefully — the input task list is returned
    unchanged so a project is never blocked by an outcome-coverage
    failure.
    """
    if not is_outcome_coverage_enabled():
        return AugmentationResult(augmented_tasks=list(tasks))
    if not prd_analysis.user_outcomes:
        return AugmentationResult(augmented_tasks=list(tasks))

    try:
        result = await apply_outcome_coverage(
            spec=prd_analysis.original_description or "",
            outcomes=prd_analysis.user_outcomes,
            tasks=tasks,
            llm_client=llm_client,
            contract_artifacts=None,
        )
    except Exception as exc:
        # Catch broadly: timeouts, API errors, parse errors all
        # downgrade to a logged warning.  Coverage failures must
        # never block project creation; the decomposer's pre-#449
        # behavior is the always-available fallback.
        logger.warning("Outcome coverage failed; task graph unchanged: %s", exc)
        return AugmentationResult(augmented_tasks=list(tasks))

    synthesized_tasks = [
        _build_feature_gap_fill_task(idx=idx, gap_dict=d, sibling_tasks=tasks)
        for idx, d in enumerate(result.synthesized_tasks)
    ]
    augmented = list(tasks) + synthesized_tasks

    logger.info(
        "Outcome coverage: score=%.2f, %d outcome(s), %d gap(s), "
        "%d synthesized task(s)",
        result.intent_fidelity_score,
        len(prd_analysis.user_outcomes),
        len(result.gaps),
        len(synthesized_tasks),
    )

    return AugmentationResult(
        augmented_tasks=augmented,
        synthesized_ids=[t.id for t in synthesized_tasks],
        telemetry=_coverage_to_telemetry(result),
    )


async def apply_outcome_coverage_to_contract_graph(
    *,
    prd_analysis: "PRDAnalysis",
    tasks: List[Task],
    contract_artifacts: Dict[str, Optional[Dict[str, Any]]],
    llm_client: Any,
) -> AugmentationResult:
    """Run outcome-coverage against a contract-first task graph.

    Issue #449 + #456.  Returns :class:`AugmentationResult` so the
    chain orchestrator can consume it directly.

    Distinct from :func:`apply_outcome_coverage_to_feature_graph`
    because contract-first tasks need ``responsibility`` set from the
    gap-fill ``responsibility`` field (which the contract-aware
    ``fill_gaps`` prompt asks the LLM for).

    Returns an empty-telemetry :class:`AugmentationResult` (input
    tasks unchanged) on flag off / no outcomes / LLM error — same
    graceful-degradation contract as the feature-based path.
    """
    if not is_outcome_coverage_enabled():
        return AugmentationResult(augmented_tasks=list(tasks))
    if not prd_analysis.user_outcomes:
        return AugmentationResult(augmented_tasks=list(tasks))

    # Filter to contract artifacts that actually have content;
    # apply_outcome_coverage's prompt-builder expects a dict with
    # populated ``artifacts`` lists, not the wrapper shape that
    # decompose_by_contract receives (which can have None payloads).
    usable_contracts: Dict[str, Any] = {
        domain: payload
        for domain, payload in contract_artifacts.items()
        if payload and payload.get("artifacts")
    }

    try:
        result = await apply_outcome_coverage(
            spec=prd_analysis.original_description or "",
            outcomes=prd_analysis.user_outcomes,
            tasks=tasks,
            llm_client=llm_client,
            contract_artifacts=usable_contracts or None,
        )
    except Exception as exc:
        logger.warning(
            "Outcome coverage (contract-first) failed; task graph unchanged: %s",
            exc,
        )
        return AugmentationResult(augmented_tasks=list(tasks))

    synthesized_tasks = [
        _build_contract_gap_fill_task(idx=idx, gap_dict=d, sibling_tasks=tasks)
        for idx, d in enumerate(result.synthesized_tasks)
    ]
    augmented = list(tasks) + synthesized_tasks

    logger.info(
        "Outcome coverage (contract-first): score=%.2f, %d outcome(s), "
        "%d gap(s), %d synthesized task(s)",
        result.intent_fidelity_score,
        len(prd_analysis.user_outcomes),
        len(result.gaps),
        len(synthesized_tasks),
    )

    return AugmentationResult(
        augmented_tasks=augmented,
        synthesized_ids=[t.id for t in synthesized_tasks],
        telemetry=_coverage_to_telemetry(result),
    )
