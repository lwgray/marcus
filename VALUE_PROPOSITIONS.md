# Marcus Value Propositions & Claims Validation

> **Last Updated:** November 2, 2025
> **Purpose:** Document all marketing claims and validate each one is backed by code

---

## Universal Value Proposition

**Main Claim:**
> Marcus transforms project descriptions into autonomous AI execution at any scale. Simple features get streamlined into 1-2 tasks, complex features get proper design and coordination. Walk away and come back to working code on git branches, with full decision logs and constraint enforcement.

---

## Core Claims & Validation

### 1. "Natural Language → Autonomous Task Execution"

**Claim:**
Describe your project in plain English, Marcus creates executable tasks and agents build them autonomously.

**Validation Checklist:**
- [ ] User can call `create_project(description, project_name)` via MCP tool
- [ ] PRD parser (`advanced_parser.py`) extracts requirements from description
- [ ] Tasks are created on Planka/GitHub board
- [ ] Agents register and request tasks automatically
- [ ] Agents work without user intervention until completion

**Code References:**
- Entry point: `src/marcus_mcp/tools/nlp.py::create_project()`
- PRD parsing: `src/ai/advanced/prd/advanced_parser.py::parse_prd_to_tasks()`
- Agent workflow: `prompts/Agent_prompt.md` - continuous work loop
- Task assignment: `src/marcus_mcp/tools/task.py::request_next_task()`

**Test Cases Needed:**
- [ ] End-to-end: "Build a todo app" → Tasks created → Agents complete them
- [ ] Simple project: "Add dark mode toggle" → 1-2 tasks created
- [ ] Complex project: "Build e-commerce platform" → 20+ tasks created

**Status:** ✅ READY (validate with integration test)

---

### 2. "Intelligent Scaling Based on Complexity"

**Claim:**
Marcus adapts task generation to feature complexity. Simple features = 1 task, Complex features = 3+ tasks.

**Validation Checklist:**
- [ ] Atomic features (CSS change) generate 1 task in Standard mode
- [ ] Simple features (one component) generate 2 tasks in Standard mode
- [ ] Coordinated features (multi-component) generate 3 tasks in Standard mode
- [ ] Distributed features (multi-service) generate 3+ tasks
- [ ] Prototype mode uses minimal task patterns
- [ ] Enterprise mode uses comprehensive task patterns

**Code References:**
- Complexity classification: `src/ai/advanced/prd/advanced_parser.py::_analyze_prd_deeply()` (PR #111)
- Task pattern selection: `src/ai/advanced/prd/advanced_parser.py::_select_task_pattern()` (PR #112)
- Patterns by mode: Lines 1266-1446 in `advanced_parser.py`

**Test Cases Needed:**
- [ ] Atomic feature + Standard mode → 1 task (Implement only)
- [ ] Simple feature + Standard mode → 2 tasks (Implement + Test)
- [ ] Coordinated feature + Standard mode → 3 tasks (Design + Implement + Test)
- [ ] Prototype mode always uses minimal patterns
- [ ] Enterprise mode uses comprehensive patterns

**Evidence:**
```python
# From PR #112 - Task Pattern Selection
TASK_PATTERNS = {
    "atomic": {
        "prototype": ["implementation"],
        "standard": ["implementation"],
        "enterprise": ["implementation", "testing"]
    },
    "simple": {
        "prototype": ["implementation"],
        "standard": ["implementation", "testing"],
        "enterprise": ["design", "implementation", "testing"]
    },
    # ... more patterns
}
```

**Status:** ✅ READY (merged in PR #112)

---

### 3. "Constraint Enforcement (vanilla-js, no-frameworks, etc.)"

**Claim:**
Technical constraints like "vanilla-js" and "no-frameworks" are respected throughout task generation.

**Validation Checklist:**
- [ ] PRD analysis extracts technical constraints from description
- [ ] Constraints propagate to all task description prompts
- [ ] Violation detection warns when AI suggests forbidden tech
- [ ] Original user description included in all prompts (context preservation)

**Code References:**
- Constraint extraction: `src/ai/advanced/prd/advanced_parser.py::_analyze_prd_deeply()` - `technicalConstraints` field
- Constraint propagation: `src/ai/advanced/prd/advanced_parser.py::_generate_task_description_for_type()` (PR #114)
- Violation detection: `src/ai/advanced/prd/advanced_parser.py::_check_constraint_violations()` (PR #114)

**Test Cases Needed:**
- [ ] Description with "vanilla-js" → All tasks mention vanilla JS, not React
- [ ] Description with "no-frameworks" → Violation detection triggers if AI suggests frameworks
- [ ] Description with "no-orm" → Task descriptions avoid ORM mentions
- [ ] Constraints formatted correctly in prompts ("Use: vanilla js", "Do not use: frameworks")

**Evidence:**
```python
# From PR #114
def _format_constraints_for_prompt(constraints: List[str]) -> str:
    """Convert constraint tags to readable format for AI."""
    # "vanilla-js" → "Use: vanilla js"
    # "no-frameworks" → "Do not use: frameworks"
```

**Status:** ✅ READY (merged in PR #114)

---

### 4. "Walk Away - Agents Work Autonomously"

**Claim:**
Start Marcus agents, walk away, come back to completed work on git branches.

**Validation Checklist:**
- [ ] Agents run continuous work loop without user prompts
- [ ] Agents auto-request next task after completing current one
- [ ] Agents work with `dangerously-skip-permissions` enabled (Claude setting)
- [ ] Agents commit changes to git automatically
- [ ] Agents push commits to dedicated branches
- [ ] Agents stop when no tasks remain

**Code References:**
- Agent prompt: `prompts/Agent_prompt.md` - "CRITICAL: maintain continuous work loop"
- Work loop: Lines 34-46 in `Agent_prompt.md`
- Auto-request: "After completing ANY task, IMMEDIATELY request next task"
- Git workflow: Lines 144-157 in `Agent_prompt.md`

**Test Cases Needed:**
- [ ] Agent completes task → Immediately calls `request_next_task()`
- [ ] Agent gets "no tasks" → Sleeps for retry duration → Requests again
- [ ] Agent commits changes with task ID in message
- [ ] Agent works without asking permission (requires Claude setting)

**Evidence:**
```markdown
# From Agent_prompt.md
YOUR WORKFLOW:
1. Register yourself ONCE at startup using register_agent
2. Enter continuous work loop:
   a. Call request_next_task (you'll get one task or none)
   ...
   h. Report completion with summary of what you built
   i. Immediately request next task
```

**Status:** ✅ READY (validate with real agent run)

---

### 5. "Git Commits with Full Traceability"

**Claim:**
All agent changes are committed to git with task IDs for full traceability.

**Validation Checklist:**
- [ ] Agents commit after completing logical units of work
- [ ] Commit messages include task ID: `feat(task-123): implement feature`
- [ ] Agents work on dedicated branches (not main/develop)
- [ ] Branch names indicate agent: `agent-1-feature-auth`
- [ ] Git history provides rollback capability

**Code References:**
- Git workflow: `prompts/Agent_prompt.md` lines 144-157
- Commit triggers: Lines 153-157
- Branch strategy: Line 145 - "You work exclusively on your dedicated branch"

**Test Cases Needed:**
- [ ] Agent commits include task ID in message
- [ ] Agent works on dedicated branch
- [ ] Commits are pushed to remote
- [ ] Multiple agents use different branches

**Evidence:**
```markdown
# From Agent_prompt.md
GIT_WORKFLOW:
- You work exclusively on your dedicated branch: {BRANCH_NAME}
- Commit messages MUST describe implementations: "feat(task-123): implement POST /api/users returning {id, email, token}"
- Include task ID in all commit messages for traceability
```

**Status:** ✅ READY (verify branch naming in launch script)

---

### 6. "Parallel Execution - 2-3x Speedup"

**Claim:**
Multiple agents work on different tasks simultaneously, completing projects 2-3x faster.

**Validation Checklist:**
- [ ] Multiple agents can request tasks concurrently
- [ ] Task scheduler assigns different tasks to different agents
- [ ] Agents work independently (no blocking)
- [ ] Subtasks enable parallelization within a single feature
- [ ] Actual speedup measured in experiments

**Code References:**
- Task assignment: `src/core/ai_powered_task_assignment.py::find_optimal_task_for_agent_ai_powered()`
- Subtask parallelization: `src/marcus_mcp/coordinator/decomposer.py`
- Parallelism analysis: Lines 227-253 in `decomposer.py`

**Test Cases Needed:**
- [ ] 3 agents request tasks → All get different tasks
- [ ] Measure time: 1 agent vs 3 agents on same project
- [ ] Verify 2-3x speedup for multi-component projects
- [ ] Single-component projects don't benefit (validate this too)

**Benchmarks Needed:**
- [ ] Todo app (8 features): 1 agent = X hours, 3 agents = X/3 hours
- [ ] E-commerce (30 features): 1 agent = Y hours, 5 agents = Y/3-5 hours

**Status:** ⚠️ NEEDS VALIDATION (run benchmark experiments)

---

### 7. "Decision Logging & Architectural Audit Trail"

**Claim:**
Agents log all architectural decisions with full traceability to dependent tasks.

**Validation Checklist:**
- [ ] Agents can call `log_decision(agent_id, task_id, decision)`
- [ ] Decisions are stored and retrievable via `get_task_context()`
- [ ] Decisions posted as comments on Kanban cards
- [ ] Dependent tasks receive relevant decisions automatically
- [ ] Decisions follow format: "I chose X because Y. This affects Z."

**Code References:**
- Decision logging: `src/marcus_mcp/tools/context.py::log_decision()`
- Decision retrieval: `src/marcus_mcp/tools/context.py::get_task_context()`
- Agent prompt: Lines 94-99 in `Agent_prompt.md`

**Test Cases Needed:**
- [ ] Agent logs decision → Appears in context system
- [ ] Dependent task calls `get_task_context()` → Receives decision
- [ ] Decision posted to Kanban as comment
- [ ] Decision format parsed correctly (what, why, impact)

**Evidence:**
```python
# From context.py
async def log_decision(agent_id: str, task_id: str, decision: str, state: Any):
    """Log an architectural decision made during task implementation."""
    # Parses: "I chose X because Y. This affects Z."
    # Stores in context system
    # Posts to Kanban
    # Cross-references to dependent tasks
```

**Status:** ✅ READY (validate with agent using log_decision)

---

### 8. "Artifact System - Design Specs, API Schemas, Documentation"

**Claim:**
Agents create and share artifacts (API specs, schemas, designs) automatically via standardized locations.

**Validation Checklist:**
- [ ] Agents can call `log_artifact(task_id, filename, content, type, project_root)`
- [ ] Artifacts stored in standard locations (docs/api/, docs/design/, etc.)
- [ ] Dependent tasks retrieve artifacts via `get_task_context()`
- [ ] Design agents create specs, Implementation agents read them
- [ ] Artifacts include: API specs, schemas, architecture docs, designs

**Code References:**
- Artifact logging: `src/marcus_mcp/tools/attachment.py::log_artifact()`
- Artifact retrieval: `src/marcus_mcp/tools/context.py::_collect_task_artifacts()`
- Standard locations: Lines 119-127 in `Agent_prompt.md`

**Test Cases Needed:**
- [ ] Design agent creates `user-api.yaml` → Stored in `docs/api/`
- [ ] Implement agent calls `get_task_context()` → Receives artifact path
- [ ] Implement agent reads artifact from file system
- [ ] Multiple artifact types tested (api, design, architecture, specification)

**Evidence:**
```python
# From attachment.py
STANDARD_LOCATIONS = {
    "api": "docs/api/",
    "design": "docs/design/",
    "architecture": "docs/architecture/",
    "specification": "docs/specifications/",
    # ... more
}
```

**Status:** ✅ READY (validate with multi-task workflow)

---

### 9. "GitHub Code Awareness - Learn from Existing Implementations"

**Claim:**
When using GitHub provider, agents see actual code from completed tasks and match patterns.

**Validation Checklist:**
- [ ] Code analyzer reads implementations from GitHub repo
- [ ] Implementation details passed to agents in `request_next_task` response
- [ ] Agents receive endpoint patterns, data models, response formats
- [ ] Agents instructed to match existing patterns

**Code References:**
- Code analysis: `src/marcus_mcp/tools/task.py::request_next_task()` lines 565-573
- Implementation context: Lines 168-173 in `task.py`
- Agent instruction: Lines 258-264 in `Agent_prompt.md`

**Test Cases Needed:**
- [ ] Task A creates `/api/users` → Task B receives implementation details
- [ ] Task B creates `/api/products` matching `/api/users` pattern
- [ ] Code analyzer actually reads from GitHub (not just metadata)

**Status:** ⚠️ NEEDS VALIDATION (verify code_analyzer implementation)

---

### 10. "Testing Enforcement Where Appropriate"

**Claim:**
Testing is enforced through task structure, but only for features that need it.

**Validation Checklist:**
- [ ] Atomic features in Standard mode → No test task (just Implement)
- [ ] Simple features in Standard mode → Test task created
- [ ] Coordinated features → Test task always created
- [ ] Test task must be completed before project marked done
- [ ] Agents actually run tests (not just claim completion)

**Code References:**
- Task pattern selection: `src/ai/advanced/prd/advanced_parser.py::_select_task_pattern()`
- Patterns include/exclude "testing" based on complexity

**Test Cases Needed:**
- [ ] Atomic feature → No test task in task list
- [ ] Simple feature → Test task exists in task list
- [ ] Test task assigned → Agent runs pytest/jest/etc
- [ ] Test failures → Agent reports blocker or fixes

**Status:** ⚠️ PARTIAL (patterns correct, need to validate agents run tests)

---

### 11. "Intelligent Retry & Dependency Handling"

**Claim:**
Agents intelligently wait for blocking tasks and resume when dependencies complete.

**Validation Checklist:**
- [ ] Agent requests task → None available (dependencies blocking)
- [ ] Marcus calculates optimal retry time based on ETA
- [ ] Agent sleeps for calculated duration
- [ ] Agent wakes up when blocking task nears completion
- [ ] Prioritizes tasks that unlock parallel work

**Code References:**
- Retry calculation: `src/marcus_mcp/tools/task.py::calculate_retry_after_seconds()` lines 318-461
- Strategy: 60% of ETA for early completion detection
- Parallel work prioritization: Lines 414-422

**Test Cases Needed:**
- [ ] Agent requests task with blocking dependency → Gets retry duration
- [ ] Blocking task completes → Agent retries and gets task
- [ ] Retry duration is intelligent (not fixed polling)
- [ ] Idle agents prioritized for unlocking tasks

**Status:** ✅ READY (validate with dependency chain)

---

### 12. "Subtask Coordination with Shared Conventions"

**Claim:**
When tasks decompose into subtasks, agents get shared conventions ensuring natural integration.

**Validation Checklist:**
- [ ] Multi-component task decomposes into subtasks
- [ ] All subtasks receive `shared_conventions` (response formats, naming, etc.)
- [ ] Subtasks can see sibling artifacts and decisions
- [ ] Integration happens naturally without coordination meetings

**Code References:**
- Subtask decomposition: `src/marcus_mcp/coordinator/decomposer.py::decompose_task()`
- Shared conventions: Returned in decomposition response
- Sibling context: `src/marcus_mcp/tools/context.py::_collect_sibling_subtask_context()` lines 331-397

**Test Cases Needed:**
- [ ] Task decomposes into 3 subtasks (API, DB, UI)
- [ ] All 3 subtasks receive same `shared_conventions`
- [ ] Subtask 2 calls `get_task_context()` → Sees artifacts from subtask 1
- [ ] Code integrates without conflicts

**Status:** ✅ READY (validate with subtask workflow)

---

## Complexity Mode Comparison Matrix

**Claim:** Different modes optimize for different use cases.

| Feature Type | Prototype Mode | Standard Mode | Enterprise Mode |
|-------------|----------------|---------------|-----------------|
| **Atomic** (1 file) | 1 task (Impl) | 1 task (Impl) | 2 tasks (Impl + Test) |
| **Simple** (1 component) | 1 task (Impl) | 2 tasks (Impl + Test) | 3 tasks (Design + Impl + Test) |
| **Coordinated** (API+DB+UI) | 2 tasks (Impl + Test) | 3 tasks (Design + Impl + Test) | 3+ tasks (Design + Impl + Test) |
| **Distributed** (multi-service) | 2 tasks (Impl + Test) | 3+ tasks | 4+ tasks (comprehensive) |

**Validation:**
- [ ] All 12 combinations tested (4 complexity × 3 modes)
- [ ] Actual task counts match table
- [ ] Mode selection works via `options` parameter in `create_project()`

**Code Reference:**
- `src/ai/advanced/prd/advanced_parser.py::_select_task_pattern()` lines 1266-1446

**Status:** ✅ READY (merged in PR #112)

---

## Use Case Validation

### Use Case 1: Solo Developer - Simple Chrome Extension

**Scenario:**
Developer wants to add a dark mode toggle to their extension.

**Expected Flow:**
1. `create_project("Add dark mode toggle to chrome extension", "dark-mode-feature")`
2. Marcus classifies: Atomic feature
3. Creates: 1 task "Implement Dark Mode Toggle"
4. 1 agent implements, commits, pushes to branch
5. Developer reviews branch next day

**Validation Checklist:**
- [ ] Only 1 task created (not 3)
- [ ] Agent completes in ~15-30 minutes
- [ ] Git commit with task ID
- [ ] Branch ready for review

**Status:** ⚠️ NEEDS INTEGRATION TEST

---

### Use Case 2: Startup - Todo App MVP

**Scenario:**
Build a full-stack todo app with vanilla JS, no frameworks.

**Expected Flow:**
1. `create_project("Build todo app with vanilla JS frontend, Node.js backend, SQLite database. CRUD operations for todos.", "todo-app-mvp", {complexity: "prototype"})`
2. Marcus extracts constraints: `["vanilla-js", "no-frameworks"]`
3. Classifies features: 3 simple (CRUD), 1 coordinated (auth)
4. Creates: ~8 tasks total (minimal for prototype mode)
5. 3 agents work in parallel, complete in 2-4 hours
6. All agents respect vanilla JS constraint

**Validation Checklist:**
- [ ] Constraints extracted: `vanilla-js`, `no-frameworks`
- [ ] Task descriptions avoid React/Vue/Angular
- [ ] Prototype mode uses minimal task patterns
- [ ] 3 agents complete in <4 hours
- [ ] All code on branches with git history

**Status:** ⚠️ NEEDS INTEGRATION TEST

---

### Use Case 3: Enterprise - E-commerce Platform

**Scenario:**
Build full e-commerce platform with user auth, product catalog, shopping cart, payment integration, admin dashboard.

**Expected Flow:**
1. `create_project("Build e-commerce platform with: user authentication, product catalog with search, shopping cart, Stripe payment integration, admin dashboard for inventory management", "ecommerce-platform", {complexity: "enterprise"})`
2. Marcus classifies: 5 coordinated/distributed features
3. Creates: 30+ tasks with full Design → Implement → Test pattern
4. 5 agents work in parallel
5. Design agents create API specs, schemas, architecture docs
6. Implementation agents read specs and build to spec
7. Test agents verify against specifications
8. Complete in days (not weeks)

**Validation Checklist:**
- [ ] 30+ tasks created
- [ ] Each major feature gets Design task
- [ ] Artifacts created in `docs/` directories
- [ ] Implementation agents read artifacts from dependencies
- [ ] Architectural decisions logged
- [ ] 5 agents work simultaneously
- [ ] 3-5x speedup vs sequential

**Status:** ⚠️ NEEDS INTEGRATION TEST + BENCHMARK

---

## Performance Benchmarks Needed

### Benchmark 1: Single Agent vs Multi-Agent (Todo App)

**Hypothesis:** 3 agents complete in 1/3 the time

**Setup:**
- Project: Todo app (8 features)
- Configuration: Standard mode
- Measure: Wall-clock time to completion

**Expected Results:**
- 1 agent: 6-8 hours
- 3 agents: 2-3 hours
- Speedup: ~2.5x

**Status:** ⚠️ NOT TESTED

---

### Benchmark 2: Task Generation Overhead

**Hypothesis:** Task generation adds <1 minute overhead

**Setup:**
- Project: Simple feature (dark mode toggle)
- Measure: Time from `create_project()` call to first task assigned

**Expected Results:**
- PRD analysis: ~5 seconds
- Task generation: ~10 seconds
- Task creation on board: ~5 seconds
- Total overhead: <30 seconds

**Status:** ⚠️ NOT TESTED

---

### Benchmark 3: Constraint Violation Detection

**Hypothesis:** 95%+ accuracy in detecting constraint violations

**Setup:**
- Create projects with "vanilla-js", "no-frameworks" constraints
- Count how many task descriptions violate constraints
- Verify violation detection catches them

**Expected Results:**
- <5% false positives (vanilla JS flagged as framework)
- >95% true positives (React mentioned when "no-frameworks")

**Status:** ⚠️ NOT TESTED

---

## Marketing Claims - Final Checklist

### Tier 1: Core Claims (MUST validate before advertising)

- [ ] **"Natural language → Autonomous execution"** - Integration test
- [ ] **"Intelligent scaling (1 task for simple, 3+ for complex)"** - Unit tests passing (PR #112) ✅
- [ ] **"Constraint enforcement (vanilla-js, no-frameworks)"** - Unit tests passing (PR #114) ✅
- [ ] **"Walk away and come back to code on branches"** - Agent workflow test
- [ ] **"Git commits with full traceability"** - Verify branch naming + task IDs
- [ ] **"2-3x speedup with parallel agents"** - Benchmark needed

### Tier 2: Advanced Claims (Nice to have validation)

- [ ] **"Decision logging with audit trail"** - Feature exists, validate usage
- [ ] **"Artifact system (API specs, schemas)"** - Feature exists, validate workflow
- [ ] **"GitHub code awareness"** - Validate code_analyzer reads actual code
- [ ] **"Testing enforcement"** - Validate agents run tests
- [ ] **"Intelligent retry logic"** - Feature exists, validate timing

### Tier 3: Mode-Specific Claims

- [ ] **Prototype mode: Minimal overhead** - Test simple project
- [ ] **Standard mode: Balanced quality/speed** - Test medium project
- [ ] **Enterprise mode: Full traceability** - Test complex project

---

## Recommended Validation Order

### Phase 1: Core Functionality (This Week)
1. ✅ Unit tests for task pattern selection (PR #112) - DONE
2. ✅ Unit tests for constraint propagation (PR #114) - DONE
3. ⚠️ Integration test: Simple project end-to-end
4. ⚠️ Integration test: Multi-agent parallel execution
5. ⚠️ Verify git commits include task IDs

### Phase 2: Performance & Benchmarks (Next Week)
6. ⚠️ Benchmark: 1 agent vs 3 agents (measure speedup)
7. ⚠️ Benchmark: Task generation overhead
8. ⚠️ Benchmark: Constraint violation accuracy

### Phase 3: Advanced Features (Following Week)
9. ⚠️ Validate: Decision logging workflow
10. ⚠️ Validate: Artifact system workflow
11. ⚠️ Validate: GitHub code awareness
12. ⚠️ Validate: Testing enforcement

---

## Safe-to-Advertise Claims (Today)

### What You Can Claim Right Now:

✅ **"Marcus automatically breaks down project descriptions into tasks"**
- Backed by: PRD parser (working for 4 months)

✅ **"Agents work autonomously without user intervention"**
- Backed by: Agent continuous work loop (working for 4 months)

✅ **"Intelligent task patterns based on complexity"**
- Backed by: PR #112 merged, unit tests passing

✅ **"Technical constraints (vanilla-js, no-frameworks) enforced"**
- Backed by: PR #114 merged, unit tests passing

✅ **"Full git traceability with task IDs in commits"**
- Backed by: Agent prompt instructions (validate with one test)

✅ **"Supports Planka, GitHub, Linear project management"**
- Backed by: Provider integrations in codebase

### What Needs Validation Before Advertising:

⚠️ **"2-3x faster with parallel agents"**
- Need benchmark data

⚠️ **"Walk away and come back to working code"**
- Need integration test showing full workflow

⚠️ **"Automatic artifact sharing (API specs, schemas)"**
- Need multi-task workflow validation

---

## Suggested Marketing Copy (Conservative)

### Landing Page Hero

**Before Validation:**
> "Describe your project in natural language. Marcus creates tasks and coordinates AI agents to build it autonomously."

**After Validation (with benchmarks):**
> "Describe your project in natural language. Marcus creates tasks and coordinates AI agents to build it 2-3x faster. Walk away and come back to working code on git branches."

### Feature List (Safe Now)

✅ **Natural Language Task Generation**
Turn project descriptions into executable tasks automatically

✅ **Intelligent Complexity Scaling**
Simple features → 1 task. Complex features → 3+ tasks with proper design

✅ **Constraint Enforcement**
Technical requirements (vanilla-js, no-frameworks) respected throughout

✅ **Autonomous Execution**
Agents work continuously without user intervention

✅ **Full Git Traceability**
Every change committed with task IDs for complete audit trail

✅ **Multi-Provider Support**
Works with Planka, GitHub, and Linear

### Feature List (After Validation)

✅ **2-3x Faster with Parallel Agents**
Multiple agents work simultaneously on different tasks

✅ **Automatic Coordination**
Agents share artifacts (API specs, schemas) and architectural decisions

✅ **Walk-Away Development**
Start agents, walk away, come back to completed features

---

## Next Steps

1. **This Week:** Run integration tests for core workflow
2. **Next Week:** Run benchmarks for speedup claims
3. **Following Week:** Validate advanced features (artifacts, decisions)
4. **Then:** Update marketing copy with validated claims + benchmark data

---

## Success Metrics for "Ready to Advertise"

- [ ] ≥3 integration tests passing (simple, medium, complex projects)
- [ ] ≥1 benchmark showing measurable speedup
- [ ] Git commit traceability verified
- [ ] Constraint enforcement verified (no false violations)
- [ ] Agent autonomous workflow verified (no user prompts needed)
- [ ] All Tier 1 claims validated
- [ ] Marketing copy updated with conservative claims only

**Target Date for Full Advertising:** [Fill in after validation]

---

## Notes

- **Conservative Approach:** Only advertise what's been validated
- **Proof Points:** Back every claim with code reference or test
- **Honesty:** Don't claim "guaranteed working code" - say "working code on branches ready for review"
- **Differentiation:** Emphasize what single-agent systems CAN'T do (parallel execution, automatic coordination)
