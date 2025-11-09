# Post-Project Analysis System - Summary

## Purpose

**The Fundamental Question:** Did we build what we said we would build, does it align with what the user wanted, and does it actually work?

This system provides definitive answers by:
1. **Requirement Traceability:** Original user request → PRD → tasks → implementation → deliverables
2. **Semantic Validation:** Using LLMs to verify implementation matches intent (not just text)
3. **Functional Verification:** Does the application actually work as intended?
4. **Gap Analysis:** Where did we diverge? Why? How do we fix it?

### The Three Critical Validations

#### 1. Did We Build What We Said We Would?
**Question:** Does the implementation match the task descriptions and requirements?

**Validation:**
- Compare original task descriptions to artifacts produced
- Check if all planned features were implemented
- Identify missing functionality or incomplete tasks
- Measure: Requirement fidelity score per task, overall completion rate

**Output:** "User authentication task required OAuth2. Implementation used username/password. Divergence detected."

#### 2. Does It Align With What the User Wanted?
**Question:** Does the application solve the user's original problem?

**Validation:**
- Compare final deliverables to original project description
- LLM semantic analysis: Does functionality match user intent?
- Check architectural decisions against user needs
- Identify "technically correct but wrong" implementations

**Output:** "User requested 'easy login for non-technical users'. OAuth2 requires GitHub accounts, but target users aren't developers. Misalignment detected."

#### 3. Does It Actually Work?
**Question:** Is the application functional and free of blockers?

**Validation:**
- Check for failed tasks, unresolved blockers
- Test execution results (if available)
- Deployment status
- User acceptance testing results
- Integration issues between components

**Output:** "Login feature fails in production due to Redis persistence issue (session data lost on restart). Application non-functional."

### The Complete Picture

```
USER REQUEST
    ↓
PROJECT DESCRIPTION (About document)
    ↓
TASKS (from PRD parser)
    ↓
IMPLEMENTATION (agent work)
    ↓
DELIVERABLES (code, designs, docs)
    ↓
VALIDATION ← This is what we're building!
```

**This system validates every step of this chain and identifies where things went wrong.**

## The Core Problem

When a MARCUS-generated application fails, you need to answer:
- **What was the agent supposed to build?** (original task description)
- **What instructions did the agent receive?** (from `get_task_context`)
- **What decisions did the agent make and why?** (architectural choices)
- **What artifacts did the agent produce?** (code, designs, specs)
- **Where did implementation diverge from requirements?** (semantic gaps)
- **Which upstream decisions caused downstream failures?** (dependency chain)

Currently, this data exists but is scattered across:
- Conversation logs (`logs/conversations/`)
- Agent events (`logs/agent_events/`)
- Kanban comments (decisions, artifacts)
- File system (artifact files in project workspace)
- Memory system (ephemeral session data)

There's no unified way to query and analyze this for post-mortem diagnosis.

## Key Insights from Research

### ✅ What We're Already Capturing

**Persistent Data:**
1. **Conversation logs** - Every worker↔PM interaction, decision, assignment, progress update
2. **Agent events** - Registrations, task assignments, completions, blockers
3. **Memory system** - TaskOutcomes (estimated vs actual hours, success, blockers)
4. **Agent profiles** - Success rates, skill proficiency, estimation accuracy (learned over time)
5. **Task patterns** - Median durations, success rates, common blockers by task type
6. **Project registry** - Metadata, provider configs, timestamps
7. **Subtask decomposition** - Parent-child relationships, bundling
8. **Artifact files** - Physical files in project workspace (`docs/design/`, etc.)
9. **Kanban state** - Task descriptions, dependencies, statuses, comments
10. **MLflow experiments** - If started, tracks real-time metrics during execution

**Ephemeral Data (Session-Only, NEEDS PERSISTENCE):**
1. **`state.context.decisions`** - Architectural decisions with rationale
   - ✅ Posted as Kanban comments (queryable but not indexed)
   - ❌ In-memory registry lost after session ends
2. **`state.task_artifacts`** - Artifact metadata (type, location, description)
   - ✅ Files persist in workspace
   - ❌ Metadata registry lost after session ends
3. **`state.project_state`** - Final project metrics (velocity, completion rate, risk level)
   - ❌ Lost after session ends

### 🚫 What We Should NOT Duplicate

**Avoid creating new storage for:**
- Task descriptions (already in Kanban)
- Task dependencies (already in Kanban)
- Conversation history (already in logs)
- Agent registrations/assignments (already in agent_events)
- TaskOutcomes (already in Memory system persistence)
- Artifact files (already in project workspace)

**Instead:** Build an aggregator that unifies existing data sources.

### 🔑 Where LLMs Add Real Value

Traditional data aggregation can tell you **what happened**, but LLMs can tell you **why it went wrong**:

| **Analysis Type** | **Input** | **LLM Output** | **Value** |
|------------------|----------|----------------|-----------|
| **Requirement Divergence** | Original task description + implementation artifacts | Semantic comparison showing where intent was misunderstood | Catches "technically correct but wrong purpose" failures |
| **Decision Impact Tracing** | Architectural decision + downstream task outcomes | Causal chain showing how decision led to failures | Identifies root cause decisions |
| **Instruction Quality** | Task instructions from `get_task_context` + task outcome | Assessment of instruction clarity/completeness | Improves future instruction generation |
| **Failure Diagnosis** | User input: "Feature X doesn't work" + execution traces | Plain English explanation of failure chain | Makes diagnosis accessible |
| **Pattern Recognition** | Multiple failed projects | Common anti-patterns (e.g., "auth tasks always block on missing creds") | Proactive prevention |
| **Code-to-Requirement Mapping** | Original spec + actual code | Line-by-line mapping showing implementation fidelity | Precise divergence identification |

**Key Principles:**
- Use structured queries for **facts** (what/when/who), use LLMs for **understanding** (why/how/should)
- **Always present raw data alongside LLM interpretation** - users need to see the facts and validate the AI's analysis
- LLM interpretations should cite specific data points (e.g., "Based on decision logged at 2025-11-03 14:32...")

## Three-Phase Approach

### Phase 1: Data Persistence & Aggregation (Foundation)
**Goal:** Capture ephemeral data and build unified query layer

**No duplication** - Just persist what's currently ephemeral and index existing sources:
1. Persist `state.context.decisions` → `data/decisions/{project_id}.json`
2. Persist `state.task_artifacts` metadata → `data/artifacts/{project_id}.json`
3. Persist `state.project_state` snapshots → `data/project_snapshots/{project_id}.json`
4. Build aggregator that indexes:
   - Conversation logs
   - Agent events
   - Memory system (TaskOutcomes, AgentProfiles)
   - New persistent files (decisions, artifacts, snapshots)
   - Kanban state (via provider APIs)

**Deliverable:** Unified query API for historical project data

### Phase 2: LLM-Powered Analysis Engine (Intelligence)
**Goal:** Generate diagnostic insights using LLMs

Build analysis modules that leverage LLMs for understanding:
1. **Requirement Divergence Analyzer**
   - Compare original task descriptions to implementation artifacts
   - Identify semantic gaps (not just text diffs)
2. **Decision Impact Tracer**
   - Map architectural decisions to downstream effects
   - Determine if decisions caused failures/blockers
3. **Failure Diagnosis Generator**
   - Input: "Login doesn't work"
   - Output: "Login failed because task_user-login_implement used JWT but task_auth_design specified OAuth2. Decision logged by agent_3 on 2025-11-05."
4. **Instruction Quality Analyzer**
   - Evaluate if task instructions were clear/complete
   - Suggest improvements for future projects

**Deliverable:** Analysis API that answers "why?" questions

### Phase 3: Cato Integration (Visualization)
**Goal:** Interactive UI for exploration and diagnosis

Extend Cato with historical analysis mode:
1. **Project Retrospective Dashboard**
   - Overall health metrics, velocity, quality scores
   - LLM-generated summary of what went right/wrong
2. **Task Execution Trace View**
   - Click any task → see full context (instructions, decisions, artifacts, outcome)
   - LLM explanation of why task succeeded/failed
3. **Failure Diagnosis Interface**
   - Input: Failing feature
   - Output: Interactive graph showing task chain, decision points, divergence locations
4. **Decision Impact Graph**
   - Visual map of architectural decisions and their ripple effects

**Deliverable:** Interactive web UI for post-project analysis

**Note on Cato Issues:** Issue #140 addresses inconsistent test task generation (not a Cato visualization bug). However, we should verify Cato correctly handles bundled design tasks before Phase 3. If visualization issues exist, they must be fixed first.

## Success Metrics

### Primary Success Criterion

**You can definitively answer the three fundamental questions for any MARCUS project:**

✅ **1. Did we build what we said we would?**

**Query:** "Show me requirement fidelity for the Task Management API project"

**System Response:**
```
PROJECT: Task Management API
ORIGINAL DESCRIPTION: "Build a REST API for task management with user auth,
                       CRUD operations, and real-time updates"

PLANNED FEATURES (from About document):
  ✅ User Authentication (OAuth2)
  ✅ Task CRUD operations
  ✅ Real-time updates (WebSockets)
  ⚠️  Admin dashboard (partially implemented)
  ❌ Email notifications (not implemented - task blocked)

REQUIREMENT FIDELITY BY TASK:
  - task_user-auth_implement: 0.25 (CRITICAL DIVERGENCE)
    Required: OAuth2
    Implemented: Username/password + JWT

  - task_task-crud_implement: 0.95 (EXCELLENT MATCH)
    Required: Create, Read, Update, Delete tasks
    Implemented: All CRUD operations working

  - task_realtime_implement: 0.80 (GOOD MATCH)
    Required: WebSocket real-time updates
    Implemented: WebSockets for task updates, missing presence detection

OVERALL COMPLETION: 80% (4/5 features delivered)
OVERALL FIDELITY: 0.70 (divergences in auth approach)
```

✅ **2. Does it align with what the user wanted?**

**Query:** "Does this project solve the user's original problem?"

**System Response:**
```
USER'S ORIGINAL REQUEST (from project creation):
"I need a task management system for my remote team. They're non-technical
 people who just need to see their tasks and get notified when things change."

LLM ALIGNMENT ANALYSIS:

✅ ALIGNED:
  - Task CRUD: Users can see and manage tasks (matches need)
  - Real-time updates: Users see changes immediately (matches need)

⚠️  PARTIALLY ALIGNED:
  - Admin dashboard: Only partially implemented, may frustrate managers

❌ MISALIGNED:
  1. Authentication Choice:
     User Need: "non-technical people"
     Implementation: OAuth2 (requires GitHub account)
     Impact: Target users don't have GitHub accounts, can't log in

  2. Missing Email Notifications:
     User Need: "get notified when things change"
     Implementation: Real-time WebSocket only
     Impact: Users only notified if actively looking at app, miss updates

ROOT CAUSE ANALYSIS:
The requirements were technically correct but didn't consider the target
audience. "Non-technical remote team" implies:
  - Simple username/password (not GitHub OAuth)
  - Email notifications (not just real-time)
  - Mobile-friendly (not mentioned in requirements)

RECOMMENDATION: Requirements gathering should explicitly capture:
  - Target user technical level
  - Notification preferences
  - Access patterns (always-online vs periodic check-in)
```

✅ **3. Does it actually work?**

**Query:** "Is the Task Management API functional?"

**System Response:**
```
FUNCTIONAL STATUS: ❌ NON-FUNCTIONAL

CRITICAL ISSUES:
  1. Authentication Broken (task_user-auth_implement)
     Issue: Users cannot log in
     Cause: OAuth2 implemented but no GitHub OAuth app configured
     Blocker: Unresolved - "Need GitHub OAuth credentials" (2025-11-03)
     Impact: Application completely unusable

  2. Real-time Updates Fail (task_realtime_implement)
     Issue: WebSocket connections drop after 60 seconds
     Cause: Nginx proxy timeout not configured
     Blocker: Unresolved - "WebSocket disconnects in production" (2025-11-04)
     Impact: Core feature non-functional

NON-CRITICAL ISSUES:
  3. Email Notifications Missing
     Impact: Users don't know about task updates unless actively using app

TASK SUCCESS RATE:
  - Total tasks: 24
  - Completed: 22 (92%)
  - Completed with blockers: 2 (8%)
  - Failed: 0

However, "completed with blockers" means features are implemented but don't work!

DEPLOYMENT STATUS:
  - Code deployed: ✅ Yes
  - Application accessible: ⚠️  Yes, but authentication fails
  - Core functionality working: ❌ No
  - User acceptance: ❌ Cannot test - users can't log in

ROOT CAUSES:
  1. Blockers marked "completed" without resolution
  2. No integration testing of OAuth flow end-to-end
  3. Production environment config (OAuth creds, Nginx) not part of tasks

IMMEDIATE ACTIONS REQUIRED:
  1. Create GitHub OAuth app, add credentials to production
  2. Configure Nginx WebSocket proxy timeout (increase to 1 hour)
  3. Add task: "Production environment configuration"
  4. Add acceptance criterion: "User can successfully log in and use app"
```

### Secondary Success Criteria

✅ **Pattern Recognition Across Projects**
   → "OAuth tasks fail 70% of the time due to missing credentials in production. Add 'Configure OAuth provider' task to all auth implementations."

✅ **Traceability**
   → Click any broken feature → See exact task → See decision that caused it → See which agent made it → See their rationale

✅ **Actionable Insights**
   → Every analysis includes concrete recommendations for fixing issues and preventing recurrence

✅ **Trust Through Transparency**
   → Every LLM claim is backed by cited raw data that users can verify

## Design Principles

1. **No Duplication:** Leverage existing data sources, only persist ephemeral state
2. **LLMs for Understanding:** Use structured queries for facts, LLMs for insights
3. **Raw Data + Interpretation:** Always show raw data alongside LLM analysis for transparency and validation
4. **Citation Required:** LLM interpretations must cite specific data points with timestamps
5. **Progressive Enhancement:** Each phase independently valuable
6. **Queryable History:** All data must be indexed and searchable
7. **Human-Readable Output:** Analysis results in plain English, not just metrics
8. **Actionable Insights:** Every analysis should suggest concrete improvements

## Related Issues & Context

- **GH-140:** Inconsistent test task generation (complexity mode issue, not Cato bug)
- **GH-127:** Make DependencyInferer domain-aware for bundled designs
- **GH-132:** Improve code quality in bundled domain designs
- **Memory System:** Already tracks TaskOutcomes, AgentProfiles, TaskPatterns with persistence
- **Context System:** Already logs decisions and provides task context (but ephemeral)
- **Artifact System:** Already stores files with metadata (but metadata is ephemeral)
- **Cato Aggregator:** Already unifies real-time data from multiple sources

## Next Steps

1. **Review this summary** - Confirm approach before detailed phase planning
2. **Create PHASE_1.md** - Detailed design for data persistence and aggregation
3. **Create PHASE_2.md** - Detailed design for LLM analysis engine
4. **Create PHASE_3.md** - Detailed design for Cato integration
5. **TDD Implementation** - Write tests first, iterate on each phase

## Questions for Consideration

1. Should we persist decisions/artifacts incrementally (on log) or at project completion?
2. Where should historical analysis API live? (Cato backend or new service?)
3. What LLM should we use for analysis? (Same as MARCUS AI engine or separate?)
4. Should analysis be real-time (during execution) or post-mortem only?
5. How long should we retain historical project data?
6. Do we need a separate database or can we use file-based storage + indexing?

## Estimated Scope

- **Phase 1:** ~3-5 days (persistence + aggregator + tests)
- **Phase 2:** ~5-7 days (LLM analysis modules + tests)
- **Phase 3:** ~5-7 days (Cato UI extension + tests)
- **Total:** ~2-3 weeks for full system

Each phase can be shipped independently for incremental value.
