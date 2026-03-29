# SQLite Kanban Provider

The SQLite provider is a zero-infrastructure kanban board for Marcus. It stores all
task data in a local SQLite database file, eliminating the need for Docker, Planka,
Postgres, or any external service.

## When to Use SQLite

| Scenario | Recommended Provider |
|----------|---------------------|
| Getting started / first experiment | SQLite |
| Local development and testing | SQLite |
| CI/CD pipelines | SQLite |
| Single developer | SQLite |
| Team with visual board needs | Planka |
| Enterprise with existing tools | GitHub / Linear |

## Configuration

In `config_marcus.json`:

```json
{
  "kanban": {
    "provider": "sqlite",
    "sqlite_db_path": "./data/kanban.db",
    "sqlite_attachments_dir": "./data/attachments"
  }
}
```

Or via environment variables:

```bash
export KANBAN_PROVIDER=sqlite
export SQLITE_KANBAN_DB_PATH=./data/kanban.db
export SQLITE_KANBAN_ATTACHMENTS_DIR=./data/attachments
```

Marcus creates the database automatically on first project creation.

## How It Works

### Database Schema

The provider creates 6 tables:

| Table | Purpose |
|-------|---------|
| `tasks` | Core task data (name, status, priority, assignment, timestamps) |
| `task_dependencies` | Task-to-task dependency relationships |
| `task_labels` | Labels/tags per task |
| `comments` | Coordination comments (progress, blockers, assignments) |
| `attachments` | Attachment metadata (files stored on disk) |
| `blockers` | Blocker records with severity |

### Concurrency

SQLite runs in WAL (Write-Ahead Logging) mode, which allows multiple agents to read
the board simultaneously while one agent writes. This is the same pattern used by
Marcus's existing `SQLitePersistence` layer.

### Task Lifecycle

The provider handles the full Marcus workflow:

```
TODO ──→ IN_PROGRESS ──→ DONE
  │          │
  │          ▼
  │       BLOCKED ──→ IN_PROGRESS (unblocked)
  │
  └──→ TODO (recovered from expired lease)
```

Each transition adds a comment for audit trail:

- **Assignment**: `"📋 Task assigned to agent-1 at 2026-03-28T..."`
- **Progress**: `"📊 Progress: 50% - Implemented core logic"`
- **Blocker**: `"🚫 BLOCKER (HIGH): API is down"`
- **Recovery**: `"⚠️ RECOVERY ADDENDUM\nFrom: agent-1\nProgress: 40%..."`

### Status/Column Mapping

The provider maps column names to statuses (case-insensitive):

| Column Name | Status |
|-------------|--------|
| backlog, todo, to do, ready | `TODO` |
| in progress, progress | `IN_PROGRESS` |
| blocked, on hold | `BLOCKED` |
| done, completed | `DONE` |

## Inspecting Your Board

Since there's no web UI, use SQLite CLI or any SQLite viewer.

### Command Line

```bash
# All tasks with status
sqlite3 data/kanban.db "SELECT name, status, assigned_to, priority FROM tasks"

# Available tasks (what agents will pick up)
sqlite3 data/kanban.db "SELECT name, priority FROM tasks WHERE status='todo' AND assigned_to IS NULL"

# Board summary
sqlite3 data/kanban.db "SELECT status, COUNT(*) as count FROM tasks GROUP BY status"

# Recent comments (coordination audit trail)
sqlite3 data/kanban.db \
  "SELECT t.name, c.content, c.created_at
   FROM comments c JOIN tasks t ON t.id = c.task_id
   ORDER BY c.created_at DESC LIMIT 10"

# Blockers
sqlite3 data/kanban.db \
  "SELECT t.name, b.description, b.severity
   FROM blockers b JOIN tasks t ON t.id = b.task_id
   WHERE b.resolved = 0"

# Task dependencies
sqlite3 data/kanban.db \
  "SELECT t1.name as task, t2.name as depends_on
   FROM task_dependencies d
   JOIN tasks t1 ON t1.id = d.task_id
   JOIN tasks t2 ON t2.id = d.depends_on_id"
```

### GUI Tools

Any SQLite browser works:
- [DB Browser for SQLite](https://sqlitebrowser.org/) (free, cross-platform)
- [TablePlus](https://tableplus.com/) (macOS)
- VS Code extension: "SQLite Viewer"

## Switching from Planka to SQLite

1. Change `config_marcus.json`:

```json
{
  "kanban": {
    "provider": "sqlite"
  }
}
```

2. Existing Planka projects in the registry won't be affected — they'll continue to
   reference Planka. New projects created via `create_project` will use SQLite.

3. To migrate existing tasks, export from Planka and re-import (manual process).

## File Locations

| File | Purpose |
|------|---------|
| `src/integrations/providers/sqlite_kanban.py` | Provider implementation |
| `src/integrations/kanban_interface.py` | Abstract interface (all providers) |
| `src/integrations/kanban_factory.py` | Provider selection logic |
| `src/config/marcus_config.py` | Configuration fields |
| `tests/unit/integrations/test_sqlite_kanban.py` | Test suite (80 tests, 93% coverage) |

## Limitations

- No web UI — use CLI or SQLite browser for visibility
- Single database file — not suitable for distributed multi-node deployments
- No real-time notifications — agents poll for changes via `get_available_tasks()`
- Attachments stored on local filesystem — not shareable across machines

For team environments or when a visual board is needed, use the [Planka provider](../../../DOCKER_QUICKSTART.md) instead.
