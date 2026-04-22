# Marcus Overhead Study: Scorecard

**Research question:** Under what conditions does Marcus's coordination overhead pay
off versus a single agent?

**Two-track design:** Track 1 measures complexity scaling. Track 2 measures
coordination correctness. See `overhead-study-protocol.md` for procedures.

---

## Track 1 — Complexity Scaling

### Descriptions Used (verbatim — do not vary)

| N | Description |
|---|---|
| 1 | Build a dashboard with a weather widget |
| 2 | Build a dashboard with weather and time widgets |
| 3 | Build a dashboard with weather, time, and calendar widgets |
| 4 | Build a dashboard with weather, time, calendar, and notifications |
| 5 | Build a dashboard with weather, time, calendar, notifications, and user settings |

---

### Raw Timing (Track 1)

| N | Single Agent Time | Marcus Time (2 agents) | Marcus / Single Ratio |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |

---

### Correctness — does it work on first open, no manual fixes (Track 1)

| N | Single Agent | Marcus |
|---|---|---|
| 1 | pass / fail | pass / fail |
| 2 | pass / fail | pass / fail |
| 3 | pass / fail | pass / fail |
| 4 | pass / fail | pass / fail |
| 5 | pass / fail | pass / fail |

---

### Defects Found — count of broken things before any fixing (Track 1)

| N | Single Agent | Marcus |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

---

### Extension Cost — time to add N+1 feature to N output (Track 1)

| N→N+1 | Single Agent Extension Time | Marcus Delta (N+1 run − N run) |
|---|---|---|
| 1→2 | | |
| 2→3 | | |
| 3→4 | | |
| 4→5 | | |

**Single agent extension notes** (did agent rewrite existing code? did all N+1 features work?):

| N→N+1 | Rewrote existing code? | All N+1 features working? |
|---|---|---|
| 1→2 | yes / no | yes / no |
| 2→3 | yes / no | yes / no |
| 3→4 | yes / no | yes / no |
| 4→5 | yes / no | yes / no |

---

### Epictetus Scores (Track 1)

#### Single Agent

| N | Architecture | Correctness | Completeness | Testing | Extensibility | Overall |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |

#### Marcus

| N | Architecture | Correctness | Completeness | Testing | Extensibility | Overall |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |

---

### Epictetus Interview Responses (Track 1)

**Q1:** How long to add N+1 widget with no prior context?
**Q2:** Are widgets independent or coupled?
**Q3:** Is there a shared pattern a new widget could plug into?

| Run | Q1 | Q2 | Q3 |
|---|---|---|---|
| SA-N1 | | | |
| SA-N2 | | | |
| SA-N3 | | | |
| SA-N4 | | | |
| SA-N5 | | | |
| M-N1 | | | |
| M-N2 | | | |
| M-N3 | | | |
| M-N4 | | | |
| M-N5 | | | |

---

## Track 2 — Coordination Correctness

### Project Description (verbatim)

Build a real-time analytics dashboard with:
- A Python FastAPI backend that serves historical data via REST endpoints
- A WebSocket server for streaming live data updates
- A React frontend that displays data from both REST and WebSocket
- A user preferences service (store and retrieve per-user display settings)

The frontend must integrate with all three backend services.

---

### Raw Timing (Track 2)

| Run | Wall Clock Time |
|---|---|
| Single Agent | |
| Marcus 2 Agents | |
| Marcus 3 Agents | |

---

### Integration Verification Results (Track 2)

Count of failures per run (0 = fully integrated, 8 = nothing works together).

#### Single Agent

| Check | Pass / Fail |
|---|---|
| Frontend calls FastAPI endpoints (correct URL + method) | |
| Frontend uses correct field names (no schema mismatches) | |
| Error responses handled (not just happy path) | |
| Frontend connects to WebSocket server | |
| Frontend handles live data message format | |
| Reconnect behavior exists | |
| Frontend loads preferences on startup | |
| Frontend saves preferences on change | |

**Integration failure count:** __ / 8

#### Marcus 2 Agents

| Check | Pass / Fail |
|---|---|
| Frontend calls FastAPI endpoints (correct URL + method) | |
| Frontend uses correct field names (no schema mismatches) | |
| Error responses handled (not just happy path) | |
| Frontend connects to WebSocket server | |
| Frontend handles live data message format | |
| Reconnect behavior exists | |
| Frontend loads preferences on startup | |
| Frontend saves preferences on change | |

**Integration failure count:** __ / 8

#### Marcus 3 Agents

| Check | Pass / Fail |
|---|---|
| Frontend calls FastAPI endpoints (correct URL + method) | |
| Frontend uses correct field names (no schema mismatches) | |
| Error responses handled (not just happy path) | |
| Frontend connects to WebSocket server | |
| Frontend handles live data message format | |
| Reconnect behavior exists | |
| Frontend loads preferences on startup | |
| Frontend saves preferences on change | |

**Integration failure count:** __ / 8

---

### Cross-Service Schema Consistency (Track 2)

| Check | Single Agent | Marcus 2 | Marcus 3 |
|---|---|---|---|
| REST and WebSocket use consistent field names | pass / fail | pass / fail | pass / fail |
| All services start without port conflicts | pass / fail | pass / fail | pass / fail |
| Shared API contract document exists | yes / no | yes / no | yes / no |

---

### Epictetus Scores (Track 2)

| Run | Architecture | Correctness | Completeness | Testing | Extensibility | Overall |
|---|---|---|---|---|---|---|
| Single Agent | | | | | | |
| Marcus 2 Agents | | | | | | |
| Marcus 3 Agents | | | | | | |

---

### Epictetus Interview Responses (Track 2)

**Q1:** Which integration points are explicitly tested vs assumed?
**Q2:** If a field name changed in FastAPI, how many files change and how do you find them?
**Q3:** Is there a shared API contract document all services reference?

| Run | Q1 | Q2 | Q3 |
|---|---|---|---|
| Single Agent | | | |
| Marcus 2 Agents | | | |
| Marcus 3 Agents | | | |

---

## Summary Analysis

### Track 1 Crossover Points

**Time crossover** (N where Marcus total time ≤ single agent total time): TBD

**Quality crossover** (N where Marcus Epictetus score > single agent score): TBD

**Extension crossover** (N where Marcus marginal cost < single agent extension time): TBD

### Track 2 Findings

**Integration failures: Single Agent vs Marcus:** TBD

**Does Marcus catch mismatches that single-agent ships?** TBD

### Key Finding

TBD

---

## Experiment Directories

### Track 1

| Run | Directory |
|---|---|
| SA-N1 | ~/experiments/overhead-study/track1/single-agent/n1 |
| SA-N2 | ~/experiments/overhead-study/track1/single-agent/n2 |
| SA-N3 | ~/experiments/overhead-study/track1/single-agent/n3 |
| SA-N4 | ~/experiments/overhead-study/track1/single-agent/n4 |
| SA-N5 | ~/experiments/overhead-study/track1/single-agent/n5 |
| M-N1 | ~/experiments/overhead-study/track1/marcus/n1 |
| M-N2 | ~/experiments/overhead-study/track1/marcus/n2 |
| M-N3 | ~/experiments/overhead-study/track1/marcus/n3 |
| M-N4 | ~/experiments/overhead-study/track1/marcus/n4 |
| M-N5 | ~/experiments/overhead-study/track1/marcus/n5 |

### Track 2

| Run | Directory |
|---|---|
| Single Agent | ~/experiments/overhead-study/track2/single-agent |
| Marcus 2 Agents | ~/experiments/overhead-study/track2/marcus-2 |
| Marcus 3 Agents | ~/experiments/overhead-study/track2/marcus-3 |
