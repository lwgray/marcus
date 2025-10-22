# Marcus Visualization Data Architecture Analysis

## Executive Summary

The viz-dashboard (frontend) and viz_backend are experiencing data architecture fragmentation where **data is spread across 5 different storage locations and flows through 7+ transformation layers**, creating complexity, duplication, and brittle dependencies. The system loads **tasks, agents, messages, events, and metrics** repeatedly from multiple sources instead of a unified data interface.

## Quick Problem Summary

- **5 storage sources**: projects.json, subtasks.json, conversations_*.jsonl, agent_events_*.jsonl, marcus.db
- **8 API endpoints** with overlapping functionality
- **7+ transformation layers** (backend) + **3+ on frontend** = 10+ data transformations
- **Metrics calculated twice**: backend AND frontend (code duplication)
- **Auto-refresh issues**: Polls every 5s → 5-8 file reads/minute → 100% data replacement, all re-renders
- **No incremental updates**: Always fetches and processes full dataset
- **Scattered filtering**: Each component filters independently (inconsistent, inefficient)

## Key Files

### Backend (Python)
- `/Users/lwgray/dev/worktrees/viz/viz_backend/api.py` - 259 lines, 8 endpoints
- `/Users/lwgray/dev/worktrees/viz/viz_backend/data_loader.py` - 1169 lines, transforms data through multiple layers

### Frontend (TypeScript/React)
- `/Users/lwgray/dev/worktrees/viz/viz-dashboard/src/store/visualizationStore.ts` - 389 lines, Zustand store with redundant getters
- `/Users/lwgray/dev/worktrees/viz/viz-dashboard/src/services/dataService.ts` - 178 lines, 8 fetch functions
- `/Users/lwgray/dev/worktrees/viz/viz-dashboard/src/data/mockDataGenerator.ts` - Mock data that duplicates backend logic
- Components: `NetworkGraphView.tsx`, `AgentSwimLanesView.tsx`, `ConversationView.tsx`, `TaskDetailPanel.tsx`, `MetricsPanel.tsx`

## Data Model (Backend Returns)

```python
{
    "tasks": [{
        id, name, description, status (todo|in_progress|done|blocked),
        priority (low|medium|high|urgent), assigned_to, created_at, updated_at,
        estimated_hours, actual_hours, dependencies, labels,
        project_id, project_name, is_subtask, parent_task_id, progress (0-100)
    }],
    "agents": [{
        id, name, role, skills, current_tasks, completed_tasks_count,
        capacity, performance_score, autonomy_score (0-1)
    }],
    "messages": [{
        id, timestamp, from, to, task_id, message,
        type (instruction|question|answer|status_update|blocker|task_request|task_assignment),
        parent_message_id, metadata (blocking, requires_response, progress, response_time, resolves_blocker)
    }],
    "events": [{
        id, timestamp, event_type, agent_id, task_id, data
    }],
    "metadata": {
        project_name, start_time, end_time, total_duration_minutes, parallelization_level
    }
}
```

## Data Flow

```
[Marcus Persistence: 5 sources]
         ↓
[Backend: 7+ transforms]
  - load_tasks_from_persistence()
  - enrich_tasks_with_timing()
  - load_messages_from_logs()
  - load_events_from_logs()
  - infer_agents_from_data()
  - calculate_metadata()
         ↓
[FastAPI: /api/data endpoint]
         ↓
[Frontend: Parse + Store in Zustand]
         ↓
[Frontend: 3+ transforms]
  - calculateMetrics() [DUPLICATE OF BACKEND]
  - getVisibleTasks()
  - getMessagesUpToCurrentTime()
  - getActiveAgentsAtCurrentTime()
         ↓
[React Components: Filter independently]
```

## The "Spread Out" Problem Manifestations

1. **Slow loads**: 500ms-2s per request (5-8 file reads serialized)
2. **Laggy auto-refresh**: Every 5s → full re-render cycle
3. **Inconsistent filtering**: Logic scattered across components
4. **Complex state**: 389-line Zustand store with overlapping concerns
5. **Memory growth**: Full dataset in memory, no pagination
6. **Duplicate calculations**: Metrics in backend AND frontend

## Where Data Is Duplicated

| Data | Lives In | Problem |
|------|----------|---------|
| **Tasks** | subtasks.json + marcus.db | Split across files, parent/child hierarchy fragmented |
| **Agents** | Inferred from tasks every load | No canonical source, recalculated constantly |
| **Messages** | Multiple JSONL files | Distributed across files, no index |
| **Events** | Multiple JSONL files | Time-series scattered |
| **Metadata** | Calculated multiple times | Backend + Frontend calculation |
| **Metrics** | Backend + Frontend | 100% code duplication |

## API Endpoints (Currently 8, all load full pipeline)

| Endpoint | Problem |
|----------|---------|
| `GET /api/data` | Loads everything even if only need one view |
| `GET /api/tasks` | Still loads full pipeline (projects, messages, events) |
| `GET /api/agents` | Infers from scratch every time |
| `GET /api/messages` | No project filtering |
| `GET /api/events` | No project filtering |
| `GET /api/projects` | Projects only |
| `GET /api/metadata` | Recalculated every time |
| `/health` | Basic check |

## Frontend Components' Data Access Patterns

| Component | Data Used | Issue |
|-----------|-----------|-------|
| NetworkGraphView | tasks, metadata, currentTime | Recalculates graph on every time change |
| AgentSwimLanesView | tasks, agents, currentTime | Redraws entire swimlane |
| ConversationView | messages, agents, currentTime | Filters messages every render |
| TaskDetailPanel | tasks, messages, agents, currentTime | Finds task by ID every render |
| MetricsPanel | metrics, metadata, agents | Uses pre-calc metrics (good) |
| TimelineControls | tasks, messages, currentTime | Updates slider |

## Auto-Refresh Problem

```typescript
// Runs every 5 seconds:
setInterval(() => {
  refreshData()  // 1 fetch → 5-8 file reads
}, 5000)

// Results in:
// - Complete state replacement (not diff)
// - ALL components re-render (even if nothing changed)
// - 5-8 file I/O per user per minute
// - No batching of updates
```

## Consolidation Opportunities

### Immediate (Fix fragmentation)
1. Merge API endpoints → consolidate to 1 data endpoint with field selection
2. Consolidate calculations → backend does metrics once
3. Unify filter logic → store handles, components just display
4. Cache metadata → don't recalculate

### Short-term (Refactor)
1. Backend: MarcusDataLoader → Aggregator → Serializer (separation of concerns)
2. Frontend: Remove redundant store getters (use selectors)
3. Replace polling with WebSocket/SSE (incremental updates)
4. Share types: TypeScript types from backend schema

### Medium-term (Architecture)
1. Project aggregate: Projects own their tasks
2. Timeline service: Server-side time-based queries
3. Pagination: Don't load all data at once
4. GraphQL: Flexible querying instead of fixed endpoints

---

**For detailed analysis with code locations and data structures, see the full document in this file.**
