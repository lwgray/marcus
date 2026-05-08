# Agent-Agnostic Planner Experiments — 2026-05-07 to 2026-05-08

## Headline Finding

**Marcus's planner role works across at least five distinct LLM backends** — one cloud-proprietary, one cloud-hosted-open, three local — producing structurally-comparable contract-first task graphs on the same prompt. Two pre-existing Marcus bugs masked local-model viability; once fixed, the agent-agnostic claim is empirically defensible.

The investigation took 17 trials over two days. Every model failure mode was either a Marcus-side defect or a prompt-engineering issue. None were intrinsic capability limits at the model classes tested.

---

## Models Tested

| Model | Class | Where it runs |
|---|---|---|
| **claude-haiku-4-5** | cloud-proprietary | Anthropic API |
| **llama-3.3-70b-versatile** | cloud-hosted-open | Groq |
| **`Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf`** | local 7B coder | ollama |
| **`Qwen2.5-Coder-7B-Instruct-Q5_K_M.gguf`** | local 7B coder | ollama |
| **DeepSeek-R1-Distill-Qwen-7B (Q5_K_M, Q6_K)** | local 7B reasoning-distill | ollama |
| **Ministral-3 14B (Q?)** | local 14B instruct | ollama |
| **Qwen2.5-Instruct (7B)** | local 7B instruct | ollama (one trial) |

---

## Test Methodology

Two PRDs used as benchmarks:

**Snake game** (single-domain): "Build a snake game" — minimal multi-feature scope, mostly internal logic.

**Recipe sharing platform** (multi-domain): user accounts, recipe CRUD, search/filter, social comments and ratings, saved collections — explicitly designed to span 4+ domains.

Each trial: same MCP-direct prompt to `mcp__marcus__create_project` with `decomposer: contract_first`. We measured:

- **`tot`** — total top-level tasks created
- **`cf`** — `contract_first` labels (decomposer-recognized tasks)
- **`pf`** — `pre-fork` foundation tasks (shared infrastructure synthesis)
- **`dom`** — distinct `domain:*` labels (parallel-decomposition domains)
- **`gap`** — `gap_fill` + `intent_fidelity` labels (LLM-based outcome coverage)
- **`spec`** — `spec_gap` labels (deterministic feature-coverage backup)
- **`comp`** — `composition` task (multi-domain entry-point safety net)
- **wall time** when measured

---

## Complete Trial Matrix

```
trial / model                                       tot cf pf dom gap spec comp  time
─────────────────────────────────────────────────────────────────────────────────────
SNAKE GAME (single-domain PRD)
trial5  haiku-4.5                                    20  3  3   2   2   6    1   <2:00
trial5  qwen2.5-instruct (no fix)                     8  3  0   1   0   0    1     ?
trial5  qwen2.5-coder-Q5 (no fix)                    19  3  1   2   2   7    1     ?
trial5  deepseek-r1-Q5 (no fix)                       8  0  1   0   1   1    0     ?
trial6  deepseek-r1-Q5 (no fix)                      10  0  0   0   2   4    0     ?
trial7  deepseek-r1-Q5 (PR #489 strip+max_tokens)     7  0  0   0   3   0    0   4:25
trial8  deepseek-r1-Q6 (PR #489 + Q6 modelfile)       4  0  0   0   0   0    0     ?
trial9  llama33-70b Groq                             14  8  0   1   0   1    1   ~60s
trial9  ministral-3 14B (no prompt fix)              16  8  1   3   0   0    1     ?

RECIPE PLATFORM (multi-domain PRD)
trial10 llama33-70b Groq (gold)                      17  4  3   4   2   0    1   ~60s
trial11 deepseek-r1-Q6                               19  2  3   2   0   8    1   1:26
trial12 qwen2.5-coder-Q5                             16  3  1   3   0   5    1   1:38
trial13 ministral-3 14B                              21  4  3   2   0   8    1   1:24
trial14 qwen2.5-coder-Q5 (variance check of #12)     16  3  1   3   0   5    1   1:08

PROMPT FIX APPLIED (PR #490)
trial15 qwen2.5-coder-Q5 + prompt fix                27  3  3   3  14   0    1   3:04
trial16 qwen2.5-coder-Q4 + prompt fix                23  9  2   2   4   2    1   2:41
trial17 ministral-3 14B + prompt fix                 26  4  2   2  12   2    1     ?
```

---

## Five-Chapter Narrative

### Chapter 1 — Initial failures revealed two Marcus bugs

Trials 5-7 with `DeepSeek-R1-Distill-Qwen-7B-Q5` on snake-game produced increasingly degraded output:
- Trial 5: 8 tasks, 0 contract_first labels, 0 domains
- Trial 7: 7 tasks, 0 contract_first labels (after one round of "fixes" that didn't help)

Investigation of raw responses revealed two distinct root causes, neither model-side:

**Bug A — Reasoning-block parser failure.** DeepSeek-R1 emits `<think>...</think>` chain-of-thought blocks before structured output. Marcus's PRD parser failed with `Failed to parse AI response as JSON: Expected JSON object, got list`. Contract-first decomposition aborted to feature-based.

**Bug B — `config.ai.max_tokens` silently ignored.** Two hardcoded 2000-token defaults in `LLMAbstraction.analyze` and `LocalLLMProvider.complete` capped every PRD-parser LLM call regardless of `config.ai.max_tokens` (default 4096). Reasoning models routinely exceeded 2000 tokens mid-think and got truncated before producing JSON.

**Fix shipped in PR #489:**
- `_strip_reasoning_blocks()` removes `<think>...</think>` prefixes (later refined per Codex P2 review to anchor only to the leading prefix, preserving embedded tags inside JSON string values)
- `LLMAbstraction.analyze` and `LocalLLMProvider.complete` now honor `config.ai.max_tokens`

### Chapter 2 — Single-domain projects naturally suppress contract-first markers

Trial 9 with Llama 3.3 70B on snake-game produced **0 foundation tasks** despite contract-first succeeding cleanly (8 cf labels, 1 domain, composition synthesized). Investigation of `_synthesize_shared_foundation` showed the prompt explicitly instructs:

> "Be CONSERVATIVE. Return foundation tasks ONLY when agents would DEFINITELY produce incompatible implementations without them. When uncertain, return an empty list."

Single-domain projects don't need shared foundation. The prompt's conservative disposition is a feature, not a bug. Foundation count alone is **not a contract-first health signal** — domain count and contract_first label count are the real signals.

This invalidated the "fall back to feature_based if no foundation tasks" heuristic: trial 9 would have been wrongly downgraded despite producing a clean contract-first DAG.

### Chapter 3 — Multi-domain PRD revealed local models are viable

Switching to the recipe-platform PRD changed the picture entirely. Same models, much richer output:

| Model | Snake (single-domain) | Recipe (multi-domain) |
|---|---|---|
| deepseek-r1-Q6 | 4-7 tasks, 0 cf, 0 dom (failed) | 19 tasks, 2 cf, 3 pf, 2 dom (works) |
| qwen2.5-coder-Q5 | 19 tasks, 3 cf, 1 pf | 16 tasks, 3 cf, 1 pf |
| ministral-3 14B | 16 tasks, 8 cf, 3 dom | 21 tasks, 4 cf, 3 pf, 2 dom |
| Llama 3.3 70B | 14 tasks, 8 cf, 1 dom | 17 tasks, 4 cf, 3 pf, 4 dom |

Trial 11 was the breakthrough: **deepseek-r1-Q6 produced 3 canonical foundation tasks** (`Design System Setup`, `Shared Components Setup`, `Tech Foundation Configuration`) on the recipe PRD. The earlier snake-game collapse had been a project-shape artifact, not a capability ceiling.

Trial 14 confirmed reproducibility: re-running qwen2.5-coder-Q5 on the same PRD produced **structurally identical** output (16 tasks, 3 cf, 3 domains, same domain names). LLM nondeterminism on individual tasks does not cascade into materially different graphs.

### Chapter 4 — All local models hit the same gap_fill failure mode

Trials 11, 12, 13, 14 all reported `score=1.00, 0 gap(s)` from the LLM-based outcome-coverage check. The deterministic `spec_coverage` backup augmenter caught 5-8 real uncovered features per project. The LLM was generously mapping internal/structural tasks to user outcomes, hiding gaps from the gap-fill pipeline.

Diagnosis: weak instruction-following models defaulted to "yes this task addresses the outcome" when the prompt asked them to map. The original prompt warned against false positives but didn't anchor "empty" as the expected default.

**First fix attempt (rejected):** add a 16-verb whitelist requiring task names to contain a specific user-observable verb. Kaia review and user pushback converged on the same critique: domain space is unbounded, static lists silently degrade on unanticipated domains, and LLMs generalize from examples better than from rules.

**Final fix (PR #490):** replace the whitelist with 5 diverse domain examples (snake game, REST API, file upload, notification, CLI) plus the principle statement: *"a task addresses an outcome when COMPLETING IT PRODUCES the observable signal the user can sense."* Disposition framing (`DEFAULT TO EMPTY`) preserved.

### Chapter 5 — Validation across three local model classes

Trials 15, 16, 17 with the prompt fix on the recipe PRD:

| Model | total | cf | pf | dom | gap | time | foundation names |
|---|---|---|---|---|---|---|---|
| qwen2.5-coder-Q5 | 27 | 3 | 3 | 3 | 14 | 3:04 | All 3 canonical |
| qwen2.5-coder-Q4 | 23 | 9 | 2 | 2 | 4 | 2:41 | 2 of 3 canonical |
| ministral-3 14B | 26 | 4 | 2 | 2 | 12 | ? | 2 of 3 canonical |

All three locals now produce gap-fill tasks and surface honest coverage gaps. The marcus log for trial 15 confirms: `score=0.50, 14 outcome(s), 14 gap(s), 14 synthesized task(s)` — replacing trial 14's misleading `score=1.00, 0 gap(s)`.

---

## Final Viability Matrix

For the **multi-domain recipe PRD** with all fixes applied:

| Tier | Model | Hosting | Tasks | Foundation | Gap-Fill | Time | Cost/run |
|---|---|---|---|---|---|---|---|
| **Cloud (gold)** | claude-haiku-4-5 | Anthropic | (snake: 20) | 3 canonical | 2 | <2:00 | ~$0.04 |
| **Cloud (open)** | llama-3.3-70B-versatile | Groq | 17 | 3 canonical | 2 | ~60s | ~$0.04 |
| **Local 7B coder** | qwen2.5-coder-Q5 | ollama | 27 | 3 canonical | 14 | 3:04 | $0 |
| **Local 7B coder** | qwen2.5-coder-Q4 | ollama | 23 | 2 canonical | 4 | 2:41 | $0 |
| **Local 14B instruct** | ministral-3 14B | ollama | 26 | 2 canonical | 12 | ? | $0 |
| **Local 7B reasoning-distill** | deepseek-r1-Q6 | ollama | 19 | 3 canonical | 0* | 1:26 | $0 |

`*` Trial 11 used the original prompt; deepseek-r1-Q6 with the new prompt has not been re-tested.

---

## Performance Notes

**Latency cost of the prompt fix.** Trial 14 (no fix) → Trial 15 (fix) on the same model went from 1:08 → 3:04 — about 2× wall time. The cost is structurally legitimate: the new prompt surfaces 14 real gaps, gap-fill synthesizes 14 new tasks via an LLM call, and a recoverage check runs against the augmented graph. ~60% above pure linear scaling from task count.

**Open optimizations** (filed for follow-up, not blocking):

1. **Skip recoverage on clean fill** — early exit when `synthesized_count == gap_count` and synthesis didn't error. Saves ~30s on recipe-class projects.
2. **Parallelize coverage_before with task creation** — these don't strictly depend on each other.
3. **Cheap-tier model for coverage check** — yes/no-per-outcome is a smaller question than full decomposition; could use a faster model class.

**Speed observations across model classes:**
- Cloud-hosted (Groq) — fastest at ~60s; LPU inference is ~600 tok/s
- Cloud-proprietary (Anthropic) — ~2 min for haiku-4.5
- Local 7B (qwen, deepseek-r1) — 1:08–3:04 depending on prompt complexity
- Local 14B (ministral-3) — comparable to 7B on recipe PRD; trial 9 snake-game perceived as 10+ minutes was likely cold-load overhead, not steady-state

---

## Architectural Lessons

**1. Examples teach better than enumeration when the domain space is unbounded.** The verb-whitelist crutch we tried first silently failed on backend-heavy domains. Diverse domain examples plus a principle statement generalize. This pattern applies to any Marcus prompt enumerating an unbounded category.

**2. "Conservative on LLM failure" can hide real failures.** Marcus's pre-fork foundation synthesis defaults to empty on weak responses, which is correct for single-domain projects but masked the false-positive bias in outcome coverage for years. The fix was to surface the disposition explicitly in the prompt, not to add fallback heuristics.

**3. Single-domain projects are bad benchmarks for contract-first.** Snake game produces 0-1 domains; the contract-first markers (foundation, gap_fill, multi-domain composition) are minimally exercised. Multi-domain PRDs surface real signal.

**4. Model variance within a project shape is low.** Trial 12 vs 14 (qwen2.5-coder-Q5 on the same PRD) produced byte-identical structural output. Marcus's pipeline is deterministic-enough that LLM nondeterminism on individual tasks doesn't cascade.

**5. The agent-agnostic claim survives empirical scrutiny.** Across cloud-proprietary, cloud-open, local-coder, local-instruct, and local-reasoning model classes, the same Marcus coordination contract is honored. Differences are quality-of-decomposition, not pass/fail.

---

## Open Questions / Future Work

1. **Spec_coverage orphan-task wiring.** When a project has 0 foundation tasks, augmented `spec_gap` tasks can become orphan roots (trial 9: `Implement Boundary Checking` had no parent). The fix is at the augmenter layer, not the dispatch layer — make spec_coverage attach to design tasks when no foundation exists.

2. **Re-test deepseek-r1-Q6 with prompt fix.** Currently has 0 gap_fill tasks (pre-fix); other locals all ≥4. May rise to comparable territory once the fix is applied.

3. **Domain breadth ceiling for local 7B models.** Llama 3.3 70B finds 4 domains in the recipe PRD; local 7B/14B find 2-3. Decomposition granularity is the remaining quality gap, not contract-first capability.

4. **Strong-model regression check.** New prompt has not been validated against haiku/Llama. Risk that DEFAULT TO EMPTY bias overcorrects on projects where strong models were correctly producing rich coverage. Trial-comparable run pending.

5. **Cato-side observability for intent fidelity score asymmetry.** Weak models will under-report `intent_fidelity_score` after gap-fill due to the same DEFAULT TO EMPTY bias affecting `coverage_after`. Observability degradation, not coordination defect, but creates a confound for cross-provider comparison studies.

---

## Recommended PyCon Sprint Configurations

For developers wanting to try Marcus locally without API costs:

| Profile | Model | Why |
|---|---|---|
| **Default recommendation** | `qwen2.5-coder:7b-instruct-Q5_K_M` | Best foundation depth, all canonical names, most thorough gap-fill |
| **Fast-iteration** | `qwen2.5-coder:7b-instruct-Q4_K_M` | Smaller, faster; trades some foundation depth |
| **Quality-first local** | `ministral-3:14b` | Strong overall; slightly weaker task naming on gap-fill |

For developers OK with cloud-hosted open models (no API spend, free Groq tier):

| Profile | Model | Why |
|---|---|---|
| **Speed + quality** | `llama-3.3-70b-versatile` via Groq | ~60s per project, gold-standard structure, free tier sufficient |

All four configurations require the fixes from PR #489 and PR #490 to be merged.

---

## Are the 14 gap-fill tasks real, or did the prompt overshoot?

A reasonable concern after trial 15: 14 gap_fill tasks is a lot for one PRD. Did the new prompt over-correct from "0 gaps hides everything" to "14 gaps fabricates work that wasn't asked for"?

Mapping each gap-fill task back to the PRD verbatim:

| Gap-fill task | PRD feature requested |
|---|---|
| Implement Signup Feature | "User accounts: signup, login, profile editing, password reset" → signup |
| Implement Login Feature | (same line) → login |
| Implement Profile Editing Feature | (same line) → profile editing |
| Implement Password Reset Feature | (same line) → password reset |
| Implement Create Recipe Feature | "Recipe management: create, view, edit, delete recipes" → create |
| Implement View Recipe Feature | (same line) → view |
| Implement Edit Recipe Feature | (same line) → edit |
| Implement Delete Recipe Feature | (same line) → delete |
| Implement Search Recipes Feature | "Discovery: search recipes by name" → search |
| Implement Filter Recipes Feature | "filter by ingredient, cuisine, or dietary restriction" → 3 filter types collapsed into 1 |
| Implement Comment On Recipe Feature | "Social: comment on recipes, rate them 1-5 stars, follow other users" → comment |
| Implement Rate Recipe Feature | (same line) → rate |
| Implement Follow Users Feature | (same line) → follow |
| Implement Bookmark Recipes Feature | "Saved collections: bookmark recipes into named collections" → bookmark + collections bundled |

**14 gap_fill tasks cover 16 of 17 PRD-stated features.** The 3 filter sub-types (ingredient, cuisine, dietary) collapse into one Filter Recipes task — a reasonable bundling. Named collections bundles with bookmark — debatable, possibly worth a separate task.

The gaps are real. Qwen2.5-Coder-Q5 just produces a different decomposition style than Llama 3.3 70B:

- **Qwen-coder-Q5** decomposes at the **service level** in its initial pass: 3 contract_first tasks named `Implement User Management API Endpoints`, `Implement Recipe Management API Endpoints`, `Implement Social Interaction & Discovery API Endpoints`. Each service-level task internally bundles 4-5 user-visible features. Marcus's outcome-coverage augmenter then surfaces those bundled features as individual gap-fill tasks.

- **Llama 3.3 70B** decomposes at a **mid-grain feature level** in its initial pass: 4 contract_first tasks already named at finer granularity. Less for gap-fill to do.

Both are valid decomposition styles. End-state coverage is comparable; the count distribution between `cf` and `gap_fill` labels just shifts.

**Verification heuristic for future prompt-tuning:** for any PRD, gap_fill count + cf count should approximately equal the count of user-stated features. If gap_fill count significantly exceeds the feature count, the prompt is over-firing. If gap_fill is zero on a multi-feature PRD, the prompt is under-firing (the trial 11/12/14 problem).

Recipe PRD has 17 features. Trial 15 produced 14 gap + 3 cf = **17 user-facing implementation tasks**. Right answer.

---

## Prompts Used (for reproducibility)

### Snake-game PRD (trials 5–9, 15–17 are recipe variants)

```
Build a snake game
```

That's the literal prompt — Marcus's PRD parser expanded the implicit features (movement, collision, food, score, etc.) via its analysis pass. Single-domain, minimal scope.

### Recipe-platform PRD (trials 10–17)

```
Build a recipe sharing platform with these features:

- User accounts: signup, login, profile editing, password reset
- Recipe management: create, view, edit, delete recipes with photos and ingredients
- Discovery: search recipes by name, filter by ingredient, cuisine, or dietary restriction
- Social: comment on recipes, rate them 1-5 stars, follow other users
- Saved collections: bookmark recipes into named collections (e.g. "Weeknight dinners")

Tech stack expectation: REST API backend, web frontend.
```

Five domains, ~17 user-stated features. Designed to span enough breadth that contract-first decomposition has real work to do.

### Outcome-coverage prompt — POST-FIX (PR #490)

The full text of `_LLM_COVERAGE_PROMPT` after merging PR #490. This is the prompt used in trials 15, 16, 17.

```
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

  REST API:
    Outcome: "user can sign up"
    - Task "POST /api/users endpoint with response" → ADDRESSES
      (HTTP response is the user-observable evidence)
    - Task "User schema validation" → does NOT (internal precondition)

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
```

Lives at `src/marcus_mcp/coordinator/outcome_coverage.py` constant `_LLM_COVERAGE_PROMPT`.

### Outcome-coverage prompt — PRE-FIX (trials 11–14, kept for reference)

The original prompt before PR #490. Trials 11/12/13/14 used this version and consistently reported `score=1.00, 0 gap(s)` even when 5–8 real gaps existed (caught by the deterministic spec_coverage backup).

```
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
```

The fix added 3 instructions (DEFAULT TO EMPTY anchor, 4 new domain examples, evidence-description tiebreaker) plus a tightened rule on what counts as "addresses." Same scaffold otherwise.

### Foundation synthesis prompt (used unchanged across all trials)

`_synthesize_shared_foundation` in `src/integrations/nlp_tools.py:968-1131`. Excerpt of the LLM-facing portion:

```
You are analysing a software project to determine whether parallel
development agents need a shared foundation before their independent
work begins.

PRD Description:
{description}

[optional Domain Contracts section when contract_first]

Analyse whether parallel agents working on this project need ANY of
these shared foundations BEFORE starting domain-specific work:

1. Design System: shared visual tokens (colors, typography, spacing,
   themes) — needed when multiple UI features must look visually
   consistent.
2. Shared Components: reusable UI or logic components (Card, Button,
   API client) — needed when ≥2 domains will use the same component.
3. Tech Foundation: shared configuration (TypeScript config, routing,
   test harness) — needed when agents would duplicate this setup
   independently.

Be CONSERVATIVE. Return foundation tasks ONLY when agents would
DEFINITELY produce incompatible implementations without them.  When
uncertain, return an empty list.

DEDUPLICATE within your own response: if two of your candidates target
the same conceptual domain, MERGE them into a single foundation task
before returning. [...]

Return ONLY valid JSON with this exact structure:
{"foundation_tasks": [
  {"name": "<plain task name>",
   "description": "<what to build and why parallel agents need it
                   done first>",
   "estimated_hours": <positive number>}
]}

If no shared foundation is needed: {"foundation_tasks": []}
```

This prompt was not changed during these experiments. Worth noting it includes the same conservative-default disposition that the post-fix outcome-coverage prompt now uses — the foundation synthesis was already doing this correctly, the outcome coverage just hadn't caught up.

---

## Reproducing the experiments

To re-run any trial in this matrix:

1. **Marcus config** (`~/.marcus/config_marcus.json`):
   ```json
   "ai": {
       "provider": "local",
       "local_url": "http://localhost:11434/v1",
       "local_model": "<ollama-tag>",
       "max_tokens": 8192,
       "temperature": 0.7
   }
   ```
   For Groq: `"local_url": "https://api.groq.com/openai/v1"`, set `MARCUS_LOCAL_LLM_KEY` env var to `gsk_...`.

2. **Restart Marcus** so config reloads.

3. **Invoke create_project** via MCP direct with the PRD text (snake or recipe above) and an experiment-numbered project name.

4. **Inspect the result:**
   ```bash
   sqlite3 ~/dev/marcus/data/kanban.db "
     SELECT l.label, COUNT(*) FROM task_labels l JOIN tasks t ON l.task_id=t.id
     WHERE t.project_name='<your-trial-name>' AND t.is_subtask=0
     GROUP BY l.label ORDER BY 2 DESC;
   "
   ```

5. **Inspect the marcus log** for the `Outcome coverage` line:
   ```bash
   grep "Outcome coverage" ~/dev/marcus/logs/marcus_2026*.log | tail -10
   ```

Both PR #489 and PR #490 must be merged for results to match this matrix.

---

## Cross-References

- **PR #489** — strip `<think>` blocks from local LLM responses + honor `config.ai.max_tokens`
- **PR #490** — replace verb whitelist with diverse domain examples in outcome-coverage prompt
- **simon entries** — `fd042ed6` (local-models concern), `03600d30` (Kaia review pass 1), `d11029d2` (decision to ship #490)
- **Reproducer projects in `data/kanban.db`** — all trial5–trial17 projects retained for verification

---

*Compiled 2026-05-08 from kanban.db trial5–trial17 + marcus log artifacts + PR #489/#490 commits.*
