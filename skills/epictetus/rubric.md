# Epictetus Rubric v1.1

## Scoring Scale

| Score | Grade | Meaning |
|-------|-------|---------|
| 5 | A | Exemplary — exceeds expectations, no meaningful issues |
| 4 | B | Solid — meets expectations with minor issues |
| 3 | C | Adequate — works but has notable gaps or problems |
| 2 | D | Below standard — significant issues that impair quality |
| 1 | F | Failing — fundamentally broken or missing |

Half-grades (A-, B+, etc.) map to: A=5, A-=4.5, B+=4, B=3.5-4, B-=3.5, C+=3, C=2.5-3, C-=2.5, D+=2, D=1.5-2, D-=1.5, F=1.

---

## Dimension 1: Architecture & Design (Base Weight: 15%)

| Score | Criteria |
|-------|----------|
| 5 | Clean component boundaries, single responsibility, acyclic dependencies, domain-matched abstractions, no over-engineering |
| 4 | Good separation, 1-2 leaky boundaries, minor coupling |
| 3 | Recognizable structure, some god-objects or circular deps |
| 2 | Monolithic or tangled, unclear boundaries, widespread coupling |
| 1 | No architecture, one file or random scatter |

**Check:** Dependency DAG, single responsibility, earned abstractions, swappable components, complexity proportional to problem.

**Process Evidence (if --session):** Did tmux logs show agents struggling with architecture decisions? Were architectural patterns specified in instructions or left to agents? Did workarounds create accidental architecture?

---

## Dimension 2: Code Quality & Craftsmanship (Base Weight: 15%)

| Score | Criteria |
|-------|----------|
| 5 | Consistent style, clear naming, no dead code, no magic values, focused functions |
| 4 | Mostly consistent, 1-2 dead code instances, minor style issues |
| 3 | Readable but inconsistent, some ghost code, scattered magic numbers |
| 2 | Hard to follow, inconsistent naming, significant dead code, duplication |
| 1 | Unreadable, no conventions, pervasive duplication |

**Check:** Ghost code (unused functions, orphaned imports), magic values, naming intent, duplication, function length, style consistency.

**Process Evidence (if --session):** Did tmux logs show copy-paste from earlier attempts that wasn't cleaned up? Did an agent leave debug code after fixing a problem? Does the log explain why ghost code exists?

---

## Dimension 3: Correctness & Reliability (Base Weight: 20%)

| Score | Criteria |
|-------|----------|
| 5 | All specified behavior works, edge cases handled, no race conditions |
| 4 | Core works, most edge cases handled, 1-2 minor issues |
| 3 | Happy path works, several unhandled edge cases |
| 2 | Core partially works, obvious bugs in normal paths |
| 1 | Does not produce correct results, crashes on basic inputs |

**Check:** Spec satisfaction, off-by-one, boundary conditions, race conditions, infinite loops, null access, error propagation, state machine completeness.

**Runtime Smoke Test Impact:** If the app starts but features crash or produce wrong results at runtime, penalize here even if unit tests pass. Tests that mock all external dependencies can hide real correctness failures. Graceful error states for missing external dependencies are correct behavior and should be credited, not penalized.

**Process Evidence (if --session):** Did agent see the error and ship anyway? Did agent misunderstand the spec? Did agent hit a bug, attempt a fix, and introduce a new bug? Was the root cause a bad instruction or bad execution?

---

## Dimension 4: Completeness (Base Weight: 15%)

| Score | Criteria |
|-------|----------|
| 5 | All specified features implemented, sensible defaults, graceful unspecified handling |
| 4 | Core features present, 1-2 minor gaps, feels functional |
| 3 | Most features present, notable gaps, usable but incomplete |
| 2 | Multiple core features missing, half-finished |
| 1 | Only skeleton, minimal functionality |

**Check:** Spec vs implementation cross-reference, TODO/FIXME comments, complete user flows, error states, README feature claims.

**Runtime Smoke Test Impact:** If a feature depends on an external service that was in scope but never built, penalize here. If the dependency was out of scope AND properly documented, no penalty. If the README claims the feature works without mentioning the missing dependency, penalize Documentation instead.

**Process Evidence (if --session):** Did agent run out of time? Did agent get stuck on a prerequisite and never reach later requirements? Was scope unclear in instructions?

---

## Dimension 5: Testing (Base Weight: 10%)

| Score | Criteria |
|-------|----------|
| 5 | Comprehensive suite: happy paths + edge cases + error paths, readable, fast |
| 4 | Good coverage of core flows, some edge cases, organized |
| 3 | Some tests, spotty coverage, possibly brittle |
| 2 | Minimal tests, only smoke/syntax checks disguised as tests |
| 1 | No tests, or "tests" that don't validate behavior |

**Check:** Tests exist? Verify behavior or just syntax? Edge cases tested? Independent and repeatable? Test infrastructure? Trustworthy (fail when broken)? Do tests mock so aggressively that they pass while the real app is broken?

**Runtime Smoke Test Impact:** If all tests pass but the smoke test reveals broken features, flag the test suite as over-mocked. Tests that verify mocked behavior but never test real integration create false confidence. Note this as a testing gap — not necessarily a low score, but a finding that tests are weaker than they appear.

**Process Evidence (if --session):** Did instructions mention testing requirements? Did agent write tests then delete them? Did agent run tests and ignore failures?

---

## Dimension 6: Documentation & Spec Fidelity (Base Weight: 10%)

| Score | Criteria |
|-------|----------|
| 5 | Docs match implementation exactly, clear setup, API documented, no contradictions |
| 4 | Mostly accurate, minor drift, setup works |
| 3 | Notable inaccuracies, some specs describe different behavior than built |
| 2 | Misleading or substantially outdated |
| 1 | No docs, or describes a different project |

**Check:** Architecture docs vs code structure, API specs vs actual signatures, setup instructions from clean state, internal contradictions, data model spec vs actual structures.

---

## Dimension 7: Security (Base Weight: 5%)

| Score | Criteria |
|-------|----------|
| 5 | No vulnerability patterns, boundaries validated, secrets handled, deps audited |
| 4 | No critical vulns, minor hardening opportunities |
| 3 | Some validation missing, edge-case injection potential |
| 2 | Known patterns (XSS, SQLi, command injection), secrets in code |
| 1 | Wide open, credentials committed, no validation |

**Check by type:**
- Web: XSS, innerHTML, CSP, CORS
- API: SQL injection, auth bypass, rate limiting, error leaking
- CLI: Path traversal, command injection
- All: Secrets in code, dependency CVEs

---

## Dimension 8: Performance & Efficiency (Base Weight: 5%)

| Score | Criteria |
|-------|----------|
| 5 | Optimal algorithms, no waste, efficient resources |
| 4 | Good performance, minor opportunities |
| 3 | Acceptable, some unnecessary work |
| 2 | Notable issues, O(n²) where O(n) obvious, memory leaks |
| 1 | Fundamentally inefficient |

**Check:** Algorithmic complexity, redundant computation, memory leaks (listeners, caches), resource cleanup, data structure choices.

---

## Dimension 9: Maintainability & Extensibility (Base Weight: 5%)

| Score | Criteria |
|-------|----------|
| 5 | New dev productive in <1 hour, clear extension points, localized changes |
| 4 | Mostly clear, some areas need surrounding context |
| 3 | Understandable with effort, some hidden deps, changes sometimes cascade |
| 2 | Significant archaeology needed, changes break other areas |
| 1 | Unmaintainable, unpredictable changes |

**Check:** Add feature without modifying existing code? Hidden dependencies? Config separated from logic? Stable interfaces? Flow readable?

---

## Dimension 10: Authorship Cohesiveness (modifier, not weighted)

Produces a verdict, does not add to weighted total. Modifies agent grades.

**Verdicts:**
- **Distinctly Multi-Author** (3+ divergent signals): Healthy. No modifier.
- **Mildly Varied** (1-2 divergent): Acceptable. Note, no penalty.
- **Suspiciously Uniform** (0 divergent): Flag concern. Agents = same LLM? One rewrote all? Strict linter?
- **Jarringly Inconsistent** (divergence within single agent's files): Penalize inconsistent agent(s).

---

## Skill Lens Details

### Web Frontend
| Dimension | Adjustment |
|---|---|
| Architecture | +5% — component hierarchy, state management, prop drilling |
| Performance | +5% — bundle size, render count, layout thrashing |
| Security | -3% — XSS via innerHTML, CSP compliance |
| Accessibility | NEW +5% — semantic HTML, ARIA, keyboard nav, contrast |
| Visual Polish | NEW +3% — responsive, spacing, loading states |

Extra: works without JS? Responsive breakpoints? Loading/empty/error states? Focus management?

### Backend / API
| Dimension | Adjustment |
|---|---|
| Security | +10% — auth, sanitization, rate limiting, SQLi |
| Correctness | +5% — idempotency, concurrency, transactions |
| Testing | +5% — integration tests, contract tests |
| Performance | +5% — query optimization, pooling, caching |

Extra: Parameterized queries? Transactions for mutations? Auth on every protected route? Consistent error responses? Rate limiting?

### CLI Tool
| Dimension | Adjustment |
|---|---|
| Completeness | +5% — help text, exit codes, stdio usage |
| Documentation | +5% — man page/--help, examples per command |
| Correctness | +5% — SIGINT/SIGTERM, pipe-friendly |
| Security | -5% — file permissions, path traversal |

Extra: --help documents all flags? Exit codes (0/1/2)? Works in pipes? Graceful SIGINT? Actionable errors?

### Library / SDK
| Dimension | Adjustment |
|---|---|
| Documentation | +10% — API reference, examples, migration guides |
| Maintainability | +5% — semver, changelog, deprecation |
| Testing | +5% — property-based, compatibility matrix |
| Architecture | +5% — minimal public API, no unnecessary exports |

Extra: Minimal API surface? Types exported? Tree-shakeable? Breaking changes documented? Peer deps correct?

### Data Pipeline / ETL
| Dimension | Adjustment |
|---|---|
| Correctness | +10% — validation, schema enforcement, idempotency |
| Performance | +5% — batch tuning, memory-bounded streaming |
| Reliability | NEW +5% — retry logic, dead letters, checkpoints |
| Observability | NEW +5% — logging, metrics, lineage, row counts |

Extra: Checkpoint resume? Partial output cleanup? Row-count validation? Known input/output test pairs? Schema validation?

### Game
| Dimension | Adjustment |
|---|---|
| Correctness | +5% — state machine validity, collision accuracy |
| Performance | +5% — frame rate stability, input latency |
| Completeness | +5% — win/lose, pause, save state, all screens |
| UX/Polish | NEW +5% — input responsiveness, visual feedback |

---

## Coordination Effectiveness (separate section, not weighted into total)

This section evaluates how well Marcus coordinated multi-agent work. It is
scored independently from code quality because coordination failures are
infrastructure/spec issues, not agent code issues.

### Scoring

| Score | Grade | Meaning |
|-------|-------|---------|
| 5 | A | All agents productive, parallelism maximized, no stuck tasks |
| 4 | B | Minor idle time, parallelism mostly achieved |
| 3 | C | Some agents underutilized, avoidable sequential work |
| 2 | D | Significant idle agents, linear chain where parallel was possible |
| 1 | F | Agent(s) produced nothing, tasks permanently stuck, zero parallelism |

### What to Measure

**Parallelization Metrics:**
- Agents available vs agents that produced work
- Max theoretical parallelism from the DAG (longest path vs graph width)
- Actual parallel tasks observed (overlapping work in timeline)
- Time wasted on retries, idle waits, trust prompts

**Agent Utilization:**
For each agent: tasks completed, active time, idle time, idle reason.
Idle reasons: dependency blocked, retry loop, trust prompt, no tasks available,
lease expired, permanently stuck.

**Dependency Chain Analysis:**
Query the DAG to determine:
- Critical path length (longest sequential chain)
- Maximum parallel width (most tasks available at once)
- Could the task planner have created more parallel work?
- Were dependencies necessary or artificial?

**Coordination Failures:**
Each failure with: duration, root cause, and whether it's fixable.
Root causes: linear dependency chain, lease/state bug, trust prompt delay,
task permanently stuck, agent retry loop with no backoff.

### How to Get DAG Data

```bash
# From kanban.db (if SQLite provider)
MARCUS_ROOT=$(python3 -c "from pathlib import Path; import marcus_mcp; print(Path(marcus_mcp.__file__).parent.parent.parent)")
PROJECT_ID="<from project_info.json or marcus_state/projects.json>"

sqlite3 ${MARCUS_ROOT}/data/kanban.db "
  SELECT t1.name as task, t1.status, t2.name as depends_on
  FROM task_dependencies d
  JOIN tasks t1 ON t1.id = d.task_id
  JOIN tasks t2 ON t2.id = d.depends_on_id
  WHERE t1.project_id = '${PROJECT_ID}'
"

# Task timeline from Cato API (if available)
curl -s http://localhost:4301/api/tasks/${TASK_ID}/conversation
```

If neither source is available, infer from tmux logs: task start/end times,
agent activity patterns, retry messages.

Extra: Game loop decoupled from render? All states reachable/escapable? Win condition? Pause/resume? Collision accuracy at all speeds?

---

## Contribution Distribution (separate section, not weighted into total)

This section answers: **"If you removed this agent's code, would the product still work?"**

Raw line counts and `git blame` are misleading. An agent can write 40% of the
lines in the repo but contribute 0% to the working product if none of their
code is reachable from the application's entry points. This analysis measures
**effective contribution** — code that is actually on the execution path of
the final working product.

### Methodology

**Step 1: Identify Product Entry Points**

Find all entry points that make the product work:
- `main()`, `app.run()`, CLI entry points, route handlers, exported APIs
- Test entry points are tracked separately (test contribution ≠ product contribution)
- Config files, build scripts, and static assets are tracked separately

**Step 2: Reachability Analysis**

From each entry point, trace the call graph through imports, function calls,
and class instantiation to build the set of **reachable code** — every file,
class, function, and line that is on the execution path of the working product.

Code that is NOT reachable from any entry point is **orphaned** — it exists in
the repo but does not contribute to the product. This includes:
- Modules that nothing imports
- Functions/classes that nothing calls or instantiates
- Dead branches behind impossible conditions
- Utility code written but never wired up

**Step 3: Attribute Reachable Code to Agents**

Using `git blame` mapped to agent identities (from Phase 1 contributor inference),
calculate for each agent:
- **Reachable lines**: lines they wrote that are on the execution path
- **Orphaned lines**: lines they wrote that nothing reaches
- **Rewritten lines**: lines they originally wrote that another agent replaced

**Step 4: Calculate Effective Contribution**

For each agent:
```
effective_contribution_pct = (agent_reachable_lines / total_reachable_lines) * 100
```

Also track:
- **Activity share**: % of total commits by this agent (effort expended)
- **Blame share**: % of total lines attributed by git blame (raw output)
- **Effective share**: % of reachable product lines (actual contribution)

The gap between these three numbers tells the story:
- Activity ≈ Blame ≈ Effective → agent's work landed and mattered
- Activity >> Effective → agent was busy but work didn't ship or was replaced
- Blame >> Effective → agent wrote code that's in the repo but orphaned
- Effective >> Activity → agent wrote small but critical glue/wiring code

**Step 5: Contribution Categories**

Not all contribution is product code. Track separately:
- **Product code**: reachable from application entry points
- **Test code**: test files and test utilities
- **Infrastructure**: build scripts, config, CI, Dockerfiles
- **Documentation**: READMEs, docs, comments

An agent whose only contribution is tests or docs is NOT contributing to the
working product — that's a valid but different kind of contribution that should
be called out explicitly.

### Verdicts

| Verdict | Criteria |
|---------|----------|
| **Balanced** | No agent has >70% effective share; all agents have >10% effective share |
| **Lopsided** | One agent has >70% effective share; others contributed but marginally |
| **Single-Author Product** | One agent has >90% effective share; multi-agency did not produce multi-authored output |
| **Complementary** | Agents contributed to different categories (e.g., one did product code, one did tests) — note this explicitly as it may or may not be intentional |

### What This Means for Multi-Agency

A **Single-Author Product** verdict with multiple active agents is the strongest
signal that multi-agency coordination failed. The agents may have been busy, but
only one produced the working product. This should be flagged prominently in the
report and should always generate a `global` recommendation for Marcus to improve
task decomposition and dependency design.

A **Lopsided** verdict may be acceptable if the task naturally had a primary
implementer and a supporting role — but only if that was the intended design.
If agents were supposed to be equal contributors, lopsided is a coordination failure.

---

## Instruction Quality Assessment (if --session)

This is NOT a scored dimension. It is a findings section that explains root causes.
Process evidence from tmux logs and agent interviews is used to assess whether
problems stem from bad instructions or bad execution.

| Factor | Rating | Evidence Required |
|--------|--------|-------------------|
| Task descriptions | clear / ambiguous / missing / contradictory | Quote the instruction AND the agent's interpretation from tmux log |
| Success criteria | clear / ambiguous / missing / contradictory | Did the agent know what "done" looked like? |
| Dependency info | clear / ambiguous / missing / contradictory | Were cross-agent dependencies specified? |
| Scope boundaries | clear / ambiguous / missing / contradictory | Did agent go out of scope or miss scope? |
| Technical constraints | clear / ambiguous / missing / contradictory | Were patterns, tools, conventions specified? |

**How this affects scoring:**
- If instructions were **ambiguous** and agent made a reasonable interpretation → mitigate penalty on agent grade, note instruction issue
- If instructions were **clear** and agent ignored them → full penalty on agent grade
- If instructions were **missing** and agent improvised well → credit the agent, flag the instruction gap
- If instructions were **contradictory** → blame the spec, not the agent

**Important:** Instruction quality issues explain root causes but do not excuse poor output. A bug is still a bug. But knowing WHY it happened informs recommendations.

---

## Agent/Developer Grading Rubric

| Score | Criteria |
|-------|----------|
| 5 (A) | Delivered exactly what needed, no ghost code, integrates cleanly, followed specs |
| 4 (B) | Core requirements met, minor dead code or spec drift, works well |
| 3 (C) | Partial requirements, notable spec violations, needs cleanup |
| 2 (D) | Incomplete, significant ghost code, causes problems for others |
| 1 (F) | Did not deliver, or net-negative output |

### Process Evidence Modifiers (if --session)

When tmux logs and interview responses are available, agent grades should
reflect the full picture:

| Situation | Grade Modifier |
|-----------|---------------|
| Agent hit unclear instruction, improvised reasonably | +0.5 mitigating credit |
| Agent hit unclear instruction, made no attempt to clarify | No modifier |
| Agent saw error in tmux, shipped workaround without fixing root cause | -0.5 penalty |
| Agent ignored clear instruction (confirmed by interview) | -1.0 penalty |
| Agent identified spec problem and adapted correctly | +0.5 credit |
| Agent's interview contradicts tmux log evidence | Flag as unreliable, note discrepancy |

### Cross-Agent Issues to Flag
- Contradictory implementations
- Duplicated work
- Integration gaps
- Spec drift cascades
- Ghost chains (spec created, ignored, becomes ghost doc)

### Cross-Agent Issues from Process Evidence (if --session)
- Agent A's tmux log shows waiting on Agent B who was stuck
- Multiple agents re-solving the same problem independently (visible in logs)
- Agent misinterpreted output from another agent (visible in log errors)
- Coordination breakdowns: instructions said to coordinate but logs show no interaction

---

## Recommendation Scoping

Every recommendation must be scoped to one of three levels:

### Scope: `project`
Fixes that only matter for this specific codebase. Examples:
- Fix the bug in `handler.py:45`
- Add missing tests for the auth module
- Remove ghost code in `utils.py`

### Scope: `global`
Changes to Marcus itself so future experiments don't repeat this problem.
These are the most valuable recommendations. Examples:
- "Agents consistently missed testing requirements → Marcus task templates should include a mandatory 'testing requirements' field"
- "Three agents duplicated the same utility function → Marcus should provide shared utility bootstrapping before agents start"
- "Instructions didn't specify coding conventions → Marcus should inject project CLAUDE.md into every agent's context"
- "Agents couldn't tell when dependencies were ready → Marcus coordination should expose dependency status to blocked agents"

### Scope: `both`
A problem found in this project that reveals a systemic Marcus gap.
Recommend both the local fix AND the Marcus improvement. Examples:
- "Agent left debug logging in production code (project fix: remove it) AND Marcus should add a pre-commit lint check for all agent output"
- "Spec said 'implement caching' with no details, agent built wrong cache type (project fix: replace with LRU) AND Marcus task templates should require specificity for technical decisions"

### How to decide scope:
| Signal | Scope |
|--------|-------|
| One-off bug, typo, missing file | project |
| Same class of problem across multiple agents | global |
| Problem caused by Marcus instruction/coordination gap | global |
| Problem in code AND in Marcus that enabled it | both |
| Could this happen again in a different experiment? | global or both |
