"""
Contract-first decomposition validation gate.

Two checks run before contract-first decomposition is allowed to ship
tasks to the kanban board:

1. **Cross-contract type consistency** — when two generated contract
   artifacts define the same field name with different types, the
   contracts disagree and agents would build incompatible code. This
   was the WidgetPosition divergence bug from Experiment 4 v2 (Python
   ``positionX (number)`` vs TypeScript ``positionX (string)``).

   The check is the in-memory sibling of
   ``check_contract_cross_file_consistency`` in the smoke test
   harness at ``dev-tools/examples/gh320_experiment_4_smoke.py``.
   The smoke test reads ``.md`` files from disk after Phase A
   completes; this version operates on the in-memory
   ``contract_artifacts`` dict produced by
   ``_generate_contracts_by_domain`` so it can run in the live
   decomposition path before agents are spawned.

2. **Functional requirement coverage** — every PRD functional
   requirement that uses a user-facing verb (display, render, show,
   visualize, present, view) must be covered by at least one task
   whose name or description contains that verb. This catches the
   "agents built API plumbing but no UI" regression where contract
   decomposition lost the user's visible intent because the contract
   generation prompt has a structural prior toward API-shape contracts.

Both checks return ``{"pass": bool, ...}`` and are caller-owned: the
caller decides whether a failure is hard (fall back to feature-based)
or soft (log + continue). For the live gate in
``_try_contract_first_decomposition``, both failures fall back.

References
----------
- GH-320 : Contract-first task decomposition
- Experiment 4 v2 (2026-04-11) : surfaced both failure modes
- Kaia review (2026-04-11) : structural diagnosis ("locally
  rigorous, globally amnesiac") and the verb-coverage rule
"""

import re
from typing import Any, Dict, List, Mapping, Optional

from src.core.models import Task

# --------------------------------------------------------------------------
# Cross-contract type consistency
# --------------------------------------------------------------------------


# Strict type-annotation pattern. Matches ``- field (type)`` or
# ``* field (type)`` where ``type`` starts with a primitive type
# keyword. This eliminates false positives where prose in
# parentheses (e.g. ``(for rendering)``) would otherwise be
# captured as a type annotation.
#
# Mirrors the pattern in dev-tools/examples/gh320_experiment_4_smoke.py
# (per PR #329 review). The two implementations should stay in sync;
# if you tighten one, tighten the other.
_TYPE_ANNOTATION_PATTERN = re.compile(
    r"[-*]\s+`?(\w[\w.]*)`?\s*\(\s*("
    r"(?:string|number|boolean|integer|float|object|array|"
    r"date|datetime|json|null|void|bigint)"
    r"(?:\s*\|\s*(?:string|number|boolean|null))*"
    r"(?:[^)]*)"
    r")\s*\)",
    re.IGNORECASE,
)

# Field names whose collision is benign (universal identifiers,
# enum-like literals). They appear in many domains and aliasing
# them as the same name doesn't constitute a contradiction.
_BENIGN_CANONICAL_FIELDS = frozenset(
    {
        "id",
        "string",
        "number",
        "boolean",
        "yes",
        "no",
        "true",
        "false",
        "null",
        "none",
    }
)


def _normalize_type(type_str: str) -> str:
    """
    Normalize a type string for cross-file comparison.

    Collapses whitespace, strips markdown formatting, strips common
    qualifiers (required, optional, nullable), and maps common
    synonyms to canonical types. Deliberately lenient: catches
    ``ISO 8601 string`` vs ``Date object`` (a real contradiction)
    while ignoring ``string`` vs ``string, required`` (stylistic
    variation on the same type).

    Parameters
    ----------
    type_str : str
        Raw type annotation as captured from the markdown contract.

    Returns
    -------
    str
        Normalized form suitable for set comparison.
    """
    t = type_str.lower().strip().strip("`")
    t = re.sub(r"\s+", " ", t)

    # Normalize union syntax: "X or Y" -> "X | Y"
    t = re.sub(r"\bor\b", "|", t)
    # Collapse spaces around union pipes
    t = re.sub(r"\s*\|\s*", "|", t)

    qualifiers = [
        ", required",
        ", optional",
        ", nullable",
        " required",
        " optional",
        " nullable",
    ]
    for qual in qualifiers:
        t = t.replace(qual, "")

    return t.strip()


def check_contract_cross_file_consistency(
    contract_artifacts: Mapping[str, Optional[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Check that no field has contradictory types across contract files.

    Walks the ``contract_artifacts`` dict produced by
    ``_generate_contracts_by_domain``, extracts ``- field (type)``
    annotations from every ``interface_contracts`` artifact, and
    flags any field name appearing in ≥2 contracts with ≠ types.

    Only ``interface_contracts`` artifacts are scanned. The other
    artifact types (architecture, api_contracts, data_models) are
    prose with no enforceable type annotations and would generate
    spurious contradictions if cross-checked.

    Parameters
    ----------
    contract_artifacts : Dict[str, Optional[Dict[str, Any]]]
        Mapping of ``domain_name -> {"artifacts": [...], "decisions":
        [...]}``. Domains where contract generation produced no
        output map to ``None`` and are skipped.

    Returns
    -------
    Dict[str, Any]
        Dict with keys:

        - ``pass`` (bool): True if no contradictions found
        - ``contradictions`` (list): one entry per contradictory field
          with ``field`` (canonical name) and ``types_by_file`` (map
          of filename -> raw type string)
        - ``total_fields`` (int): total field annotations scanned
        - ``unique_fields`` (int): distinct canonical field names
          observed across all files
        - ``files_scanned`` (int): number of interface_contracts
          artifacts processed

    Notes
    -----
    Heuristic, not perfect. Will miss contradictions described in
    prose form and may flag benign duplicates where two files use
    slightly different type vocabulary for the same concept. The
    goal is to catch obvious scope bugs before agents burn credits,
    not to be an exhaustive type checker.
    """
    # field_name -> {filename: type_str}
    field_types: Dict[str, Dict[str, str]] = {}
    total_fields = 0
    files_scanned = 0

    for _domain_name, payload in contract_artifacts.items():
        if payload is None:
            continue
        artifacts = payload.get("artifacts", [])
        for artifact in artifacts:
            if artifact.get("artifact_type") != "interface_contracts":
                continue
            files_scanned += 1
            filename = artifact.get("filename", "")
            content = artifact.get("content", "")

            for match in _TYPE_ANNOTATION_PATTERN.finditer(content):
                field_name = match.group(1).strip()
                type_str = match.group(2).strip()
                total_fields += 1

                # Normalize compound field names: ``weather.temperature``
                # collides with ``temperature`` when they refer to the
                # same concept. Use the last dotted segment as the
                # canonical key.
                canonical = field_name.split(".")[-1].lower()

                # Skip benign aliases and obvious type/interface refs.
                if (
                    len(canonical) < 3
                    or canonical in _BENIGN_CANONICAL_FIELDS
                    # CamelCase identifiers are usually class/interface
                    # references, not fields.
                    or (
                        field_name[0].isupper()
                        and any(c.isupper() for c in field_name[1:])
                    )
                ):
                    continue

                field_types.setdefault(canonical, {})[filename] = type_str

    contradictions: List[Dict[str, Any]] = []
    for canonical, file_type_map in field_types.items():
        if len(file_type_map) < 2:
            continue
        type_set = {_normalize_type(t) for t in file_type_map.values()}
        if len(type_set) > 1:
            contradictions.append(
                {
                    "field": canonical,
                    "types_by_file": dict(file_type_map),
                }
            )

    return {
        "pass": len(contradictions) == 0,
        "contradictions": contradictions,
        "total_fields": total_fields,
        "unique_fields": len(field_types),
        "files_scanned": files_scanned,
    }


# --------------------------------------------------------------------------
# Functional requirement coverage (verb check)
# --------------------------------------------------------------------------


# User-facing verbs from Kaia's review of Experiment 4 v2. These
# encode the user's visible intent — when a PRD requirement says
# "display X" and no task says "display", the implementation
# skipped the user-facing step. Verbs unrelated to user-visible
# action (build, implement, create, refactor) are NOT in this list
# because they're too generic to carry intent.
#
# Keep this list small and explicit. Adding verbs is cheap; removing
# them later may break regression tests, so favor precision over
# recall.
USER_FACING_VERBS: frozenset[str] = frozenset(
    {
        "display",
        "render",
        "show",
        "visualize",
        "present",
        "view",
    }
)


def _extract_user_facing_verb(requirement_name: str) -> Optional[str]:
    """
    Extract the user-facing verb from a functional requirement name.

    Looks for any USER_FACING_VERBS as a whole word in the
    requirement name (case-insensitive). Returns the first match,
    or ``None`` if no user-facing verb is present.

    Parameters
    ----------
    requirement_name : str
        The ``name`` field of a PRD functional requirement, e.g.
        "Display current weather temperature".

    Returns
    -------
    Optional[str]
        The matched verb in lowercase, or None.
    """
    name_lower = requirement_name.lower()
    for verb in USER_FACING_VERBS:
        if re.search(rf"\b{verb}\b", name_lower):
            return verb
    return None


def _task_covers_verb(task: Task, verb: str) -> bool:
    """
    Check whether a task covers a user-facing verb.

    Word-boundary substring match against the task name and
    description (case-insensitive). Word boundary is important so
    ``display`` matches ``displayed`` (a valid covering inflection)
    but not arbitrary identifier substrings.

    Parameters
    ----------
    task : Task
        Task object from the decomposed output.
    verb : str
        Lowercase user-facing verb to look for.

    Returns
    -------
    bool
        True if the task name or description contains the verb as
        a word (or as a prefix of a word like "displayed").
    """
    name = (task.name or "").lower()
    description = (task.description or "").lower()
    # ``\b`` matches at word boundaries on either side; the trailing
    # ``\w*`` permits inflections like "displayed" / "rendering" /
    # "showing" without matching unrelated identifiers like
    # "displaytron" via prefix.
    pattern = rf"\b{verb}\w*\b"
    return bool(re.search(pattern, name) or re.search(pattern, description))


def check_requirement_coverage(
    functional_requirements: List[Dict[str, Any]],
    tasks: List[Task],
) -> Dict[str, Any]:
    """
    Check that every user-facing requirement is covered by a task.

    Walks ``functional_requirements`` looking for requirements whose
    name contains a user-facing verb (display/render/show/etc.).
    For each such requirement, checks that at least one task in
    ``tasks`` has the same verb in its name or description.

    Requirements without user-facing verbs are not checked. The
    rationale is that user-facing verbs encode the user's visible
    intent ("I want to SEE this"), and contract-first decomposition
    has a structural tendency to drop that dimension when generating
    interface contracts. Non-user-facing requirements (auth,
    validation, caching) survive contract decomposition fine.

    Parameters
    ----------
    functional_requirements : List[Dict[str, Any]]
        From ``PRDAnalysis.functional_requirements``. Each requirement
        dict must have a ``name`` field; ``id`` and others are
        carried through to the missing-requirements report for
        debugging.
    tasks : List[Task]
        Decomposed task output to check coverage against.

    Returns
    -------
    Dict[str, Any]
        Dict with keys:

        - ``pass`` (bool): True if all user-facing requirements are
          covered (or no user-facing requirements exist)
        - ``missing_requirements`` (list): one entry per uncovered
          requirement with ``id``, ``name``, and ``verb`` (the
          unmatched user-facing verb)
        - ``checked_requirements`` (int): how many requirements
          contained a user-facing verb and were actually checked

    Examples
    --------
    Coverage gap (Experiment 4 v2 regression):

    >>> requirements = [{"name": "Display weather", "id": "f1"}]
    >>> tasks = [Task(name="Implement WeatherWidget", ...)]
    >>> result = check_requirement_coverage(requirements, tasks)
    >>> result["pass"]
    False
    >>> result["missing_requirements"][0]["verb"]
    'display'

    Verb covered by inflection:

    >>> requirements = [{"name": "Render chart", "id": "f1"}]
    >>> tasks = [Task(name="Build chart rendering pipeline", ...)]
    >>> check_requirement_coverage(requirements, tasks)["pass"]
    True
    """
    missing: List[Dict[str, Any]] = []
    checked = 0

    for requirement in functional_requirements:
        name = requirement.get("name", "")
        if not name:
            continue
        verb = _extract_user_facing_verb(name)
        if verb is None:
            # Requirement uses a non-user-facing verb (or none) —
            # not load-bearing for this check.
            continue
        checked += 1
        if not any(_task_covers_verb(t, verb) for t in tasks):
            missing.append(
                {
                    "id": requirement.get("id", ""),
                    "name": name,
                    "verb": verb,
                }
            )

    return {
        "pass": len(missing) == 0,
        "missing_requirements": missing,
        "checked_requirements": checked,
    }
