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
    r"(?:[^)]{0,200})"
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
            # Match interface-contracts artifacts by filename, NOT by
            # artifact_type. The live generator emits these with
            # artifact_type="specification" (shared with data_models),
            # not "interface_contracts". The smoke test harness at
            # dev-tools/examples/gh320_experiment_4_smoke.py uses the
            # same filename-glob approach (``*-interface-contracts.md``)
            # for the same reason. Codex P1 on PR #335 caught the
            # original artifact_type filter that would have silently
            # scanned 0 files.
            filename = artifact.get("filename", "")
            if "interface-contracts" not in filename:
                continue
            files_scanned += 1
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
