# GH-320 Experiment 4 — LLM-generated contract snake game (validation gate)

| Field | Value |
|-------|-------|
| Status | Not yet run |
| Blocked by | PR #327 must merge (contract-aware decomposer implementation) |
| Motivation | Validate that contract-first decomposition works end-to-end through Marcus's actual pipeline with an LLM-generated contract, not a hand-crafted one |
| Success criterion | Reproduce Experiment 1's ~30/70 contribution split and clean merge on snake game **without** a human writing the contract |
| Related | GH-320, PR #327, Experiment 1 (2026-04-10, hand-crafted contract) |

## Why this experiment exists

This is **the real productionization validation gate for PR 2b**.

Experiment 1 proved the mechanism: if you give two agents a good contract and task descriptions that tie each agent to one side of the contract, they produce integrated code. But the contract was **hand-crafted by a human**. Production Marcus will use **LLM-generated contracts** via `_generate_contracts_by_domain`.

The weak link in contract-first decomposition is the contract itself. An LLM-generated contract can be:
- Ambiguous (interface methods without semantics)
- Incomplete (missing a method one agent needs)
- Misaligned (types that don't actually compose)

If the LLM-generated contract is bad, downstream decomposition produces tasks with vague responsibilities, agents produce code that doesn't integrate, and we're back to the Single-Author Product verdict. **Until Experiment 4 passes, PR #327 is unproven in production.**

GH-320 issue body, verbatim: *"LLM-generated contracts are the weak link. Everything above assumes contract generation produces output good enough to decompose from. The experiment-1 contract was hand-crafted by a human. Production Marcus will use LLM-generated contracts. Failure mode: the contract is ambiguous, has type mismatches, or omits a method one agent needs."*

## Prerequisites

1. **PR #327 merged to develop**. Contract-aware decomposer, Task.responsibility field, feature flag, and agent prompt surfacing must all be live.
2. **PR #326 merged to develop**. Phase A→B handoff must work so design artifacts flow to `state.task_artifacts` and downstream agents can discover them via `get_task_context`. (Merged 2026-04-11.)
3. **Marcus configured with Anthropic API key**. Contract generation needs real LLM calls.
4. **Clean baseline directory** for the experiment (no prior project state).

## Setup

```bash
# Ensure develop is up to date
cd /Users/lwgray/dev/marcus
git checkout develop
git pull origin develop

# Verify both prereqs landed
git log --oneline | head -5
# Expect: feat(#320): contract-aware decomposer + Task.responsibility (PR 2)
#         fix(#320): reconnect Phase A→B design artifact registration (#326)

# Start Marcus with contract-first flag on
export MARCUS_DECOMPOSER=contract_first
# Start Marcus per your normal startup procedure
```

## Execution

Create a new snake game project via Marcus with contract-first enabled:

```python
# Via Claude Code or direct MCP call:
create_project(
    description=(
        "Build a classic snake game in TypeScript with React. "
        "The snake moves on a grid, eats food, grows, and ends "
        "the game on wall or self collision. Arrow keys control "
        "direction. Display current score and a restart button "
        "on game over."
    ),
    project_name="snake-game-exp4",
    options={
        "decomposer": "contract_first",  # Explicit override, belt-and-suspenders
        "agent_count": 2,
        "project_root": "/Users/lwgray/dev/snake-game-exp4",
        "complexity": "standard",
    }
)
```

Then spawn 2 agents as usual. Observe:

1. **Contract generation**: Marcus's design phase should produce contract artifacts under `snake-game-exp4/docs/` — at minimum an API contract describing `GameState`, `GameEngine`, and UI consumer interface. **Capture a copy of the generated contract file.** This is the experiment's input for analysis.
2. **Task list**: the kanban board should have tasks with `responsibility` field set, naming specific interfaces from the generated contract. Tasks with `responsibility == None` are a failure — the contract-first decomposer didn't fire or fell back to feature-based.
3. **Agent work**: two agents pick up contract-first tasks. Each agent's instruction should include the `CONTRACT RESPONSIBILITY` layer (visible in agent logs or `get_task_context` output). Each agent reads the contract file before writing code.
4. **Integration verification**: after both agents complete, the integration verification task runs with the contract-first preamble, treating the contract file as authoritative.

## Measurements to capture

Same structure as Experiment 1, plus contract-quality metrics:

### Primary — did contract-first work?

1. **Contribution distribution via Epictetus audit**: target ~30/70 or better balance. Hard failure if Single-Author Product verdict fires.
2. **Contract adherence**: neither agent modified the contract file. Diff against the pre-agent-work snapshot.
3. **Clean integration**: `tsc --noEmit` exit 0 post-merge, game actually runs, arrow keys work.
4. **Integration verification**: passes without needing to rewrite the contract. If integration agent flags a mismatch and fixes the implementation (not the contract), that's a successful run.

### Secondary — how good was the LLM contract?

5. **Contract completeness**: did the generated contract define all the interfaces needed? If Agent A asked for a method that wasn't in the contract, that's a completeness gap.
6. **Contract ambiguity**: did either agent have to guess at semantics? Look for agent logs or decision artifacts mentioning "unclear from contract" or equivalent.
7. **Contract type soundness**: did the interfaces compose without the agents needing to add glue types?
8. **Decomposer task count**: did `decompose_by_contract` produce 2-3 tasks as instructed? More means the decomposer failed to isolate boundaries; fewer means the contract was too thin.

## Three possible outcomes

### Outcome A — contract-first works as advertised

Contribution ~30/70, clean merge, contract unmodified, integration verification passes. LLM-generated contract was as good as hand-crafted.

**Implication**: GH-320 is effectively closed. PR #327 productionization is validated. Experiment 3 can proceed using LLM-generated contracts as well. Consider defaulting `MARCUS_DECOMPOSER=contract_first` for tightly-coupled project classes.

### Outcome B — contract quality is the bottleneck

Contribution is better than feature-based (some improvement over 100/0 baseline) but not as balanced as Experiment 1. Or the integration agent had to make significant fixes. Or the contract had clear completeness/ambiguity gaps.

**Implication**: PR #327 plumbing is correct but the contract-generation prompts (`_ARTIFACT_PROMPT`, `_INTERFACE_CONTRACTS_PROMPT`) need iteration. File a follow-up issue on prompt tuning. Keep contract-first behind the flag until prompts are good enough.

### Outcome C — contract-first re-collapses to Single-Author

One agent absorbs all the work. Either the contract was too thin to isolate work, the decomposer's tasks were vague, or the agents ignored the contract layer in their prompts.

**Implication**: something structural in PR #327 is broken or insufficient. Investigate whether:
- Agent prompt layer isn't actually reaching the agent (prompts truncated, layer skipped)
- `Task.responsibility` isn't making it to the agent via `get_task_context`
- The LLM-generated contract is fundamentally thinner than a hand-crafted one, and the delta matters
- Marcus's decompose_by_contract is producing tasks with weak `responsibility` values that don't give agents enough to lock onto

Likely requires one or more of: contract amendment flow, stricter decomposer prompt, agent prompt emphasis, or a hybrid strategy that falls back to feature_based inside specific sub-domains.

## What to do with the result

Write the outcome to `docs/audit-reports/snake-contract-llm-YYYY-MM-DD.json`. Update GH-320 with the finding. Specifically:

- **If Outcome A fires**: close GH-320 PR 2 as validated. Mention the experiment in the CHANGELOG. Consider running Experiment 3 with LLM-generated 3-way contract.
- **If Outcome B fires**: file a new issue "improve contract generation prompts for contract-first decomposition" with specific failure modes observed.
- **If Outcome C fires**: file a new issue "contract-first decomposition fails with LLM-generated contracts — investigate" with the observed failure mode and a hypothesis. Keep the flag off by default until resolved.

## Baseline for comparison

The v0.3.0 CHANGELOG documents the feature-based baseline on snake game: contribution split 100/0, 98.5/1.5, 96.9/3.1 across three runs. Experiment 1 (hand-crafted contract) improved this to ~30/70. Experiment 4 should match or exceed that result. Anything worse than 70/30 on an LLM-generated contract is a warning sign.

## Related

- GH-320 issue body, "Experiment 4" section
- PR #327 (contract-aware decomposer + Task.responsibility)
- PR #326 (Phase A→B handoff reconnect, prerequisite)
- Experiment 1 (`~/experiments/snake-contract-test/RESULT.md`)
- Experiment 3 (`gh320-experiment-3-runbook.md`, 3-agent contract-based)
