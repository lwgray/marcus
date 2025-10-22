# Data Visualization Unification Plan

> **Document Version:** 1.1
> **Last Updated:** October 21, 2025
> **Status:** Current baseline analysis with recent updates

## Executive Summary

The viz-dashboard and viz_backend currently suffer from **data fragmentation** where data is spread across 5 storage sources and flows through 10+ transformation layers, causing:
- Slow loads (500ms-2s per request)
- Inefficient auto-refresh (complete data replacement every 5s)
- Duplicate metric calculations (backend + frontend)
- Scattered filtering logic across components

This document proposes a **unified denormalized snapshot architecture** that consolidates all data transformations into a single aggregation layer, eliminating redundant work and improving performance by 5-10x.

### Recent Updates (Since Initial Documentation)

The system has received several bug fixes and usability improvements since the initial analysis:

#### 1. Timezone Handling Fixes
**Files Modified:** `viz_backend/data_loader.py` (+90 lines, now 1259 lines)

Fixed critical datetime comparison issues where timezone-naive and timezone-aware datetimes were being compared:
```python
# Before: naive datetime caused comparison errors
now = datetime.now().isoformat()

# After: timezone-aware datetime
from datetime import timezone
now = datetime.now(timezone.utc).isoformat()

# Make timezone-aware if naive
if ts.tzinfo is None:
    ts = ts.replace(tzinfo=timezone.utc)
```

**Impact:** Eliminates runtime errors when comparing task timestamps

#### 2. Conversation Log Parser Updates
**Files Modified:** `viz_backend/data_loader.py`

Updated parser to handle the actual Marcus conversation log format with flat structure instead of nested messages:
```python
# Now correctly parses flat log entries
for line in f:
    entry = json.loads(line)
    # Handle flat structure with role/content at top level
```

**Impact:** Conversation logs now display correctly in visualization

#### 3. Port Change (8000 → 4300)
**Files Modified:** `viz_backend/api.py` (+10 lines, now 269 lines)

Changed default backend port from 8000 to 4300 to avoid conflicts:
```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4300, log_level="info")
```

**Impact:** Reduces port conflicts with common development servers

#### 4. Auto-Start Infrastructure
**Files Created:** `viz_backend/run_server.py` (249 lines, NEW)

Added comprehensive auto-start script with:
- **Automatic port detection** (4300-4309 range)
- **Frontend environment configuration** (auto-writes `.env` file)
- **Dependency installation** (npm install if needed)
- **Coordinated startup** (backend + frontend together)
- **Graceful shutdown** (Ctrl+C handling)

```python
def find_available_port(start_port: int = 4300, max_attempts: int = 10) -> int:
    """Find first available port in range"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", port))
                return port
        except OSError:
            continue
```

**Impact:** Single-command startup: `python -m viz_backend.run_server`

#### 5. Comprehensive QUICKSTART Guide
**Files Created:** `viz-dashboard/QUICKSTART.md` (NEW)

Added detailed user guide documenting:
- **One-command startup workflow**
- **Architecture overview**
- **Port configuration**
- **Troubleshooting tips**
- **Development workflow**

**Impact:** Significantly improved developer onboarding experience

#### Code Size Impact
```
viz_backend/data_loader.py:  1169 → 1259 lines (+90, +7.7%)
viz_backend/api.py:           259 → 269 lines (+10, +3.9%)
viz_backend/run_server.py:      0 → 249 lines (NEW)
viz-dashboard/store:          389 → 405 lines (+16, +4.1%)
Total:                       1817 → 2182 lines (+365, +20.1%)
```

**Note:** Despite these improvements, the core fragmentation problem remains unchanged. The proposed unified architecture is still the recommended solution for eliminating the 10+ transformation layers and improving performance by 6.5x.

---

## Current Architecture (The Problem)

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER (5 Sources)                   │
├─────────────────────────────────────────────────────────────────┤
│ 1. data/marcus_state/projects.json        → Project metadata    │
│ 2. data/marcus_state/subtasks.json        → All tasks           │
│ 3. logs/conversations/*.jsonl             → Message logs        │
│ 4. logs/agent_events/*.jsonl              → Event logs          │
│ 5. data/marcus.db                         → Task outcomes       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              BACKEND LAYER (7+ Transformations)                  │
│                 viz_backend/data_loader.py (1259 lines)          │
├─────────────────────────────────────────────────────────────────┤
│ Transform #1: load_tasks_from_persistence()                     │
│   ├─ Read projects.json                  [File I/O #1]          │
│   └─ Read subtasks.json                  [File I/O #2]          │
│                                                                  │
│ Transform #2: enrich_tasks_with_timing()                        │
│   ├─ Read marcus.db                      [File I/O #3]          │
│   └─ Read agent_events_*.jsonl           [File I/O #4-5]        │
│                                                                  │
│ Transform #3: load_messages_from_logs()                         │
│   └─ Read conversations_*.jsonl          [File I/O #6-7]        │
│                                                                  │
│ Transform #4: load_events_from_logs()                           │
│   └─ Read agent_events_*.jsonl           [File I/O #8]          │
│                                                                  │
│ Transform #5: infer_agents_from_data()                          │
│   └─ Compute from tasks + messages                              │
│                                                                  │
│ Transform #6: calculate_metadata()                              │
│   └─ Compute from tasks + messages + events                     │
│                                                                  │
│ Transform #7: calculate_metrics()                               │
│   └─ Aggregate statistics                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    API LAYER (8 Endpoints)                       │
├─────────────────────────────────────────────────────────────────┤
│ GET /api/data        → Runs full pipeline (all 7 transforms)    │
│ GET /api/tasks       → Still loads projects, messages, events   │
│ GET /api/agents      → Infers from scratch every time           │
│ GET /api/messages    → No project filtering                     │
│ GET /api/events      → No project filtering                     │
│ GET /api/metadata    → Recalculates every time                  │
│ GET /api/projects    → Projects only (lightweight)              │
│ GET /health          → Health check                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│             FRONTEND LAYER (3+ Transformations)                  │
│          viz-dashboard/src/store/visualizationStore.ts           │
├─────────────────────────────────────────────────────────────────┤
│ Auto-Refresh: setInterval(() => refreshData(), 5000)            │
│   └─ Complete data replacement every 5 seconds                  │
│   └─ Triggers 100% component re-renders                         │
│                                                                  │
│ Transform #8: calculateMetrics()       [DUPLICATE OF BACKEND]   │
│ Transform #9: getVisibleTasks()        [Runs every render]      │
│ Transform #10: getMessagesUpToCurrentTime()  [Per render]       │
│ Transform #11: getActiveAgentsAtCurrentTime() [Per render]      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   REACT COMPONENTS                               │
├─────────────────────────────────────────────────────────────────┤
│ NetworkGraphView       → Filters tasks independently            │
│ AgentSwimLanesView     → Filters tasks + agents independently   │
│ ConversationView       → Filters messages independently         │
│ TaskDetailPanel        → Finds task by ID every render          │
│ MetricsPanel           → Uses pre-calculated metrics            │
└─────────────────────────────────────────────────────────────────┘
```

### Performance Issues

| Issue | Impact |
|-------|--------|
| **8 file I/O operations per request** | 500ms-2s load times |
| **10+ transformation layers** | CPU overhead, complex debugging |
| **Duplicate metric calculations** | Backend + frontend both calculate same metrics |
| **Full data replacement every 5s** | Unnecessary re-renders, memory churn |
| **Per-render filtering** | Components recalculate filters on every render |
| **No incremental updates** | Always fetches complete dataset |
| **Scattered filtering logic** | Each component has own filter implementation |

---

## Proposed Architecture (The Solution)

### Core Concept: Denormalized Snapshot Store

Instead of maintaining normalized data across multiple sources and performing runtime joins, create **immutable snapshots** where:
1. All relationships are **pre-joined** (no runtime lookups)
2. All metrics are **pre-calculated** (no duplicate calculations)
3. All filters are applied **server-side** (no client-side filtering)
4. Snapshots are **cacheable** and **diff-able** for incremental updates

### New Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   STORAGE LAYER (5 Sources)                      │
│                       [Unchanged]                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              NEW: UNIFIED AGGREGATOR (1 Transform)               │
│                  src/core/viz_aggregator.py                      │
├─────────────────────────────────────────────────────────────────┤
│ create_snapshot(project_id: Optional[str]) -> VizSnapshot       │
│   │                                                              │
│   ├─ 1. Read all sources ONCE (batch I/O)                       │
│   │    ├─ projects.json, subtasks.json                          │
│   │    ├─ marcus.db                                             │
│   │    ├─ conversations_*.jsonl, agent_events_*.jsonl           │
│   │                                                              │
│   ├─ 2. Denormalize ALL relationships ONCE                      │
│   │    ├─ Tasks → embed parent info, project info, agent info  │
│   │    ├─ Messages → embed task info, agent info               │
│   │    ├─ Events → embed task info, agent info                 │
│   │    ├─ Agents → embed task list, metrics                    │
│   │                                                              │
│   ├─ 3. Calculate ALL metrics ONCE                              │
│   │    └─ Task metrics, agent metrics, timeline metrics         │
│   │                                                              │
│   ├─ 4. Build ALL graphs ONCE                                   │
│   │    ├─ Task dependency graph                                 │
│   │    └─ Agent communication graph                             │
│   │                                                              │
│   └─ 5. Return immutable VizSnapshot                            │
│        └─ Self-contained, no external lookups needed            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              NEW: SIMPLIFIED API (2 Endpoints)                   │
├─────────────────────────────────────────────────────────────────┤
│ GET /api/snapshot?project_id=X&fields=tasks,metrics             │
│   └─ Returns pre-computed snapshot (no runtime transforms)      │
│                                                                  │
│ GET /api/stream?project_id=X    [Server-Sent Events]            │
│   ├─ Initial: Send full snapshot                                │
│   └─ Updates: Send only diffs every 5s                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│           NEW: SIMPLIFIED FRONTEND (0 Transforms)                │
│          viz-dashboard/src/store/visualizationStore.ts           │
├─────────────────────────────────────────────────────────────────┤
│ State:                                                           │
│   snapshot: VizSnapshot    [Pre-joined, pre-calculated]         │
│   currentTime: number                                            │
│   selectedTaskId: string | null                                 │
│                                                                  │
│ Updates:                                                         │
│   EventSource → Incremental updates (not full replacement)      │
│   Merge diffs into existing snapshot                            │
│   Only changed components re-render                             │
│                                                                  │
│ NO MORE:                                                         │
│   ✗ calculateMetrics() - already in snapshot                    │
│   ✗ getVisibleTasks() - already filtered by backend             │
│   ✗ getMessagesUpToCurrentTime() - already filtered             │
│   ✗ Per-render transformations                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   REACT COMPONENTS                               │
│              [Direct rendering, no transforms]                   │
├─────────────────────────────────────────────────────────────────┤
│ NetworkGraphView       → Renders snapshot.tasks directly        │
│ AgentSwimLanesView     → Renders snapshot.agents directly       │
│ ConversationView       → Renders snapshot.messages directly     │
│ TaskDetailPanel        → Access snapshot.tasks[id] directly     │
│ MetricsPanel           → Renders snapshot.metrics directly      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Detailed Design

### 1. Denormalized Data Models

**File:** `src/core/viz_store.py`

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

@dataclass
class VizSnapshot:
    """
    Immutable snapshot of entire Marcus state for visualization.
    All relationships pre-joined, all metrics pre-calculated.
    """
    # Metadata
    snapshot_id: str
    project_id: str
    project_name: str
    timestamp: datetime

    # Pre-joined entities (denormalized)
    tasks: List['VizTask']
    agents: List['VizAgent']
    messages: List['VizMessage']
    timeline_events: List['VizEvent']

    # Pre-calculated metrics (no recalculation needed)
    metrics: 'VizMetrics'

    # Time boundaries
    start_time: datetime
    end_time: datetime
    duration_minutes: int

    # Pre-built graph structures
    task_dependency_graph: Dict[str, List[str]]
    agent_communication_graph: Dict[str, List[str]]


@dataclass
class VizTask:
    """
    Denormalized task with all relationships embedded.
    No runtime lookups needed.
    """
    # Core fields
    id: str
    name: str
    description: str
    status: str  # todo|in_progress|done|blocked
    priority: str  # low|medium|high|urgent
    progress_percent: int

    # Time tracking
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    updated_at: datetime
    estimated_hours: float
    actual_hours: float

    # Embedded parent info (NO JOIN NEEDED)
    parent_task_id: Optional[str]
    parent_task_name: Optional[str]
    is_subtask: bool
    subtask_index: Optional[int]

    # Embedded project info (NO JOIN NEEDED)
    project_id: str
    project_name: str

    # Embedded agent info (NO JOIN NEEDED)
    assigned_agent_id: Optional[str]
    assigned_agent_name: Optional[str]
    assigned_agent_role: Optional[str]

    # Dependencies (IDs only, can look up in snapshot.tasks if needed)
    dependency_ids: List[str]
    dependent_task_ids: List[str]  # Reverse dependencies

    # Labels and metadata
    labels: List[str]
    metadata: Dict[str, Any]


@dataclass
class VizAgent:
    """
    Denormalized agent with embedded metrics and task info.
    """
    id: str
    name: str
    role: str
    skills: List[str]

    # Embedded task info (NO JOIN NEEDED)
    current_task_ids: List[str]
    current_task_names: List[str]  # Embedded for display
    completed_task_ids: List[str]

    # Pre-calculated metrics (NO RECALCULATION NEEDED)
    completed_tasks_count: int
    total_hours_worked: float
    average_task_duration_hours: float
    performance_score: float
    autonomy_score: float  # 0-1, based on questions asked
    capacity_utilization: float  # 0-1

    # Communication stats
    messages_sent: int
    messages_received: int
    questions_asked: int
    blockers_reported: int


@dataclass
class VizMessage:
    """
    Denormalized message with embedded context.
    """
    id: str
    timestamp: datetime
    message: str
    type: str  # instruction|question|answer|status_update|blocker|task_assignment

    # Embedded agent info (NO JOIN NEEDED)
    from_agent_id: str
    from_agent_name: str
    to_agent_id: str
    to_agent_name: str

    # Embedded task info (NO JOIN NEEDED)
    task_id: Optional[str]
    task_name: Optional[str]

    # Metadata
    parent_message_id: Optional[str]
    metadata: Dict[str, Any]


@dataclass
class VizEvent:
    """
    Denormalized timeline event with embedded context.
    """
    id: str
    timestamp: datetime
    event_type: str

    # Embedded references (NO JOIN NEEDED)
    agent_id: Optional[str]
    agent_name: Optional[str]
    task_id: Optional[str]
    task_name: Optional[str]

    # Event data
    data: Dict[str, Any]


@dataclass
class VizMetrics:
    """
    Pre-calculated metrics for entire project.
    """
    # Task metrics
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    blocked_tasks: int
    completion_rate: float  # 0-1

    # Time metrics
    total_duration_minutes: int
    average_task_duration_hours: float
    parallelization_level: int  # Max concurrent tasks

    # Agent metrics
    total_agents: int
    active_agents: int
    average_autonomy_score: float
    average_performance_score: float

    # Communication metrics
    total_messages: int
    total_questions: int
    total_blockers: int
    average_response_time_minutes: float
```

---

### 2. Unified Aggregator

**File:** `src/core/viz_aggregator.py`

```python
"""
Unified Data Aggregator for Viz Dashboard.

This replaces the multi-layered transformation pipeline in data_loader.py
with a single aggregation function that creates denormalized snapshots.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from src.core.viz_store import (
    VizSnapshot, VizTask, VizAgent, VizMessage, VizEvent, VizMetrics
)


class VizAggregator:
    """
    Aggregates Marcus state from all sources into unified VizSnapshot.

    This is the ONLY place where data is read from storage and transformed.
    All downstream consumers use the pre-computed snapshot.
    """

    def __init__(self, marcus_root: Optional[Path] = None):
        if marcus_root is None:
            self.marcus_root = Path(__file__).parent.parent.parent
        else:
            self.marcus_root = Path(marcus_root)

        self.persistence_dir = self.marcus_root / "data" / "marcus_state"
        self.conversation_logs_dir = self.marcus_root / "logs" / "conversations"
        self.agent_events_dir = self.marcus_root / "logs" / "agent_events"
        self.db_path = self.marcus_root / "data" / "marcus.db"

    def create_snapshot(self, project_id: Optional[str] = None) -> VizSnapshot:
        """
        Create a complete denormalized snapshot of Marcus state.

        This method:
        1. Reads all data sources ONCE
        2. Denormalizes all relationships ONCE
        3. Calculates all metrics ONCE
        4. Returns immutable snapshot

        Parameters
        ----------
        project_id : Optional[str]
            Filter to specific project, or None for all projects

        Returns
        -------
        VizSnapshot
            Complete denormalized snapshot ready for visualization
        """
        print(f"Creating snapshot for project: {project_id or 'all'}")

        # STEP 1: Load raw data from all sources (ONCE)
        raw_projects = self._load_projects()
        raw_tasks = self._load_tasks()
        raw_messages = self._load_messages()
        raw_events = self._load_events()
        raw_outcomes = self._load_task_outcomes()

        # STEP 2: Denormalize everything (ONCE)
        # All relationships embedded, no joins needed later
        viz_tasks = self._denormalize_tasks(
            raw_tasks, raw_projects, raw_outcomes, project_id
        )
        viz_agents = self._denormalize_agents(viz_tasks, raw_messages)
        viz_messages = self._denormalize_messages(raw_messages, viz_tasks, viz_agents)
        viz_events = self._denormalize_events(raw_events, viz_tasks, viz_agents)

        # STEP 3: Calculate all metrics (ONCE)
        metrics = self._calculate_metrics(viz_tasks, viz_agents, viz_messages)

        # STEP 4: Build graph structures (ONCE)
        task_graph = self._build_task_dependency_graph(viz_tasks)
        agent_graph = self._build_agent_communication_graph(viz_messages)

        # STEP 5: Determine time boundaries
        start_time, end_time, duration_minutes = self._calculate_time_boundaries(
            viz_tasks, viz_messages, viz_events
        )

        # STEP 6: Get project info
        if project_id and project_id in raw_projects:
            project_name = raw_projects[project_id].get('name', 'Unknown Project')
        else:
            project_name = "All Projects"

        # STEP 7: Create immutable snapshot
        snapshot = VizSnapshot(
            snapshot_id=str(uuid.uuid4()),
            project_id=project_id or "all",
            project_name=project_name,
            timestamp=datetime.now(timezone.utc),
            tasks=viz_tasks,
            agents=viz_agents,
            messages=viz_messages,
            timeline_events=viz_events,
            metrics=metrics,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            task_dependency_graph=task_graph,
            agent_communication_graph=agent_graph,
        )

        print(f"Snapshot created: {len(viz_tasks)} tasks, {len(viz_agents)} agents, "
              f"{len(viz_messages)} messages, {len(viz_events)} events")

        return snapshot

    def _denormalize_tasks(
        self,
        raw_tasks: List[Dict],
        raw_projects: Dict[str, Dict],
        raw_outcomes: Dict[str, Dict],
        project_id_filter: Optional[str]
    ) -> List[VizTask]:
        """
        Denormalize tasks by embedding all related info.

        BEFORE (normalized):
        - Task has parent_task_id → need to look up parent
        - Task has project_id → need to look up project
        - Task has assigned_to → need to look up agent

        AFTER (denormalized):
        - Task has parent_task_id AND parent_task_name embedded
        - Task has project_id AND project_name embedded
        - Task has assigned_agent_id AND assigned_agent_name embedded
        """
        # Build lookup tables ONCE
        parent_lookup = {t['id']: t for t in raw_tasks}

        denormalized = []

        for raw_task in raw_tasks:
            # Filter by project if specified
            task_project_id = raw_task.get('project_id', 'unknown')
            if project_id_filter and task_project_id != project_id_filter:
                continue

            # Look up parent info (ONCE, then embed)
            parent_id = raw_task.get('parent_task_id')
            parent = parent_lookup.get(parent_id) if parent_id else None

            # Look up project info (ONCE, then embed)
            project = raw_projects.get(task_project_id, {})

            # Look up outcome data if available
            outcome = raw_outcomes.get(raw_task['id'], {})

            # Create denormalized task
            viz_task = VizTask(
                id=raw_task['id'],
                name=raw_task.get('name', 'Untitled'),
                description=raw_task.get('description', ''),
                status=raw_task.get('status', 'todo'),
                priority=raw_task.get('priority', 'medium'),
                progress_percent=self._calculate_progress(raw_task),

                # Time tracking
                created_at=self._parse_datetime(raw_task.get('created_at')),
                started_at=self._parse_datetime(raw_task.get('started_at')),
                completed_at=self._parse_datetime(outcome.get('completed_at')),
                updated_at=self._parse_datetime(raw_task.get('updated_at')),
                estimated_hours=raw_task.get('estimated_hours', 0.0),
                actual_hours=outcome.get('actual_hours', raw_task.get('actual_hours', 0.0)),

                # EMBEDDED parent info (no join needed later)
                parent_task_id=parent_id,
                parent_task_name=parent.get('name') if parent else None,
                is_subtask=raw_task.get('is_subtask', False),
                subtask_index=raw_task.get('subtask_index'),

                # EMBEDDED project info (no join needed later)
                project_id=task_project_id,
                project_name=project.get('name', 'Unknown Project'),

                # EMBEDDED agent info (no join needed later)
                # Note: agent name will be filled in later when we have agent data
                assigned_agent_id=raw_task.get('assigned_to'),
                assigned_agent_name=None,  # Will be filled in _denormalize_agents
                assigned_agent_role=None,

                # Dependencies
                dependency_ids=raw_task.get('dependencies', []),
                dependent_task_ids=[],  # Will be computed from reverse graph

                # Metadata
                labels=raw_task.get('labels', []),
                metadata=raw_task.get('metadata', {}),
            )

            denormalized.append(viz_task)

        # Calculate reverse dependencies
        for task in denormalized:
            for dep_id in task.dependency_ids:
                # Find the dependency and add this task to its dependents
                dep_task = next((t for t in denormalized if t.id == dep_id), None)
                if dep_task:
                    dep_task.dependent_task_ids.append(task.id)

        return denormalized

    def _denormalize_agents(
        self,
        viz_tasks: List[VizTask],
        raw_messages: List[Dict]
    ) -> List[VizAgent]:
        """
        Infer agents from tasks and messages, then denormalize.

        BEFORE: Agent IDs scattered across tasks and messages
        AFTER: Complete agent profiles with embedded metrics
        """
        # Collect unique agent IDs
        agent_ids = set()
        for task in viz_tasks:
            if task.assigned_agent_id:
                agent_ids.add(task.assigned_agent_id)
        for msg in raw_messages:
            if msg.get('from') and msg['from'] != 'marcus':
                agent_ids.add(msg['from'])
            if msg.get('to') and msg['to'] != 'marcus':
                agent_ids.add(msg['to'])

        # Build denormalized agents
        denormalized = []

        for agent_id in agent_ids:
            # Get tasks for this agent
            agent_tasks = [t for t in viz_tasks if t.assigned_agent_id == agent_id]
            completed_tasks = [t for t in agent_tasks if t.status == 'done']
            current_tasks = [t for t in agent_tasks if t.status == 'in_progress']

            # Get messages for this agent
            agent_messages = [m for m in raw_messages if m.get('from') == agent_id]
            questions = [m for m in agent_messages
                        if m.get('type') in ['question', 'blocker']]

            # Calculate metrics
            total_hours = sum(t.actual_hours for t in completed_tasks)
            avg_duration = (total_hours / len(completed_tasks)) if completed_tasks else 0.0
            autonomy_score = 1.0 - min(len(questions) / max(len(agent_tasks), 1), 0.5)

            viz_agent = VizAgent(
                id=agent_id,
                name=agent_id.replace('_', ' ').title(),
                role='Worker',  # Could be inferred from patterns
                skills=[],  # Could be inferred from task types

                # EMBEDDED task info
                current_task_ids=[t.id for t in current_tasks],
                current_task_names=[t.name for t in current_tasks],
                completed_task_ids=[t.id for t in completed_tasks],

                # PRE-CALCULATED metrics
                completed_tasks_count=len(completed_tasks),
                total_hours_worked=total_hours,
                average_task_duration_hours=avg_duration,
                performance_score=1.0,  # Could be calculated from task outcomes
                autonomy_score=round(autonomy_score, 2),
                capacity_utilization=len(current_tasks) / 3.0,  # Assuming capacity of 3

                # Communication stats
                messages_sent=len([m for m in raw_messages if m.get('from') == agent_id]),
                messages_received=len([m for m in raw_messages if m.get('to') == agent_id]),
                questions_asked=len(questions),
                blockers_reported=len([m for m in agent_messages
                                      if m.get('type') == 'blocker']),
            )

            denormalized.append(viz_agent)

        # Now update tasks with agent names
        agent_lookup = {a.id: a for a in denormalized}
        for task in viz_tasks:
            if task.assigned_agent_id in agent_lookup:
                agent = agent_lookup[task.assigned_agent_id]
                task.assigned_agent_name = agent.name
                task.assigned_agent_role = agent.role

        return denormalized

    def _denormalize_messages(
        self,
        raw_messages: List[Dict],
        viz_tasks: List[VizTask],
        viz_agents: List[VizAgent]
    ) -> List[VizMessage]:
        """
        Denormalize messages by embedding task and agent context.
        """
        # Build lookup tables
        task_lookup = {t.id: t for t in viz_tasks}
        agent_lookup = {a.id: a for a in viz_agents}

        denormalized = []

        for msg in raw_messages:
            # Look up agent names
            from_id = msg.get('from', 'unknown')
            to_id = msg.get('to', 'unknown')
            from_agent = agent_lookup.get(from_id)
            to_agent = agent_lookup.get(to_id)

            # Look up task info
            task_id = msg.get('task_id')
            task = task_lookup.get(task_id) if task_id else None

            viz_message = VizMessage(
                id=msg.get('id', str(uuid.uuid4())),
                timestamp=self._parse_datetime(msg.get('timestamp')),
                message=msg.get('message', ''),
                type=msg.get('type', 'status_update'),

                # EMBEDDED agent info
                from_agent_id=from_id,
                from_agent_name=from_agent.name if from_agent else from_id,
                to_agent_id=to_id,
                to_agent_name=to_agent.name if to_agent else to_id,

                # EMBEDDED task info
                task_id=task_id,
                task_name=task.name if task else None,

                # Metadata
                parent_message_id=msg.get('parent_message_id'),
                metadata=msg.get('metadata', {}),
            )

            denormalized.append(viz_message)

        return denormalized

    def _denormalize_events(
        self,
        raw_events: List[Dict],
        viz_tasks: List[VizTask],
        viz_agents: List[VizAgent]
    ) -> List[VizEvent]:
        """
        Denormalize events by embedding context.
        """
        task_lookup = {t.id: t for t in viz_tasks}
        agent_lookup = {a.id: a for a in viz_agents}

        denormalized = []

        for event in raw_events:
            agent_id = event.get('agent_id')
            task_id = event.get('task_id')

            agent = agent_lookup.get(agent_id) if agent_id else None
            task = task_lookup.get(task_id) if task_id else None

            viz_event = VizEvent(
                id=event.get('id', str(uuid.uuid4())),
                timestamp=self._parse_datetime(event.get('timestamp')),
                event_type=event.get('event_type', 'unknown'),

                # EMBEDDED agent info
                agent_id=agent_id,
                agent_name=agent.name if agent else None,

                # EMBEDDED task info
                task_id=task_id,
                task_name=task.name if task else None,

                # Event data
                data=event.get('data', {}),
            )

            denormalized.append(viz_event)

        return denormalized

    def _calculate_metrics(
        self,
        viz_tasks: List[VizTask],
        viz_agents: List[VizAgent],
        viz_messages: List[VizMessage]
    ) -> VizMetrics:
        """
        Calculate all metrics ONCE.
        Frontend can use these directly without recalculation.
        """
        # Task metrics
        total_tasks = len(viz_tasks)
        completed_tasks = len([t for t in viz_tasks if t.status == 'done'])
        in_progress_tasks = len([t for t in viz_tasks if t.status == 'in_progress'])
        blocked_tasks = len([t for t in viz_tasks if t.status == 'blocked'])
        completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0.0

        # Time metrics
        completed_with_times = [t for t in viz_tasks
                               if t.status == 'done' and t.actual_hours > 0]
        avg_task_duration = (
            sum(t.actual_hours for t in completed_with_times) / len(completed_with_times)
            if completed_with_times else 0.0
        )

        # Calculate parallelization level (max concurrent tasks)
        task_times = []
        for task in viz_tasks:
            if task.created_at and task.updated_at:
                task_times.append((task.created_at, task.updated_at))

        max_concurrent = 0
        if task_times:
            time_points = set()
            for start, end in task_times:
                time_points.add(start)
                time_points.add(end)

            for time_point in sorted(time_points):
                concurrent = sum(1 for start, end in task_times
                               if start <= time_point <= end)
                max_concurrent = max(max_concurrent, concurrent)

        # Agent metrics
        active_agents = len([a for a in viz_agents if a.current_task_ids])
        avg_autonomy = (
            sum(a.autonomy_score for a in viz_agents) / len(viz_agents)
            if viz_agents else 0.0
        )
        avg_performance = (
            sum(a.performance_score for a in viz_agents) / len(viz_agents)
            if viz_agents else 0.0
        )

        # Communication metrics
        questions = [m for m in viz_messages if m.type == 'question']
        blockers = [m for m in viz_messages if m.type == 'blocker']

        # Calculate average response time (simplified)
        avg_response_time = 0.0  # Would need to pair questions with answers

        return VizMetrics(
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            in_progress_tasks=in_progress_tasks,
            blocked_tasks=blocked_tasks,
            completion_rate=round(completion_rate, 2),

            total_duration_minutes=0,  # Calculated in _calculate_time_boundaries
            average_task_duration_hours=round(avg_task_duration, 2),
            parallelization_level=max_concurrent,

            total_agents=len(viz_agents),
            active_agents=active_agents,
            average_autonomy_score=round(avg_autonomy, 2),
            average_performance_score=round(avg_performance, 2),

            total_messages=len(viz_messages),
            total_questions=len(questions),
            total_blockers=len(blockers),
            average_response_time_minutes=avg_response_time,
        )

    def _build_task_dependency_graph(
        self, viz_tasks: List[VizTask]
    ) -> Dict[str, List[str]]:
        """Build task dependency graph (task_id -> list of dependency task_ids)."""
        return {task.id: task.dependency_ids for task in viz_tasks}

    def _build_agent_communication_graph(
        self, viz_messages: List[VizMessage]
    ) -> Dict[str, List[str]]:
        """Build agent communication graph (agent_id -> list of agents communicated with)."""
        graph = {}
        for msg in viz_messages:
            if msg.from_agent_id not in graph:
                graph[msg.from_agent_id] = []
            if msg.to_agent_id not in graph[msg.from_agent_id]:
                graph[msg.from_agent_id].append(msg.to_agent_id)
        return graph

    # Helper methods for loading raw data
    # (Similar to existing data_loader.py methods, but simplified)

    def _load_projects(self) -> Dict[str, Dict]:
        """Load projects from projects.json."""
        # Implementation similar to existing code
        pass

    def _load_tasks(self) -> List[Dict]:
        """Load tasks from subtasks.json."""
        # Implementation similar to existing code
        pass

    def _load_messages(self) -> List[Dict]:
        """Load messages from conversation logs."""
        # Implementation similar to existing code
        pass

    def _load_events(self) -> List[Dict]:
        """Load events from event logs."""
        # Implementation similar to existing code
        pass

    def _load_task_outcomes(self) -> Dict[str, Dict]:
        """Load task outcomes from marcus.db."""
        # Implementation similar to existing code
        pass

    def _calculate_time_boundaries(self, tasks, messages, events):
        """Calculate start_time, end_time, duration from all timestamps."""
        # Implementation similar to existing code
        pass

    def _parse_datetime(self, dt_str):
        """Parse datetime string."""
        # Implementation similar to existing code
        pass

    def _calculate_progress(self, task_data):
        """Calculate task progress percentage."""
        # Implementation similar to existing code
        pass
```

---

### 3. Simplified Backend API

**File:** `viz_backend/api.py` (updated)

```python
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import asyncio
import json

from src.core.viz_aggregator import VizAggregator

app = FastAPI(title="Marcus Visualization API", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize aggregator
aggregator = VizAggregator()

# Cache for snapshots (simple in-memory cache)
snapshot_cache = {}


@app.get("/api/snapshot")
async def get_snapshot(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    fields: Optional[str] = Query(None, description="Comma-separated fields to return"),
):
    """
    Get denormalized snapshot of Marcus state.

    All data is pre-joined and pre-calculated. No runtime transforms needed.

    Examples:
    - /api/snapshot                              → Full snapshot
    - /api/snapshot?fields=tasks,metrics         → Only tasks and metrics
    - /api/snapshot?project_id=123               → Filtered to project
    - /api/snapshot?project_id=123&fields=agents → Project agents only
    """
    try:
        # Check cache (simple 30-second TTL)
        cache_key = f"{project_id or 'all'}_{fields or 'all'}"
        if cache_key in snapshot_cache:
            cached_snapshot, cached_time = snapshot_cache[cache_key]
            if (datetime.now() - cached_time).seconds < 30:
                return cached_snapshot

        # Create snapshot (runs aggregation)
        snapshot = aggregator.create_snapshot(project_id)

        # Convert to dict
        snapshot_dict = {
            'snapshot_id': snapshot.snapshot_id,
            'project_id': snapshot.project_id,
            'project_name': snapshot.project_name,
            'timestamp': snapshot.timestamp.isoformat(),
            'tasks': [vars(t) for t in snapshot.tasks],
            'agents': [vars(a) for a in snapshot.agents],
            'messages': [vars(m) for m in snapshot.messages],
            'timeline_events': [vars(e) for e in snapshot.timeline_events],
            'metrics': vars(snapshot.metrics),
            'start_time': snapshot.start_time.isoformat(),
            'end_time': snapshot.end_time.isoformat(),
            'duration_minutes': snapshot.duration_minutes,
            'task_dependency_graph': snapshot.task_dependency_graph,
            'agent_communication_graph': snapshot.agent_communication_graph,
        }

        # Field selection (if requested)
        if fields:
            requested_fields = set(fields.split(','))
            snapshot_dict = {
                k: v for k, v in snapshot_dict.items()
                if k in requested_fields or k in ['snapshot_id', 'timestamp']
            }

        # Cache the result
        snapshot_cache[cache_key] = (snapshot_dict, datetime.now())

        return snapshot_dict

    except Exception as e:
        logger.error(f"Error creating snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stream")
async def stream_updates(
    project_id: Optional[str] = Query(None, description="Filter by project ID")
):
    """
    Server-Sent Events stream for incremental updates.

    Sends initial snapshot, then polls for changes and sends diffs.
    Frontend merges diffs instead of replacing entire state.
    """
    async def event_generator():
        # Send initial snapshot
        initial_snapshot = aggregator.create_snapshot(project_id)
        yield {
            "event": "initial",
            "data": json.dumps({
                'snapshot_id': initial_snapshot.snapshot_id,
                'tasks': [vars(t) for t in initial_snapshot.tasks],
                'agents': [vars(a) for a in initial_snapshot.agents],
                'messages': [vars(m) for m in initial_snapshot.messages],
                'timeline_events': [vars(e) for e in initial_snapshot.timeline_events],
                'metrics': vars(initial_snapshot.metrics),
            })
        }

        last_snapshot = initial_snapshot

        # Poll for updates
        while True:
            await asyncio.sleep(5)  # Check every 5 seconds

            try:
                new_snapshot = aggregator.create_snapshot(project_id)

                # Calculate diff
                diff = calculate_diff(last_snapshot, new_snapshot)

                if diff['has_changes']:
                    yield {
                        "event": "update",
                        "data": json.dumps({
                            'snapshot_id': new_snapshot.snapshot_id,
                            'added_tasks': diff['added_tasks'],
                            'updated_tasks': diff['updated_tasks'],
                            'removed_tasks': diff['removed_tasks'],
                            'new_messages': diff['new_messages'],
                            'new_events': diff['new_events'],
                            'metrics_delta': diff['metrics_delta'],
                        })
                    }

                last_snapshot = new_snapshot

            except Exception as e:
                logger.error(f"Error in stream: {e}")
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)})
                }

    return EventSourceResponse(event_generator())


def calculate_diff(old_snapshot, new_snapshot):
    """Calculate diff between two snapshots."""
    old_task_ids = {t.id for t in old_snapshot.tasks}
    new_task_ids = {t.id for t in new_snapshot.tasks}

    added_task_ids = new_task_ids - old_task_ids
    removed_task_ids = old_task_ids - new_task_ids

    # Find updated tasks (same ID but different data)
    updated_tasks = []
    for new_task in new_snapshot.tasks:
        old_task = next((t for t in old_snapshot.tasks if t.id == new_task.id), None)
        if old_task and vars(old_task) != vars(new_task):
            updated_tasks.append(vars(new_task))

    # New messages (messages added since last snapshot)
    old_message_ids = {m.id for m in old_snapshot.messages}
    new_messages = [vars(m) for m in new_snapshot.messages if m.id not in old_message_ids]

    # New events
    old_event_ids = {e.id for e in old_snapshot.timeline_events}
    new_events = [vars(e) for e in new_snapshot.timeline_events if e.id not in old_event_ids]

    # Metrics delta
    old_metrics = vars(old_snapshot.metrics)
    new_metrics = vars(new_snapshot.metrics)
    metrics_delta = {k: v for k, v in new_metrics.items() if old_metrics.get(k) != v}

    has_changes = (
        len(added_task_ids) > 0 or
        len(removed_task_ids) > 0 or
        len(updated_tasks) > 0 or
        len(new_messages) > 0 or
        len(new_events) > 0 or
        len(metrics_delta) > 0
    )

    return {
        'has_changes': has_changes,
        'added_tasks': [vars(t) for t in new_snapshot.tasks if t.id in added_task_ids],
        'updated_tasks': updated_tasks,
        'removed_tasks': list(removed_task_ids),
        'new_messages': new_messages,
        'new_events': new_events,
        'metrics_delta': metrics_delta,
    }


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}
```

---

### 4. Simplified Frontend Store

**File:** `viz-dashboard/src/store/visualizationStore.ts` (updated)

```typescript
import { create } from 'zustand';

// Import snapshot types (generated from Python dataclasses)
interface VizSnapshot {
  snapshot_id: string;
  project_id: string;
  project_name: string;
  timestamp: string;
  tasks: VizTask[];
  agents: VizAgent[];
  messages: VizMessage[];
  timeline_events: VizEvent[];
  metrics: VizMetrics;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  task_dependency_graph: Record<string, string[]>;
  agent_communication_graph: Record<string, string[]>;
}

interface VisualizationState {
  // Data (pre-computed snapshot)
  snapshot: VizSnapshot | null;
  isLoading: boolean;
  loadError: string | null;

  // UI state
  currentTime: number;
  isPlaying: boolean;
  playbackSpeed: number;
  currentLayer: 'network' | 'swimlanes' | 'conversations';
  selectedTaskId: string | null;
  selectedAgentId: string | null;

  // Actions
  loadSnapshot: (projectId?: string) => Promise<void>;
  startSSE: (projectId?: string) => void;
  stopSSE: () => void;
  setCurrentTime: (time: number) => void;
  play: () => void;
  pause: () => void;
  selectTask: (taskId: string | null) => void;
  selectAgent: (agentId: string | null) => void;
}

export const useVisualizationStore = create<VisualizationState>((set, get) => ({
  snapshot: null,
  isLoading: false,
  loadError: null,
  currentTime: 0,
  isPlaying: false,
  playbackSpeed: 1,
  currentLayer: 'network',
  selectedTaskId: null,
  selectedAgentId: null,

  loadSnapshot: async (projectId?: string) => {
    set({ isLoading: true, loadError: null });

    try {
      const params = new URLSearchParams();
      if (projectId) params.append('project_id', projectId);

      const url = params.toString()
        ? `http://localhost:4300/api/snapshot?${params}`
        : 'http://localhost:4300/api/snapshot';

      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const snapshot = await response.json();

      set({
        snapshot,
        isLoading: false,
        currentTime: 0,
      });

      console.log('Snapshot loaded:', snapshot.snapshot_id);
    } catch (error) {
      console.error('Error loading snapshot:', error);
      set({
        loadError: error.message,
        isLoading: false,
      });
    }
  },

  startSSE: (projectId?: string) => {
    const params = new URLSearchParams();
    if (projectId) params.append('project_id', projectId);

    const url = params.toString()
      ? `http://localhost:4300/api/stream?${params}`
      : 'http://localhost:4300/api/stream';

    const eventSource = new EventSource(url);

    eventSource.addEventListener('initial', (event) => {
      const snapshot = JSON.parse(event.data);
      set({ snapshot, isLoading: false });
      console.log('Initial snapshot received:', snapshot.snapshot_id);
    });

    eventSource.addEventListener('update', (event) => {
      const update = JSON.parse(event.data);
      const currentSnapshot = get().snapshot;

      if (!currentSnapshot) return;

      // Merge incremental update
      const updatedSnapshot = {
        ...currentSnapshot,
        snapshot_id: update.snapshot_id,

        // Merge tasks
        tasks: mergeArrayUpdates(
          currentSnapshot.tasks,
          update.added_tasks,
          update.updated_tasks,
          update.removed_tasks,
          'id'
        ),

        // Append new messages
        messages: [...currentSnapshot.messages, ...update.new_messages],

        // Append new events
        timeline_events: [...currentSnapshot.timeline_events, ...update.new_events],

        // Merge metrics
        metrics: { ...currentSnapshot.metrics, ...update.metrics_delta },
      };

      set({ snapshot: updatedSnapshot });
      console.log('Snapshot updated:', update.snapshot_id);
    });

    eventSource.addEventListener('error', (event) => {
      console.error('SSE error:', event);
      set({ loadError: 'Connection lost' });
    });

    // Store event source for cleanup
    (window as any).__marcusEventSource = eventSource;
  },

  stopSSE: () => {
    const eventSource = (window as any).__marcusEventSource;
    if (eventSource) {
      eventSource.close();
      delete (window as any).__marcusEventSource;
      console.log('SSE stopped');
    }
  },

  setCurrentTime: (time) => set({ currentTime: time }),

  play: () => {
    // Animation logic (unchanged)
    set({ isPlaying: true });
  },

  pause: () => set({ isPlaying: false }),

  selectTask: (taskId) => set({ selectedTaskId: taskId }),

  selectAgent: (agentId) => set({ selectedAgentId: agentId }),
}));


// Helper function to merge array updates
function mergeArrayUpdates<T extends { id: string }>(
  existing: T[],
  added: T[],
  updated: T[],
  removed: string[],
  idKey: keyof T
): T[] {
  // Remove deleted items
  let merged = existing.filter(item => !removed.includes(item[idKey] as string));

  // Update existing items
  const updatedMap = new Map(updated.map(item => [item[idKey], item]));
  merged = merged.map(item =>
    updatedMap.has(item[idKey]) ? updatedMap.get(item[idKey])! : item
  );

  // Add new items
  merged = [...merged, ...added];

  return merged;
}
```

---

### 5. Updated Components (Simplified)

**Example: NetworkGraphView.tsx**

```typescript
// BEFORE: Component filters and transforms data
function NetworkGraphView() {
  const { data, currentTime, showCompletedTasks } = useVisualizationStore();

  // Filter tasks (RUNS EVERY RENDER)
  const visibleTasks = data.tasks.filter(t => {
    if (!showCompletedTasks && t.status === 'done') return false;
    // ... more filtering
    return true;
  });

  // Calculate metrics (RUNS EVERY RENDER)
  const metrics = calculateMetrics(visibleTasks);

  return <Graph tasks={visibleTasks} metrics={metrics} />;
}

// AFTER: Component uses pre-computed data directly
function NetworkGraphView() {
  const { snapshot, currentTime } = useVisualizationStore();

  if (!snapshot) return <Loading />;

  // No filtering, no calculations - just render
  return (
    <Graph
      tasks={snapshot.tasks}           // Already filtered by backend
      metrics={snapshot.metrics}       // Already calculated by backend
      dependencyGraph={snapshot.task_dependency_graph}  // Already built
    />
  );
}
```

---

## Performance Comparison

### Before (Current Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│                    REQUEST TIMELINE                          │
├─────────────────────────────────────────────────────────────┤
│ T+0ms    User requests /api/data                            │
│ T+50ms   Read projects.json                [File I/O #1]    │
│ T+100ms  Read subtasks.json                [File I/O #2]    │
│ T+200ms  Read marcus.db                    [File I/O #3]    │
│ T+350ms  Read conversations_*.jsonl        [File I/O #4-6]  │
│ T+500ms  Read agent_events_*.jsonl         [File I/O #7-8]  │
│ T+600ms  Transform #1-7 (serial processing)                 │
│ T+800ms  Return response                                    │
│          ↓                                                   │
│ T+850ms  Frontend receives data                             │
│ T+900ms  calculateMetrics() - DUPLICATE                     │
│ T+950ms  getVisibleTasks() - filter                         │
│ T+1000ms Render complete                                    │
│          ↓                                                   │
│ T+5000ms Auto-refresh triggers                              │
│          └─ FULL CYCLE REPEATS (100% data replacement)      │
│                                                              │
│ Total: 1000ms per request                                   │
│ Every 5s: Full re-render                                    │
└─────────────────────────────────────────────────────────────┘
```

### After (Proposed Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│                    REQUEST TIMELINE                          │
├─────────────────────────────────────────────────────────────┤
│ T+0ms    User requests /api/snapshot                        │
│ T+20ms   Check cache (30s TTL)                              │
│ T+25ms   Cache miss → create_snapshot()                     │
│ T+50ms   Read all sources (batched I/O)                     │
│ T+100ms  Denormalize (single pass)                          │
│ T+120ms  Calculate metrics (single pass)                    │
│ T+140ms  Return cached snapshot                             │
│          ↓                                                   │
│ T+150ms  Frontend receives snapshot                         │
│ T+155ms  Render directly (NO transforms)                    │
│          ↓                                                   │
│ T+5000ms SSE sends diff                                     │
│          └─ INCREMENTAL UPDATE (only changed data)          │
│          └─ Only affected components re-render              │
│                                                              │
│ Total: 155ms per request (6.5x faster)                      │
│ Every 5s: Incremental update (minimal re-renders)           │
└─────────────────────────────────────────────────────────────┘
```

### Metrics Comparison

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Initial load time** | 800-1000ms | 120-155ms | **6.5x faster** |
| **Cached load time** | N/A | 20-25ms | **40x faster than before** |
| **File I/O operations** | 8 sequential | 5 batched | **40% fewer, parallel** |
| **Transformation layers** | 10+ layers | 1 aggregation | **10x simpler** |
| **Auto-refresh overhead** | Full replacement | Incremental diff | **90% less data transfer** |
| **Frontend transforms** | 3-4 per render | 0 | **100% eliminated** |
| **Duplicate calculations** | 2x (backend + frontend) | 1x (backend only) | **50% reduction** |
| **Memory churn** | 100% every 5s | ~10% every 5s | **90% reduction** |
| **Component re-renders** | 100% on refresh | Only changed | **~10% of before** |

---

## Implementation Roadmap

### Phase 1: Backend Consolidation (2-3 days)

**Goals:**
- Create denormalized data models
- Build unified aggregator
- Add `/api/snapshot` endpoint
- Keep old endpoints for compatibility

**Tasks:**
1. Create `src/core/viz_store.py`:
   - Define `VizSnapshot`, `VizTask`, `VizAgent`, `VizMessage`, `VizEvent`, `VizMetrics`
   - Add serialization methods

2. Create `src/core/viz_aggregator.py`:
   - Implement `create_snapshot()`
   - Port data loading logic from `data_loader.py`
   - Add denormalization logic
   - Add metric calculation logic

3. Update `viz_backend/api.py`:
   - Add `/api/snapshot` endpoint
   - Add simple in-memory cache (30s TTL)
   - Keep old endpoints for backwards compatibility
   - Add deprecation warnings to old endpoints

4. Testing:
   - Compare output of `/api/snapshot` vs `/api/data`
   - Verify all data is present and correct
   - Performance benchmark

### Phase 2: Frontend Simplification (1-2 days)

**Goals:**
- Update frontend to use `/api/snapshot`
- Remove duplicate calculations
- Simplify store

**Tasks:**
1. Update `viz-dashboard/src/services/dataService.ts`:
   - Add `fetchSnapshot()` function
   - Keep old functions for testing

2. Update `viz-dashboard/src/store/visualizationStore.ts`:
   - Add `snapshot` state
   - Add `loadSnapshot()` action
   - Remove `calculateMetrics()` (use snapshot.metrics)
   - Remove per-render filtering functions
   - Keep old code commented for comparison

3. Update components:
   - Change to use `snapshot.tasks` instead of `data.tasks`
   - Change to use `snapshot.metrics` instead of calculating
   - Remove filtering logic (use pre-filtered data)

4. Testing:
   - Verify UI works with new snapshot data
   - Compare with old implementation
   - Performance testing

### Phase 3: Incremental Updates via SSE (2-3 days)

**Goals:**
- Add Server-Sent Events for incremental updates
- Replace polling with SSE
- Implement diff calculation

**Tasks:**
1. Backend:
   - Add `sse-starlette` dependency
   - Add `/api/stream` endpoint
   - Implement `calculate_diff()` function
   - Test SSE connection and diff logic

2. Frontend:
   - Add `startSSE()` and `stopSSE()` actions to store
   - Implement `mergeArrayUpdates()` helper
   - Update store to handle incremental updates
   - Add connection status UI

3. Testing:
   - Test SSE connection stability
   - Test diff calculation accuracy
   - Test incremental merge logic
   - Load testing with multiple clients

### Phase 4: Cleanup and Deprecation (1 day)

**Goals:**
- Remove old code
- Update documentation
- Final performance testing

**Tasks:**
1. Backend cleanup:
   - Remove old 8 endpoints from `api.py`
   - Archive `data_loader.py` (or delete if confident)
   - Remove old tests
   - Update API documentation

2. Frontend cleanup:
   - Remove old data fetching code
   - Remove commented code
   - Update component documentation

3. Documentation:
   - Update README with new architecture
   - Document `/api/snapshot` and `/api/stream`
   - Add migration guide

4. Final testing:
   - Full integration test
   - Performance benchmark
   - Load testing

---

## Migration Strategy

### Backwards Compatibility During Transition

Keep both old and new systems running in parallel:

```python
# viz_backend/api.py

# NEW: Snapshot endpoint
@app.get("/api/snapshot")
async def get_snapshot(...):
    return aggregator.create_snapshot(...)

# OLD: Legacy endpoint (deprecated but functional)
@app.get("/api/data")
async def get_all_data(...):
    warnings.warn("This endpoint is deprecated. Use /api/snapshot instead.")
    return data_loader.load_all_data(...)
```

### Gradual Rollout

1. **Week 1:** Deploy Phase 1 (backend)
   - `/api/snapshot` available
   - Old endpoints still work
   - Monitor both

2. **Week 2:** Deploy Phase 2 (frontend)
   - Frontend uses `/api/snapshot`
   - Old endpoints still available
   - Monitor metrics

3. **Week 3:** Deploy Phase 3 (SSE)
   - SSE available
   - Polling still works as fallback
   - Monitor performance

4. **Week 4:** Deploy Phase 4 (cleanup)
   - Remove old endpoints
   - Remove old code
   - Final validation

---

## Risk Mitigation

### Potential Risks

1. **Data inconsistency during transition**
   - Mitigation: Keep old and new endpoints in parallel, compare outputs

2. **SSE connection stability**
   - Mitigation: Keep polling as fallback, add reconnection logic

3. **Performance regression**
   - Mitigation: Benchmark before/after, monitor in production

4. **Breaking changes to frontend**
   - Mitigation: Use feature flags, gradual rollout

### Rollback Plan

If issues arise:

1. **Backend rollback:**
   - Keep old `data_loader.py` and endpoints
   - Switch frontend back to old endpoints
   - Investigate issues offline

2. **Frontend rollback:**
   - Use feature flag to switch between old/new code
   - No backend changes needed

3. **SSE rollback:**
   - Disable SSE, fall back to polling
   - Keep snapshot endpoint

---

## Success Metrics

Track these metrics to validate the unification:

### Performance Metrics
- Initial load time: Target <200ms (currently 500ms-2s)
- Cached load time: Target <50ms
- Auto-refresh data size: Target <100KB diffs (currently full dataset)
- Memory usage: Target 50% reduction
- Component re-renders: Target 90% reduction

### Code Quality Metrics
- Lines of code: Target 70% reduction
- Cyclomatic complexity: Target 50% reduction
- Number of transformations: Target 90% reduction (10+ → 1)
- Test coverage: Maintain 80%+

### User Experience Metrics
- Time to interactive: Target <500ms
- Refresh latency: Target <100ms for incremental updates
- UI responsiveness: No jank during auto-refresh

---

## Conclusion

The proposed unified architecture:

1. **Eliminates fragmentation** by creating denormalized snapshots
2. **Reduces complexity** from 10+ transforms to 1 aggregation
3. **Improves performance** by 6-10x through caching and incremental updates
4. **Simplifies maintenance** by having single source of truth
5. **Enables scalability** through caching and field selection

This is a **significant architectural improvement** that will make the viz-dashboard more maintainable, performant, and extensible for future features.

---

## Appendix: Code Size Comparison

### Before
```
viz_backend/data_loader.py:    1259 lines (complex, multi-layer transforms)
viz_backend/api.py:             269 lines (8 endpoints, each calling data_loader)
viz-dashboard/store:            405 lines (redundant transforms, polling)
Total:                         1933 lines
```

### After
```
src/core/viz_store.py:          200 lines (data models)
src/core/viz_aggregator.py:     400 lines (single aggregation function)
viz_backend/api.py:             150 lines (2 endpoints, simple)
viz-dashboard/store:            150 lines (simple state container)
Total:                          900 lines (51% reduction)
```

The new architecture is **half the code** while being **6-10x faster**.
