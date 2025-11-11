# Phase 3 Implementation Plan: Cato Integration

## Overview

This document provides an implementation plan for Phase 3 that correctly integrates with the actual Phase 1 and Phase 2 APIs as implemented.

**Status:** Ready for implementation (Updated for Cato v0.1)
**Dependencies:** Phase 1 ✅ Complete, Phase 2 ✅ Complete, Cato v0.1 ✅ Released
**Duration:** 5-7 days
**Deliverable:** Web UI for post-project analysis and diagnosis

## Cato v0.1 Architecture (December 2024)

**IMPORTANT:** Cato has been significantly refactored since the original Phase 3 design. This implementation plan reflects the current Cato v0.1 architecture.

### Key Changes in Cato v0.1

1. **✅ Mock Mode Removed** - Cato now uses live-only data architecture
2. **✅ Background Auto-Refresh** - 60-second automatic refresh (disable in historical mode)
3. **✅ Newest Project Selection** - Projects auto-sorted by most recent activity
4. **✅ On-Demand Project Refresh** - Dropdown click refreshes project list
5. **✅ Linear Timeline** - Power scale changed from 0.4 to 1.0 for accurate time representation
6. **✅ Bundled Design Tasks Fixed** - Critical blocker resolved (commit 639523f)
7. **✅ State Preservation** - Playback position preserved during refresh

### Current Cato Architecture

```typescript
// visualizationStore.ts (current state)
interface VisualizationState {
  snapshot: Snapshot | null;
  isLoading: boolean;
  loadError: string | null;

  // Project management (already working)
  projects: Project[];  // Auto-sorted by newest first
  selectedProjectId: string | null;

  // Auto-refresh (always-on for live data)
  autoRefreshIntervalId: number | null;
  autoRefreshInterval: number;  // 60000ms = 60 seconds

  // View layers
  currentLayer: 'network' | 'swimlanes' | 'conversations';

  // Actions (already working)
  loadData: (projectId?: string) => Promise<void>;
  loadProjects: () => Promise<void>;  // Sorted by newest
  setSelectedProject: (projectId: string | null) => void;
  refreshData: () => Promise<void>;
  startAutoRefresh: () => void;
  stopAutoRefresh: () => void;
}
```

**Live Data Flow:**
```
Marcus (running) → HTTP API → Cato Backend → fetchSnapshot() → React UI
                                                     ↓
                                          Auto-refresh every 60s
```

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
# - task_redundancy: Optional[TaskRedundancyAnalysis]
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
- `get_task_redundancy(project_id)`

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
        "task_redundancy": {
            "project_id": analysis.task_redundancy.project_id,
            "redundant_pairs": [
                {
                    "task_1_id": rp.task_1_id,
                    "task_1_name": rp.task_1_name,
                    "task_2_id": rp.task_2_id,
                    "task_2_name": rp.task_2_name,
                    "overlap_score": rp.overlap_score,
                    "evidence": rp.evidence,
                    "time_wasted": rp.time_wasted,
                }
                for rp in analysis.task_redundancy.redundant_pairs
            ],
            "redundancy_score": analysis.task_redundancy.redundancy_score,
            "total_time_wasted": analysis.task_redundancy.total_time_wasted,
            "over_decomposition_detected": analysis.task_redundancy.over_decomposition_detected,
            "recommended_complexity": analysis.task_redundancy.recommended_complexity,
            "raw_data": analysis.task_redundancy.raw_data,
            "llm_interpretation": analysis.task_redundancy.llm_interpretation,
            "recommendations": analysis.task_redundancy.recommendations,
        } if analysis.task_redundancy else None,
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

## Cato Frontend Implementation (Updated for v0.1)

### Add Historical Mode to Existing Architecture

**Key Principle:** Reuse existing Cato infrastructure, add historical mode alongside live mode.

#### 1. Update Store to Support Historical Mode

```typescript
// dashboard/src/store/visualizationStore.ts
export type CatoMode = 'live' | 'historical';

interface HistoricalAnalysis {
  project_id: string;
  project_name: string;
  total_tasks: number;
  completed_tasks: number;
  completion_rate: number;
  blocked_tasks: number;
  total_decisions: number;
  project_duration_hours: number;
  analysis_timestamp: string;
  summary: string;
  requirement_divergences: RequirementDivergence[];
  decision_impacts: DecisionImpact[];
  instruction_quality_issues: InstructionQuality[];
  failure_diagnoses: FailureDiagnosis[];
  metadata: Record<string, any>;
}

interface VisualizationState {
  // Existing state (keep all)
  snapshot: Snapshot | null;
  isLoading: boolean;
  loadError: string | null;
  projects: Project[];
  selectedProjectId: string | null;
  autoRefreshIntervalId: number | null;
  autoRefreshInterval: number;
  currentLayer: ViewLayer;
  // ... all existing fields

  // NEW: Historical mode state
  mode: CatoMode;  // 'live' | 'historical'
  historicalAnalysis: HistoricalAnalysis | null;

  // NEW: Historical mode actions
  setMode: (mode: CatoMode) => void;
  loadHistoricalAnalysis: (projectId: string) => Promise<void>;
}

export const useVisualizationStore = create<VisualizationState>((set, get) => {
  return {
    // Keep all existing state initialization
    snapshot: null,
    isLoading: false,
    loadError: null,
    projects: [],
    selectedProjectId: null,
    autoRefreshIntervalId: null,
    autoRefreshInterval: 60000,
    currentLayer: 'network',
    // ... all existing fields

    // NEW: Initialize historical state
    mode: 'live',
    historicalAnalysis: null,

    // Keep ALL existing actions unchanged:
    // - loadData (for live mode)
    // - loadProjects (works for both modes - already perfect!)
    // - setSelectedProject
    // - refreshData
    // - startAutoRefresh
    // - stopAutoRefresh
    // ... all existing actions

    // NEW: Mode management
    setMode: (mode: CatoMode) => {
      set({ mode });

      // Auto-refresh only in live mode
      if (mode === 'live') {
        get().startAutoRefresh();
      } else {
        get().stopAutoRefresh(); // Historical data is static
      }
    },

    // NEW: Historical data loading
    loadHistoricalAnalysis: async (projectId: string) => {
      set({ isLoading: true, loadError: null });

      try {
        const response = await fetch(
          `http://localhost:4301/api/historical/projects/${projectId}/analysis`
        );

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const analysis = await response.json();

        set({
          historicalAnalysis: analysis,
          isLoading: false,
          selectedProjectId: projectId,
        });

        console.log('Historical analysis loaded successfully');
      } catch (error) {
        console.error('Error loading historical analysis:', error);
        set({
          isLoading: false,
          loadError: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    },
  };
});
```

#### 2. Update Header with Mode Toggle

```typescript
// dashboard/src/components/HeaderControls.tsx
const HeaderControls = () => {
  // Existing subscriptions (keep all)
  const isLoading = useVisualizationStore((state) => state.isLoading);
  const projects = useVisualizationStore((state) => state.projects);
  const selectedProjectId = useVisualizationStore((state) => state.selectedProjectId);

  // NEW: Mode state
  const mode = useVisualizationStore((state) => state.mode);

  // Existing actions (keep all)
  const loadProjects = useVisualizationStore((state) => state.loadProjects);
  const setSelectedProject = useVisualizationStore((state) => state.setSelectedProject);
  const refreshData = useVisualizationStore((state) => state.refreshData);

  // NEW: Mode actions
  const setMode = useVisualizationStore((state) => state.setMode);
  const loadHistoricalAnalysis = useVisualizationStore(
    (state) => state.loadHistoricalAnalysis
  );

  // Existing handlers (keep all)
  const handleProjectChange = useCallback(async (event) => {
    const projectId = event.target.value || null;

    if (mode === 'live') {
      await setSelectedProject(projectId);
    } else {
      await loadHistoricalAnalysis(projectId);
    }
  }, [mode, setSelectedProject, loadHistoricalAnalysis]);

  // Keep existing handleDropdownFocus

  // NEW: Mode toggle handler
  const handleModeToggle = useCallback(() => {
    const newMode = mode === 'live' ? 'historical' : 'live';
    setMode(newMode);

    // Reload data for current project in new mode
    const projectId = useVisualizationStore.getState().selectedProjectId;
    if (projectId) {
      if (newMode === 'live') {
        setSelectedProject(projectId);
      } else {
        loadHistoricalAnalysis(projectId);
      }
    }
  }, [mode, setMode, setSelectedProject, loadHistoricalAnalysis]);

  return (
    <>
      <div className="header-top">
        <h1>Cato - Marcus Visualization Dashboard</h1>
        <div className="header-controls">
          {/* NEW: Mode toggle */}
          <button
            className={`mode-toggle ${mode === 'historical' ? 'historical' : 'live'}`}
            onClick={handleModeToggle}
            disabled={isLoading}
            title={mode === 'live' ? 'Switch to Historical Analysis' : 'Switch to Live Monitoring'}
          >
            {mode === 'live' ? '🟢 Live Monitoring' : '📊 Historical Analysis'}
          </button>

          {/* Existing project dropdown (works for both modes!) */}
          {projects.length > 0 && (
            <select
              className="project-selector"
              value={selectedProjectId || ''}
              onChange={handleProjectChange}
              onFocus={handleDropdownFocus}
              disabled={isLoading}
              title="Select project to visualize (auto-refreshes on open)"
            >
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          )}

          {/* Existing refresh button (live mode only) */}
          {mode === 'live' && (
            <button
              className="refresh-button"
              onClick={refreshData}
              disabled={isLoading}
              title="Refresh live data now"
            >
              🔄 Refresh
            </button>
          )}
        </div>
      </div>
      {/* Existing error banner */}
    </>
  );
};
```

#### 3. Update App.tsx with Historical Views

```typescript
// dashboard/src/App.tsx
function App() {
  const currentLayer = useVisualizationStore((state) => state.currentLayer);
  const setCurrentLayer = useVisualizationStore((state) => state.setCurrentLayer);
  const mode = useVisualizationStore((state) => state.mode);

  // Existing initialization (keep unchanged)
  const loadProjects = useVisualizationStore((state) => state.loadProjects);

  useEffect(() => {
    loadProjects(); // Works for both modes!
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <HeaderControls />

        {/* Conditional tabs based on mode */}
        {mode === 'live' ? (
          // Existing live mode tabs (keep unchanged)
          <div className="layer-tabs">
            <button
              className={currentLayer === 'network' ? 'active' : ''}
              onClick={() => setCurrentLayer('network')}
            >
              🔗 Network Graph
            </button>
            <button
              className={currentLayer === 'swimlanes' ? 'active' : ''}
              onClick={() => setCurrentLayer('swimlanes')}
            >
              📊 Agent Swim Lanes
            </button>
            <button
              className={currentLayer === 'conversations' ? 'active' : ''}
              onClick={() => setCurrentLayer('conversations')}
            >
              💬 Conversations
            </button>
          </div>
        ) : (
          // NEW: Historical mode tabs
          <div className="layer-tabs">
            <button
              className={currentLayer === 'retrospective' ? 'active' : ''}
              onClick={() => setCurrentLayer('retrospective')}
            >
              📈 Project Retrospective
            </button>
            <button
              className={currentLayer === 'fidelity' ? 'active' : ''}
              onClick={() => setCurrentLayer('fidelity')}
            >
              🎯 Requirement Fidelity
            </button>
            <button
              className={currentLayer === 'decisions' ? 'active' : ''}
              onClick={() => setCurrentLayer('decisions')}
            >
              🔀 Decision Impacts
            </button>
            <button
              className={currentLayer === 'failures' ? 'active' : ''}
              onClick={() => setCurrentLayer('failures')}
            >
              ⚠️ Failure Diagnosis
            </button>
            <button
              className={currentLayer === 'redundancy' ? 'active' : ''}
              onClick={() => setCurrentLayer('redundancy')}
            >
              🔁 Task Redundancy
            </button>
          </div>
        )}
      </header>

      <div className="app-content">
        <div className="visualization-container">
          {/* Existing live mode views */}
          {mode === 'live' && currentLayer === 'network' && <NetworkGraphView />}
          {mode === 'live' && currentLayer === 'swimlanes' && <AgentSwimLanesView />}
          {mode === 'live' && currentLayer === 'conversations' && <ConversationView />}

          {/* NEW: Historical mode views */}
          {mode === 'historical' && currentLayer === 'retrospective' && (
            <RetrospectiveDashboard />
          )}
          {mode === 'historical' && currentLayer === 'fidelity' && (
            <RequirementFidelityView />
          )}
          {mode === 'historical' && currentLayer === 'decisions' && (
            <DecisionImpactView />
          )}
          {mode === 'historical' && currentLayer === 'failures' && (
            <FailureDiagnosisView />
          )}
          {mode === 'historical' && currentLayer === 'redundancy' && (
            <TaskRedundancyView />
          )}
        </div>

        {/* Metrics panel (both modes) */}
        <MetricsPanel />
      </div>

      {/* Timeline controls (live mode only) */}
      {mode === 'live' && <TimelineControls />}
    </div>
  );
}
```

### Reuse Existing Cato Infrastructure

**✅ Already Perfect (No Changes Needed):**

1. **Project Loading** (`loadProjects()`)
   - ✅ Auto-sorted by newest first
   - ✅ Works for both live and historical projects
   - ✅ On-demand refresh on dropdown click

2. **Project Dropdown**
   - ✅ Already implemented in HeaderControls
   - ✅ Just update handler to check mode

3. **Auto-Refresh**
   - ✅ Already implemented (60s interval)
   - ✅ Just disable in historical mode

4. **Error Handling**
   - ✅ Already implemented
   - ✅ Works for both modes

5. **Loading States**
   - ✅ Already implemented
   - ✅ Reuse for historical data loading

**✅ Key Insight:** Cato v0.1 refactoring made historical mode integration trivial!

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
7. ✅ **Task redundancy visualization** - Data available in analysis results

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

## Success Criteria (Updated for Cato v0.1)

Phase 3 MVP is complete when:

✅ Mode toggle added to Cato header (Live/Historical)
✅ Project selector reuses existing dropdown (✅ already works!)
✅ Historical analysis endpoint returns Phase 1 + Phase 2 data
✅ Retrospective dashboard displays project summary
✅ Requirement fidelity view displays divergences
✅ Decision impact view displays impact chains
✅ Failure diagnosis view displays root causes
✅ Task redundancy view displays redundant pairs and recommendations
✅ UI tests passing for all new components
✅ End-to-end test validates live ↔ historical mode switching
✅ Documentation with screenshots

## Timeline (Revised for Cato v0.1)

**Total Duration: 4-5 days** (reduced from 7 days due to Cato v0.1 infrastructure)

### Day 1: Backend Integration
- ✅ Add `/api/historical/projects` endpoint (list all projects)
- ✅ Add `/api/historical/projects/{id}/analysis` endpoint
- ✅ Test with real Phase 1 + Phase 2 data
- ✅ Verify JSON response structure

**Estimated: 4-6 hours** (endpoints are straightforward)

### Day 2: Core Store Updates
- ✅ Add `mode: 'live' | 'historical'` state
- ✅ Add `historicalAnalysis` state
- ✅ Add `setMode()` action
- ✅ Add `loadHistoricalAnalysis()` action
- ✅ Update `setMode()` to control auto-refresh
- ✅ Test mode switching in browser

**Estimated: 4-6 hours** (minimal changes to existing store)

### Day 3: UI Integration
- ✅ Add mode toggle button to HeaderControls
- ✅ Update handleProjectChange to check mode
- ✅ Add conditional tabs to App.tsx (live vs historical)
- ✅ Style mode toggle button
- ✅ Test mode switching UX

**Estimated: 6-8 hours** (mostly UI updates)

### Day 4: Historical Views (Part 1)
- ✅ Create `RetrospectiveDashboard.tsx` (project summary)
- ✅ Create `RequirementFidelityView.tsx` (divergences table)
- ✅ Basic styling for both views
- ✅ Display Phase 1 metrics in retrospective
- ✅ Display Phase 2 divergences in fidelity view

**Estimated: 6-8 hours** (two simple views)

### Day 5: Historical Views (Part 2) + Polish
- ✅ Create `DecisionImpactView.tsx` (impact chains)
- ✅ Create `FailureDiagnosisView.tsx` (failure causes)
- ✅ Add loading states for all views
- ✅ Add error handling for API failures
- ✅ Polish styling and responsive layout
- ✅ Write component tests
- ✅ End-to-end test (live → historical → live)
- ✅ Update documentation

**Estimated: 8-10 hours** (two views + testing + docs)

## What Cato v0.1 Gives Us For Free

**✅ Already Implemented (0 hours needed):**

1. **Project Loading** - `loadProjects()` works perfectly
2. **Project Sorting** - Newest first, exactly what we need
3. **Project Dropdown** - Fully functional HeaderControls component
4. **On-Demand Refresh** - Dropdown click refreshes projects
5. **Auto-Refresh Logic** - Just needs mode check added
6. **Error Handling** - Works for both modes
7. **Loading States** - Reusable for historical data
8. **Bundled Design Task Fix** - Phase 3 blocker already resolved
9. **Linear Timeline** - Correct power scale (1.0) for analysis

**Total Time Saved: ~2-3 days of implementation**

## Next Action

Choose implementation approach and document decision in this file. Recommended: **Start with Option A** for faster delivery and real user feedback.

---

## Appendix: Impact of Cato v0.1 Changes on Phase 3

### Summary of Changes (December 2024)

This section documents how Cato v0.1 refactoring simplified Phase 3 implementation.

#### Changes Made to Cato

| Change | Commit | Impact on Phase 3 |
|--------|--------|-------------------|
| Remove mock mode | 415e235 | ✅ Simplifies architecture - no mock/live complexity |
| Add background auto-refresh (60s) | 39c5b5e, 1e57ffd | ✅ Reusable - just disable in historical mode |
| Auto-select newest project | d62020a | ✅ Perfect for historical analysis UX |
| On-demand project refresh | ee3f689 | ✅ Exactly what historical mode needs |
| Fix bundled design tasks | 639523f | ✅ **Removed Phase 3 blocker** |
| Linear timeline (1.0 power scale) | 74e855c, ebbf312 | ✅ Accurate for failure analysis |
| State preservation during refresh | (multiple) | ✅ Pattern useful for historical views |

#### Key Architectural Decisions

**1. Mode vs Data Source**
- **Old Plan:** `dataMode: 'live' | 'mock'` (data source selection)
- **New Plan:** `mode: 'live' | 'historical'` (view mode selection)
- **Benefit:** Clearer separation of concerns, simpler mental model

**2. Project Management**
- **Old Plan:** Build project selector from scratch
- **New Plan:** Reuse existing `loadProjects()` with newest-first sorting
- **Benefit:** Zero implementation time, better UX

**3. Auto-Refresh**
- **Old Plan:** Manual refresh button only
- **New Plan:** Background refresh for live, disabled for historical
- **Benefit:** Better live UX, correct historical behavior

**4. Timeline Accuracy**
- **Old Plan:** Power scale 0.4 (mentioned in analysis needs)
- **New Plan:** Linear scale 1.0 (already implemented)
- **Benefit:** Accurate temporal relationships for failure diagnosis

#### Time Savings

| Task | Original Estimate | After v0.1 | Time Saved |
|------|------------------|------------|------------|
| Project loading infrastructure | 8 hours | 0 hours | ✅ 8 hours |
| Project selector UI | 6 hours | 1 hour | ✅ 5 hours |
| Auto-refresh logic | 4 hours | 1 hour | ✅ 3 hours |
| Bundled design task fix | 8 hours | 0 hours | ✅ 8 hours |
| Timeline accuracy fix | 4 hours | 0 hours | ✅ 4 hours |
| Error handling | 4 hours | 0 hours | ✅ 4 hours |
| **TOTAL** | **34 hours** | **2 hours** | **✅ 32 hours saved** |

**Original Estimate:** 7 days (56 hours)
**Revised Estimate:** 4-5 days (32-40 hours)
**Time Saved:** ~2-3 days thanks to Cato v0.1 refactoring

#### Risk Assessment

**Risks Eliminated by v0.1:**

1. ✅ **Mock mode complexity** - No longer exists
2. ✅ **Bundled design visualization** - Already fixed
3. ✅ **Project selector bugs** - Already tested and working
4. ✅ **Timeline accuracy issues** - Linear scale implemented
5. ✅ **Auto-refresh interference** - Clean disable pattern

**Remaining Risks:**

1. ⚠️ **Phase 2 analysis performance** - LLM calls may be slow (10-30s)
   - Mitigation: Show loading indicator, consider caching
2. ⚠️ **Large project data** - Many tasks/decisions may impact UI performance
   - Mitigation: Pagination or virtualization if needed
3. ⚠️ **Historical data compatibility** - Old project history may have different schema
   - Mitigation: Test with real historical data early

#### Recommendations

1. **Start Phase 3 immediately** - All blockers resolved
2. **Reuse Cato v0.1 patterns** - Don't reinvent the wheel
3. **Test with real data early** - Validate Phase 1 + Phase 2 integration
4. **Consider caching** - Analysis is expensive, cache results
5. **Monitor performance** - Large projects may need optimization

#### Success Metrics

Phase 3 is successful if:

- ✅ Mode switching works seamlessly
- ✅ Historical analysis loads within 30 seconds
- ✅ All Phase 2 insights displayed clearly
- ✅ Users can diagnose failures without checking logs
- ✅ Zero regression in live monitoring mode
