# Contract Validation (Invariant 5)

## Status

| Field | Value |
|-------|-------|
| Status | Implemented |
| Version | 1.0 |
| Date | 2026-04-11 |
| Issue | GH-320 (PR #335) |

## Problem

When contract-first decomposition generates interface contracts for multiple domains, those contracts may define the same named type with incompatible field types. For example:

- Weather service contract: `WidgetPosition { x: int, y: int, width: int }`
- Time widget contract: `WidgetPosition { x: string, y: string, width: string }`

If both contracts reach implementation agents, each agent writes code that compiles against its own contract but fails at integration. The type mismatch is invisible until runtime.

## Solution

`check_contract_cross_file_consistency` in `src/integrations/contract_validation.py` scans all in-memory contract artifacts for type contradictions before decomposition proceeds. This is called **Invariant 5** and is the only hard gate in the contract-first pipeline.

## How It Works

The function receives the contract artifacts dict (keyed by domain name) and:

1. **Filters to interface contracts** by filename pattern: keeps only artifacts where `"interface-contracts"` appears in the filename. This is a deliberate choice over filtering by `artifact_type` because the live generator emits `artifact_type="specification"` for interface contracts (a naming mismatch caught by Codex P1 review).

2. **Extracts type definitions** from each contract document. Types are identified by common patterns: `class`/`interface`/`type`/`struct` declarations, TypeScript interfaces, Python dataclasses, and Pydantic models.

3. **Cross-references types across domains**. When the same type name appears in multiple domains, the function compares field names and field types.

4. **Reports contradictions**. A contradiction exists when two domains define a type with the same field name but different field types. Field presence differences (domain A has a field that domain B lacks) are not contradictions -- they indicate one contract is a superset, which is safe.

## Gate Behavior

```
check_contract_cross_file_consistency(contract_artifacts)
  ├── No contradictions found → returns success, pipeline continues
  └── Contradictions found → returns failure with details
        └── _try_contract_first_decomposition falls back to feature-based
```

The gate is binary: any type contradiction triggers fallback. There is no "partial accept" mode because a single type mismatch can cascade through the entire integration boundary.

## Why Only Type Contradictions

Invariant 5 checks only for type contradictions, not for:
- Missing types (a domain references a type no other domain defines)
- Missing verbs (contracts omit user-facing actions from the PRD)
- Incomplete coverage (contracts do not cover all requirements)

These are quality issues, not correctness failures. A missing verb produces a product that lacks a feature; a type contradiction produces a product where two modules cannot communicate. The first is fixable by the integration agent; the second is not.

A verb-coverage gate was proposed and rejected during GH-320 review. A six-verb hard-coded checklist was too brittle (false positives on non-UI projects) and too destructive (discarding the 55/45 coordination win). See [Contract-First Decomposition](../../concepts/contract-first-decomposition.md) for the full rationale.

## What Invariant 5 Does NOT Catch

- **Semantic contradictions**: domain A says "temperature in Celsius" while domain B assumes Fahrenheit. These are natural-language disagreements that text parsing cannot detect reliably.
- **Behavioral contradictions**: domain A expects synchronous calls while domain B provides async-only APIs. These require deeper analysis than type comparison.
- **Schema shape differences**: domain A nests `position` inside `widget` while domain B uses a flat structure. Both may define `WidgetPosition` consistently but use it differently.

These gaps are acknowledged. Invariant 5 catches the most common and most dangerous class of cross-contract error. Future invariants may extend coverage.

## Implementation

### Module

`src/integrations/contract_validation.py`

### Public API

```python
def check_contract_cross_file_consistency(
    contract_artifacts: dict[str, list[dict[str, str]]]
) -> tuple[bool, list[str]]:
    """
    Check generated contracts for type contradictions across domains.

    Parameters
    ----------
    contract_artifacts : dict[str, list[dict[str, str]]]
        Contract artifacts keyed by domain name. Each value is a list
        of artifact dicts with "filename" and "content" keys.

    Returns
    -------
    tuple[bool, list[str]]
        (is_consistent, contradiction_descriptions).
        is_consistent is True when no type contradictions are found.
        contradiction_descriptions lists human-readable descriptions
        of each contradiction found.
    """
```

### Integration Point

Called inside `_try_contract_first_decomposition` in `src/integrations/nlp_tools.py`, between contract generation and `decompose_by_contract`:

```python
is_consistent, contradictions = check_contract_cross_file_consistency(
    contract_artifacts
)
if not is_consistent:
    logger.warning(
        "Contract cross-file inconsistency detected, "
        "falling back to feature-based: %s",
        contradictions,
    )
    return self._feature_based_fallback(...)
```

## Test Coverage

`tests/unit/integrations/test_contract_validation.py` -- 7 tests:

- Consistent contracts pass validation
- Type contradictions are detected across two domains
- Type contradictions are detected across three or more domains
- Field presence differences (superset) do not trigger contradiction
- Non-interface-contract artifacts are ignored
- Empty contract artifacts pass validation
- Single-domain contracts pass validation (no cross-reference possible)

## See Also

- [Contract-First Pipeline](../coordination/53-contract-first-pipeline.md) -- Full pipeline specification
- [Contract-First Decomposition](../../concepts/contract-first-decomposition.md) -- Conceptual overview and decisions
- [Quality Assurance](18-quality-assurance.md) -- Marcus's broader quality framework
