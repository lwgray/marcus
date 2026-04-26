# MarcusBench Research Notebook
**Version**: 1.0 — PyCon 2026 Sprint Edition
**Last Updated**: 2026-04-25
**Issues**: #214 (pipeline tracker), #325 (methodology), #210 (benchmark harness)

---

## What We Are Measuring

**Central claim**: Board-mediated coordination (Marcus) degrades less than
unstructured multi-agent approaches as task coupling increases.

**Operationalization** (from #325):

```
MarcusBench = PRD Taxonomy × Marcus Experiment × Epictetus Report → aggregate metrics
```

**Key metric**:

```
retention = Marcus_pass_rate / Solo_pass_rate
  > 1.0  → coordination adds value
  = 1.0  → coordination is neutral
  < 1.0  → coordination overhead destroys value
```

**Secondary metrics from Epictetus**:
- `coordination_effectiveness.score` — did agents work in parallel?
- `contribution_distribution.verdict` — did multiple agents produce the output?
- `weighted_total.score` — code quality
- `dag_shape` — was the dependency graph a chain or a fan-out?

---

## The PRD Taxonomy (4 Tiers)

| Tier | DAG Shape | Coordination Challenge | PRDs Available |
|------|-----------|----------------------|----------------|
| 1 | Wide fan-out | Independent parallel work, minimal deps | ⬜ needs writing |
| 2 | Diamond | Parallel work with merge point | ✅ datetime-api |
| 3 | Sequential chain | Strict handoffs, fidelity matters | ⬜ needs writing |
| 4 | Conflict-by-design | Intentional overlap requiring arbitration | ⬜ needs writing |

**Sprint priority**: Tier 1 first (easiest to run, establishes baseline).
Tier 4 is the most scientifically interesting but requires hand-crafted PRDs.

---

## Experiment Conditions Matrix

All Marcus conditions (B–E) use **the same coordination mechanism**: the
kanban board as the shared environment. The variable is how many worker
agents are running simultaneously. This lets us measure the retention curve
across team sizes — where does parallelism start paying off, and where does
coordination overhead cause saturation?

```
Expected retention curve shape (illustrative):

retention
  ^
1.2|                C    D
   |           B
1.0|---A(solo baseline)----------
   |                        E(saturation?)
0.8|
   +---Solo--1w---2w---4w---6w---> workers
```

At low worker counts (B), coordination overhead may cancel out parallelism
gains. At some point (C or D), parallelism wins and retention exceeds 1.0.
At high counts (E), the DAG may not have enough parallel work to keep all
agents busy — you pay coordination overhead for idle agents.

The curve shape, where it peaks, and whether it differs by tier (1→4) is
the primary empirical contribution.

| Condition | Workers | The One Variable | API Key Needed |
|-----------|---------|-----------------|----------------|
| **A: Solo** | 0 (1 Opus, no board) | No coordination at all — pure baseline | Yes (Claude) or Ollama |
| **B: Marcus 1w** | 1 worker + orchestrator | Minimum board-mediated team | Yes (Claude) or Ollama |
| **C: Marcus 2w** | 2 workers + orchestrator | Small parallel team | Yes (Claude) or Ollama |
| **D: Marcus 4w** | 4 workers + orchestrator | Medium parallel team | Yes (Claude) or Ollama |
| **E: Marcus 6w** | 6 workers + orchestrator | Large team, possible saturation | Yes (Claude) or Ollama |

For **Paper 2** ablations (run after Tier 1/2 data is collected):
- **F**: Marcus without design validation (#205 off)
- **G**: Marcus without baton arbitration (#206 off)

---

## Model Configuration — CRITICAL CAVEATS

**Results are only comparable if all contributors use the same model configuration.**
Mixing model families across runs makes the data meaningless for the paper.

### VRAM Reference (16GB GPU)

| Model | Role | Quantization | VRAM | Pull Command |
|-------|------|-------------|------|-------------|
| `deepseek-r1:14b` | Orchestrator | Q8_0 | ~14GB | `ollama pull deepseek-r1:14b` |
| `qwen2.5-coder:14b` | Workers | Q4_K_M | ~9GB | `ollama pull qwen2.5-coder:14b` |
| `devstral-small-2` | Orchestrator alt | Q4_K_M | ~14GB | `ollama pull devstral-small-2` |
| `qwen3:30b-a3b` | Orchestrator alt | Q4_K_M | ~14–16GB | `ollama pull qwen3:30b-a3b` |
| `claude-sonnet-4-6` | Orchestrator | API | — | (API key) |
| `claude-haiku-4-5-20251001` | Workers | API | — | (API key) |

Do **not** try `qwen3:32b` (dense, ~19GB) or `llama4:scout` (~24GB) — both
exceed 16GB at any practical quantization.

---

### Path A: Ollama / Local (primary path for sprint contributors)

The standard configuration for all PyCon sprint runs. Free to run, no API key
required. **DeepSeek-R1-Distill 14B** is chosen as orchestrator because its
chain-of-thought reasoning is the best open-source proxy for the PRD
decomposition task — reading an ambiguous spec and producing a valid dependency
graph.

```bash
# Pull both models (one-time, ~10GB download total)
ollama pull deepseek-r1:14b          # orchestrator (~14GB VRAM at Q8_0)
ollama pull qwen2.5-coder:14b        # workers (~9GB VRAM at Q4_K_M)

# Start Ollama if not already running
ollama serve
```

Configure Marcus to use local models:

```bash
export MARCUS_AI_PROVIDER=local
export MARCUS_LOCAL_URL=http://localhost:11434/v1
export MARCUS_LOCAL_KEY=ollama

# Orchestrator model (used for PRD decomposition)
export MARCUS_ORCHESTRATOR_MODEL=deepseek-r1:14b

# Worker model (used for task execution)
export MARCUS_LOCAL_MODEL=qwen2.5-coder:14b
```

**Important**: The R1 model wraps its reasoning in `<think>...</think>` tags
before producing output. Marcus strips these automatically, but if you see
raw `<think>` blocks in task descriptions, set:

```bash
export MARCUS_STRIP_THINKING_TAGS=true
```

**VRAM note**: Running orchestrator + workers simultaneously on one GPU requires
~23GB (14GB + 9GB). On a 16GB GPU, run them **sequentially** — the orchestrator
finishes its one call per PRD before workers start, so they do not overlap in
practice. Confirm with `nvidia-smi` that VRAM is released between phases.

**If you have less than 14GB free VRAM**, use this smaller config instead
(results must be labeled separately):

```bash
ollama pull qwen2.5-coder:14b        # both roles
export MARCUS_ORCHESTRATOR_MODEL=qwen2.5-coder:14b
export MARCUS_LOCAL_MODEL=qwen2.5-coder:14b
# Label all results: [OLLAMA-qwen2.5-coder:14b-both]
```

**MUST label your results clearly** using the model tag in the Experiment ID:
- Standard config: `tier2-condC-[OLLAMA-r1:14b]-20260425-1430`
- Fallback config: `tier2-condC-[OLLAMA-coder:14b-both]-20260425-1430`

Never aggregate results from different model configs in the same retention table.

---

### Path B: Claude API (for paper-quality data — maintainer use)

```bash
export CLAUDE_API_KEY=sk-ant-...
```

Marcus config:
- Orchestrator: `claude-sonnet-4-6` (replaces Opus 4.7 — cheaper, still strong)
- Workers: `claude-haiku-4-5-20251001`

**Cost estimate per experiment run**:
- Solo condition: ~$0.20–$0.80 (single Sonnet agent, one full PRD)
- Marcus 3-worker: ~$0.40–$1.50 (Sonnet orchestrator + 3 Haiku workers)
- Tier 4 (complex PRD): up to $3.00 per run

Claude results are the paper's primary dataset. Ollama results from Path A
are replications used to test whether findings hold across model families.

### Path C: OpenAI (acceptable if agreed in advance)

```bash
export OPENAI_API_KEY=sk-...
export MARCUS_AI_PROVIDER=openai
```

Model: `gpt-4o-mini` for orchestrator, `gpt-4o-mini` for workers.
Check with notebook maintainer before running — must be pre-approved.

---

## Prerequisites Checklist

Complete ALL items before running any experiment.

### Install Marcus (clone only — no PyPI package)

```bash
git clone https://github.com/lwgray/marcus.git
cd marcus
pip install -e .
cp -r skills/marcus ~/.claude/skills/marcus   # Runner mode only
cp .env.example .env
cp config_marcus.example.json config_marcus.json
```

Edit `.env` for your model path (see Model Configuration above).

### Install Posidonius (the experiment runner)

```bash
git clone https://github.com/lwgray/posidonius.git
cd posidonius
pip install -e .           # runtime deps only — sufficient for running experiments
# pip install -e ".[dev]"  # adds linting/type-checking tools (Posidonius devs only)
```

### Install Claude Code CLI (the agent runtime)

```bash
npm install -g @anthropic-ai/claude-code   # or follow claude.ai/code instructions
claude --version   # verify
```

Agents run as `claude --dangerously-skip-permissions < prompt_file` inside
tmux panes. Claude Code is the agent runtime — it calls Marcus MCP tools
internally. You do not call Marcus MCP endpoints directly.

### Checklist

- [ ] `git clone` of marcus done, `pip install -e .` succeeded
- [ ] `./marcus start` runs without errors
- [ ] `curl http://localhost:4298/mcp/health` returns 200
- [ ] `git clone` of posidonius done, `pip install -e .` succeeded
- [ ] Posidonius starts: `python -m posidonius` → http://localhost:8420 loads
- [ ] `claude --version` works in terminal (Claude Code CLI installed)
- [ ] `tmux` installed: `tmux -V`

### Model Path

- [ ] (Path A) Ollama running: `ollama serve` → `curl http://localhost:11434`
- [ ] (Path A) `deepseek-r1:14b` pulled: `ollama list | grep deepseek-r1`
- [ ] (Path A) `qwen2.5-coder:14b` pulled: `ollama list | grep qwen2.5-coder`
- [ ] (Path A) VRAM available: `nvidia-smi` shows ≥14GB free
- [ ] (Path B) `CLAUDE_API_KEY` set in `.env` (maintainer only)

### Coordination With Other Contributors

- [ ] Claimed your experiment slot in the tracking sheet (see bottom of this doc)
- [ ] Confirmed PRD tier and condition (A/B/C/D/E)
- [ ] Confirmed model path and labeled results accordingly

---

## How the Pieces Fit Together

```
PRD (markdown file)
    │
    ├─ Condition A (Solo) ──► run_single_agent_experiment.py
    │                             └─ launches Claude in tmux
    │                             └─ Claude implements PRD alone (no Marcus)
    │                             └─ MLflow logs timing + metrics
    │
    └─ Conditions B–E (Marcus) ──► Posidonius web UI (http://localhost:8420)
                                      └─ calls run_experiment.py per run
                                      └─ launches Marcus + agents in tmux
                                      └─ Epictetus runs automatically on completion
                                      └─ MLflow tracks each run as a child run

Test suite (pytest) runs AFTER the agent finishes, against the output directory.
Epictetus also runs AFTER, auditing the same output directory.
Both are automatic in the Posidonius pipeline.
```

---

## Step-by-Step: Running One Experiment

### Step 0 — Choose Your PRD and Condition

Claim a row in the tracking sheet before starting. One person per cell.

**For first-time contributors**: Start with Tier 2 / Condition A (Solo).
The datetime-api PRD exists and has a known baseline.

### Step 1 — Prepare Your PRD File

```bash
# Each run needs its own experiment ID
EXPERIMENT_ID="tier2-condA-$(date +%Y%m%d-%H%M)"

# Copy the PRD for your tier into a working directory
mkdir -p ~/marcusbench-runs/$EXPERIMENT_ID
cp /path/to/marcus/dev-tools/experiments/prd-library/tier2-datetime-api.md \
   ~/marcusbench-runs/$EXPERIMENT_ID/prd.md
```

**NEVER reuse a directory.** Each run gets its own `$EXPERIMENT_ID`.

### Step 2 — Start Marcus

```bash
cd ~/dev/marcus
./marcus start
# Verify: curl http://localhost:4298/mcp/health  → should return 200
```

### Step 3a — Condition A: Solo Baseline

The solo runner initialises a structured experiment directory, generates a
prompt from your PRD (with task checkpoints and timing instructions), then
launches a single Claude Code agent in a tmux pane. The agent works alone —
no Marcus board, no other agents.

```bash
cd ~/dev/marcus

# 1. Initialise the experiment directory
python dev-tools/experiments/runners/run_single_agent_experiment.py \
  --init ~/marcusbench-runs/$EXPERIMENT_ID/solo

# 2. Copy your PRD into the experiment as project_spec.md
cp ~/marcusbench-runs/$EXPERIMENT_ID/prd.md \
   ~/marcusbench-runs/$EXPERIMENT_ID/solo/project_spec.md

# 3. Edit config.yaml — set agent_mode to "structured" or "unstructured"
#    structured  = PRD task breakdown is given to the agent as checkpoints
#    unstructured = raw PRD only, agent decides its own breakdown
nano ~/marcusbench-runs/$EXPERIMENT_ID/solo/config.yaml

# 4. Run (launches Claude in tmux, auto-attaches)
python dev-tools/experiments/runners/run_single_agent_experiment.py \
  ~/marcusbench-runs/$EXPERIMENT_ID/solo
```

Output lands in `~/marcusbench-runs/$EXPERIMENT_ID/solo/implementation/`.
MLflow logs timing automatically. tmux session name is printed on launch.

### Step 3b — Conditions B/C/D/E: Marcus Multi-Agent via Posidonius

Posidonius handles everything: project creation, agent spawning, monitoring,
Epictetus audit, and MLflow tracking. You interact via its web UI.

```bash
# Start Posidonius (from its repo directory)
cd ~/dev/posidonius

# If you cloned Marcus into ~/dev/marcus (the default), just:
python -m posidonius

# If you cloned Marcus elsewhere, pass the templates path explicitly:
python -m posidonius \
  --templates-dir ~/path/to/marcus/dev-tools/experiments/templates

# Opens http://localhost:8420
```

> **Note**: Posidonius hardcodes `~/dev/marcus` as the Marcus root. If your
> Marcus clone lives elsewhere, the `--templates-dir` flag above fixes the
> template lookup. The Marcus MCP server itself (port 4298) must already be
> running regardless.

In the web UI:
1. **Project name**: your `$EXPERIMENT_ID`
2. **Project spec**: paste contents of your `prd.md`
3. **Agent counts**: one entry per condition you want to run
   - Condition B: `1`
   - Condition C: `2`
   - Condition D: `4`
   - Condition E: `6`
4. **Complexity**: match to your PRD's tier
5. Click **Start All** (not just "Start") — this starts run 0 AND enables
   auto-advance through all runs in sequence.

Posidonius runs each agent count sequentially. For each run it:
- Creates Marcus project from the PRD
- Spawns N agents in tmux (each agent is a `claude` process)
- Monitors completion (polls every 30s for `experiment_complete.json`)
- **Automatically runs Epictetus** after the run finishes (pipeline.py:627,
  while agents are still alive for interrogation) — only when auto-advance
  is active, which "Start All" enables
- Tears down tmux, advances to next run

Monitor live at http://localhost:8420. View MLflow at:
```bash
mlflow ui --backend-store-uri sqlite:///$HOME/experiments/mlflow.db
# Open http://localhost:5000
```

### Step 4 — The Test Suite

Every MarcusBench PRD ships with a `tests/` directory. The test suite is
the scoring oracle — it runs against the agent output and produces the pass
rate that feeds the retention metric.

**For solo runs**: run manually after the agent declares completion:

```bash
cd ~/marcusbench-runs/$EXPERIMENT_ID/solo/implementation
pip install -r requirements.txt 2>/dev/null || true
pytest tests/ -v --tb=short --json-report \
  --json-report-file=../../test-results.json
```

**For Posidonius runs**: Posidonius runs the test suite automatically as part
of its completion detection. The results are logged to MLflow and written to
`{run_dir}/test-results.json`.

Extract pass rate:
```bash
python3 -c "
import json, pathlib
r = json.load(open('test-results.json'))
passed = r['summary']['passed']
total  = r['summary']['total']
print(f'{passed}/{total} = {passed/total:.1%}')
"
```

### Step 5 — Epictetus

**For Posidonius runs (Conditions B–E) using "Start All"**: Epictetus runs
automatically inside the auto-advance loop. You do not invoke it manually.
Posidonius calls it while agents are still alive, then tears down tmux.
Output is written to `{run_dir}/epictetus.log` and the JSON report to
`{run_dir}/implementation/docs/audit-reports/`.

If you used the manual "Start" button (no auto-advance), Epictetus did NOT
run automatically. In that case, pause the pipeline before teardown and run
Epictetus manually (same instructions as Condition A below).

**For solo runs (Condition A)**: Run Epictetus manually inside Claude Code
after the agent finishes. The `--research` flag (⚠️ not yet implemented —
tracked as a future issue) will output a condensed JSON summary with only
the MarcusBench-relevant fields. Until then, use the full audit:

```
# Inside Claude Code, from the solo implementation directory:
/epictetus ~/marcusbench-runs/$EXPERIMENT_ID/solo/implementation --type backend_api
```

Epictetus writes 3 artifacts automatically:
- `docs/audit-reports/<name>-<date>.json` — source of truth
- `docs/audit-reports/<name>-<date>.md` — human readable
- `docs/audit-reports/audit-index.json` — running index

Extract the MarcusBench-relevant fields:

```bash
REPORT=$(ls ~/marcusbench-runs/$EXPERIMENT_ID/solo/implementation/docs/audit-reports/*.json | head -1)

python3 - <<'EOF'
import json, sys
r = json.load(open(sys.argv[1]))
print(f"Code quality:         {r.get('weighted_total',{}).get('score')} / 5")
print(f"Coordination:         {r.get('coordination_effectiveness',{}).get('score')} / 5")
print(f"Contribution verdict: {r.get('contribution_distribution',{}).get('verdict')}")
print(f"DAG shape:            {r.get('dag_shape')}")
EOF $REPORT
```

### Step 6 — Record Results

Copy this template into the tracking sheet at the bottom of this doc:

```
EXPERIMENT RECORD
─────────────────────────────────────────────────────────
Date/Time:        ____________________
Experimenter:     ____________________
Experiment ID:    ____________________
PRD Tier:         [ ] 1  [ ] 2  [ ] 3  [ ] 4
Condition:        [ ] A-Solo  [ ] B-1w  [ ] C-2w  [ ] D-4w  [ ] E-6w
Model Path:       [ ] Claude  [ ] Ollama  [ ] OpenAI
Model (orch):     ____________________
Model (worker):   ____________________

TIMING
Wall clock start:   __________  (paste exact timestamp)
Wall clock end:     __________
Wall clock total:   __________ minutes

TESTS
Tests passed:     ____  / ____  total
Pass rate:        ____%

EPICTETUS
Code quality score:       ____ / 5
Coordination score:       ____ / 5
Contribution verdict:     [ ] Balanced  [ ] Lopsided  [ ] Single-Author  [ ] Complementary
DAG shape:               ____________________
Weighted total:           ____

RETENTION (fill after you have a Solo baseline for this PRD/tier)
Solo pass rate:    _____%
Marcus pass rate:  _____%
Retention:         _____ (Marcus / Solo)

ARTIFACTS
project_id:        ____________________
JSON report path:  ____________________
tmux session:      ____________________ (if multi-agent)

NOTES / ANOMALIES
________________________________________________________________
________________________________________________________________
```

### Step 7 — Archive the Run

```bash
# Compress the full run for sharing
cd ~/marcusbench-runs
tar -czf $EXPERIMENT_ID.tar.gz $EXPERIMENT_ID/

# Share with the team (upload to shared location or attach to issue #210)
```

---

## Parallel Experiments (Running Multiple Conditions Simultaneously)

For contributors with powerful machines, run conditions B/C/D/E in parallel.
PR #400 (feat/parallel-experiment-platform) enables this.

```bash
# Configure 3 parallel Marcus instances
cp dev-tools/experiments/marcus_instances.example.json marcus_instances.json
# Edit ports if needed (default: 4298, 4299, 4300)

# Start all 3 Marcus instances
./marcus start --port 4298 --db ./data/kanban_parallel_0.db &
./marcus start --port 4299 --db ./data/kanban_parallel_1.db &
./marcus start --port 4300 --db ./data/kanban_parallel_2.db &

# Run comparison (reads marcus_instances.json)
python dev-tools/experiments/runners/run_comparison_experiment.py \
  --prd ./prd.md \
  --parallel \
  --max-parallel 3 \
  --instances-file ./marcus_instances.json

# Each instance gets its own isolated SQLite DB — no cross-contamination
```

---

## Quality Gates

Do not record a run as valid unless ALL of these pass:

- [ ] Experiment ID is unique (new directory, not reused)
- [ ] Model config recorded BEFORE running (not inferred after)
- [ ] Wall clock time was measured with an actual timer (not estimated)
- [ ] Test suite ran to completion without being interrupted
- [ ] Epictetus produced all 3 artifacts (JSON + MD + index)
- [ ] No manual code edits were made to agent output before scoring
- [ ] Any interruptions or anomalies are documented in Notes section

**If an experiment fails mid-run**: mark it `ABORTED` in the tracking sheet,
note the reason, and start a fresh run with a new `$EXPERIMENT_ID`.

---

## Computing Retention (After Collecting Data)

Once you have a Solo baseline (Condition A) AND at least one Marcus condition
(B/C/D/E) for the same PRD tier:

```python
# retention.py
import json, pathlib

def compute_retention(solo_test_results: str, marcus_test_results: str) -> float:
    """Compute retention = Marcus_pass_rate / Solo_pass_rate."""
    solo = json.loads(pathlib.Path(solo_test_results).read_text())
    marcus = json.loads(pathlib.Path(marcus_test_results).read_text())

    solo_rate = solo["summary"]["passed"] / solo["summary"]["total"]
    marcus_rate = marcus["summary"]["passed"] / marcus["summary"]["total"]

    print(f"Solo pass rate:   {solo_rate:.1%}")
    print(f"Marcus pass rate: {marcus_rate:.1%}")
    print(f"Retention:        {marcus_rate / solo_rate:.3f}")
    return marcus_rate / solo_rate
```

---

## Experiment Backlog and Claim Sheet

**Instructions**: Before starting, add your name to the row you are claiming.
One person per cell. Leave unclaimed rows blank.

### Tier 2 — Diamond DAG (datetime-api PRD, existing baseline)

| Condition | Claimed By | Status | Experiment ID | Retention |
|-----------|-----------|--------|--------------|-----------|
| A: Solo | *(baseline exists: 21.37 min)* | ✅ done | datetime-api-marcus-2025-10-23 | 1.0 (baseline) |
| B: Marcus 1w | | | | |
| C: Marcus 2w | | | | |
| D: Marcus 4w | | | | |
| E: Marcus 6w | | | | |

### Tier 1 — Wide Fan-Out (PRD needs writing first)

| Condition | Claimed By | Status | Experiment ID | Retention |
|-----------|-----------|--------|--------------|-----------|
| A: Solo | | ⬜ PRD needed | | |
| B: Marcus 1w | | ⬜ PRD needed | | |
| C: Marcus 2w | | ⬜ PRD needed | | |
| D: Marcus 4w | | ⬜ PRD needed | | |
| E: Marcus 6w | | ⬜ PRD needed | | |

### Tier 3 — Sequential Chain (PRD needs writing first)

| Condition | Claimed By | Status | Experiment ID | Retention |
|-----------|-----------|--------|--------------|-----------|
| A: Solo | | ⬜ PRD needed | | |
| B: Marcus 1w | | ⬜ PRD needed | | |
| D: Marcus 4w | | ⬜ PRD needed | | |

### Tier 4 — Conflict-by-Design (PRDs need writing first)

| Condition | Claimed By | Status | Experiment ID | Retention |
|-----------|-----------|--------|--------------|-----------|
| A: Solo | | ⬜ PRD needed | | |
| B: Marcus 1w | | ⬜ PRD needed | | |
| D: Marcus 4w | | ⬜ PRD needed | | |

---

## PRD Writing Guide

A MarcusBench PRD is not a product document — it is a **controlled experiment
stimulus**. Every word is a lever that changes what Marcus decomposes, how many
tasks it creates, and whether agents collide or cooperate. This guide explains
how to write one that produces valid, reproducible research data.

---

### How Marcus Reads a PRD

Understanding Marcus's parser prevents you from accidentally writing something
that produces garbage decomposition.

Marcus extracts these fields from any PRD it receives:

| Field | What Marcus Does With It |
|-------|--------------------------|
| **Features** | Each becomes one or more tasks on the kanban board |
| **Acceptance criteria** | Injected into each task's description as success gates |
| **Technical notes** | Inform the orchestrator's design phase |
| **Tech stack** | Filters which libraries and patterns agents choose |
| **Dependencies between features** | Informs the dependency graph (DAG) |
| **Priority** | Affects task ordering when agents pull from the board |

Marcus uses **two decomposition strategies** and auto-selects between them
(issue #382):

- **Feature-based**: Each feature → independent tasks. Best for loosely-coupled
  work (Tier 1, Tier 2).
- **Contract-first**: Generates interface contracts between domains before
  splitting tasks. Best for tightly-coupled work (Tier 3, Tier 4). Prevents
  the "Single-Author Product" failure where one agent absorbs all the work.

**You do not control which strategy Marcus picks.** Write the PRD accurately
and let Marcus choose. If you want to force a strategy for ablation purposes,
use the `--decomposer` flag when running.

---

### Anatomy of a Valid MarcusBench PRD

Every PRD must have all seven sections. Missing sections cause Marcus to
hallucinate requirements or produce an under-specified DAG.

```markdown
# PRD: [Descriptive Name] ([Tier N] — [Tier Label])

## Benchmark Metadata
- **Tier**: N (1=Fan-out | 2=Diamond | 3=Chain | 4=Conflict)
- **Coordination trap**: [one sentence — what makes this hard for agents]
- **Shared resources**: [list files/modules multiple agents must touch, or "none"]
- **Expected DAG shape**: [fan-out | diamond | chain | conflict]

## Overview
[2–4 sentences. What is being built and why. No implementation details here.
Marcus uses this to name the project and anchor the design phase.]

## Goals
- [Concrete, verifiable goal 1]
- [Concrete, verifiable goal 2]
- [Concrete, verifiable goal 3]
[3–5 goals. Each must map to at least one test case in your test suite.]

## Features

### Feature A: [Name]
**Priority**: high | medium | low
**Complexity**: low | medium | high
**Dependencies**: [none | "requires Feature B"]
**Shared resources**: [none | filename(s)]

[2–4 sentences describing what this feature does. Be specific about inputs,
outputs, and behavior. Ambiguity here produces unreliable experiments — if
two different agents can legitimately build two different things from this
description, the test suite will be unpredictable.]

**Acceptance criteria**:
- [ ] [Specific, testable criterion — e.g., "GET /api/date returns 200 with ISO date"]
- [ ] [Specific, testable criterion]
- [ ] [Specific, testable criterion]

**Technical notes**:
- [Any constraint Marcus should know: library to use, interface to honor,
  pattern to follow. Do NOT over-specify — agents must retain implementation
  freedom or the multi-agency test is invalid.]

### Feature B: [Name]
[same structure]

[Repeat for all features. Tier 1: 4–6 independent features.
Tier 2: 3–4 features with one integration point. Tier 3: 4–5 features in a
pipeline. Tier 4: 3–4 features with explicit shared-file conflicts.]

## Tech Stack
- **Language**: Python 3.11+
- **Framework**: [e.g., FastAPI, Flask, click — be specific]
- **Testing**: pytest
- **Other**: [any specific libraries required]

[Keep this minimal. Every library you mandate is a constraint that narrows the
test. Only specify what is necessary for the test suite to work.]

## Non-Functional Requirements
- [Performance: e.g., "endpoints must respond in < 200ms"]
- [Structure: e.g., "each feature must live in its own module"]
- [Compatibility: e.g., "must run with Python 3.11"]

[1–3 requirements. These feed into Epictetus's correctness and performance
dimensions. Do not add requirements you cannot test.]

## Success Metrics
- All tests in `tests/` pass with 100% of defined test cases
- Epictetus code quality score ≥ 3.0 / 5
- [Any domain-specific metric, e.g., "API response time < 200ms on localhost"]

## Deliverables
[Exhaustive list. Agents use this as their completion checklist. Every item
here should correspond to at least one test assertion.]

- [ ] `src/[feature_a_module].py` — Feature A implementation
- [ ] `src/[feature_b_module].py` — Feature B implementation
- [ ] `tests/test_[feature_a].py` — Feature A test suite
- [ ] `tests/test_[feature_b].py` — Feature B test suite
- [ ] `tests/test_integration.py` — cross-feature integration tests
- [ ] `requirements.txt`
- [ ] `README.md` with setup instructions and curl examples for every endpoint
```

---

### Tier-by-Tier Writing Guide

#### Tier 1 — Wide Fan-Out

**Goal**: All features are fully independent. No feature depends on another.
The coordination test is whether Marcus realizes the parallelism or serializes
unnecessarily.

**What to write**:
- 4–6 features with `Dependencies: none` on every one
- No shared files between features (each feature gets its own module)
- Features can be thematically related (same project) but structurally isolated

**Good example**: A CLI toolkit with independent subcommands — `convert`,
`validate`, `summarize`, `format`. Each subcommand reads stdin, writes stdout,
touches no shared state.

**Bad example**: Anything where "Feature B needs the data model from Feature A."
That is a Tier 2 or 3, not a Tier 1.

**Epictetus signal to watch**: `dag_shape` should be `wide_fan_out`.
`contribution_distribution.verdict` should be `Balanced`. If it's
`Single-Author Product`, the PRD accidentally encoded a hidden dependency.

---

#### Tier 2 — Diamond DAG

**Goal**: Multiple features work in parallel and then converge at one
integration point. This is the most common real-world project shape.

**What to write**:
- 1 foundation feature (no dependencies)
- 2–3 parallel features (each depends on the foundation)
- 1 integration feature (depends on all parallel features)
- No shared files between the parallel features (they share the foundation
  but don't touch each other)

**Structure**:
```
Foundation (no deps)
    ├── Feature B (depends on Foundation)
    ├── Feature C (depends on Foundation)
    └── Feature D (depends on Foundation)
              └── Integration (depends on B + C + D)
```

**Example**: A weather dashboard. Foundation = shared data models.
B = weather-fetching module. C = time-display module. D = location service.
Integration = the dashboard that wires them together.

**The datetime-api PRD is a Tier 2**: Design phases (foundation) → parallel
implementation phases → integration testing.

---

#### Tier 3 — Sequential Chain

**Goal**: Features form a pipeline where each stage consumes the output of
the previous. Tests whether Marcus correctly enforces handoff fidelity and
whether agents build to the right interface.

**What to write**:
- 4–5 features in a strict linear chain
- Each feature has `Dependencies: [previous feature]`
- Each feature produces an output that the next feature consumes
- The interface between stages must be explicit in acceptance criteria

**Critical**: **Specify the interface contract between stages explicitly.**
If you write "Stage B processes the output of Stage A" without defining what
that output looks like, agents will invent incompatible interfaces and the
pipeline will break at the seam. That is a PRD defect, not a coordination
failure worth measuring.

**Structure**:
```
Ingest → Validate → Transform → Enrich → Output
```

**Example**: A data pipeline. Ingest reads CSV, Validate checks schema,
Transform normalizes fields, Enrich adds derived columns, Output writes JSON.
Each stage has a typed interface (row schema) that the next stage must honor.

---

#### Tier 4 — Conflict-by-Design

**Goal**: Multiple features intentionally require modifying the same file or
module. Without coordination, agents overwrite each other. Tests whether
Marcus's board-mediated coordination prevents work overlap.

**What to write**:
- 3–4 features that explicitly share one or more files
- Name the shared files in `## Benchmark Metadata` and in each feature's
  `Shared resources` field
- Make the conflict inevitable — if an agent can implement its feature WITHOUT
  touching the shared file, the conflict trap doesn't fire

**Naming the shared resource explicitly** is intentional — real users would
name these files too. The test is not whether Marcus can infer conflicts, it's
whether the board substrate prevents them when they're known.

**Structure**:
```
Feature A: implements auth middleware → touches src/middleware.py
Feature B: implements rate limiting   → touches src/middleware.py
Feature C: implements request logging → touches src/middleware.py
```

**Example**: A web API with auth, rate-limiting, and request logging — all
three register middleware in the same file. Or a config system where three
providers (env vars, file, defaults) must all merge into the same `Config`
class.

**Epictetus signal to watch**: `coordination_failures` — each failure should
have `root_cause: bad_coordination` if Marcus failed, or the list should be
empty if coordination succeeded. If failures show `root_cause: bad_spec`,
the PRD was too ambiguous.

---

### Writing the Test Suite

The test suite is the **scoring oracle**. Pass rate is the primary MarcusBench
metric. A bad test suite invalidates the entire experiment.

**Rules**:

1. **Tests must be runnable on a clean install.** Run `pip install -r
   requirements.txt && pytest tests/` in a fresh virtualenv before committing
   the PRD. If it fails, fix the test before adding it to the library.

2. **Tests must test behavior, not structure.** Avoid `assert os.path.exists("src/feature_a.py")` — that is a file check, not a behavior test. Test that
   `GET /api/feature-a` returns 200. Test that `feature_a.compute(x)` returns
   the correct value.

3. **Tests must be deterministic.** No tests that depend on wall clock time
   beyond ±1 second, network access, or random state. If you need time, mock
   it. Agents cannot control non-determinism and it will inflate variance
   across runs.

4. **Tests must be independent.** No test should require another test to run
   first. Use fixtures for shared state, not module-level globals.

5. **Test the integration point.** For Tier 2 and above, at least 20% of
   tests should be integration tests that verify features work together, not
   just individually.

6. **Do not over-test.** 20–40 tests per PRD is the target. Too few and the
   pass rate is noisy (1 failure = 10% swing). Too many and you are testing
   implementation details that differ legitimately between runs.

**Minimal test structure**:

```python
# tests/test_feature_a.py
"""Tests for Feature A — [what it does]."""
import pytest
from [project_module] import [feature_a]


class TestFeatureAHappyPath:
    """Core behavior tests."""

    def test_[behavior]_returns_[expected](self):
        """[Feature A] [behavior] should return [expected]."""
        result = feature_a.[method]([input])
        assert result == [expected]

    def test_[behavior]_with_[edge_case](self):
        """[Feature A] handles [edge case] correctly."""
        result = feature_a.[method]([edge_input])
        assert result == [edge_expected]


class TestFeatureAErrorHandling:
    """Error path tests."""

    def test_[invalid_input]_raises_[exception](self):
        """[Feature A] raises [Exception] for [invalid input]."""
        with pytest.raises([ExpectedException]):
            feature_a.[method]([bad_input])


# tests/test_integration.py  (Tier 2+ only)
"""Integration tests verifying features work together."""

class TestFeatureIntegration:
    """Cross-feature behavior tests."""

    def test_[feature_a]_output_compatible_with_[feature_b]_input(self):
        """Feature A output format is accepted by Feature B."""
        output_a = feature_a.[method]([input])
        result_b = feature_b.[method](output_a)  # must not raise
        assert result_b is not None
```

---

### Validation Checklist Before Submitting a PRD

Run through this before adding a PRD to the library. If any item fails,
the PRD is not ready.

**Content**
- [ ] All 7 sections present (Metadata, Overview, Goals, Features, Tech Stack,
      NFRs, Success Metrics, Deliverables)
- [ ] Every goal maps to at least one test case
- [ ] Every acceptance criterion is testable (not "it should be fast")
- [ ] Shared resources named explicitly (or "none" for Tier 1/2)
- [ ] Feature dependencies accurately reflect the tier's DAG shape

**Test Suite**
- [ ] `pip install -r requirements.txt && pytest tests/ -v` passes on clean install
- [ ] Tests test behavior, not file existence
- [ ] All tests are deterministic (no uncontrolled randomness or real network calls)
- [ ] At least one integration test for Tier 2+
- [ ] 20–40 total tests

**Research Validity**
- [ ] Tier label matches the actual DAG shape (would a human draw the same graph?)
- [ ] The coordination trap description is accurate (is the conflict real or
      avoidable with a different implementation?)
- [ ] The PRD does not mandate a specific implementation (agents must have
      freedom or multi-agency is not being tested)
- [ ] You ran Marcus on it once and confirmed the decomposition makes sense
      (run `--dry-run` or inspect the kanban board after project creation)

---

### Anti-Patterns

**Over-specification**
```markdown
# BAD: This tells agents exactly which class to write
## Technical notes:
- Create a `DateTimeService` class with `get_date()` and `get_time()` methods
- Use `datetime.now().isoformat()` in `get_date()`
```
Two agents given the same spec must be able to produce legitimately different
implementations. If the PRD dictates the implementation, you are testing whether
agents can copy instructions, not whether multi-agent coordination produces
better outcomes.

**Hidden dependencies in Tier 1 PRDs**
```markdown
# BAD: Feature B secretly depends on Feature A
### Feature B: User authentication
...
- Uses the User model from Feature A's database setup
```
This is a Tier 2 or 3 PRD masquerading as a Tier 1. The DAG will not be the
wide fan-out you expected, and the retention measurement will be measuring
the wrong thing.

**Untestable acceptance criteria**
```markdown
# BAD: "clean" is not testable
- [ ] Code is clean and well-organized
- [ ] Error messages are friendly

# GOOD: specific and testable
- [ ] GET /api/date returns 200 with body {"date": "[YYYY-MM-DD]"}
- [ ] GET /api/date with invalid param returns 400 with body {"error": "[message]"}
```

**Tests that mirror the deliverables list**
```python
# BAD: This is a file check, not a behavior test
def test_feature_a_file_exists():
    assert os.path.exists("src/feature_a.py")
```
File existence tests cannot fail even if the file is empty. They inflate the
pass rate without measuring correctness.

**Conflict traps that are avoidable**
```markdown
# BAD: Agents can dodge this conflict
### Feature A: Auth middleware
- Shared resources: src/middleware.py

### Feature B: Rate limiting
- Shared resources: src/middleware.py
# If agents are smart, Feature B just imports from Feature A.
# No conflict. The trap doesn't fire.
```
For Tier 4, the conflict must be structurally unavoidable. Both features must
register with the same hook, modify the same class, or write to the same config
key. If a clever agent can implement their feature without touching the shared
file, the conflict is optional and the measurement is invalid.

---

## Troubleshooting

### Marcus won't start
```bash
# Check port isn't in use
lsof -i :4298
# Check logs
./marcus start --verbose
```

### Agents get stuck / no tasks assigned
```bash
# Check board state
curl http://localhost:4298/mcp/project_status | python3 -m json.tool
# Check for dependency cycles
sqlite3 data/kanban.db "SELECT * FROM task_dependencies"
```

### Epictetus can't find kanban.db
```bash
# Verify db location
python3 -c "from pathlib import Path; import marcus_mcp; print(Path(marcus_mcp.__file__).parent.parent.parent / 'data')"
```

### Tests fail immediately (not agent failures)
- Check agent output directory exists and has files
- Check `requirements.txt` was created by agents and installed
- Check Python version matches what agents used

### Parallel instances interfering
- Verify each instance has a distinct `db_path` in the instances JSON
- Verify each instance is using a different port (4298, 4299, 4300)
- Check `MARCUS_URL` env var is set per-instance by the runner

---

## Experiment Logs (Append After Each Run)

```
────────────────────────────────────────────────────────
DATE:
EXPERIMENTER:
ID:
TIER / CONDITION:
MODEL:
WALL CLOCK:
PASS RATE:
RETENTION:
EPICTETUS (code / coord / contrib):
NOTES:
────────────────────────────────────────────────────────
```
