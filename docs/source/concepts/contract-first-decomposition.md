# Contract-First Task Decomposition

## Overview

Contract-first decomposition is Marcus's strategy for splitting tightly-coupled multi-agent projects into tasks that produce balanced agent contributions. It replaces the default feature-based decomposition when the user selects `--decomposer contract_first` via the `/marcus` skill.

The core idea: generate interface contracts between domains **before** splitting the project into implementation tasks, so each agent owns a distinct contract boundary rather than a feature silo.

## The Single-Author Problem

Marcus's original decomposition strategy (feature-based) splits a project by user-visible features. Each feature becomes one task. This works well for loosely-coupled projects where features are independent (e.g., a snake game where rendering, input handling, and game logic have minimal overlap).

For tightly-coupled projects, feature-based decomposition produces a **Single-Author Product**: one agent absorbs most of the work while others contribute negligibly.

**Why it happens:** In tightly-coupled systems, one feature depends heavily on another. The first agent to run builds shared infrastructure (data models, API layer, configuration) because its feature needs it. The second agent arrives, discovers the infrastructure already exists, and has little left to build. The contribution split skews to 90/10 or worse.

**Evidence:** Multiple experiments before GH-320 showed Single-Author Products on tightly-coupled prompts. The dashboard experiment (v53 predecessor) consistently produced 85-95% contribution from a single agent.

## How Contract-First Solves It

Contract-first decomposition introduces an intermediate step: **domain discovery and contract generation**. Instead of mapping features directly to tasks, Marcus:

1. Identifies the functional domains in the project (e.g., "weather service", "time service", "dashboard layout")
2. Generates interface contracts between those domains (data types, API shapes, shared schemas)
3. Splits implementation tasks along domain boundaries, with contracts as the glue

Each agent receives:
- A domain to implement
- The interface contracts its domain must honor
- Dependencies on design ghost tasks that carry the contract artifacts

Because the contracts define boundaries explicitly, agents cannot accidentally absorb each other's work. Agent A implements the weather service contract; Agent B implements the time widget contract. Even though both need shared types, the contracts specify those types once and both agents code to the same specification.

## Experimental Validation

### Experiment 4 v2 (dashboard-v53)

- **Project**: "Build a dashboard with weather and time widgets"
- **Strategy**: `--decomposer contract_first`, 2 agents
- **Result**: Multi-Agency Effective with Balanced contribution (55.5% / 44.5%)
- **Grade**: B- (3.65/5), 168 tests passing, 92% Python coverage

This was the second consecutive anti-Single-Author result (the first was the snake game at 30/70 with feature-based decomposition on a loosely-coupled project). The dashboard is a tightly-coupled project that previously produced Single-Author Products under feature-based decomposition.

### What Worked

Contract-first successfully distributed implementation work across agents. Both agents built meaningful, non-overlapping components. The 55/45 split is close to ideal for a two-agent project.

### What Did Not Work

The product scored B- because both agents built API plumbing rather than a visible dashboard. The contracts had an API-shape structural prior: they specified data models and service interfaces but not user-facing behavior like "display" and "render."

**Root cause (diagnosed by Kaia):** "Locally rigorous, globally amnesiac." Each translation step in the pipeline (requirements to domains to contracts to tasks) is correct in isolation, but the contract generation prompt has a structural bias toward API-shape contracts. User-facing verbs like "display" and "render" are silently dropped because they do not map to interface types.

The old feature-based system preserved user intent for free because features and tasks were the same object. Contract-first introduced abstraction layers without a discipline for carrying PRD information across them.

### Schema Divergence

The experiment also exposed WidgetPosition schema divergence: the Python contract defined one shape while the TypeScript contract defined another. This type of cross-domain inconsistency is now caught by Invariant 5 (see [Contract Validation](../systems/quality/contract-validation.md)).

## Architectural Decisions

### 1. Cato Observability Uses Synthetic Design Ghosts

**Decision**: When contract-first generates contracts, Marcus synthesizes one DONE design ghost task per usable contract domain. These ghosts carry the contract artifacts and appear in Cato's DAG view.

**Alternatives considered**:
- **Option B (new emitter path)**: Create a dedicated contract emitter in Cato. Rejected because it required Cato changes and a new data model.
- **Option C (Cato classifier fix)**: Teach Cato to infer contract provenance from task metadata. Rejected because it was fragile and pushed domain logic into the visualization layer.

**Rationale**: Option A (synthetic ghosts) reuses four existing code paths: `_run_design_phase`, `log_artifact`, the `auto_completed` label filter, and the dependency graph. Zero Cato changes needed. Implementation tasks depend on their matching design ghost via `source_context["contract_file"]`.

### 2. Invariant 5 Is the Only Hard Gate

**Decision**: The only condition that triggers fallback from contract-first to feature-based decomposition is a type contradiction across contract domains (Invariant 5). All other quality signals are additive.

**Rationale**: Type contradictions are correctness failures. If domain A says `WidgetPosition.x` is an `int` and domain B says it is a `string`, no amount of downstream work can reconcile them. Fallback is the only safe response. Other issues (missing verbs, incomplete coverage) degrade quality but do not produce incorrect code. Those are better addressed by enriching prompts than by throwing away the contract-first coordination win.

### 3. Verb-Coverage Gate Was Rejected

**Decision**: A proposed gate that would reject contracts missing user-facing verbs (display, render, etc.) from the PRD was removed after review.

**Rationale**: A six-verb hard-coded checklist was too brittle (false positives on projects that genuinely have no UI verbs) and too destructive (throwing away the 55/45 coordination win to fix a prompt quality issue). The requirement coverage problem will be handled additively in task #64 by threading functional requirements through the contract generation prompt and enriching the integration task with the full requirements list.

### 4. No PRD Information May Be Dropped Across Decomposition Boundaries

**Decision**: This is the general principle that Invariant 5 and the future #64 intent preservation are instances of. Any future decomposer strategy must prove it does not drop PRD information between pipeline stages.

**Rationale**: The "globally amnesiac" failure mode is structural, not accidental. Each abstraction layer is a lossy compression of the one above it. Without explicit discipline, information loss is the default. The general rule forces every new pipeline stage to account for what it carries forward and what it drops.

### 5. Contract-First Experiments Are Atomic

**Decision**: `/marcus` runs Phase A through integration with no pause point. There is no interactive "review contracts before decomposing" step.

**Rationale**: The smoke test harness is the pre-check vehicle. Pausing for human review would break the autonomous experiment model and add latency without clear benefit (the human cannot evaluate contract quality faster than Invariant 5 can check type consistency).

## The Pipeline

The full contract-first pipeline runs inside `_try_contract_first_decomposition` in `src/integrations/nlp_tools.py`:

```
PRD Analysis
  |
  v
Domain Discovery (identify functional domains from requirements)
  |
  v
Contract Generation (_generate_contracts_by_domain)
  |  - One LLM call per domain
  |  - Generates interface contracts, data models, API shapes
  |  - FORBIDDEN PATTERNS prevent cross-domain scope drift
  |
  v
Invariant 5 Gate (check_contract_cross_file_consistency)
  |  - Scans all contracts for type contradictions
  |  - FAIL: fallback to feature-based decomposition
  |  - PASS: continue
  |
  v
decompose_by_contract (split into implementation tasks)
  |
  v
Ghost Synthesis (one DONE design ghost per domain)
  |  - labels=["design", "auto_completed"]
  |  - assigned_to="Marcus"
  |  - Implementation tasks depend on their domain's ghost
  |
  v
Phase B Handoff (pre_generated_content parameter)
  |  - _run_design_phase skips Phase A when pre_generated_content is supplied
  |  - Phase B registers pre-generated contracts as artifacts
  |
  v
Integration Task (verifies cross-domain contract compliance)
```

For technical details of each pipeline stage, see [Contract-First Pipeline](../systems/coordination/53-contract-first-pipeline.md).

For the Invariant 5 consistency check, see [Contract Validation](../systems/quality/contract-validation.md).

## What Remains: Task #64

The "globally amnesiac" problem requires upstream intent preservation. Two parts:

1. **Thread functional requirements into the contract generation prompt** so the LLM sees "this domain must support: [requirements list]." This is preventive -- it stops the information loss at the source.

2. **Enrich the integration verification task with ALL functional requirements** as `acceptance_criteria` so the integration agent verifies user intent was realized, not just contract compliance. This is detective/additive -- it catches anything that slipped through.

Together, these close the loop between what the user asked for and what the agents build.

## Related Documentation

- [Hierarchical Task Decomposition](hierarchical-task-decomposition.md) -- The original decomposition concept
- [Design Autocomplete](../systems/coordination/52-design-autocomplete.md) -- Phase A/B mechanism that contract-first builds on
- [Contract-First Pipeline](../systems/coordination/53-contract-first-pipeline.md) -- Technical specification of the pipeline
- [Contract Validation](../systems/quality/contract-validation.md) -- Invariant 5 specification
- [Philosophy](philosophy.md) -- Marcus's Stoic principles, particularly "Safety Through Guardrails"
