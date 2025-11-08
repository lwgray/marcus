# Marcus Documentation Audit Plan

**Created:** 2025-11-07
**Total Systems:** 55
**Estimated Time:** 10-12 sessions (20-30 hours)
**Approach:** Systematic, category-by-category deep audit

---

## Audit Methodology

### For Each System:
1. **Read complete documentation** (every line, every example)
2. **Locate implementation files** (grep for classes, functions)
3. **Compare signatures** (parameters, return types, defaults)
4. **Compare data structures** (dataclasses, fields, types)
5. **Compare behavior** (thresholds, logic, algorithms)
6. **Check examples** (do documented examples work?)
7. **Document discrepancies** (specific file:line references)

### Verification Checklist per System:
- [ ] Function signatures match
- [ ] Class structures match
- [ ] Parameters and return types match
- [ ] Threshold values match
- [ ] Algorithm descriptions match
- [ ] Code examples work
- [ ] Integration points accurate
- [ ] Status markers accurate

---

## Session Breakdown

### Session 1: Infrastructure Systems (Core Foundation) ✅ PARTIALLY DONE
**Systems:** 06, 08, 09, 10, 14, 15
**Time:** 3-4 hours
**Status:** 2/6 surface checked, need deep audit

**Systems:**
- [x] 06 - MCP Server (surface checked - needs deep)
- [x] 08 - Error Framework (surface checked - needs deep)
- [ ] 09 - Event-Driven Architecture
- [ ] 10 - Persistence Layer
- [ ] 14 - Workspace Isolation
- [ ] 15 - Service Registry

**Key Files to Check:**
- `src/marcus_mcp/server.py`
- `src/core/error_framework.py`
- `src/core/events.py`
- `src/core/persistence.py`
- `src/core/workspace.py`
- `src/core/service_registry.py`

---

### Session 2: Intelligence Systems (AI & Learning)
**Systems:** 01, 07, 17, 23, 27, 44
**Time:** 4-5 hours
**Status:** 1/6 partially checked

**Systems:**
- [~] 01 - Memory System (partially checked - needs completion)
- [ ] 07 - AI Intelligence Engine
- [ ] 17 - Learning Systems
- [ ] 23 - Task Management Intelligence
- [ ] 27 - Recommendation Engine
- [ ] 44 - Enhanced Task Classifier

**Key Files to Check:**
- `src/core/memory.py`
- `src/core/memory_advanced.py`
- `src/ai/llm_abstraction.py`
- `src/intelligence/`
- `src/learning/`

---

### Session 3: Agent Coordination Systems
**Systems:** 21, 26, 03, 12
**Time:** 2-3 hours
**Status:** 0/4 not checked

**Systems:**
- [ ] 21 - Agent Coordination
- [ ] 26 - Worker Support
- [ ] 03 - Context & Dependency System
- [ ] 12 - Communication Hub

**Key Files to Check:**
- `src/marcus_mcp/tools/agent.py`
- `src/worker/`
- `src/core/context.py`
- `src/communication/`

---

### Session 4: Project Management Systems (Part 1)
**Systems:** 16, 04, 34, 54
**Time:** 3-4 hours
**Status:** 2/4 checked

**Systems:**
- [ ] 16 - Project Management
- [ ] 04 - Kanban Integration
- [x] 34 - Create Project Tool (surface checked)
- [x] 54 - Hierarchical Task Decomposition (DEEP checked - discrepancies found)

**Key Files to Check:**
- `src/marcus_mcp/tools/project_management.py`
- `src/integrations/planka/`
- `src/integrations/github/`
- `src/integrations/nlp_tools.py`
- `src/marcus_mcp/coordinator/decomposer.py`
- `src/marcus_mcp/coordinator/subtask_manager.py`

---

### Session 5: Project Management Systems (Part 2)
**Systems:** 24, 25, 53, 47, 48, 49
**Time:** 3-4 hours
**Status:** 0/6 not checked

**Systems:**
- [ ] 24 - Analysis Tools
- [ ] 25 - Report Generation
- [ ] 53 - Workflow Management
- [ ] 47 - Active Project Overview
- [ ] 48 - Active Project Selection Reference
- [ ] 49 - Active Project Timing Analysis

**Key Files to Check:**
- `src/marcus_mcp/tools/analytics.py`
- `src/reports/`
- `src/workflow/`
- `src/core/project_context_manager.py`

---

### Session 6: Coordination & Dependencies Systems
**Systems:** 36, 35, 33, 31, 50, 51
**Time:** 3-4 hours
**Status:** 0/6 not checked

**Systems:**
- [ ] 36 - Task Dependency System
- [ ] 35 - Assignment Lease System
- [ ] 33 - Orphan Task Recovery
- [ ] 31 - Resilience
- [ ] 50 - CPM Analysis Overview
- [ ] 51 - CPM Subtask Timing Analysis

**Key Files to Check:**
- `src/core/adaptive_dependencies.py`
- `src/core/assignment_lease.py`
- `src/core/task_recovery.py`
- `src/core/resilience.py`

---

### Session 7: Quality, Testing & Monitoring
**Systems:** 18, 30, 11, 29, 37, 52, 55
**Time:** 3-4 hours
**Status:** 0/7 not checked

**Systems:**
- [ ] 18 - Quality Assurance
- [ ] 30 - Testing Framework
- [ ] 11 - Monitoring Systems
- [ ] 29 - Detection Systems
- [ ] 37 - Board Health Analyzer
- [ ] 52 - Gridlock Detection
- [ ] 55 - Task Graph Auto-Fix

**Key Files to Check:**
- `src/quality/`
- `tests/`
- `src/monitoring/`
- `src/detection/`
- `src/core/board_health_analyzer.py`
- `src/core/gridlock_detector.py`
- `src/core/task_graph_validator.py`

---

### Session 8: Development, Analysis & Security
**Systems:** 42, 43, 51, 45, 46
**Time:** 2-3 hours
**Status:** 0/5 not checked

**Systems:**
- [ ] 42 - Code Analysis System
- [ ] 43 - API Systems
- [ ] 51 - Security Systems
- [ ] 45 - Optimal Agent Scheduling (formerly 37)
- [ ] 46 - Smart Retry Strategy (formerly 38)

**Key Files to Check:**
- `src/core/code_analyzer.py`
- `src/api/`
- Security files (TBD location)
- `src/marcus_mcp/coordinator/scheduler.py`
- `src/core/error_strategies.py`

---

### Session 9: Data, Storage & Operations
**Systems:** 10, 32, 13, 19, 28
**Time:** 2-3 hours
**Status:** 0/5 not checked

**Systems:**
- [ ] 10 - Persistence Layer
- [ ] 32 - Core Models
- [ ] 13 - Cost Tracking
- [ ] 19 - NLP System
- [ ] 28 - Configuration Management

**Key Files to Check:**
- `src/core/persistence.py`
- `src/core/models.py`
- `src/cost_tracking/`
- `src/marcus_mcp/tools/nlp.py`
- `src/config/`

---

### Session 10: Visualization, Logging & Operations
**Systems:** 05, 02, 22, 20, 40, 41
**Time:** 2-3 hours
**Status:** 0/6 not checked

**Systems:**
- [ ] 05 - Visualization System
- [ ] 02 - Logging System
- [ ] 22 - Operational Modes
- [ ] 20 - Pipeline Systems
- [ ] 40 - Enhanced Ping Tool (if exists)
- [ ] 41 - Assignment Monitor (if exists)

**Key Files to Check:**
- `src/visualization/`
- `src/logging/`
- `src/modes/`
- `src/marcus_mcp/tools/pipeline.py`

---

### Session 11: Catch-up & Deep Dives
**Time:** 3-4 hours
**Purpose:**
- Re-audit systems with major discrepancies
- Check systems missed in numbering
- Verify cross-references between systems
- Update system interdependency diagrams

---

### Session 12: Final Review & Documentation Update
**Time:** 3-4 hours
**Tasks:**
- Compile master discrepancies report
- Prioritize fixes by severity
- Update all outdated documentation
- Create migration guides for breaking changes
- Update system README with accurate status
- Generate automated validation scripts

---

## Progress Tracking

### Overall Progress
- **Total Systems:** 55
- **Completed:** 1 (System 54 - deep)
- **Partially Completed:** 3 (Systems 01, 06, 08, 34 - surface)
- **Remaining:** 51
- **Percentage:** 2% deep, 7% surface = ~5% complete

### Session Completion
- [ ] Session 1: Infrastructure (0/6 deep)
- [ ] Session 2: Intelligence (0/6 deep)
- [ ] Session 3: Coordination (0/4)
- [ ] Session 4: Project Mgmt Part 1 (1/4 deep)
- [ ] Session 5: Project Mgmt Part 2 (0/6)
- [ ] Session 6: Dependencies (0/6)
- [ ] Session 7: Quality & Monitoring (0/7)
- [ ] Session 8: Dev & Security (0/5)
- [ ] Session 9: Data & Storage (0/5)
- [ ] Session 10: Visualization (0/6)
- [ ] Session 11: Catch-up
- [ ] Session 12: Final Review

---

## Deliverables Per Session

Each session produces:
1. **Session Report:** `docs/audit/SESSION_N_REPORT.md`
2. **Discrepancies Found:** Added to master list
3. **Updated System Status:** Checkmarks in this plan
4. **Code References:** File:line numbers for all issues

---

## Master Discrepancies Tracker

**Location:** `docs/DOCUMENTATION_DISCREPANCIES.md`

**Structure:**
```markdown
## System XX - System Name

**Severity:** 🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low

### Discrepancy #1: [Title]
- **Documented:** [what docs say]
- **Actual:** [what code does]
- **File:** `path/to/file.py:line`
- **Impact:** [user impact]
- **Fix Priority:** [P0/P1/P2/P3]
```

---

## Quality Standards

### Audit is "Complete" for a System When:
- ✅ Every function signature verified
- ✅ Every class structure verified
- ✅ Every code example tested
- ✅ All integration points checked
- ✅ Discrepancies documented with file:line references
- ✅ Status marker updated
- ✅ Cross-references validated

### Audit is "Surface" When:
- ⚠️ Only key functions checked
- ⚠️ Examples not tested
- ⚠️ May have missed discrepancies

---

## Next Session (Session 1)

**When:** Next working session
**Focus:** Infrastructure Systems (06, 08, 09, 10, 14, 15)
**Time Needed:** 3-4 hours

**Preparation:**
1. Read all 6 system docs completely
2. Have source code open
3. Take detailed notes
4. Create session report template

**Expected Outcome:**
- 6 systems fully audited
- Session 1 report created
- Infrastructure discrepancies documented
- Updated progress in this plan

---

## Notes

- Each session is designed to be ~3-4 hours
- Related systems grouped together for context
- Can pause/resume within sessions
- Priority is thoroughness over speed
- Document EVERYTHING - if unsure, it's a discrepancy

---

**Remember:** This is not about finding problems - it's about ensuring documentation accurately represents the powerful system you've built.
