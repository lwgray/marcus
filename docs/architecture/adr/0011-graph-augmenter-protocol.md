# ADR 0011: GraphAugmenter Protocol for Pre-Inference Task Synthesis

**Status:** Accepted

**Date:** 2026-04-30

**Deciders:** Marcus Core Team

**Issue:** [#456](https://github.com/lwgray/marcus/issues/456)

---

## Context

Pre-#456, Marcus had two parallel pipelines that synthesized tasks
into the graph after the decomposer produced its initial task list:

1. **Outcome coverage** (`outcome_coverage` — issue #449) ran *inside*
   the decomposer between `_create_detailed_tasks` and
   `_infer_smart_dependencies`. Synthesized gap-fill tasks correctly
   participated in dependency inference and foundation wiring.

2. **Spec coverage** (`spec_coverage`) ran *after* the decomposer +
   safety checks at `nlp_tools.py:1336`. Synthesized gap tasks were
   appended to the task list with `dependencies=[]` — orphans that
   bypassed both `_infer_smart_dependencies` and foundation wiring.
   This was the v37 orphan-failure-mode.

Both pipelines did the same fundamental thing: "look at the graph,
detect a gap, synthesize a task to fill it." But they integrated at
different points in the pipeline with different failure modes.

The forcing function: a third would-be augmenter (NFR coverage,
security checks, lint coverage…) faced an unclear question — *where*
in the pipeline does it slot in? Each new addition risked being
either (a) another orphan, like spec_coverage, or (b) a parallel
implementation of the same lift-and-fill pattern.

### Requirements

- Single integration point for pre-inference task synthesis so all
  augmenters land at the same correct location.
- Synthesized tasks always participate in dependency inference and
  foundation wiring as first-class graph members.
- Defense-in-depth against augmenter exceptions — one buggy augmenter
  must never crash the decomposer.
- Telemetry namespace per augmenter so future additions don't
  collide on event-payload keys.
- Compatible with Marcus's existing duck-typing convention (no
  inheritance-from-base requirement).
- Observable: failures must be loud and named in logs so operators
  can diagnose which augmenter failed without grepping for stack
  traces.

---

## Decision

Define a structural Protocol — `GraphAugmenter` — and a chain
orchestrator — `run_augmenter_chain` — both in
`src/marcus_mcp/coordinator/graph_augmentation.py`. Both decomposers
(`parse_prd_to_tasks` and `decompose_by_contract`) route their
post-`_create_detailed_tasks` task list through the chain before
calling `_infer_smart_dependencies`.

### The Protocol

```python
@runtime_checkable
class GraphAugmenter(Protocol):
    name: str

    async def augment(
        self,
        *,
        prd_analysis: "PRDAnalysis",
        tasks: List[Task],
        contract_artifacts: Optional[Dict[str, Any]] = None,
    ) -> AugmentationResult: ...
```

**Why a Protocol (structural) and not an ABC (nominal):** Marcus's
existing pipeline conventions favor duck typing; structural typing
keeps the interface non-invasive to existing classes.
`@runtime_checkable` lets the chain orchestrator validate registered
augmenters with `isinstance` when registration happens.

**Why `name: str`:** the chain namespaces telemetry by `augmenter.name`
so each augmenter's payload sits in its own slice of the result dict.
Cato consumers read `result.telemetry["outcome_coverage"]`,
`result.telemetry["spec_coverage"]`, etc. without key collisions.

**Why keyword-only `augment` parameters:** prevents positional-arg
coupling as the parameter list evolves. Future augmenters can
ignore parameters they don't need.

### The Chain Orchestrator

```python
async def run_augmenter_chain(
    augmenters: Sequence[GraphAugmenter],
    *,
    prd_analysis: "PRDAnalysis",
    tasks: List[Task],
    contract_artifacts: Optional[Dict[str, Any]] = None,
) -> AugmentationResult:
```

**Behavior contract:**

1. Validates name uniqueness at chain entry — duplicate names raise
   `ValueError` before any augmenter runs (fail-fast, no half-applied
   side effects).
2. Augmenters run sequentially; each sees the post-previous-augmenter
   task list, so synthesized tasks flow forward through the chain.
3. Every `augment` call is wrapped in `try/except` — defense-in-depth.
   A buggy or future augmenter that forgot to catch its own
   exceptions cannot crash the decomposer. Failures log a warning
   naming the augmenter and continue with prior tasks (no-op for
   that step).
4. Telemetry is namespaced by `augmenter.name`. Empty-telemetry
   augmenters are omitted from the namespace so consumers can
   distinguish "augmenter ran, no data" from "augmenter didn't run."

### Single Registration Site

Both decomposers call:

```python
augmenter_result = await run_augmenter_chain(
    self._build_augmenter_chain(),
    prd_analysis=prd_analysis,
    tasks=tasks,
    contract_artifacts=...,  # None for feature-based
)
```

Where `_build_augmenter_chain()` is a single helper on
`AdvancedPRDParser` returning the canonical chain — the only place
that knows the chain order and registration set.

---

## Consequences

### Positive

- **Single integration point.** Future augmenters (NFR coverage,
  security checks) join `_build_augmenter_chain()` and inherit
  correct positioning automatically.
- **No more orphans.** Spec-coverage gap tasks now flow through
  `_infer_smart_dependencies`, foundation wiring, and safety checks
  like any other implementation task. The v37 orphan-failure-mode
  is closed.
- **Observable failures.** Augmenter exceptions log with the
  augmenter's name; no silent regressions.
- **Telemetry future-proof.** Each augmenter owns its own keyspace.
  Cato consumers don't break when a new augmenter joins.
- **Order is load-bearing and tested.** `outcome_coverage` runs before
  `spec_coverage` so the spec-feature scan sees outcome-fill tasks.
  Pinned by `test_second_augmenter_sees_first_augmenter_tasks`.

### Negative

- **Augmenter chain runs synchronously per augmenter.** Two
  independent augmenters that don't read each other's output could in
  principle run concurrently with `asyncio.gather`, but the chain is
  sequential to preserve the "downstream sees upstream output"
  property. Future optimization opportunity: dependency-aware chain
  scheduler.
- **No retry/circuit-breaker per augmenter.** The chain catches
  exceptions but doesn't retry. Each augmenter is responsible for
  its own retry logic if needed (currently none do — both call
  underlying functions that already handle LLM transients).

### Trade-offs Considered

**Inheritance vs Protocol:** chose Protocol. ABC requires existing
classes to inherit from a base, which would have required modifying
the parser. Protocol is non-invasive — any class with the right
shape satisfies it.

**Eager vs lazy chain construction:** chose eager (chain built once
per decomposer call in `_build_augmenter_chain`). Augmenters are
stateless apart from `llm_client` references, so per-call construction
costs nothing. If future augmenters acquire state (caching, retry
budgets), this needs revisiting.

**Telemetry namespace shape:** chose `{augmenter.name: dict}` over
flat merge. Namespace makes per-augmenter event payloads
addressable from Cato (`result.telemetry["outcome_coverage"]`)
without forcing a unified key schema across all augmenters.

---

## Adding a New Augmenter

Pattern for future augmenters (NFR coverage, security checks, etc.):

1. Create `src/marcus_mcp/coordinator/<name>_augmenter.py` with a
   class that satisfies the `GraphAugmenter` Protocol:

   ```python
   class NfrCoverageAugmenter:
       name: str = "nfr_coverage"

       async def augment(
           self,
           *,
           prd_analysis: "PRDAnalysis",
           tasks: List[Task],
           contract_artifacts: Optional[Dict[str, Any]] = None,
       ) -> AugmentationResult:
           # ... detect gaps, synthesize tasks, return result
   ```

2. Register it in
   `AdvancedPRDParser._build_augmenter_chain()`:

   ```python
   return [
       OutcomeCoverageAugmenter(llm_client=self.llm_client),
       SpecCoverageAugmenter(),
       NfrCoverageAugmenter(),
   ]
   ```

3. Decide chain position by what the augmenter reads. If the new
   augmenter scores against the post-outcome-coverage graph, place
   after `OutcomeCoverageAugmenter`. If it operates on raw input
   independent of upstream synthesis, position is flexible.

4. Add unit tests covering Protocol satisfaction, the augmenter's
   own behavior, and (if relevant) interaction with upstream
   augmenters.

5. Pick a unique `name` string. The chain enforces uniqueness at
   registration time, but verify against existing augmenter names
   to avoid the `ValueError` at boot.

6. **Stay stateless.** Augmenters are constructed per-call by
   `AdvancedPRDParser._build_augmenter_chain()`. Adding instance
   state (caches, retry budgets, rate-limit windows) silently
   discards it across calls — see the lifetime-expectation note in
   :class:`OutcomeCoverageAugmenter` for the tripwire pattern. If an
   augmenter genuinely needs persistent state, audit the
   construction site and move it to per-decomposer-instance or
   per-process scope before adding the attribute.

---

## References

- Issue #456 — GraphAugmenter unification
- Issue #449 — Outcome coverage (intent fidelity)
- Kaia review #2 (Simon `c26c7ec5`) — defense-in-depth try/except
- Kaia review #3 (Simon `4453bd2c`) — lift helpers to public module
  functions
- Kaia review #4 (Simon `f36c49c4`) — augmenter-name uniqueness check
- Kaia review #5 (Simon `a37d415d`) — Stage 5 cleanup gates
- ADR 0001 — Layered Architecture with DDD (the coordinator layer)
- `src/marcus_mcp/coordinator/graph_augmentation.py` — Protocol +
  chain orchestrator
- `src/marcus_mcp/coordinator/outcome_coverage_augmenter.py` —
  reference implementation (dispatcher pattern)
- `src/marcus_mcp/coordinator/spec_coverage_augmenter.py` —
  reference implementation (single-helper delegation pattern)
