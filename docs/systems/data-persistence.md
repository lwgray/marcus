# Marcus Data Persistence Architecture

## Overview

Marcus uses a file-based persistence system that stores runtime state, operational data, and learned patterns in the `data/` directory. This document details what data is stored, where it comes from, and evaluates the long-term viability of this approach.

## Data Directory Structure

```
data/
├── assignments/              # Task-to-agent mappings
│   ├── assignments.json     # Current task assignments
│   ├── .assignments.lock    # Lock file for concurrent access
│   └── project_*/           # Per-project assignment data
│
├── audit_logs/              # MCP tool usage audit trail
│   └── audit_YYYYMMDD.jsonl # Daily audit logs (JSON Lines format)
│
├── marcus_state/            # Core state persistence (FilePersistence)
│   ├── projects.json        # Project registry and metadata
│   ├── events/              # Event system data
│   ├── context/             # Context system data
│   └── memory/              # Memory system data
│
├── marcus_state.db          # SQLite alternative (SQLitePersistence)
│
├── learned_patterns.json    # Machine learning patterns
│
└── token_usage.json         # API token cost tracking
```

## Data Sources and Lifecycle

### 1. Task Assignments (`data/assignments/`)

**Source:** `src/core/assignment_persistence.py`

**Purpose:** Tracks which agent is assigned to which task, preventing duplicate work and enabling recovery after crashes.

**Data Flow:**
```python
Agent requests task → Marcus assigns → Creates assignment record → Writes to assignments.json
Task completed → Remove assignment → Update assignments.json
```

**Format:**
```json
{
  "agent-001": {
    "task_id": "task-123",
    "assigned_at": "2025-08-31T10:30:00",
    "task_data": {
      "name": "Implement user API",
      "priority": "high",
      "estimated_hours": 4
    }
  }
}
```

**Lifecycle:**
- Created when task assigned
- Updated on progress reports
- Deleted on task completion
- Survives Marcus restarts

### 2. Audit Logs (`data/audit_logs/`)

**Source:** `src/marcus_mcp/audit.py`

**Purpose:** Records every MCP tool call for debugging, analytics, security, and compliance.

**Data Flow:**
```python
Tool called → AuditLogger.log_event() → Append to daily JSONL file
```

**Format (JSON Lines):**
```json
{"timestamp": "2025-08-31T10:30:00", "event_type": "tool_call", "client_id": "agent-001", "tool_name": "request_next_task", "success": true}
{"timestamp": "2025-08-31T10:31:00", "event_type": "tool_call", "client_id": "agent-001", "tool_name": "report_progress", "details": {"progress": 25}, "success": true}
```

**Lifecycle:**
- New file created daily
- Append-only (never modified)
- Should be rotated/archived periodically
- Can grow large (100MB+ per day with heavy usage)

### 3. Marcus State (`data/marcus_state/`)

**Source:** `src/core/persistence.py` - FilePersistence backend

**Purpose:** Core system state including projects, events, context, and memory data.

**Components:**

#### Projects Registry
```json
{
  "projects": {
    "project-001": {
      "id": "project-001",
      "name": "E-commerce Platform",
      "created_at": "2025-08-31T09:00:00",
      "kanban_board_id": "board-123",
      "task_count": 42,
      "agents_assigned": ["agent-001", "agent-002"]
    }
  }
}
```

#### Event System Data
- Event history
- Subscriptions
- Event metrics

#### Context System Data
- Task implementations
- Architectural decisions
- Dependency mappings

#### Memory System Data
- Agent performance history
- Task outcomes
- Prediction models

**Lifecycle:**
- Loaded on Marcus startup
- Updated continuously during operation
- Persisted on shutdown
- Critical for system continuity

### 4. Learned Patterns (`data/learned_patterns.json`)

**Source:** `src/learning/project_pattern_learner.py`

**Purpose:** Stores patterns Marcus learns about project structures, dependencies, and successful strategies.

**Format:**
```json
{
  "patterns": [
    {
      "type": "dependency",
      "pattern": "frontend_needs_api",
      "confidence": 0.95,
      "examples": 47,
      "last_seen": "2025-08-31T10:00:00"
    }
  ]
}
```

**Lifecycle:**
- Loaded on startup
- Updated when patterns detected
- Grows over time
- Should be pruned periodically

### 5. Token Usage (`data/token_usage.json`)

**Source:** `src/cost_tracking/token_tracker.py`

**Purpose:** Tracks AI API usage for cost management and optimization.

**Format:**
```json
{
  "daily_usage": {
    "2025-08-31": {
      "anthropic": {
        "tokens_used": 145000,
        "cost_usd": 3.45,
        "requests": 89
      }
    }
  },
  "project_usage": {
    "project-001": {
      "total_tokens": 500000,
      "total_cost": 12.50
    }
  }
}
```

**Lifecycle:**
- Updated on every AI call
- Aggregated daily
- Historical data should be archived

## Long-Term Viability Assessment

### Current Approach: File-Based Persistence

#### Pros ✅
1. **Simplicity** - Easy to implement and debug
2. **Portability** - Works anywhere without dependencies
3. **Transparency** - Human-readable JSON files
4. **Version Control Friendly** - Can track schema changes
5. **No External Dependencies** - No database server needed
6. **Easy Backup** - Just copy files

#### Cons ❌
1. **Concurrency Issues** - File locks don't scale well
2. **Performance Degradation** - JSON parsing becomes slow with large files
3. **No ACID Guarantees** - Risk of data corruption
4. **Limited Querying** - Can't efficiently search/filter
5. **Memory Constraints** - Must load entire files into memory
6. **No Transactions** - Multi-file updates aren't atomic

### Scalability Limits

The current file-based system will hit limits at:

| Data Type | Limit | Issue |
|-----------|-------|-------|
| Assignments | ~1000 concurrent agents | Lock contention |
| Audit Logs | ~10GB per file | Parse time |
| Marcus State | ~100MB | Memory usage |
| Learned Patterns | ~10,000 patterns | Search performance |

### Migration Path

Marcus already has infrastructure for better persistence:

1. **SQLitePersistence** (Already implemented)
   - Good for: Single-server deployments up to 100 agents
   - Migration: Change config from FilePersistence to SQLitePersistence

2. **PostgreSQL** (Future)
   - Good for: Multi-server, 1000+ agents
   - Benefits: ACID, concurrent access, advanced queries

3. **Hybrid Approach** (Recommended)
   - SQLite for structured data (assignments, state)
   - Files for append-only logs (audit)
   - Redis for hot cache (active assignments)
   - S3/Blob storage for archives

## Recommendations

### Immediate Actions
1. **Add startup directory creation** to prevent missing directory errors
2. **Implement log rotation** for audit logs (daily → weekly → archive)
3. **Add data directory validation** on startup
4. **Create backup strategy** for critical state files

### Short-term (1-3 months)
1. **Switch to SQLitePersistence** for marcus_state
2. **Add Redis cache** for hot assignment data
3. **Implement data pruning** for old patterns and logs
4. **Add metrics collection** on data sizes

### Long-term (6+ months)
1. **Design PostgreSQL schema** for production deployments
2. **Implement data archival pipeline**
3. **Add data migration tools**
4. **Create monitoring dashboards**

## Configuration

Current persistence is configured in `config_marcus.json`:

```json
{
  "features": {
    "persistence": "file",  // or "sqlite", "memory"
    "persistence_options": {
      "storage_dir": "data/marcus_state",
      "backup_enabled": true,
      "backup_interval_hours": 24
    }
  }
}
```

## Conclusion

The file-based persistence is **adequate for development and small deployments** (< 10 agents, < 100 projects) but will need migration to a database-backed solution for production use. The modular persistence design (`PersistenceBackend` interface) makes this migration straightforward when needed.

The immediate concern is not the persistence mechanism but rather:
1. Ensuring directories exist before use
2. Implementing proper cleanup/rotation
3. Adding monitoring for data growth
4. Creating a backup strategy

For Marcus to scale to production use with hundreds of agents and thousands of projects, a migration to PostgreSQL with Redis caching would be necessary.
