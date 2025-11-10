# Master Implementation Order
**Date**: 2025-11-09
**Status**: Strategic Planning - FINALIZED
**Scope**: Coordinates three major workstreams

---

## Executive Summary

**Recommended Order**: Phase 3 → MVP → Cato MCP

**Why This Order**:
1. **Phase 3** works with existing historical data (no MVP dependencies)
2. **MVP** fundamentally changes Marcus architecture (Feature entity, workspace isolation, feature context)
3. **Cato MCP** needs to be built with Feature context from day 1 (avoid expensive refactoring)

**Key Insight**: Building Cato MCP before MVP would mean building it twice - once without features, then refactoring to add feature context. Much better to build it once with the full feature model.

---

## Current State (Reality Check)

### What's Actually Built

✅ **Post-Project Analysis Phase 1**: Complete
- SQLite-based historical data query API
- Conversation logs as source of truth
- Pagination system
- 26 tests passing

✅ **Post-Project Analysis Phase 2**: Complete
- LLM-powered analysis engine
- 4 analysis modules (requirement divergence, decision impacts, instruction quality, failure diagnosis)
- MCP tools for analysis

### What's NOT Built

❌ **MVP Implementation (WEEK 1-6)**: Not built
- Week 1: Configuration management
- Week 2: Feature entity
- Week 3: Workspace isolation
- Week 4: Feature context aggregation
- Week 5: CATO Integration API
- Week 6: Production readiness

❌ **Post-Project Analysis Phase 3**: In progress 🔨
- Cato UI integration for historical analysis

❌ **Cato MCP Integration**: Not started
- Replace Planka with Cato using MCP protocol

---

## The Three Workstreams

### 1. Post-Project Analysis Phase 3
**Duration**: 5-7 days
**Status**: Current work 🔨
**Location**: `/Users/lwgray/dev/marcus/docs/post_project_analysis/PHASE_3_IMPLEMENTATION_PLAN.md`

**What It Does**: Add historical project analysis visualization to Cato dashboard

**Key Deliverables**:
- Cato backend endpoints for historical data:
  ```python
  @app.get("/api/historical/projects")  # List all completed projects
  @app.get("/api/historical/projects/{project_id}")  # Get project history
  @app.get("/api/historical/projects/{project_id}/analysis")  # Run LLM analysis
  @app.get("/api/historical/projects/{project_id}/tasks")  # Get project tasks
  ```
- Project selector UI (list all completed projects)
- Project retrospective dashboard (Phase 2 analysis results)
- Task execution trace viewer
- Requirement divergence visualization
- Decision impact visualization
- Failure diagnosis display

**Why First**:
- ✅ No dependencies on MVP features
- ✅ Works with existing historical data from Phase 1-2
- ✅ Teaches us Cato UI patterns before major refactoring
- ✅ Provides immediate value (can analyze past projects now)

**Dependencies**: None (uses existing Phase 1-2 APIs)

---

### 2. MVP Implementation (WEEK 1-6)
**Duration**: 2-3 weeks
**Status**: Not started 🔜
**Location**: `/Users/lwgray/dev/marcus/docs/implementation/WEEK_*_PLAN.md`

**What It Does**: Add fundamental features to Marcus that change its architecture

**Week-by-Week Breakdown**:

#### Week 1: Configuration & Foundation (2-3 days)
**Goal**: Centralize configuration management

**Key Deliverables**:
- Type-safe configuration system (`src/config/marcus_config.py`)
- Validation with clear error messages
- Environment variable override support
- `config_marcus.example.json` template
- Migration of existing code

**Impact**: Makes deployment easier, unblocks all other work

---

#### Week 2: Workspace Isolation - Phase 1 (3-4 days)
**Goal**: Add Feature entity and prepare infrastructure

**Key Deliverables**:
- **Project and Feature dataclasses** (NEW DATA MODEL!)
  ```python
  @dataclass
  class Feature:
      feature_id: str
      project_id: str
      name: str
      description: str
      status: str
      branch_name: str  # For git worktree
      created_at: datetime
  ```
- **Feature-aware artifact and decision logging**
  ```python
  log_artifact(task_id, filename, content, artifact_type, feature_id)
  log_decision(agent_id, task_id, decision, feature_id)
  ```
- Feature indexing system
- WorkspaceManager skeleton

**Impact**: **Fundamental architecture change** - tasks now belong to features, not just projects

---

#### Week 3: Workspace Isolation - Phase 2 (3-4 days)
**Goal**: Implement git worktree-based workspace isolation

**Key Deliverables**:
- Full WorkspaceManager implementation
- Git worktree creation and cleanup
- Workspace conflict detection
- Integration with task assignment

**Impact**: Enables parallel agent work without conflicts

---

#### Week 4: Feature Context Aggregation (3-4 days)
**Goal**: Build comprehensive feature context automatically

**Key Deliverables**:
- **FeatureContextBuilder** (the core of feature intelligence!)
  ```python
  context = await builder.build_context(feature_id)
  # Returns:
  # - All git commits for this feature
  # - All artifacts created
  # - All decisions made
  # - All tasks completed/failed
  # - Dependencies and relationships
  ```
- Git commit tracking and annotation
- Context injection system
- `get_feature_context` and `get_feature_status` MCP tools

**Impact**: **This is the big one** - agents can understand full feature history

---

#### Week 5: Telemetry & CATO Integration (3-4 days)
**Goal**: Add real-time visualization and research instrumentation

**Key Deliverables**:
- User journey tracking system (milestone tracking)
- Research event logging (for MAS studies)
- **CATO Dashboard Integration API**:
  ```python
  # src/api/cato_routes.py
  @router.get("/api/cato/snapshot")  # System state with features!
  @router.get("/api/cato/events/stream")  # Real-time SSE stream
  @router.get("/api/cato/metrics/journey")  # User journey metrics
  @router.get("/api/cato/metrics/research")  # Research metrics
  @router.get("/api/cato/agent/{agent_id}")  # Agent details
  ```
- Real-time event broadcasting (SSE)

**Impact**: Enables real-time visualization of feature progress

---

#### Week 6: Production Readiness & MVP Release (3-4 days)
**Goal**: Make it production-ready

**Key Deliverables**:
- Core validations (Issues #118-125)
- Multi-stage Dockerfile and Docker Compose
- Comprehensive user documentation
- Performance testing and bug fixes
- MVP release (v0.1.0)

**Impact**: System is ready for production deployment

---

**Why Second**:
- ✅ Phase 3 complete, so we understand Cato UI
- ✅ Adds Feature entity (fundamental data model change)
- ✅ Adds feature context aggregation (critical for Cato MCP)
- ✅ Adds CATO Integration API (what Cato MCP will use)
- ✅ Building Cato MCP after this means building it once, correctly

**Dependencies**: None (Phase 3 doesn't need MVP features)

---

### 3. Cato MCP Integration (Stage 0-6)
**Duration**: 2-3 weeks
**Status**: Not started 🔜
**Location**: `/Users/lwgray/dev/marcus/docs/implementation/CATO_MCP_INTEGRATION_PLAN.md`

**What It Does**: Replace Planka with Cato as primary kanban provider using MCP protocol

**6 Stages**:

#### Stage 0: Planning & Setup (1-2 days)
- Understand Marcus SQLite schema (now with Features!)
- Design MCP tools that support feature context
- Create test data with features

#### Stage 1: Read-Only MCP Server (3-5 days)
- `CatoMCPServer` class
- Read tools:
  ```python
  @server.tool()
  async def cato_list_projects() -> Dict[str, Any]:
      # Returns projects with feature counts

  @server.tool()
  async def cato_list_features(project_id: str) -> Dict[str, Any]:
      # NEW: List features for a project

  @server.tool()
  async def cato_get_feature_context(feature_id: str) -> Dict[str, Any]:
      # NEW: Get full feature context (uses Week 4's FeatureContextBuilder!)

  @server.tool()
  async def cato_get_all_tasks(project_id: str, feature_id: Optional[str] = None):
      # Filter tasks by feature
  ```

#### Stage 2: Write Operations (3-4 days)
- Create/update/delete tasks
- **Support feature_id on task creation**
- Transaction handling
- Optimistic locking

#### Stage 3: Connect Marcus to Cato (3-4 days)
- `CatoClient` (MCP communication)
- `CatoKanban` provider (implements `KanbanInterface`)
- Register in Marcus
- **Workspace integration**: Sync workspace context to Cato

#### Stage 4: Improve Cato UI (2-3 days)
- Multi-project support
- **Feature visualization** (show feature relationships, progress)
- **Feature context panel** (show aggregated commits, artifacts, decisions)
- Drag-and-drop task management
- Task creation/editing modals

#### Stage 5: Migration & Setup Tools (1-2 days)
- `marcus migrate` command (migrate from Planka to Cato)
- `marcus start` command
- Setup wizard

#### Stage 6: Testing & Release (2-3 days)
- Comprehensive testing with features
- Ensure Phase 3 works with new MCP
- Documentation
- Release

---

**Why Third (Last)**:
- ✅ MVP features exist (Feature entity, feature context, workspace isolation)
- ✅ Can build Cato MCP with full feature support from day 1
- ✅ Avoid expensive refactoring (don't build it twice)
- ✅ MCP schema includes feature_id, feature context from the start
- ✅ Phase 3 already taught us Cato UI patterns

**Dependencies**: MVP Implementation (needs Feature entity and feature context)

---

## Timeline

```
┌─────────────────────────────────────────────────────────────────┐
│ Week 1        │ Week 2-4       │ Week 5-7                       │
├─────────────────────────────────────────────────────────────────┤
│ Phase 3       │ MVP            │ Cato MCP Integration           │
│ (5-7 days)    │ (Weeks 1-6)    │ (Stages 0-6)                   │
│               │ (2-3 weeks)    │ (2-3 weeks)                    │
├─────────────────────────────────────────────────────────────────┤
│ Historical    │ Feature Entity │ MCP with Feature Support       │
│ Analysis UI   │ + Context      │ Replace Planka                 │
│               │ + CATO API     │                                │
└─────────────────────────────────────────────────────────────────┘

Total Duration: 5-7 weeks
```

---

## Critical Dependencies

```
Post-Project Analysis Phase 1-2 (Complete)
    ↓
    └─→ Post-Project Analysis Phase 3 (Week 1)
            │ (No dependencies, works with existing data)
            ↓
            └─→ MVP Implementation (Weeks 2-4)
                    │ Adds Feature entity (Week 2)
                    │ Adds Workspace isolation (Week 3)
                    │ Adds Feature context aggregation (Week 4)
                    │ Adds CATO Integration API (Week 5)
                    ↓
                    └─→ Cato MCP Integration (Weeks 5-7)
                            ↓ Built with Feature support from day 1
                            └─→ Complete System
                                - Live monitoring (Cato MCP)
                                - Historical analysis (Phase 3)
                                - Feature intelligence (MVP)
```

---

## Why This Order? (The Logic)

### Phase 3 First

**Pros**:
- ✅ No dependencies on MVP
- ✅ Works with existing Phase 1-2 APIs
- ✅ Provides immediate value (analyze past projects)
- ✅ Teaches us Cato UI patterns before major refactoring
- ✅ Quick win (5-7 days)

**Cons**:
- None (completely independent)

---

### MVP Second

**Pros**:
- ✅ Fundamentally changes Marcus architecture
- ✅ Adds Feature entity (needed by Cato MCP)
- ✅ Adds feature context aggregation (critical for intelligent task management)
- ✅ Adds CATO Integration API (what Cato MCP will consume)
- ✅ If built after Cato MCP, would require expensive refactoring

**Cons**:
- Takes 2-3 weeks (but necessary foundation)

**Why Not Last**:
- ❌ Cato MCP built without features = built twice
- ❌ Adding features later = expensive schema migrations
- ❌ Feature context is fundamental, not optional

---

### Cato MCP Third (Last)

**Pros**:
- ✅ Built with full knowledge of Feature entity
- ✅ MCP schema includes feature_id from day 1
- ✅ MCP tools support feature context queries from day 1
- ✅ No refactoring needed
- ✅ Can use CATO Integration API from MVP Week 5
- ✅ Phase 3 already taught us Cato UI patterns

**Cons**:
- None (this is the optimal position)

**Why Not First**:
- ❌ Would need to refactor when MVP adds features
- ❌ Schema would need migration to add feature_id
- ❌ MCP tools would need to be rewritten for feature context

**Why Not Second (before MVP)**:
- ❌ Same problems as "first"
- ❌ Building without feature support = technical debt

---

## The Feature Context Problem (Why Order Matters)

### Scenario A: Cato MCP BEFORE MVP (Wrong Order)

```
Week 1-3: Build Cato MCP
├─ Schema: {project_id, task_id, status, priority}
├─ MCP Tools: cato_list_tasks(project_id)
└─ Works! ✅

Week 4-6: Build MVP (adds Feature entity)
├─ Now tasks have: {project_id, feature_id, task_id, ...}
├─ Schema migration needed 💥
├─ MCP tools need rewrite:
│   - cato_list_tasks(project_id, feature_id?)
│   - cato_get_feature_context(feature_id) <- NEW TOOL
├─ Cato UI needs feature visualization 💥
└─ Expensive refactoring! ❌

Total cost: Build + Refactor = 5-6 weeks
```

### Scenario B: MVP BEFORE Cato MCP (Correct Order)

```
Week 1: Build Phase 3
└─ Works with existing data ✅

Week 2-4: Build MVP (adds Feature entity)
├─ Schema: {project_id, feature_id, task_id, ...}
├─ Feature context builder
└─ CATO Integration API ✅

Week 5-7: Build Cato MCP (with feature support from day 1)
├─ Schema: {project_id, feature_id, task_id, ...} ✅
├─ MCP Tools:
│   - cato_list_features(project_id)
│   - cato_get_feature_context(feature_id)
│   - cato_list_tasks(project_id, feature_id?)
├─ Cato UI: Feature visualization from day 1 ✅
└─ Built once, correctly! ✅

Total cost: Phase 3 + MVP + Cato MCP = 5-7 weeks
(Same time, but no refactoring!)
```

**Conclusion**: Building Cato MCP before MVP saves 0 weeks but creates massive technical debt. Building MVP first means building Cato MCP once, correctly.

---

## Success Criteria

### After Phase 3 (Week 1):
- ✅ Historical analysis UI in Cato
- ✅ Can analyze any completed Marcus project
- ✅ Understand Cato UI patterns
- ✅ Phase 1-2 integration tested

### After MVP (Week 4):
- ✅ Feature entity in Marcus core
- ✅ Workspace isolation working
- ✅ Feature context aggregation working
- ✅ CATO Integration API functional
- ✅ All MVP tests passing (100+ tests)
- ✅ Configuration centralized
- ✅ Docker deployment ready

### After Cato MCP (Week 7):
- ✅ Marcus uses Cato via MCP (Planka dependency removed)
- ✅ Cato supports all MVP features (features, workspaces, contexts)
- ✅ Real-time feature visualization
- ✅ Historical + Live modes in one dashboard
- ✅ Migration tools working
- ✅ End-to-end tests passing
- ✅ Production ready

---

## Risk Assessment

| Risk | Impact | Mitigation | When |
|------|--------|------------|------|
| Phase 3 breaks existing Cato | Medium | Incremental changes, thorough testing | Week 1 |
| MVP features incomplete | High | Follow week-by-week plan exactly | Weeks 2-4 |
| Feature context too complex | High | Start simple (Week 2), build incrementally | Weeks 2-4 |
| Cato MCP incompatible with features | Critical | MVP done first, schema designed upfront | Week 5 |
| Migration from Planka fails | High | Comprehensive migration tools (Stage 5) | Week 6-7 |
| Phase 3 needs refactoring after MVP | Low | Minimal - Phase 3 works with historical data | Week 4 |

---

## Alternative Orders (Considered and Rejected)

### Alternative A: Cato MCP → MVP → Phase 3
**Rejected because**: Cato MCP would need expensive refactoring after MVP adds features

### Alternative B: MVP → Cato MCP → Phase 3
**Rejected because**: Phase 3 is independent and provides quick value; no reason to delay it

### Alternative C: Parallel (Phase 3 + MVP at same time)
**Rejected because**: High coordination overhead, risk of conflicts

---

## Next Actions

### Immediate (This Week):
1. **Finish Post-Project Analysis Phase 3** (5-7 days)
   - Follow `PHASE_3_IMPLEMENTATION_PLAN.md`
   - Add historical endpoints to Cato backend
   - Build project selector UI
   - Build analysis visualization UI
   - Test end-to-end

### Week 2-4 (MVP Implementation):
1. **Week 1**: Configuration management
2. **Week 2**: Feature entity (critical!)
3. **Week 3**: Workspace isolation
4. **Week 4**: Feature context aggregation (critical!)
5. **Week 5**: CATO Integration API
6. **Week 6**: Production readiness

### Week 5-7 (Cato MCP Integration):
1. **Stage 0-1**: Read-only MCP with feature support
2. **Stage 2-3**: Write ops + Marcus integration
3. **Stage 4-6**: UI + migration + testing

---

## Documentation Updates Needed

- [ ] Update `MVP_IMPLEMENTATION_PLAN.md` status to "Not Started"
- [ ] Update `PHASE_3_IMPLEMENTATION_PLAN.md` to clarify it uses current Cato (no MVP features)
- [ ] Update `CATO_MCP_INTEGRATION_PLAN.md` to emphasize feature support from day 1
- [ ] Create `FEATURE_CONTEXT_DESIGN.md` to document the feature model before MVP Week 2

---

**Last Updated**: 2025-11-09
**Status**: FINALIZED - Ready to execute
**Recommended Order**: Phase 3 → MVP → Cato MCP
**Rationale**: Build Cato MCP once with full feature support, avoid expensive refactoring
