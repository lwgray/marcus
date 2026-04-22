# Marcus Overhead Study — Experimental Protocol

**Research question:** Under what conditions does Marcus's coordination overhead pay
off versus a single agent, measured in wall-clock time, output correctness, integration
correctness, and extension cost?

**Status:** Protocol v2.0 — two-track design. Run Track 1 first (N=1 and N=2 only)
before committing to the full suite.

---

## Why Two Tracks

The original single-track design ("vanilla JS single HTML") set Marcus up to fail:
a single-file constraint eliminates file separation, API contracts, and shared
components — exactly the coordination artifacts Marcus produces. You'd be measuring
Marcus's overhead against a problem that structurally disallows its value proposition.

**Track 1 — Complexity Scaling** answers: at what feature count does Marcus's quality
exceed single-agent quality, and is there a crossover on time?

**Track 2 — Coordination Correctness** answers: does Marcus catch integration failures
that single-agent misses, and is the output correct end-to-end without manual fixing?

Track 1 uses Epictetus for scoring. Track 2 uses binary integration outcomes.
Both are required for an honest finding.

---

## Greenfield Constraint

Marcus cannot append features to existing projects. All Marcus runs start fresh.
Extension cost for Marcus = time delta between consecutive N-level runs (Track 1),
not modification of existing output.

Single-agent extension tests (Track 1, Part C) run a fresh agent against existing
files in-place.

---

## Track 1 — Complexity Scaling

### Descriptions (use verbatim — do not rephrase)

| N | Prompt |
|---|---|
| 1 | `Build a dashboard with a weather widget` |
| 2 | `Build a dashboard with weather and time widgets` |
| 3 | `Build a dashboard with weather, time, and calendar widgets` |
| 4 | `Build a dashboard with weather, time, calendar, and notifications` |
| 5 | `Build a dashboard with weather, time, calendar, notifications, and user settings` |

No architecture constraint. Agents choose their own structure.

### Setup

```bash
mkdir -p ~/experiments/overhead-study/track1/single-agent/{n1,n2,n3,n4,n5}
mkdir -p ~/experiments/overhead-study/track1/marcus/{n1,n2,n3,n4,n5}
```

---

### Part A — Single Agent Runs (Track 1)

Run N1 through N5 in order. Each run is a fresh Claude Code session with no
prior context.

**For each N:**

```bash
# 1. Go to the run directory
cd ~/experiments/overhead-study/track1/single-agent/nN   # replace N

# 2. Record start time
date > run_log.txt

# 3. Run the agent — capture wall clock
time claude --dangerously-skip-permissions \
  -p "PROMPT_FOR_N. When you are finished and everything works, exit."

# 4. Record end time and elapsed
date >> run_log.txt
# Copy the time output into run_log.txt
```

**Immediately after each run:**

```bash
# Open the output
open index.html 2>/dev/null || python3 -m http.server 8080 &

# Count output files
find . -not -path './.git/*' -type f | wc -l >> run_log.txt

# Check for tests
ls test* tests/ *test* 2>/dev/null >> run_log.txt
```

Fill in the Track 1 single-agent rows of the scorecard before running the next N.

---

### Part B — Marcus Runs (Track 1)

Run N1 through N5 in order. Use 2 agents.

**For each N:**

```bash
# 1. Go to the run directory
cd ~/experiments/overhead-study/track1/marcus/nN   # replace N

# 2. Record start time
date > run_log.txt

# 3. Start Marcus session
time claude --dangerously-skip-permissions
```

Inside Claude Code:

```
/marcus PROMPT_FOR_N using 2 agents
```

Wait for completion. Then:

```bash
# 4. Record end time
date >> run_log.txt
# Copy time output into run_log.txt

# Check integration verification result
cat project_info.json

# Count files
find . -not -path './.git/*' -type f | wc -l >> run_log.txt
```

Fill in the Track 1 Marcus rows of the scorecard before running the next N.

---

### Part C — Extension Cost (Track 1)

Run after Parts A and B are complete.

**Single-agent extension:** For each N from 1 to 4, take the existing single-agent
output and ask a fresh agent to add the N+1 feature in-place:

```bash
cd ~/experiments/overhead-study/track1/single-agent/nN

time claude --dangerously-skip-permissions \
  -p "This is an existing dashboard project. Review the current files, then add
  [FEATURE_N+1] to the dashboard. The existing features must continue to work.
  When done, exit."
```

Record: time elapsed, did all N+1 features work, did the agent rewrite existing
code to fit the new feature.

**Marcus extension:** No additional runs. Calculate from recorded timestamps:

```
Marcus extension cost (N → N+1) = Marcus N+1 run time − Marcus N run time
```

---

### Part D — Epictetus Audit (Track 1)

Run Epictetus on all 10 output directories after Parts A, B, and C.

```bash
cd ~/experiments/overhead-study/track1/single-agent/nN
/epictetus --session   # if tmux session still alive
# or
/epictetus             # code-only audit
```

```bash
cd ~/experiments/overhead-study/track1/marcus/nN
/epictetus --session
```

#### Mandatory Interview Questions

Include these three questions in every run's interview phase:

```
X. If a developer needed to add one more widget to this dashboard tomorrow
   with no prior context about this codebase, what would they need to
   understand first and roughly how long would that orientation take?

X. Are the widgets implemented as independent units that could be removed
   individually, or are they coupled together in ways that would require
   touching shared code to modify any single widget?

X. Is there a shared pattern (API client, container structure, CSS system)
   that a new widget could plug into, or would a new widget need to invent
   its own approach from scratch?
```

#### Dimensions to Watch

- **Dimension 1 (Architecture)** — component structure, coupling
- **Dimension 3 (Correctness)** — are all N widgets actually functional
- **Dimension 4 (Completeness)** — are all N widgets present
- **Dimension 5 (Testing)** — single agent likely skips, Marcus enforces TDD
- **Dimension 9 (Maintainability/Extensibility)** — direct measure of extension cost

---

## Track 2 — Coordination Correctness

This is the real test. Track 2 uses a genuinely multi-domain project where parallel
workstreams must produce compatible artifacts. It validates Marcus's integration
verification and contract enforcement, not just speed.

### Project Description (use verbatim)

```
Build a real-time analytics dashboard with:
- A Python FastAPI backend that serves historical data via REST endpoints
- A WebSocket server for streaming live data updates
- A React frontend that displays data from both REST and WebSocket
- A user preferences service (store and retrieve per-user display settings)
The frontend must integrate with all three backend services. Use realistic
mock data — no external API calls required.
```

This project has four domains with real API contracts between them. Single agents
routinely ship mismatched endpoints, wrong field names, or a frontend that only
integrates with one backend service. Marcus's integration verification phase is
designed to catch exactly these failures.

### Setup

```bash
mkdir -p ~/experiments/overhead-study/track2/{single-agent,marcus-2,marcus-3}
```

### Runs

#### Run SA — Single Agent

```bash
cd ~/experiments/overhead-study/track2/single-agent

date > run_log.txt
time claude --dangerously-skip-permissions \
  -p "PROMPT_ABOVE. When you are finished and everything works, exit."
date >> run_log.txt
```

#### Run M2 — Marcus, 2 Agents

```bash
cd ~/experiments/overhead-study/track2/marcus-2

date > run_log.txt
time claude --dangerously-skip-permissions
```

Inside Claude Code:

```
/marcus PROMPT_ABOVE using 2 agents
```

```bash
date >> run_log.txt
```

#### Run M3 — Marcus, 3 Agents

```bash
cd ~/experiments/overhead-study/track2/marcus-3

date > run_log.txt
time claude --dangerously-skip-permissions
```

Inside Claude Code:

```
/marcus PROMPT_ABOVE using 3 agents
```

```bash
date >> run_log.txt
```

---

### Integration Verification Checklist (Track 2)

After each run, manually verify each integration point. Record pass/fail per item.

**REST API integration:**
- [ ] Frontend can call the FastAPI endpoints (correct URL, correct method)
- [ ] Frontend sends and receives correct field names (no schema mismatches)
- [ ] Error responses are handled (not just happy path)

**WebSocket integration:**
- [ ] Frontend connects to the WebSocket server successfully
- [ ] Frontend handles the live data message format correctly
- [ ] Reconnect behavior exists

**User preferences integration:**
- [ ] Frontend calls the preferences service to load settings on startup
- [ ] Frontend saves settings when the user changes them
- [ ] Settings persist across a page refresh (or equivalent)

**Cross-service correctness:**
- [ ] REST data and WebSocket data use consistent schemas
- [ ] All four services can start and run simultaneously without port conflicts

Record the count of failures (0 = fully integrated, 8 = nothing works together).

---

### Epictetus Audit (Track 2)

Run Epictetus on all three Track 2 output directories.

```bash
cd ~/experiments/overhead-study/track2/single-agent
/epictetus --session

cd ~/experiments/overhead-study/track2/marcus-2
/epictetus --session

cd ~/experiments/overhead-study/track2/marcus-3
/epictetus --session
```

#### Mandatory Interview Questions (Track 2)

```
X. Which integration points between services are explicitly tested, and which
   are assumed to work based on the implementation alone?

X. If the FastAPI team changed a response field name, how many files would
   need to change and how would a developer find them all?

X. Is there a shared API contract document (OpenAPI spec, schema file, or
   equivalent) that all services reference, or did each service define its
   own interface independently?
```

---

## Filling in the Scorecard

Open `overhead-study-scorecard.md` and fill in every cell after each run.
Do not wait until all runs are done — fill as you go.

---

## Run Order Recommendation

1. Track 1, N=1 single agent and Marcus — establishes the baseline overhead
2. Track 1, N=2 single agent and Marcus — first real crossover data point
3. Track 2, all three runs — the coordination correctness test
4. Track 1, N=3 through N=5 — only if N=2 leaves the crossover uncertain

If Track 2 shows Marcus catching integration failures that single-agent misses,
that finding is Marcus's strongest argument and should lead the messaging even
if Track 1 never shows a time crossover.

---

## What to Look For

**If Marcus never recovers the time overhead (Track 1):**
- Valid finding: Marcus is not appropriate for single-domain widget aggregation
- Actionable: implement a complexity gate in `create_project` that skips pre-fork
  synthesis when `recommended_agents = 1`

**If Track 2 shows integration failures in single-agent but not Marcus:**
- This is the result: Marcus's value is integration correctness, not speed
- Reframe positioning: Marcus is for projects where integration bugs are expensive,
  not for simple widget dashboards

**If Track 1 crossover happens by N=3:**
- Earlier than expected; Marcus's shared foundation is paying off
- Foundation tasks (Design System, Tech Foundation) are avoiding rework at N=4+

**If extension cost gap is the largest signal:**
- Single agent output is tightly coupled; Marcus output has shared patterns
- This validates the extensibility story and should inform the roadmap

---

## Files

| File | Purpose |
|---|---|
| `overhead-study-protocol.md` | This file — the procedure |
| `overhead-study-scorecard.md` | Results table — fill as you run |
| `~/experiments/overhead-study/track1/` | Track 1 experiment output |
| `~/experiments/overhead-study/track2/` | Track 2 experiment output |
