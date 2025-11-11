# Phase 3: Cato Integration - Interactive Visualization

> **⚠️ IMPORTANT: This document is the original design spec.**
>
> **For accurate implementation guidance based on actual Phase 1 & 2 APIs, see:**
> **[PHASE_3_IMPLEMENTATION_PLAN.md](./PHASE_3_IMPLEMENTATION_PLAN.md)**
>
> This original document contains API examples that don't match the final Phase 1 & 2 implementation. It's kept for reference, but all implementation work should follow the corrected plan.

## Overview

Phase 3 brings post-project analysis to life with interactive visualizations by:
1. Extending Cato with "Historical Analysis" mode (vs current "Live Monitoring" mode)
2. Creating interactive UI for exploring failures and understanding root causes
3. Displaying raw data + LLM interpretations side-by-side
4. Enabling drill-down from high-level project health to specific task failures

**Duration:** 5-7 days
**Dependencies:** Phase 1 complete (Phase 2 enhances but not required)
**Deliverable:** Web UI for post-project analysis and diagnosis
**Blocker:** Must verify/fix Cato bundled design task visualization first

## Prerequisites: Fix Cato Issues

### Issue: Bundled Design Task Visualization

**Status:** Needs verification

**Concern:** User mentioned Cato has problems with bundled design tasks (GH-108, GH-127)

**Action Required:**
1. Create test project with bundled design tasks
2. Load in Cato and verify:
   - Tasks display correctly in dependency graph
   - Task relationships are clear
   - No rendering errors or missing tasks
3. If issues found, fix before proceeding with Phase 3

**Potential Issues:**
- Task grouping may not display correctly
- Dependency edges may cross incorrectly
- Task names may be confusing (e.g., "design_user_authentication" vs "task_user-login_design")

**Testing:**
```bash
# Create test project with bundled designs
python scripts/test_bundled_designs.py

# Launch Cato
cd /Users/lwgray/dev/cato
npm run dev

# Manually verify visualization
# [ ] Bundled design tasks appear in graph
# [ ] Dependencies render correctly
# [ ] Task details panel shows correct info
# [ ] No console errors
```

**Timeline:** Fix Cato issues in days 0-1 before starting Phase 3 proper

## Architecture: Historical Mode vs Live Mode

### Current Cato (Live Monitoring)

**Purpose:** Real-time visualization of active project execution

**Data Flow:**
```
Marcus (running) → Logs/Events (streaming) → Cato Aggregator → React UI (auto-refresh)
```

**Features:**
- Task dependency graph (live)
- Agent swim lanes (current assignments)
- Message timeline (scrolling)
- Metrics panel (real-time)

### New: Historical Analysis Mode

**Purpose:** Post-project exploration and failure diagnosis

**Data Flow:**
```
Completed Project → Project History API (Phase 1) → Analysis API (Phase 2) → Cato UI
```

**Features (New):**
- Project retrospective dashboard
- Task execution trace viewer
- Failure diagnosis interface
- Decision impact graph
- Requirement fidelity heatmap
- Task redundancy analyzer (detects duplicate/redundant work)

**Key Difference:**
- Live mode: "What's happening now?"
- Historical mode: "Why did this fail?"

## UI Design

### 1. Mode Selector

Add mode toggle to Cato header:

```tsx
// dashboard/src/components/Header.tsx

interface HeaderProps {
  mode: 'live' | 'historical'
  onModeChange: (mode: 'live' | 'historical') => void
  currentProject?: string
}

function Header({ mode, onModeChange, currentProject }: HeaderProps) {
  return (
    <header className="cato-header">
      <h1>Cato - Marcus Visualization</h1>

      {/* Mode Selector */}
      <div className="mode-selector">
        <button
          className={mode === 'live' ? 'active' : ''}
          onClick={() => onModeChange('live')}
        >
          📡 Live Monitoring
        </button>
        <button
          className={mode === 'historical' ? 'active' : ''}
          onClick={() => onModeChange('historical')}
        >
          📊 Historical Analysis
        </button>
      </div>

      {currentProject && (
        <div className="project-info">
          Project: {currentProject}
        </div>
      )}
    </header>
  )
}
```

### 2. Project Selector (Historical Mode)

When in historical mode, show completed projects:

```tsx
// dashboard/src/components/ProjectSelector.tsx

interface CompletedProject {
  project_id: string
  project_name: string
  completed_at: string
  completion_rate: number
  total_tasks: number
  risk_level: 'low' | 'medium' | 'high'
}

function ProjectSelector({ onSelectProject }: Props) {
  const [projects, setProjects] = useState<CompletedProject[]>([])

  useEffect(() => {
    // Load completed projects from API
    fetch('/api/historical/projects')
      .then(res => res.json())
      .then(data => setProjects(data.projects))
  }, [])

  return (
    <div className="project-selector">
      <h2>Select Completed Project</h2>

      <table className="projects-table">
        <thead>
          <tr>
            <th>Project Name</th>
            <th>Completed</th>
            <th>Tasks</th>
            <th>Completion Rate</th>
            <th>Risk Level</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {projects.map(project => (
            <tr key={project.project_id}>
              <td>{project.project_name}</td>
              <td>{formatDate(project.completed_at)}</td>
              <td>{project.total_tasks}</td>
              <td>
                <ProgressBar value={project.completion_rate} />
                {(project.completion_rate * 100).toFixed(0)}%
              </td>
              <td>
                <RiskBadge level={project.risk_level} />
              </td>
              <td>
                <button onClick={() => onSelectProject(project.project_id)}>
                  Analyze →
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

### 3. Project Retrospective Dashboard

Main view for historical analysis:

```tsx
// dashboard/src/components/ProjectRetrospective.tsx

interface ProjectRetrospectiveProps {
  projectId: string
}

function ProjectRetrospective({ projectId }: ProjectRetrospectiveProps) {
  const [analysis, setAnalysis] = useState<ProjectAnalysis | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Load full project analysis
    fetch(`/api/historical/projects/${projectId}/analysis`)
      .then(res => res.json())
      .then(data => {
        setAnalysis(data)
        setLoading(false)
      })
  }, [projectId])

  if (loading) return <LoadingSpinner />

  return (
    <div className="project-retrospective">
      {/* Executive Summary */}
      <section className="executive-summary">
        <h2>{analysis.project_name} - Post-Project Analysis</h2>

        <div className="summary-cards">
          <MetricCard
            title="Completion Rate"
            value={`${(analysis.completion_rate * 100).toFixed(0)}%`}
            status={analysis.completion_rate > 0.9 ? 'good' : 'warning'}
          />
          <MetricCard
            title="Estimation Accuracy"
            value={`${(analysis.estimation_accuracy * 100).toFixed(0)}%`}
            status={analysis.estimation_accuracy > 0.8 ? 'good' : 'warning'}
          />
          <MetricCard
            title="Tasks Blocked"
            value={analysis.blocked_count}
            status={analysis.blocked_count === 0 ? 'good' : 'warning'}
          />
          <MetricCard
            title="Average Task Duration"
            value={`${analysis.avg_duration.toFixed(1)}h`}
          />
        </div>

        {/* LLM-Generated Assessment */}
        <div className="llm-assessment">
          <h3>Overall Assessment</h3>
          <div className="assessment-content">
            {analysis.overall_assessment}
          </div>
        </div>
      </section>

      {/* Task Heatmap */}
      <section className="task-heatmap">
        <h3>Task Quality Heatmap</h3>
        <TaskFidelityHeatmap tasks={analysis.task_analyses} />
      </section>

      {/* Decision Impact Graph */}
      <section className="decision-graph">
        <h3>Architectural Decisions & Impact</h3>
        <DecisionImpactGraph
          decisions={analysis.decisions}
          tasks={analysis.tasks}
        />
      </section>

      {/* Failed/Blocked Tasks */}
      {analysis.failed_tasks.length > 0 && (
        <section className="failed-tasks">
          <h3>⚠️ Failed or Blocked Tasks</h3>
          <FailedTasksList tasks={analysis.failed_tasks} />
        </section>
      )}

      {/* Detailed Task List */}
      <section className="task-details">
        <h3>All Tasks</h3>
        <TaskHistoryTable
          tasks={analysis.task_analyses}
          onSelectTask={handleTaskSelect}
        />
      </section>
    </div>
  )
}
```

### 4. Task Execution Trace Viewer

Drill down into individual task:

```tsx
// dashboard/src/components/TaskTraceViewer.tsx

function TaskTraceViewer({ projectId, taskId }: Props) {
  const [taskHistory, setTaskHistory] = useState<TaskHistory | null>(null)
  const [showRawData, setShowRawData] = useState(false)

  return (
    <div className="task-trace-viewer">
      <header>
        <h2>Task Execution Trace: {taskHistory?.name}</h2>
        <button onClick={() => setShowRawData(!showRawData)}>
          {showRawData ? 'Hide' : 'Show'} Raw Data
        </button>
      </header>

      {/* Basic Info */}
      <section className="task-info">
        <InfoRow label="Status" value={taskHistory.status} />
        <InfoRow label="Assigned To" value={taskHistory.assigned_to} />
        <InfoRow label="Duration" value={`${taskHistory.actual_hours}h (est. ${taskHistory.estimated_hours}h)`} />
        <InfoRow label="Started" value={formatTimestamp(taskHistory.started_at)} />
        <InfoRow label="Completed" value={formatTimestamp(taskHistory.completed_at)} />
      </section>

      {/* Original Requirements */}
      <section className="requirements">
        <h3>Original Requirements</h3>
        <div className="requirement-text">
          {taskHistory.description}
        </div>
      </section>

      {/* Context Received */}
      <section className="context-received">
        <h3>Context Received from Dependencies</h3>

        {taskHistory.decisions_consumed.length > 0 && (
          <div className="consumed-decisions">
            <h4>Decisions from Dependencies:</h4>
            {taskHistory.decisions_consumed.map(decision => (
              <DecisionCard key={decision.decision_id} decision={decision} />
            ))}
          </div>
        )}

        {taskHistory.artifacts_consumed.length > 0 && (
          <div className="consumed-artifacts">
            <h4>Artifacts from Dependencies:</h4>
            {taskHistory.artifacts_consumed.map(artifact => (
              <ArtifactCard key={artifact.artifact_id} artifact={artifact} />
            ))}
          </div>
        )}
      </section>

      {/* Decisions Made */}
      {taskHistory.decisions_made.length > 0 && (
        <section className="decisions-made">
          <h3>Architectural Decisions Made</h3>
          {taskHistory.decisions_made.map(decision => (
            <DecisionDetail key={decision.decision_id} decision={decision} />
          ))}
        </section>
      )}

      {/* Artifacts Produced */}
      {taskHistory.artifacts_produced.length > 0 && (
        <section className="artifacts-produced">
          <h3>Artifacts Produced</h3>
          {taskHistory.artifacts_produced.map(artifact => (
            <div key={artifact.artifact_id} className="artifact-detail">
              <h4>{artifact.filename}</h4>
              <div className="artifact-meta">
                Type: {artifact.artifact_type} | Size: {formatSize(artifact.file_size_bytes)}
              </div>
              <button onClick={() => viewArtifact(artifact.absolute_path)}>
                View File →
              </button>
            </div>
          ))}
        </section>
      )}

      {/* Requirement Fidelity Analysis (Phase 2) */}
      {taskHistory.requirement_fidelity && (
        <section className="fidelity-analysis">
          <h3>Requirement Fidelity Analysis</h3>

          <div className="fidelity-score">
            <label>Fidelity Score:</label>
            <ProgressBar value={taskHistory.requirement_fidelity.fidelity_score} />
            <span>{(taskHistory.requirement_fidelity.fidelity_score * 100).toFixed(0)}%</span>
          </div>

          {/* Raw Data (Collapsible) */}
          {showRawData && (
            <details open>
              <summary>Raw Data</summary>
              <pre className="raw-data">
                {JSON.stringify(taskHistory.requirement_fidelity.raw_data, null, 2)}
              </pre>
            </details>
          )}

          {/* LLM Interpretation */}
          <div className="llm-interpretation">
            <h4>Analysis</h4>
            <div className="interpretation-text">
              {taskHistory.requirement_fidelity.llm_interpretation}
            </div>
          </div>

          {/* Divergences */}
          {taskHistory.requirement_fidelity.divergences.length > 0 && (
            <div className="divergences">
              <h4>Identified Divergences</h4>
              {taskHistory.requirement_fidelity.divergences.map((div, idx) => (
                <DivergenceCard key={idx} divergence={div} />
              ))}
            </div>
          )}
        </section>
      )}

      {/* Blockers */}
      {taskHistory.blockers_reported.length > 0 && (
        <section className="blockers">
          <h3>⚠️ Blockers Encountered</h3>
          {taskHistory.blockers_reported.map((blocker, idx) => (
            <BlockerCard key={idx} blocker={blocker} />
          ))}
        </section>
      )}

      {/* Conversation Timeline */}
      <section className="conversation-timeline">
        <h3>Communication Timeline</h3>
        <Timeline events={taskHistory.conversations} />
      </section>
    </div>
  )
}
```

### 5. Failure Diagnosis Interface

Interactive root cause analysis:

```tsx
// dashboard/src/components/FailureDiagnoser.tsx

function FailureDiagnoser({ projectId }: Props) {
  const [query, setQuery] = useState('')
  const [diagnosis, setDiagnosis] = useState<FailureDiagnosis | null>(null)
  const [loading, setLoading] = useState(false)

  const handleDiagnose = async () => {
    setLoading(true)

    const response = await fetch(`/api/historical/projects/${projectId}/diagnose`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    })

    const data = await response.json()
    setDiagnosis(data)
    setLoading(false)
  }

  return (
    <div className="failure-diagnoser">
      <h2>Failure Diagnosis</h2>

      <div className="query-input">
        <input
          type="text"
          placeholder="e.g., Why doesn't the login feature work?"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && handleDiagnose()}
        />
        <button onClick={handleDiagnose} disabled={!query || loading}>
          {loading ? 'Analyzing...' : 'Diagnose'}
        </button>
      </div>

      {diagnosis && (
        <div className="diagnosis-result">
          {/* Task Chain Visualization */}
          <section className="task-chain">
            <h3>Task Execution Chain</h3>
            <TaskChainGraph taskIds={diagnosis.task_chain} />
          </section>

          {/* Raw Evidence (Collapsible) */}
          <section className="raw-evidence">
            <details>
              <summary>📋 Raw Evidence ({Object.keys(diagnosis.raw_evidence).length} items)</summary>
              <pre className="evidence-data">
                {JSON.stringify(diagnosis.raw_evidence, null, 2)}
              </pre>
            </details>
          </section>

          {/* LLM Diagnosis */}
          <section className="llm-diagnosis">
            <h3>Diagnosis</h3>
            <div className="diagnosis-text">
              <ReactMarkdown>{diagnosis.diagnosis}</ReactMarkdown>
            </div>
          </section>

          {/* Root Causes */}
          <section className="root-causes">
            <h3>Root Causes Identified</h3>
            <ul className="causes-list">
              {diagnosis.root_causes.map((cause, idx) => (
                <li key={idx} className="cause-item">
                  <span className="cause-icon">⚠️</span>
                  {cause}
                </li>
              ))}
            </ul>
          </section>

          {/* Recommendations */}
          <section className="recommendations">
            <h3>Recommendations</h3>
            <ul className="recommendations-list">
              {diagnosis.recommendations.map((rec, idx) => (
                <li key={idx} className="recommendation-item">
                  <span className="rec-icon">✅</span>
                  {rec}
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  )
}
```

### 6. Decision Impact Graph

Visualize how decisions ripple through the project:

```tsx
// dashboard/src/components/DecisionImpactGraph.tsx

import { Network } from 'vis-network'

function DecisionImpactGraph({ decisions, tasks }: Props) {
  const graphRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!graphRef.current) return

    // Build graph nodes and edges
    const nodes = [
      // Decision nodes
      ...decisions.map(d => ({
        id: d.decision_id,
        label: d.what.substring(0, 30) + '...',
        shape: 'diamond',
        color: getConfidenceColor(d.confidence),
        title: `${d.what}\n\nBy: ${d.agent_id}\nConfidence: ${d.confidence}`
      })),

      // Task nodes
      ...tasks.map(t => ({
        id: t.task_id,
        label: t.name,
        shape: 'box',
        color: getStatusColor(t.status),
        title: `${t.name}\n\nStatus: ${t.status}\nDuration: ${t.actual_hours}h`
      }))
    ]

    const edges = []

    // Link decisions to tasks they affected
    for (const decision of decisions) {
      for (const taskId of decision.affected_tasks) {
        edges.push({
          from: decision.decision_id,
          to: taskId,
          arrows: 'to',
          color: { color: '#666' }
        })
      }
    }

    // Link tasks to their dependencies
    for (const task of tasks) {
      for (const depId of task.dependencies) {
        edges.push({
          from: depId,
          to: task.task_id,
          arrows: 'to',
          color: { color: '#ccc' },
          dashes: true
        })
      }
    }

    const network = new Network(graphRef.current, { nodes, edges }, {
      layout: { hierarchical: { direction: 'LR' } },
      physics: { enabled: false }
    })

    network.on('selectNode', (params) => {
      const nodeId = params.nodes[0]
      if (nodeId.startsWith('dec_')) {
        showDecisionDetails(nodeId)
      } else {
        showTaskDetails(nodeId)
      }
    })

  }, [decisions, tasks])

  return (
    <div className="decision-impact-graph">
      <div ref={graphRef} style={{ height: '600px' }} />
      <div className="legend">
        <div className="legend-item">
          <span className="legend-icon" style={{ background: '#4CAF50' }}>◆</span>
          High Confidence Decision
        </div>
        <div className="legend-item">
          <span className="legend-icon" style={{ background: '#FFC107' }}>◆</span>
          Medium Confidence Decision
        </div>
        <div className="legend-item">
          <span className="legend-icon" style={{ background: '#F44336' }}>◆</span>
          Low Confidence Decision
        </div>
      </div>
    </div>
  )
}
```

### 7. Task Redundancy View

Detect duplicate and redundant work across tasks:

```tsx
// dashboard/src/components/TaskRedundancyView.tsx

interface TaskRedundancyViewProps {
  projectId: string;
}

function TaskRedundancyView({ projectId }: TaskRedundancyViewProps) {
  const [redundancyData, setRedundancyData] = useState<TaskRedundancyAnalysis | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadRedundancyAnalysis() {
      const response = await fetch(`/api/historical/projects/${projectId}/analysis`)
      const data = await response.json()
      setRedundancyData(data.task_redundancy)
      setLoading(false)
    }

    loadRedundancyAnalysis()
  }, [projectId])

  if (loading) return <div>Loading redundancy analysis...</div>
  if (!redundancyData) return <div>No redundancy data available</div>

  return (
    <div className="task-redundancy-view">
      <h2>Task Redundancy Analysis</h2>

      {/* Overall Metrics */}
      <section className="redundancy-metrics">
        <div className="metric-card">
          <label>Redundancy Score</label>
          <div className="score-display">
            <CircularProgress value={redundancyData.redundancy_score * 100} />
            <span className="score-value">
              {(redundancyData.redundancy_score * 100).toFixed(0)}%
            </span>
          </div>
        </div>

        <div className="metric-card">
          <label>Time Wasted</label>
          <div className="time-wasted">
            <span className="hours">{redundancyData.total_time_wasted.toFixed(1)}h</span>
            <span className="subtitle">on redundant work</span>
          </div>
        </div>

        <div className="metric-card">
          <label>Recommended Complexity</label>
          <div className={`complexity-badge ${redundancyData.recommended_complexity}`}>
            {redundancyData.recommended_complexity.toUpperCase()}
          </div>
          {redundancyData.over_decomposition_detected && (
            <div className="warning">
              ⚠️ Over-decomposition detected
            </div>
          )}
        </div>
      </section>

      {/* Redundant Pairs */}
      {redundancyData.redundant_pairs.length > 0 && (
        <section className="redundant-pairs">
          <h3>Redundant Task Pairs ({redundancyData.redundant_pairs.length})</h3>
          <div className="pairs-list">
            {redundancyData.redundant_pairs.map((pair, idx) => (
              <div key={idx} className="redundant-pair-card">
                <div className="pair-header">
                  <div className="overlap-score">
                    <CircularProgress
                      value={pair.overlap_score * 100}
                      size="small"
                    />
                    <span>{(pair.overlap_score * 100).toFixed(0)}% overlap</span>
                  </div>
                  <div className="time-wasted-badge">
                    {pair.time_wasted.toFixed(1)}h wasted
                  </div>
                </div>

                <div className="pair-tasks">
                  <div className="task-info">
                    <span className="task-id">{pair.task_1_id}</span>
                    <span className="task-name">{pair.task_1_name}</span>
                  </div>
                  <div className="overlap-indicator">⟷</div>
                  <div className="task-info">
                    <span className="task-id">{pair.task_2_id}</span>
                    <span className="task-name">{pair.task_2_name}</span>
                  </div>
                </div>

                {/* Evidence (Collapsible) */}
                <details className="evidence-details">
                  <summary>📋 Evidence & Citations</summary>
                  <div className="evidence-content">
                    <ReactMarkdown>{pair.evidence}</ReactMarkdown>
                  </div>
                </details>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Raw Data (Collapsible) */}
      <section className="raw-data-section">
        <details>
          <summary>
            📊 Raw Analysis Data ({Object.keys(redundancyData.raw_data).length} fields)
          </summary>
          <pre className="raw-data">
            {JSON.stringify(redundancyData.raw_data, null, 2)}
          </pre>
        </details>
      </section>

      {/* LLM Interpretation */}
      <section className="llm-interpretation">
        <h3>Analysis Summary</h3>
        <div className="interpretation-text">
          <ReactMarkdown>{redundancyData.llm_interpretation}</ReactMarkdown>
        </div>
      </section>

      {/* Recommendations */}
      {redundancyData.recommendations.length > 0 && (
        <section className="recommendations">
          <h3>Recommendations</h3>
          <ul className="recommendations-list">
            {redundancyData.recommendations.map((rec, idx) => (
              <li key={idx} className="recommendation-item">
                <span className="rec-icon">💡</span>
                {rec}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
```

**Key Features:**
- **Redundancy Score**: Overall percentage of redundant work detected (0-100%)
- **Time Wasted**: Total hours spent on duplicate/redundant tasks
- **Complexity Recommendation**: Suggests prototype/standard/enterprise based on analysis
- **Redundant Pairs**: Visual cards showing overlapping tasks with overlap scores
- **Evidence & Citations**: Collapsible sections with task_id, timestamps, and proof
- **Quick Completion Detection**: Identifies tasks completing in < 30 seconds
- **Over-decomposition Warning**: Alerts when enterprise mode created unnecessary breakdowns

**Use Cases:**
1. **Post-Project Review**: "Why did this take longer than expected?"
2. **Process Improvement**: Identify patterns of duplicate work across projects
3. **Complexity Tuning**: Determine if using wrong complexity mode (prototype vs enterprise)
4. **Resource Optimization**: Calculate time wasted on redundant efforts

## Backend API Endpoints

### Cato Backend Extensions

Add new endpoints to Cato backend (`/Users/lwgray/dev/cato/backend/api.py`):

```python
# GET /api/historical/projects
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
          "completed_at": "2025-11-05T18:00:00Z",
          "completion_rate": 0.917,
          "total_tasks": 24,
          "risk_level": "medium"
        }
      ]
    }
    """
    query = ProjectHistoryQuery(aggregator)
    snapshots = await query.list_completed_projects()

    return {
        "projects": [
            {
                "project_id": s.project_id,
                "project_name": s.project_name,
                "completed_at": s.snapshot_timestamp.isoformat(),
                "completion_rate": s.task_statistics["completion_rate"],
                "total_tasks": s.task_statistics["total_tasks"],
                "risk_level": s.quality_metrics["risk_level"]
            }
            for s in snapshots
        ]
    }


# GET /api/historical/projects/{project_id}
async def get_project_history(project_id: str):
    """
    Get complete project history (without analysis).

    Returns raw historical data only.
    """
    query = ProjectHistoryQuery(aggregator)
    history = await query.get_project_history(project_id)

    return {
        "project_id": history.project_id,
        "snapshot": history.snapshot.to_dict(),
        "tasks": [t.to_dict() for t in history.tasks],
        "agents": [a.to_dict() for a in history.agents],
        "decisions": [d.to_dict() for d in history.decisions],
        "artifacts": [a.to_dict() for a in history.artifacts],
        "timeline": [e.to_dict() for e in history.timeline]
    }


# GET /api/historical/projects/{project_id}/analysis
async def get_project_analysis(project_id: str):
    """
    Get complete project analysis (with LLM insights).

    This is heavier - includes Phase 2 LLM analysis.
    May take 10-30 seconds depending on project size.
    """
    analyzer = PostProjectAnalyzer(query_api, ai_engine)
    analysis = await analyzer.analyze_project(project_id)

    return {
        "project_id": analysis.project_id,
        "project_name": analysis.snapshot.project_name,
        "completion_rate": analysis.snapshot.task_statistics["completion_rate"],
        "estimation_accuracy": analysis.snapshot.timing["estimation_accuracy"],
        "blocked_count": analysis.snapshot.task_statistics["blocked"],
        "avg_duration": analysis.snapshot.quality_metrics["average_task_duration"],
        "overall_assessment": analysis.overall_assessment,
        "task_analyses": [ta.to_dict() for ta in analysis.task_analyses],
        "decisions": [d.to_dict() for d in analysis.decisions],
        "failed_tasks": [t.to_dict() for t in analysis.failed_tasks],
        "tasks": [t.to_dict() for t in analysis.tasks]
    }


# GET /api/historical/projects/{project_id}/tasks/{task_id}
async def get_task_history(project_id: str, task_id: str):
    """Get detailed history for a specific task."""
    query = ProjectHistoryQuery(aggregator)
    task = await query.get_task_history(project_id, task_id)

    return task.to_dict()


# POST /api/historical/projects/{project_id}/diagnose
async def diagnose_failure(project_id: str, request: DiagnoseRequest):
    """
    Diagnose why a feature failed.

    Request body:
    {
      "query": "Why doesn't the login feature work?"
    }

    Response:
    {
      "feature_name": "login",
      "diagnosis": "...",
      "task_chain": ["task_1", "task_2", ...],
      "root_causes": ["cause 1", "cause 2"],
      "raw_evidence": {...},
      "recommendations": ["rec 1", "rec 2"]
    }
    """
    analyzer = PostProjectAnalyzer(query_api, ai_engine)
    diagnosis = await analyzer.diagnose_failure(
        project_id=project_id,
        query=request.query
    )

    return diagnosis.to_dict()


# GET /api/historical/projects/{project_id}/decisions/{decision_id}/impact
async def trace_decision_impact(project_id: str, decision_id: str):
    """Trace the full impact of a specific decision."""
    query = ProjectHistoryQuery(aggregator)
    impact = await query.trace_decision_impact(project_id, decision_id)

    return impact
```

## Testing Strategy

### 1. UI Component Tests

```tsx
// dashboard/src/components/__tests__/ProjectRetrospective.test.tsx

describe('ProjectRetrospective', () => {
  it('renders project summary', async () => {
    const mockAnalysis = {
      project_name: 'Test Project',
      completion_rate: 0.9,
      estimation_accuracy: 0.85
    }

    render(<ProjectRetrospective projectId="test_123" />)

    await waitFor(() => {
      expect(screen.getByText('Test Project')).toBeInTheDocument()
      expect(screen.getByText('90%')).toBeInTheDocument()  // completion rate
    })
  })

  it('displays LLM assessment', async () => {
    render(<ProjectRetrospective projectId="test_123" />)

    await waitFor(() => {
      expect(screen.getByText(/Overall Assessment/i)).toBeInTheDocument()
    })
  })

  it('shows failed tasks if any exist', async () => {
    const mockAnalysis = {
      failed_tasks: [{ task_id: 'task_1', name: 'Failed Task' }]
    }

    render(<ProjectRetrospective projectId="test_123" />)

    await waitFor(() => {
      expect(screen.getByText(/Failed or Blocked Tasks/i)).toBeInTheDocument()
    })
  })
})
```

### 2. API Integration Tests

```python
# tests/integration/api/test_historical_api.py

async def test_list_completed_projects(client):
    """Test listing completed projects."""
    response = await client.get("/api/historical/projects")

    assert response.status_code == 200
    data = response.json()
    assert "projects" in data
    assert len(data["projects"]) > 0


async def test_get_project_analysis(client):
    """Test getting full project analysis."""
    response = await client.get("/api/historical/projects/marcus_proj_123/analysis")

    assert response.status_code == 200
    data = response.json()

    # Should have all key sections
    assert "overall_assessment" in data
    assert "task_analyses" in data
    assert "decisions" in data


async def test_diagnose_failure(client):
    """Test failure diagnosis."""
    response = await client.post(
        "/api/historical/projects/marcus_proj_123/diagnose",
        json={"query": "Why doesn't login work?"}
    )

    assert response.status_code == 200
    data = response.json()

    assert "diagnosis" in data
    assert "raw_evidence" in data
    assert "recommendations" in data
```

### 3. End-to-End Tests

```python
# tests/e2e/test_historical_ui.py

@pytest.mark.e2e
async def test_full_analysis_workflow(browser):
    """Test complete workflow from project selection to diagnosis."""

    # Navigate to Cato
    page = await browser.new_page()
    await page.goto("http://localhost:4301")

    # Switch to historical mode
    await page.click("button:has-text('Historical Analysis')")

    # Select a project
    await page.click("tr:has-text('Task Management API') button:has-text('Analyze')")

    # Wait for analysis to load
    await page.wait_for_selector(".project-retrospective")

    # Verify summary cards are displayed
    assert await page.is_visible(".metric-card:has-text('Completion Rate')")

    # Open failure diagnoser
    await page.click("a:has-text('Diagnose Failure')")

    # Enter query
    await page.fill("input[placeholder*='login']", "Why doesn't login work?")
    await page.click("button:has-text('Diagnose')")

    # Wait for diagnosis
    await page.wait_for_selector(".diagnosis-result")

    # Verify raw evidence is present
    assert await page.is_visible("details:has-text('Raw Evidence')")

    # Verify LLM diagnosis is present
    assert await page.is_visible(".llm-diagnosis")

    # Verify recommendations are present
    assert await page.is_visible(".recommendations")
```

## Performance Considerations

### Challenge: Analysis can be slow for large projects

**Problem:**
- Large projects (100+ tasks) may have lots of data
- LLM analysis (Phase 2) can take 10-30 seconds
- User waiting for analysis is poor UX

**Solutions:**

#### 1. Progressive Loading

Load data in stages:

```tsx
function ProjectRetrospective({ projectId }: Props) {
  const [snapshot, setSnapshot] = useState(null)     // Load immediately
  const [basicData, setBasicData] = useState(null)   // Load at +1s
  const [analysis, setAnalysis] = useState(null)     // Load at +5-30s

  useEffect(() => {
    // Stage 1: Load snapshot (fast)
    fetchSnapshot(projectId).then(setSnapshot)

    // Stage 2: Load basic historical data (medium)
    fetchBasicData(projectId).then(setBasicData)

    // Stage 3: Run LLM analysis (slow)
    fetchAnalysis(projectId).then(setAnalysis)
  }, [projectId])

  return (
    <div>
      {snapshot && <ExecutiveSummary data={snapshot} />}
      {basicData && <TaskList tasks={basicData.tasks} />}
      {!analysis && <AnalysisSpinner />}
      {analysis && <LLMInsights analysis={analysis} />}
    </div>
  )
}
```

#### 2. Caching

Cache analysis results (they don't change for completed projects):

```python
# Cato backend
from functools import lru_cache

@lru_cache(maxsize=10)  # Cache last 10 project analyses
async def get_project_analysis_cached(project_id: str):
    return await get_project_analysis(project_id)
```

#### 3. Pre-compute on Project Completion

Run analysis when project completes, not when user requests:

```python
# In Marcus - when project completes
async def finalize_project(project_id: str):
    # ... create snapshot ...

    # Trigger background analysis
    asyncio.create_task(pre_compute_analysis(project_id))

async def pre_compute_analysis(project_id: str):
    """Run analysis and cache results for instant retrieval."""
    analyzer = PostProjectAnalyzer(query_api, ai_engine)
    analysis = await analyzer.analyze_project(project_id)

    # Store in cache or database
    await store_analysis(project_id, analysis)
```

## Implementation Sequence

### Day 1: Fix Cato Issues & Setup

1. Test Cato with bundled design tasks
2. Fix any visualization issues
3. Set up historical mode infrastructure
4. Add mode selector to header

### Day 2-3: Basic Historical UI

1. Implement project selector
2. Implement project retrospective dashboard (without Phase 2 analysis)
3. Implement task history table
4. Test with real completed project

### Day 4-5: Advanced Features

1. Implement task execution trace viewer
2. Implement failure diagnoser (if Phase 2 complete)
3. Implement decision impact graph
4. Add raw data / interpretation toggles

### Day 6-7: Polish & Testing

1. End-to-end testing
2. Performance optimization
3. UI/UX refinement
4. Documentation

## Success Criteria

Phase 3 is complete when:

✅ Cato bundled design task visualization works correctly
✅ Historical mode selector implemented
✅ Project selector shows all completed projects
✅ Project retrospective dashboard displays summary metrics
✅ Task execution trace viewer shows full task history
✅ Raw data is always available alongside LLM interpretations
✅ Failure diagnoser provides interactive root cause analysis
✅ Decision impact graph visualizes decision ripple effects
✅ UI tests passing for all components
✅ E2E test validates full workflow
✅ Performance acceptable (< 5s initial load, progressive loading for analysis)
✅ Documentation complete with screenshots

## Future Enhancements

- **Comparative Analysis:** Compare multiple projects side-by-side
- **Pattern Detection:** Identify recurring failure patterns across projects
- **Export Reports:** Generate PDF/Markdown reports
- **Collaborative Annotations:** Allow users to add notes to analyses
- **Real-time + Historical:** Overlay historical patterns on live monitoring
- **Agent Training:** Use historical failures to improve agent prompts

## Next Steps

After Phase 3 completion:
1. User acceptance testing with real projects
2. Collect feedback on analysis quality and UI/UX
3. Iterate on visualizations based on user needs
4. Document best practices for post-project analysis
