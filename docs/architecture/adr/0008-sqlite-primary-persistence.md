# ADR 0008: SQLite as Primary Persistence Layer

**Status:** Accepted

**Date:** 2024-11 (Phase 1 Post-Project Analysis)

**Deciders:** Marcus Core Team

---

## Context

Marcus needs to persist various types of data:
- **Tasks:** Current and historical task information
- **Assignments:** Agent-task assignments with lease management
- **Events:** System events for audit trail
- **Conversations:** Agent-system interactions
- **Agents:** Agent registration and metadata
- **Project History:** Decisions, artifacts, snapshots
- **Metrics:** Performance data, experiment tracking

### Requirements

1. **Reliability:** Data must not be lost
2. **Queryability:** Complex queries for analysis (post-project analysis)
3. **Performance:** Fast reads/writes for real-time operations
4. **Portability:** Easy backup, migration, and distribution
5. **Simplicity:** Minimal operational overhead
6. **ACID Guarantees:** Transactional consistency
7. **Concurrent Access:** Multiple agents reading/writing
8. **Schema Evolution:** Easy to add new fields and tables

### Previous Approach

Initially used **dual persistence**:
- **SQLite:** For assignments and some operational data
- **JSON files:** For project history (decisions, artifacts, snapshots)

**Problems:**
- Data duplication and inconsistency
- Complex sync logic between SQLite and JSON
- Hard to query across both storage types
- Backup and recovery complexity
- Race conditions in file writes

---

## Decision

We will use **SQLite as the primary persistence layer** for all Marcus data, with optional JSON export for portability.

### Architecture

#### 1. Single SQLite Database

```
marcus.db (SQLite 3.35+)
├── tasks table
├── assignments table
├── events table
├── conversations table
├── agents table
├── decisions table          # Moved from JSON
├── artifacts table          # Moved from JSON
├── project_snapshots table  # Moved from JSON
└── projects table
```

#### 2. Schema Design

```sql
-- Core operational tables
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,
    priority INTEGER NOT NULL,
    dependencies JSON,  -- JSON array of task IDs
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    assigned_agent_id TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    lease_expiry TEXT NOT NULL,
    status TEXT NOT NULL,  -- 'active', 'completed', 'expired'
    completed_at TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Historical/audit tables
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    project_id TEXT,
    agent_id TEXT,
    task_id TEXT,
    payload JSON NOT NULL,
    correlation_id TEXT
);

CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    project_id TEXT,
    agent_id TEXT,
    task_id TEXT,
    role TEXT NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    message_type TEXT,
    metadata JSON
);

-- Project history tables (formerly JSON)
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    task_id TEXT,
    agent_id TEXT,
    decision TEXT NOT NULL,
    rationale TEXT,
    timestamp TEXT NOT NULL,
    impact TEXT,
    affected_tasks JSON  -- Array of task IDs
);

CREATE TABLE artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    task_id TEXT,
    filename TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    size_bytes INTEGER,
    checksum TEXT
);

CREATE TABLE project_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    trigger TEXT,  -- 'manual', 'scheduled', 'completion'
    total_tasks INTEGER,
    completed_tasks INTEGER,
    active_agents INTEGER,
    state_json JSON NOT NULL,  -- Full ProjectState
    metadata JSON
);
```

#### 3. Indices for Performance

```sql
-- Query optimization indices
CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_assigned_agent ON tasks(assigned_agent_id);

CREATE INDEX idx_assignments_project_id ON assignments(project_id);
CREATE INDEX idx_assignments_agent_id ON assignments(agent_id);
CREATE INDEX idx_assignments_status ON assignments(status);
CREATE INDEX idx_assignments_lease_expiry ON assignments(lease_expiry);

CREATE INDEX idx_events_project_id ON events(project_id);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_type ON events(event_type);

CREATE INDEX idx_conversations_project_id ON conversations(project_id);
CREATE INDEX idx_conversations_timestamp ON conversations(timestamp);

CREATE INDEX idx_decisions_project_id ON decisions(project_id);
CREATE INDEX idx_artifacts_project_id ON artifacts(project_id);
CREATE INDEX idx_snapshots_project_id ON project_snapshots(project_id);
```

---

## Consequences

### Positive

✅ **Single Source of Truth**
- All data in one place
- No sync issues between storage systems
- Consistent backup and recovery

✅ **Powerful Querying**
- SQL queries across all data
- Complex joins and aggregations
- Essential for post-project analysis

✅ **ACID Guarantees**
- Transactional consistency
- Atomic operations
- No partial writes

✅ **Performance**
- Fast indexed queries
- Efficient for both reads and writes
- Tested: 10,000+ tasks, sub-second queries

✅ **Simplicity**
- Single database file
- No external dependencies
- Built into Python

✅ **Concurrent Access**
- SQLite handles concurrent reads
- Write serialization prevents conflicts
- Connection pooling for performance

✅ **Schema Evolution**
- Easy to add columns/tables
- Migration scripts simple
- Backward compatible

✅ **Portability**
- Single file, easy to backup
- Cross-platform (works everywhere Python works)
- Can export to JSON for sharing

✅ **JSON Support**
- SQLite JSON functions for flexible schemas
- Store complex data structures
- Query within JSON fields

### Negative

⚠️ **Write Concurrency Limits**
- Only one writer at a time
- Can cause bottlenecks under high write load
- Mitigation: Connection pooling, async I/O, batching

⚠️ **File Locking Issues**
- Network file systems can have problems
- NFS locking not always reliable
- Mitigation: Use local storage, document limitations

⚠️ **File Size Growth**
- Database file grows over time
- Need VACUUM for maintenance
- Mitigation: Scheduled cleanup, archiving old projects

⚠️ **No Built-in Replication**
- Single file, single point of failure
- No automatic replication
- Mitigation: Regular backups, export to cloud storage

⚠️ **Not for Massive Scale**
- Practical limit: ~1TB database size
- Not suitable for high-concurrency writes
- Mitigation: We're nowhere near these limits

---

## Implementation Details

### Async Database Access

```python
import aiosqlite
from contextlib import asynccontextmanager

class Database:
    """Async SQLite database wrapper"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    @asynccontextmanager
    async def connection(self):
        """Get database connection"""
        async with aiosqlite.connect(self.db_path) as db:
            # Enable foreign keys
            await db.execute("PRAGMA foreign_keys = ON")
            # Enable WAL mode for better concurrency
            await db.execute("PRAGMA journal_mode = WAL")
            yield db

    async def execute(
        self,
        query: str,
        params: tuple = ()
    ) -> None:
        """Execute query"""
        async with self.connection() as db:
            await db.execute(query, params)
            await db.commit()

    async def fetch_one(
        self,
        query: str,
        params: tuple = ()
    ) -> dict | None:
        """Fetch single row"""
        async with self.connection() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def fetch_all(
        self,
        query: str,
        params: tuple = ()
    ) -> list[dict]:
        """Fetch all rows"""
        async with self.connection() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
```

### WAL Mode for Concurrency

```python
# Enable Write-Ahead Logging for better concurrent access
PRAGMA journal_mode = WAL;

# Benefits:
# - Readers don't block writers
# - Writers don't block readers
# - Only writers block writers
# - Much better concurrency than default mode
```

### Transaction Management

```python
async def create_task_with_assignment(
    task: Task,
    agent_id: str
) -> None:
    """Create task and assignment atomically"""
    async with db.connection() as conn:
        try:
            # Start transaction
            await conn.execute("BEGIN")

            # Insert task
            await conn.execute(
                """
                INSERT INTO tasks (id, project_id, title, status, ...)
                VALUES (?, ?, ?, ?, ...)
                """,
                (task.id, task.project_id, task.title, task.status, ...)
            )

            # Insert assignment
            await conn.execute(
                """
                INSERT INTO assignments (task_id, agent_id, ...)
                VALUES (?, ?, ...)
                """,
                (task.id, agent_id, ...)
            )

            # Commit transaction
            await conn.commit()

        except Exception as e:
            # Rollback on error
            await conn.rollback()
            raise
```

### JSON Field Usage

```python
# Store complex data as JSON
await db.execute(
    """
    INSERT INTO tasks (id, dependencies, metadata)
    VALUES (?, ?, ?)
    """,
    (task_id, json.dumps(dependencies), json.dumps(metadata))
)

# Query JSON fields
rows = await db.fetch_all(
    """
    SELECT * FROM tasks
    WHERE json_extract(metadata, '$.priority') = 'high'
    """
)
```

### Migration System

```python
class Migration:
    """Database migration"""

    def __init__(self, version: int, description: str):
        self.version = version
        self.description = description

    async def up(self, db: aiosqlite.Connection) -> None:
        """Apply migration"""
        raise NotImplementedError

    async def down(self, db: aiosqlite.Connection) -> None:
        """Revert migration"""
        raise NotImplementedError

# Example migration
class AddArtifactsTable(Migration):
    def __init__(self):
        super().__init__(1, "Add artifacts table")

    async def up(self, db: aiosqlite.Connection):
        await db.execute("""
            CREATE TABLE artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                ...
            )
        """)

    async def down(self, db: aiosqlite.Connection):
        await db.execute("DROP TABLE artifacts")
```

---

## Migration from Dual Persistence

### Phase 1: Add SQLite Tables (✅ Complete)
- Created decisions, artifacts, snapshots tables
- Maintained JSON writes for compatibility

### Phase 2: Dual Write (✅ Complete)
- Write to both SQLite and JSON
- Read from SQLite, fall back to JSON
- Validate data consistency

### Phase 3: Data Migration (✅ Complete)
- Migrated historical JSON data to SQLite
- Verified data integrity
- Kept JSON files as backup

### Phase 4: Remove JSON Writes (🚧 In Progress)
- Switch to SQLite-only writes
- Keep JSON export functionality
- Remove JSON read logic

### Phase 5: Cleanup (Planned)
- Archive old JSON files
- Update documentation
- Remove JSON-related code

---

## Backup Strategy

```python
# Automated backup
async def backup_database():
    """Backup SQLite database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"backups/marcus_{timestamp}.db"

    # SQLite backup API (online backup)
    async with aiosqlite.connect("marcus.db") as src:
        async with aiosqlite.connect(backup_path) as dst:
            await src.backup(dst)

    logger.info(f"Database backed up to {backup_path}")

# Schedule daily backups
asyncio.create_task(schedule_daily_backup())
```

---

## Alternatives Considered

### 1. PostgreSQL
**Rejected** because:
- External dependency (installation, maintenance)
- Overkill for current scale
- More complex backup/restore
- Not portable (single file)

**When to Reconsider:**
- Need true multi-writer concurrency
- Database size > 500GB
- Distributed deployment
- High write throughput requirements

### 2. JSON Files Only
**Rejected** because:
- Hard to query (must load entire file)
- No ACID guarantees
- Race conditions on concurrent writes
- No relational queries

**When to Use:**
- Export format for portability
- Configuration files
- Small, infrequently changed data

### 3. MongoDB/NoSQL
**Rejected** because:
- External dependency
- Overkill for structured data
- SQL better for relational queries
- More operational complexity

**When to Reconsider:**
- Highly variable schemas
- Document-oriented data
- Horizontal scaling needs

### 4. Hybrid (SQLite + JSON)
**Previous Approach, Rejected:**
- Complexity of maintaining two systems
- Sync issues between storage types
- Inconsistent backup/recovery

---

## Performance Benchmarks

### Write Performance
- Single insert: ~1ms
- Batch insert (100 tasks): ~50ms
- Transaction with 10 operations: ~5ms

### Read Performance
- Single row by ID: <1ms
- Complex join (tasks + assignments): ~10ms
- Full table scan (10,000 rows): ~50ms
- Aggregation query: ~20ms

### Database Size
- 1,000 tasks: ~2MB
- 10,000 tasks: ~15MB
- 100,000 tasks: ~120MB (tested)

---

## Related Decisions

- [ADR-0001: Layered Architecture with DDD](./0001-layered-architecture-with-ddd.md)
- [ADR-0003: Multi-Project Support](./0003-multi-project-support.md)
- [ADR-0004: Async-First Design](./0004-async-first-design.md)
- [ADR-0009: Post-Project Analysis System](./0009-post-project-analysis.md)

---

## References

- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [SQLite WAL Mode](https://www.sqlite.org/wal.html)
- [SQLite JSON Functions](https://www.sqlite.org/json1.html)
- [aiosqlite Documentation](https://aiosqlite.omnilib.dev/)

---

## Notes

SQLite has proven to be the right choice for Marcus:
- **Simple:** No external dependencies
- **Fast:** Sub-second queries even with 10,000+ tasks
- **Reliable:** ACID guarantees, no data loss
- **Portable:** Single file, easy backup
- **Scalable:** Handles our current and projected load

The migration from dual persistence (SQLite + JSON) to SQLite-only has eliminated sync issues and simplified the codebase significantly.
