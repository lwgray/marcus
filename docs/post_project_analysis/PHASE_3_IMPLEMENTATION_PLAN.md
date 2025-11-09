# Phase 3 Implementation Plan: Cato Integration

## Overview

This document provides an implementation plan for Phase 3 that correctly integrates with the actual Phase 1 and Phase 2 APIs as implemented.

**Status:** Ready for implementation
**Dependencies:** Phase 1 ✅ Complete, Phase 2 ✅ Complete
**Duration:** 5-7 days
**Deliverable:** Web UI for post-project analysis and diagnosis

## What Phase 1 & 2 Actually Provide

### Phase 1: Data Foundation

**Aggregator API (`ProjectHistoryAggregator`):**
```python
aggregator = ProjectHistoryAggregator()
history = await aggregator.aggregate_project(
    project_id="proj-123",
    include_conversations=True,
    include_kanban=False,
)
# Returns: ProjectHistory with tasks, decisions, artifacts, agents, timeline
```

**Query API (`ProjectHistoryQuery`):**
```python
query = ProjectHistoryQuery(aggregator)

# Get project history
history = await query.get_project_history(project_id)

# Get project summary
summary = await query.get_project_summary(project_id)

# Find specific tasks
failed_tasks = await query.find_tasks_by_status(project_id, "failed")
blocked_tasks = await query.find_blocked_tasks(project_id)

# Find decisions
decisions = await query.find_decisions_by_task(project_id, task_id)

# Get agent performance
metrics = await query.get_agent_performance_metrics(project_id, agent_id)
```

**Data Structures:**
- `ProjectHistory`: Complete project data
- `TaskHistory`: Full task execution trace
- `Decision`: Architectural decisions made
- `ArtifactMetadata`: Files and outputs produced
- `AgentHistory`: Agent performance metrics

### Phase 2: LLM Analysis

**Analyzer API (`PostProjectAnalyzer`):**
```python
# Initialize (no parameters needed)
analyzer = PostProjectAnalyzer()

# Run analysis
analysis = await analyzer.analyze_project(
    project_id="proj-123",
    tasks=history.tasks,          # From Phase 1
    decisions=history.decisions,  # From Phase 1
    scope=None,  # Optional: selective analysis
    progress_callback=None,  # Optional: progress tracking
)

# Returns: PostProjectAnalysis with:
# - requirement_divergences: list[RequirementDivergenceAnalysis]
# - decision_impacts: list[DecisionImpactAnalysis]
# - instruction_quality_issues: list[InstructionQualityAnalysis]
# - failure_diagnoses: list[FailureDiagnosis]
# - summary: str (executive summary)
# - metadata: dict
```

**MCP Tools Available:**
Via Marcus MCP server at `src/marcus_mcp/tools/post_project_analysis.py`:
- `analyze_project(project_id, scope=None)`
- `get_requirement_divergence(project_id, task_ids=None)`
- `get_decision_impacts(project_id, decision_ids=None)`
- `get_instruction_quality(project_id, task_ids=None)`
- `get_failure_diagnoses(project_id, task_ids=None)`

## Cato Backend API Endpoints

### Required Endpoints (Corrected)

Add these endpoints to `/Users/lwgray/dev/cato/backend/api.py`:

```python
from src.analysis.aggregator import ProjectHistoryAggregator
from src.analysis.query_api import ProjectHistoryQuery
from src.analysis.post_project_analyzer import PostProjectAnalyzer

# Initialize once
aggregator = ProjectHistoryAggregator()
query_api = ProjectHistoryQuery(aggregator)

@app.get("/api/historical/projects")
async def list_completed_projects():
    """
    List all completed projects with summary metrics.

    Returns
    -------
    {
      "projects": [
        {
          "project_id": "marcus_proj_123",
          "project_name": "Task Management API",
          "total_tasks": 24,
          "completed_tasks": 22,
          "completion_rate": 91.7,
          "blocked_tasks": 1,
          "total_decisions": 15,
          "project_duration_hours": 48.5
        }
      ]
    }
    """
    # Find all project IDs from persistence layer
    from pathlib import Path
    history_dir = Path(__file__).parent.parent / "data" / "project_history"

    projects = []
    if history_dir.exists():
        for project_dir in history_dir.iterdir():
            if project_dir.is_dir():
                project_id = project_dir.name
                try:
                    summary = await query_api.get_project_summary(project_id)
                    projects.append(summary)
                except Exception as e:
                    logger.warning(f"Error loading project {project_id}: {e}")

    return {"projects": projects}


@app.get("/api/historical/projects/{project_id}")
async def get_project_history(project_id: str):
    """
    Get complete project history (raw data only, no LLM analysis).

    Fast endpoint for browsing project data.
    """
    history = await query_api.get_project_history(project_id)

    return {
        "project_id": history.project_id,
        "snapshot": history.snapshot.to_dict() if history.snapshot else None,
        "tasks": [t.to_dict() for t in history.tasks],
        "agents": [a.to_dict() for a in history.agents],
        "decisions": [d.to_dict() for d in history.decisions],
        "artifacts": [a.to_dict() for a in history.artifacts],
        "timeline_count": len(history.timeline),
    }


@app.get("/api/historical/projects/{project_id}/summary")
async def get_project_summary(project_id: str):
    """Get high-level project summary statistics."""
    return await query_api.get_project_summary(project_id)


@app.get("/api/historical/projects/{project_id}/analysis")
async def get_project_analysis(project_id: str):
    """
    Run complete LLM-powered post-project analysis.

    This is the heavy endpoint - may take 10-30 seconds.
    Includes all Phase 2 analyzers.
    """
    # Load project history
    history = await query_api.get_project_history(project_id)

    # Run Phase 2 analysis
    analyzer = PostProjectAnalyzer()
    analysis = await analyzer.analyze_project(
        project_id=project_id,
        tasks=history.tasks,
        decisions=history.decisions,
    )

    # Get summary stats from Phase 1
    summary = await query_api.get_project_summary(project_id)

    # Combine Phase 1 + Phase 2 data
    return {
        # Phase 1 summary stats
        "project_id": analysis.project_id,
        "project_name": summary["project_name"],
        "total_tasks": summary["total_tasks"],
        "completed_tasks": summary["completed_tasks"],
        "completion_rate": summary["completion_rate"],
        "blocked_tasks": summary["blocked_tasks"],
        "total_decisions": summary["total_decisions"],
        "project_duration_hours": summary["project_duration_hours"],

        # Phase 2 analysis results
        "analysis_timestamp": analysis.analysis_timestamp.isoformat(),
        "summary": analysis.summary,
        "requirement_divergences": [
            {
                "task_id": rd.task_id,
                "fidelity_score": rd.fidelity_score,
                "divergences": [
                    {
                        "requirement": d.requirement,
                        "implementation": d.implementation,
                        "severity": d.severity,
                        "impact": d.impact,
                        "citation": d.citation,
                    }
                    for d in rd.divergences
                ],
                "recommendations": rd.recommendations,
            }
            for rd in analysis.requirement_divergences
        ],
        "decision_impacts": [
            {
                "decision_id": di.decision_id,
                "impact_chains": [
                    {
                        "decision_summary": ic.decision_summary,
                        "direct_impacts": ic.direct_impacts,
                        "indirect_impacts": ic.indirect_impacts,
                        "depth": ic.depth,
                        "citation": ic.citation,
                    }
                    for ic in di.impact_chains
                ],
                "unexpected_impacts": [
                    {
                        "affected_task": ui.affected_task_name,
                        "anticipated": ui.anticipated,
                        "actual_impact": ui.actual_impact,
                        "severity": ui.severity,
                    }
                    for ui in di.unexpected_impacts
                ],
                "recommendations": di.recommendations,
            }
            for di in analysis.decision_impacts
        ],
        "instruction_quality_issues": [
            {
                "task_id": iq.task_id,
                "quality_scores": {
                    "clarity": iq.quality_scores.clarity,
                    "completeness": iq.quality_scores.completeness,
                    "specificity": iq.quality_scores.specificity,
                    "overall": iq.quality_scores.overall,
                },
                "ambiguity_issues": [
                    {
                        "aspect": ai.ambiguous_aspect,
                        "evidence": ai.evidence,
                        "consequence": ai.consequence,
                        "severity": ai.severity,
                    }
                    for ai in iq.ambiguity_issues
                ],
                "recommendations": iq.recommendations,
            }
            for iq in analysis.instruction_quality_issues
        ],
        "failure_diagnoses": [
            {
                "task_id": fd.task_id,
                "failure_causes": [
                    {
                        "category": fc.category,
                        "root_cause": fc.root_cause,
                        "contributing_factors": fc.contributing_factors,
                        "evidence": fc.evidence,
                    }
                    for fc in fd.failure_causes
                ],
                "prevention_strategies": [
                    {
                        "strategy": ps.strategy,
                        "rationale": ps.rationale,
                        "effort": ps.effort,
                        "priority": ps.priority,
                    }
                    for ps in fd.prevention_strategies
                ],
                "lessons_learned": fd.lessons_learned,
            }
            for fd in analysis.failure_diagnoses
        ],
        "metadata": analysis.metadata,
    }


@app.get("/api/historical/projects/{project_id}/tasks/{task_id}")
async def get_task_history(project_id: str, task_id: str):
    """Get detailed history for a specific task."""
    history = await query_api.get_project_history(project_id)

    # Find the task
    task = next((t for t in history.tasks if t.task_id == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task.to_dict()


@app.get("/api/historical/projects/{project_id}/tasks")
async def get_project_tasks(project_id: str, status: Optional[str] = None):
    """
    Get all tasks for a project, optionally filtered by status.

    Query parameters:
    - status: Filter by task status (completed, failed, blocked)
    """
    if status:
        tasks = await query_api.find_tasks_by_status(project_id, status)
    else:
        history = await query_api.get_project_history(project_id)
        tasks = history.tasks

    return {"tasks": [t.to_dict() for t in tasks]}
```

## What We DON'T Have Yet

The following features from the original Phase 3 spec are **NOT** yet implemented and would need to be built:

### Missing Features

1. **`list_completed_projects()` endpoint** - Need to scan the project_history directory to find all projects
2. **Feature-based failure diagnosis** - The Phase 2 analyzers work on tasks, not "features"
3. **Decision impact graph traversal** - We have decision impacts but not graph visualization helpers
4. **Pre-computed analysis cache** - Analysis runs on-demand, no caching yet

### Features We CAN Build With Current APIs

1. ✅ **Project selector** - Use `get_project_summary()` for each project
2. ✅ **Project retrospective dashboard** - Use `get_project_analysis()`
3. ✅ **Task execution trace viewer** - Use `get_task_history()`
4. ✅ **Requirement fidelity visualization** - Data available in analysis results
5. ✅ **Decision impact visualization** - Data available in analysis results
6. ✅ **Failure diagnosis display** - Data available in analysis results

## Implementation Approach

### Option A: Simple Approach (Recommended)

Build Phase 3 UI with what we have now:

1. **Project Selector** - List projects by scanning directory, show summaries
2. **Project Dashboard** - Display analysis results from Phase 2
3. **Task Detail View** - Show individual task history
4. **Raw Data Toggle** - Show/hide JSON alongside LLM interpretations

**Pros:**
- Can start immediately
- Uses proven APIs
- No new backend code needed

**Cons:**
- No "feature-based" queries (only task-based)
- No caching (slower for large projects)

### Option B: Extended Approach

Build missing APIs first, then UI:

1. **New Query Methods:**
   ```python
   # In query_api.py
   async def list_all_projects(self) -> list[dict]:
       """Scan project_history dir and return all projects."""

   async def trace_decision_impact_graph(self, project_id: str, decision_id: str):
       """Build complete impact graph for a decision."""
   ```

2. **Caching Layer:**
   ```python
   # In Cato backend
   @lru_cache(maxsize=10)
   async def get_cached_analysis(project_id: str):
       """Cache analysis results."""
   ```

3. **Feature Query:**
   ```python
   # New analyzer
   async def diagnose_feature_failure(self, project_id: str, feature_query: str):
       """Map feature to tasks and diagnose."""
   ```

**Pros:**
- More complete feature set
- Better performance

**Cons:**
- More work before UI can start
- Need to design new APIs carefully

## Recommended Next Steps

1. **Start with Option A** - Build UI with existing APIs
2. **Get user feedback** - See what's actually useful
3. **Add features incrementally** - Based on real needs

## Updated Phase 3 Spec Reference

The original `post_project_analysis_PHASE_3.md` document has several API references that don't match our implementation:

| Original Spec | Actual API | Status |
|---------------|------------|--------|
| `query.list_completed_projects()` | Need to build | ❌ Missing |
| `query.get_project_history(project_id)` | ✅ Exists | ✅ Works |
| `PostProjectAnalyzer(query_api, ai_engine)` | `PostProjectAnalyzer()` | ⚠️ Different signature |
| `query.get_task_history(project_id, task_id)` | Need to filter tasks list | ⚠️ Workaround available |
| `analyzer.diagnose_failure(project_id, query)` | Not implemented | ❌ Missing |
| `query.trace_decision_impact(project_id, decision_id)` | Not implemented | ❌ Missing |

**Action:** Update `post_project_analysis_PHASE_3.md` with correct API references or create this new implementation plan as the source of truth.

## Success Criteria (Adjusted)

Phase 3 MVP is complete when:

✅ Historical mode toggle in Cato header
✅ Project selector lists all projects from disk
✅ Project summary dashboard displays Phase 1 metrics
✅ Project analysis view displays Phase 2 LLM insights
✅ Task detail view shows complete task history
✅ Raw data toggle shows/hides JSON data
✅ UI tests passing for all components
✅ End-to-end test validates full workflow
✅ Documentation with screenshots

## Timeline (Revised)

### Day 1: Setup & API Integration
- Add Cato backend endpoints
- Test endpoints with real data
- Verify Phase 1 & 2 integration

### Day 2-3: Core UI
- Project selector component
- Project summary dashboard
- Task list view

### Day 4-5: Analysis Views
- Requirement divergence visualization
- Decision impact display
- Failure diagnosis display
- Instruction quality display

### Day 6-7: Polish & Testing
- Raw data toggles
- Error handling
- End-to-end tests
- Documentation

## Next Action

Choose implementation approach and document decision in this file. Recommended: **Start with Option A** for faster delivery and real user feedback.
