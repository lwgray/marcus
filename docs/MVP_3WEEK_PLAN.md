# Marcus MVP - 3 Week Release Plan

**Created:** 2025-01-05
**Target Release:** End of Week 3
**Phase:** Phase 1 (Greenfield Software Development)
**Strategy:** Open source to establish standard before competitors

---

## Strategic Context

### Competitive Position
- **VibeKanban:** Adjacent market (visual UI for manual orchestration)
- **Marcus:** Infrastructure layer (autonomous coordination platform)
- **Potential synergy:** VibeKanban could use Marcus as backend
- **No immediate threat:** Different value propositions

### Open Source Rationale
"Surprisingly this is to squash competition" - Establish the standard for agent coordination infrastructure before market consolidates

### Long-term Vision (1 year = 4 phases)
1. **Phase 1 (MVP):** Greenfield software projects
2. **Phase 2:** Brownfield (existing codebases)
3. **Phase 3:** Domain-agnostic (content, research, marketing)
4. **Phase 4:** Cross-org infrastructure + agent marketplace

---

## What You Already Have (Infrastructure Audit)

### ✅ Observability & Monitoring (STRONG)
**Location:** `src/monitoring/`, `src/core/error_monitoring.py`, `src/marcus_mcp/tools/analytics.py`

**What exists:**
1. **Error Monitoring System** (`error_monitoring.py`)
   - Pattern detection (frequency, burst, agent-specific, cascade)
   - Error correlation and root cause analysis
   - Health scoring and recommendations
   - Persistent storage in JSON
   - Alert callbacks

2. **Project Monitor** (`project_monitor.py`)
   - Real-time health tracking
   - AI-powered risk assessment
   - Stalled task detection
   - Historical metrics
   - Integration with kanban system

3. **Analytics Tools** (`analytics.py`)
   - System-wide metrics (throughput, duration, health score)
   - Agent performance metrics
   - Project-level analytics
   - Task-level analytics

4. **Assignment Monitor** (`assignment_monitor.py`)
   - Task assignment tracking
   - Agent utilization metrics

**Gap Analysis:**
- ❌ No external telemetry (PostHog/Mixpanel) for product analytics
- ❌ No user opt-in telemetry system
- ✅ Internal observability is comprehensive
- ✅ Error framework is mature

**MVP Decision:** **Keep internal observability, defer external telemetry to post-MVP**
**Rationale:**
- You have sophisticated internal monitoring already
- External telemetry adds packaging complexity
- Focus on validation, not analytics (week 3 priorities)

---

## What You Need to Validate (From VALUE_PROPOSITIONS.md)

### Tier 1: MVP Blockers (MUST PASS)

| Issue | Claim | Status | Effort | Priority |
|-------|-------|--------|---------|----------|
| #118 | Simple project end-to-end | 🔴 OPEN | 2 days | P0 |
| #119 | Multi-agent parallelization | 🔴 OPEN | 2 days | P0 |
| #121 | Git traceability (task IDs) | 🔴 OPEN | 1 day | P0 |

**Total: 5 days of validation work**

### Tier 2: Important but Not Blocking

| Issue | Claim | Status | Effort | Priority |
|-------|-------|--------|---------|----------|
| #122 | Artifact system workflow | 🔴 OPEN | 1 day | P1 |
| #123 | Decision logging | 🔴 OPEN | 1 day | P1 |

**Total: 2 days of validation work**

### Tier 3: Defer to Post-MVP

| Issue | Type | Reason to Defer |
|-------|------|-----------------|
| #120 | Benchmark (speedup) | Marketing claim, not functionality |
| #124 | Benchmark (overhead) | Performance optimization, not validation |
| #125 | Constraint accuracy | Advanced validation, not critical path |

---

## 3-Week Sprint Plan

### Week 1: Core Validation (Jan 6-12)

**Goal:** Pass Tier 1 validations (#118, #119, #121)

#### Day 1-2 (Mon-Tue): Issue #118 - Simple Project E2E
**What to validate:**
```bash
# Test case: Dark mode toggle (atomic feature)
create_project(
    description="Add dark mode toggle to chrome extension with vanilla JavaScript",
    project_name="dark-mode-feature",
    options={"complexity": "standard"}
)

# Expected: 1 task created (Implement only, no Design/Test)
# Expected: Agent completes autonomously in ~30 min
# Expected: Git commit with task ID
```

**Success criteria:**
- [ ] Only 1 task created (atomic → implement pattern)
- [ ] Task description mentions "vanilla JavaScript" (constraint enforcement)
- [ ] Agent completes without user intervention
- [ ] Commit message includes task ID: `feat(task-XXX): ...`
- [ ] Code on dedicated branch

**If fails:** Fix task pattern selection or agent workflow

#### Day 3-4 (Wed-Thu): Issue #119 - Multi-Agent Parallel
**What to validate:**
```bash
# Test case: Todo app (multiple simple features)
create_project(
    description="Build todo app with vanilla JS: create, read, update, delete todos",
    project_name="todo-app-mvp",
    options={"complexity": "prototype"}
)

# Expected: 6-8 tasks
# Run 3 agents simultaneously
```

**Success criteria:**
- [ ] 3 agents request tasks concurrently
- [ ] All agents get different tasks
- [ ] Agents work without conflicts
- [ ] Completion time < sequential time
- [ ] All tasks marked DONE on board

**If fails:** Fix task assignment or locking logic

#### Day 5 (Fri): Issue #121 - Git Traceability
**What to validate:**
```bash
# From #118 or #119 runs:
# 1. Check git log for task IDs
git log --oneline | grep "task-"

# 2. Verify branch naming
git branch -a | grep "agent-"

# 3. Check commit format
git log -1 --format="%B"
# Should see: feat(task-XXX): description
```

**Success criteria:**
- [ ] All commits include task ID
- [ ] Branch names indicate agent/feature
- [ ] Commit messages follow convention
- [ ] Can trace task → commits → code changes

**If fails:** Update agent prompt or add git hooks

---

### Week 2: Polish & Packaging (Jan 13-19)

**Goal:** Make installation frictionless

#### Day 1-2 (Mon-Tue): Packaging Strategy

**Decision Point:** How to distribute Marcus?

**Option A: Keep Current (Docker Compose)**
```bash
git clone https://github.com/lwgray/marcus
cd marcus
docker-compose up -d
claude mcp add marcus http://localhost:4298/mcp
```

**Pros:**
- Already working
- No new code needed
- Complete control

**Cons:**
- Requires Docker knowledge
- Multi-step setup
- Not "one command" install

**Option B: NPX Wrapper (Like VibeKanban)**
```bash
npx @marcus/server init
# Auto-configures MCP, starts Docker, registers with Claude
```

**Pros:**
- Single command install
- Competitive with VibeKanban
- Modern developer UX

**Cons:**
- 2-3 days to build wrapper
- Packaging complexity
- Windows/Mac/Linux testing

**Option C: Hybrid (Recommended for MVP)**
```bash
# Primary: Docker Compose (current)
# Bonus: Add install script
curl -fsSL https://get.marcus.ai | sh
# Script runs docker-compose, configures MCP automatically
```

**Pros:**
- Minimal new code (bash script)
- Single command UX
- Build on existing foundation

**Cons:**
- Still requires Docker

**MVP Recommendation:** **Option C (install script)**
**Effort:** 1 day
**Rationale:** Best ROI - modern UX without rewriting packaging

#### Day 3-4 (Wed-Thu): Documentation Overhaul

**Update:**
1. **README.md**
   - Add "one command" install
   - Update quick start with validated workflows
   - Add demo GIF/video
   - Add "Bring Your Own Agent" clarity

2. **Installation Guide**
   - Prerequisites clearly listed
   - Troubleshooting section
   - Platform-specific instructions (Mac/Linux/Windows)

3. **Agent Setup Guide**
   - Copy/paste agent prompt
   - Claude Code configuration
   - Other agents (Cursor, Windsurf, etc.)

4. **First Project Tutorial**
   - Step-by-step walkthrough
   - Expected output at each step
   - Common issues and fixes

**Deliverable:** Clear docs that anyone can follow

#### Day 5 (Fri): Validation Round 2

**Run Tier 2 validations:**

**#122: Artifact System**
```bash
# Create project with design → implement dependency
create_project(
    description="Build REST API with OpenAPI spec: user CRUD endpoints",
    project_name="user-api",
    options={"complexity": "standard"}
)

# Expected:
# 1. Design task creates docs/api/user-api.yaml
# 2. Implement task calls get_task_context()
# 3. Implement task reads spec and builds to it
```

**Success:** Implementation matches design spec

**#123: Decision Logging**
```bash
# From #122:
# Design agent logs decision: "I chose REST over GraphQL because..."
# Implement agent receives decision in context
```

**Success:** Decisions flow between tasks

---

### Week 3: Launch Prep (Jan 20-26)

**Goal:** Public release

#### Day 1-2 (Mon-Tue): Final Testing & Fixes

**Alpha Test Plan:**
1. Fresh machine install (Mac)
2. Fresh machine install (Linux)
3. Run #118 test (simple project)
4. Run #119 test (multi-agent)
5. Check all git commits

**Bug Bash:**
- Fix any install issues
- Fix any workflow issues
- Update docs for discovered pain points

#### Day 3 (Wed): Launch Assets

**Create:**
1. **Demo Video (3 min)**
   - Install Marcus (30 sec)
   - Create project (30 sec)
   - Agents work autonomously (2 min)
   - Show completed code (30 sec)

2. **Landing Page Copy**
   - Value proposition (validated claims only)
   - Quick start
   - Feature list
   - GitHub link

3. **Launch Blog Post**
   - Why I built Marcus
   - How it works
   - What makes it different
   - Roadmap (4 phases)

4. **Social Media Posts**
   - HackerNews Show HN template
   - Twitter/X announcement
   - Reddit r/LocalLLaMA post
   - LinkedIn post

#### Day 4 (Thu): Soft Launch

**Release to limited audience:**
- Marcus Discord (if exists)
- Personal network
- 5-10 beta testers

**Collect feedback:**
- Installation issues?
- Workflow confusion?
- Documentation gaps?
- Feature requests?

**Quick iteration:** Fix critical issues discovered

#### Day 5 (Fri): Public Launch

**Launch sequence:**
1. **Morning:** Publish to GitHub (make repo public)
2. **Morning:** Post to HackerNews Show HN
3. **Afternoon:** Twitter/X announcement
4. **Afternoon:** Reddit posts
5. **Evening:** Monitor feedback, respond to questions

**Success Metrics:**
- GitHub stars > 50 (week 1)
- Successful installs > 20
- Working projects created > 10
- No critical bugs reported

---

## MVP Scope: What's IN vs OUT

### ✅ IN SCOPE (Must Have)

1. **Core Functionality**
   - ✅ create_project from natural language
   - ✅ Intelligent task decomposition (complexity-aware)
   - ✅ Constraint enforcement (vanilla-js, no-frameworks)
   - ✅ Multi-agent coordination
   - ✅ Artifact system (design → implement)
   - ✅ Decision logging
   - ✅ Git traceability

2. **Integration**
   - ✅ Planka (already working)
   - ✅ GitHub Projects (already working?)
   - ✅ MCP protocol
   - ✅ Claude Code agent

3. **Observability**
   - ✅ Internal monitoring (already have)
   - ✅ Error tracking (already have)
   - ✅ Health metrics (already have)

4. **Documentation**
   - ✅ Installation guide
   - ✅ Agent setup guide
   - ✅ First project tutorial
   - ✅ Architecture docs

### ❌ OUT OF SCOPE (Post-MVP)

1. **Advanced Features**
   - ❌ Brownfield project support (Phase 2)
   - ❌ Domain-agnostic workflows (Phase 3)
   - ❌ Cross-org infrastructure (Phase 4)
   - ❌ Agent marketplace (Phase 4)

2. **Polish**
   - ❌ Web UI / dashboard (keep BYOK approach)
   - ❌ External telemetry (PostHog/Mixpanel)
   - ❌ Advanced metrics (speedup benchmarks)
   - ❌ Performance optimization

3. **Integrations**
   - ❌ Linear (post-MVP)
   - ❌ Jira (post-MVP)
   - ❌ Other agents beyond Claude (future)

4. **Enterprise Features**
   - ❌ Team management
   - ❌ Access controls
   - ❌ SSO/SAML
   - ❌ Audit logging beyond current

---

## Risk Assessment

### High Risk (Could Block Release)

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Core validations fail (#118, #119) | Medium | HIGH | Allocate full week 1, buffer time week 2 |
| Installation too complex | Medium | HIGH | Test on fresh machines, iterate docs |
| Agent workflow breaks | Low | HIGH | Extensive testing, clear error messages |

### Medium Risk (Could Delay Release)

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Documentation gaps | High | Medium | Alpha testers identify gaps week 3 |
| Platform-specific issues | Medium | Medium | Test Mac/Linux/Windows early |
| Performance issues | Low | Medium | Defer optimization to post-MVP |

### Low Risk (Acceptable)

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Low initial adoption | Medium | Low | Open source = long-term play |
| Feature requests | High | Low | Triage to roadmap, focus on MVP |
| Competitor launches | Low | Low | Different value prop, not threatened |

---

## Success Criteria

### Week 1 Success
- [ ] Pass issue #118 (simple project)
- [ ] Pass issue #119 (multi-agent)
- [ ] Pass issue #121 (git traceability)
- [ ] Document any bugs found

### Week 2 Success
- [ ] One-command install working
- [ ] Documentation complete and tested
- [ ] Pass issue #122 (artifacts)
- [ ] Pass issue #123 (decisions)

### Week 3 Success
- [ ] 5+ successful alpha tests
- [ ] Critical bugs fixed
- [ ] Demo video published
- [ ] Public launch completed

### Post-Launch Success (Week 4-5)
- [ ] 50+ GitHub stars
- [ ] 20+ successful installs
- [ ] 10+ projects created
- [ ] Active community forming

---

## Open Questions (Need Your Input)

### 1. Packaging Decision
**Question:** Option A (current Docker), B (NPX wrapper), or C (install script)?
**My Recommendation:** C (install script) - best ROI
**Your Decision:** ?

### 2. GitHub Projects Integration
**Question:** Is GitHub Projects integration already working? If not, priority?
**Context:** Many users prefer GitHub over self-hosted Planka
**Your Status:** ?

### 3. Linear Integration
**Question:** Is Linear integration important for MVP?
**Context:** Modern teams use Linear, but adds scope
**Your Priority:** ?

### 4. Agent Support Beyond Claude
**Question:** Support other agents (Cursor, Windsurf) for MVP?
**Context:** Marcus is BYOA, but testing multiple agents adds work
**Your Decision:** ?

### 5. Research Support (Issue #30)
**Question:** MVP include basic research logging infrastructure?
**Context:** Long-term vision, but adds 2 days
**Your Priority:** ?

### 6. Telemetry
**Question:** Add opt-in telemetry for MVP?
**My Recommendation:** No - focus on validation, add post-MVP
**Your Decision:** ?

---

## Next Steps (Immediately)

1. **Your Decisions:**
   - Review open questions above
   - Confirm packaging approach
   - Confirm scope (anything to add/remove?)

2. **My Actions:**
   - Set up Week 1 validation environment
   - Create test cases for #118, #119, #121
   - Prepare documentation templates

3. **Monday Morning (Week 1 Start):**
   - Kick off #118 validation
   - Begin parallel work on docs
   - Daily check-ins on progress

---

## Why This Plan Works

1. **Realistic Timeline:** 3 weeks with buffer for unknowns
2. **Validation-First:** Prove it works before marketing
3. **Leverage Existing:** Use your strong observability foundation
4. **Defer Complexity:** No telemetry, no advanced features, no scope creep
5. **Open Source Strategy:** Release early, iterate with community
6. **Phase-Appropriate:** MVP targets Phase 1 (greenfield), foundation for later phases

**Key Insight:** You're further along than you think. You have:
- ✅ Core functionality working
- ✅ Sophisticated monitoring
- ✅ Error framework
- ✅ Integration adapters

**You need:**
- ⏳ Validation evidence (5-7 days)
- ⏳ Polish & docs (3-4 days)
- ⏳ Launch assets (2-3 days)

**Total:** 10-14 days of focused work = 3 weeks with buffer

---

## Post-MVP Roadmap (Next 3-6 Months)

### Month 1-2: Stability & Adoption
- Fix bugs from initial users
- Add missing docs
- Improve error messages
- Build community (Discord, issues, PRs)

### Month 2-3: Phase 2 Foundation (Brownfield)
- Code analysis for existing projects
- "Add feature to existing codebase" workflow
- Context understanding from existing code

### Month 3-4: Phase 3 (Domain-Agnostic)
- Content creation workflows
- Research coordination
- Marketing campaign management
- Generalize beyond software

### Month 4-6: Phase 4 Foundation (Marketplace)
- Agent communication protocols
- Cross-org task sharing
- Specialized agent registry
- "Agent economy" primitives

**Goal:** All 4 phases in 1 year (aggressive but achievable with open source community)

---

## Appendix: What You Already Have (Detailed Audit)

### Monitoring & Observability

**Error Monitoring (`error_monitoring.py`):**
- Real-time error tracking with pattern detection
- Correlation analysis for root cause
- Health scoring (0-100 scale)
- Alert callbacks for critical patterns
- JSON persistence for historical analysis
- Metrics: error rate, type distribution, severity breakdown

**Project Monitoring (`project_monitor.py`):**
- Continuous health tracking loop
- AI-powered risk assessment
- Stalled task detection
- Velocity tracking (tasks/week)
- Integration with kanban boards
- Historical trend analysis

**Analytics (`analytics.py`):**
- System metrics: active agents, throughput, health
- Agent metrics: performance, task completion rate
- Project metrics: progress, velocity, blockers
- Task metrics: duration, status distribution

**Assignment Monitoring (`assignment_monitor.py`):**
- Task assignment tracking
- Agent utilization metrics
- Load balancing analysis

**What This Means:**
You have **enterprise-grade observability** already built. This is not MVP work - this is mature infrastructure. Don't rebuild or add external telemetry. Focus on validation and polish.

---

**Ready to start Week 1?** Let me know your decisions on open questions and we can begin validation immediately.
