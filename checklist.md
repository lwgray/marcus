# Project Checklist

## Planned Features

- [ ] [Enhancement] Add context access logging/traceability to get_task_context (#196)
- [ ] [Enhancement] Add detailed agent quality metrics to VALIDATION_METRICS (#186)
- [ ] [Enhancement] Revisit git worktree isolation for multi-agent branch conflicts (#250)
- [ ] [Enhancement] Project deletion UI — unified delete across Cato, ProjectRegistry, and kanban providers (#256) 🔴
- [ ] [Refactor] Extract KanbanWorkflowMixin to eliminate workflow duplication across providers (#251) 🟡
- [ ] [Refactor] Validator should evaluate evidence, not truncated source code (#270) 🟡
- [ ] [Enhancement] Add Integration Verification phase after implementation tasks complete (#271) 🔴
- [ ] [Feature] Cato Living Architecture Diagram — real-time IDEA flow with drill-down and GIF export (#378) 🟡
- [ ] [Enhancement] Spread-first task assignment for independent tasks (#379) 🔴
- [ ] [Research] Auto-select decomposer strategy — remove MARCUS_DECOMPOSER user knob (#382) 🔴
- [ ] [Feature] Synthetic agent — deterministic Marcus-protocol agent for CI, research, and runner validation (#383) 🟡
- [ ] [Feature] Terminate agents automatically when experiment/project completes (#389) 🔴
- [ ] [Feature] BuildKits system — package, publish, and reuse agent-built project templates (#415) 🟡
- [ ] [Feature] Persistent metrics store for validation, lease, and blocker health (#418) 🟡

## Bug Fixes

- [ ] [Bug] Agents from concurrent experiments steal tasks across project boundaries (#388) 🔴
- [ ] [Bug] Validation cannot access acceptance criteria stored as Planka checklists (#189)
- [ ] [Performance] Project filtering loads all 6,970 tasks instead of project subset (#192)
- [ ] [Bug] feature_based agents receive contract docs as primary spec, produce stubs instead of implementations (#353) 🔴
- [ ] [Bug] Stale dedup cache causes project to be planned under literal name "CachedProject" (#419) 🔴
- [ ] [Bug] project_config entries accumulate in marcus.db indefinitely — 184 orphaned rows with no matching kanban project (#420) 🟡
