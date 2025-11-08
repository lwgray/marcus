# ADR 0003: Project Switching with Isolated State Management

**Status:** Accepted

**Date:** 2024-11 (Post-MVP Enhancement)

**Deciders:** Marcus Core Team

---

## Context

Initially, Marcus was designed to manage a single project. As usage grew, requirements emerged for managing multiple projects:

### User Needs
1. **Multiple Projects:** Users want to manage multiple project configurations
2. **Project Switching:** Ability to switch between projects without restart
3. **Isolated State:** Each project's configuration and state kept separate
4. **No Cross-Contamination:** Project A's data shouldn't leak into Project B
5. **Resource Efficiency:** Don't duplicate entire system for each project

### Important Constraint
**Marcus operates on ONE active project at a time.** While multiple project configurations can be stored and managed, only a single project can be actively worked on at any given moment. Agents cannot work on different projects simultaneously.

### Technical Challenges
1. **State Management:** How to store and switch between project states
2. **Configuration Storage:** Where to persist multiple project configs
3. **Context Switching:** How to efficiently switch active project
4. **Resource Cleanup:** Managing memory for inactive projects
5. **Discovery:** How to find and list available projects

---

## Decision

We will implement **Project Switching with Isolated State Management** using a **Project Context Manager** with LRU caching.

### Architecture Components

#### 1. Project Registry (`src/core/project_registry.py`)

Central registry for storing and managing project configurations:

```python
class ProjectRegistry:
    """
    Registry for managing multiple project configurations.

    Stores project configs but only ONE project can be active at a time.
    """

    def __init__(self):
        self._cache: Dict[str, ProjectConfig] = {}
        self._active_project_id: Optional[str] = None  # SINGLE active project

    async def set_active_project(self, project_id: str) -> bool:
        """Set the ONE active project"""
        self._active_project_id = project_id  # Replaces previous active
        await self.persistence.store("active_project", {"project_id": project_id})

    async def get_active_project(self) -> Optional[ProjectConfig]:
        """Get the CURRENTLY active project (only one)"""
        if self._active_project_id:
            return await self.get_project(self._active_project_id)
        return None
```

**Key Point:** `_active_project_id` is a **single value**, not a collection. Only ONE project is active.

#### 2. Project Context Manager (`src/core/project_context_manager.py`)

Manages switching between projects and maintains isolated state:

```python
class ProjectContextManager:
    """
    Manages project switching with state isolation.

    IMPORTANT: Only ONE project is active at a time.
    Switching projects saves the current state and loads the new one.
    """

    def __init__(self, registry: Optional[ProjectRegistry] = None):
        self.registry = registry or ProjectRegistry()
        self.contexts: OrderedDict[str, ProjectContext] = OrderedDict()
        self.active_project_id: Optional[str] = None  # SINGLE active project
        self.active_project_name: Optional[str] = None

    async def switch_project(self, project_id: str) -> bool:
        """
        Switch from current project to a different project.

        This REPLACES the active project, not adds to it.
        """
        # Save current project state
        if self.active_project_id:
            await self._save_project_state(self.active_project_id)

        # Load new project context
        await self._get_or_create_context(project)

        # UPDATE (not append) the active project
        self.active_project_id = project_id  # Replaces previous
        self.active_project_name = project.name
        await self.registry.set_active_project(project_id)

        return True
```

**Key Point:** `switch_project()` **replaces** the active project, it doesn't add another concurrent project.

#### 3. Project Context (`src/core/models.py`)

Encapsulates all state for a single project:

```python
@dataclass
class ProjectContext:
    """Isolated state for a single project"""

    project_id: str
    project_name: str

    # Project-specific instances (loaded when project is active)
    kanban_client: Optional[KanbanInterface] = None
    context: Optional[Context] = None
    events: Optional[Events] = None
    project_state: Optional[ProjectState] = None
    assignment_persistence: Optional[AssignmentPersistence] = None

    # Metadata
    created_at: datetime
    last_accessed: datetime
    is_connected: bool = False
```

#### 4. LRU Cache for Performance

The context manager keeps recent project contexts in memory (LRU cache) to avoid reloading from disk on every switch:

```python
# Use OrderedDict for LRU behavior
self.contexts: OrderedDict[str, ProjectContext] = OrderedDict()

# When switching projects
self.contexts.move_to_end(project_id)  # Mark as recently used

# Cleanup old contexts if cache is full
await self._cleanup_old_contexts()
```

**Key Point:** The cache stores multiple contexts for **fast switching**, not for **concurrent execution**.

---

## Consequences

### Positive

✅ **Clean Project Management**
- Users can manage multiple project configurations
- Easy switching between projects
- No need to restart Marcus

✅ **State Isolation**
- Each project's state is completely separate
- No cross-contamination between projects
- Safe to work on different projects at different times

✅ **Resource Efficiency**
- LRU cache prevents memory bloat (only recent projects in memory)
- Inactive projects can be evicted
- Fast switching without full reload

✅ **Clean Architecture**
- Each project has isolated instances of core components
- Easy to test (create isolated project context)
- No global state pollution

✅ **Backward Compatible**
- Single-project usage still works (default active project)
- Gradual migration path from legacy config
- Can work without ever switching projects

✅ **Fast Context Switching**
- Switch time ~5-10ms for cached projects
- Projects stay warm in LRU cache
- No system restart needed

### Negative

⚠️ **Single Active Project Limitation**
- **CANNOT run multiple projects concurrently**
- **CANNOT have Agent A on Project 1 while Agent B works on Project 2**
- All operations use the single active project
- Must manually switch to work on different project

⚠️ **Manual Switching Required**
- User must explicitly call `switch_project`
- No automatic routing of agents to their projects
- Context switching overhead (though minimal)

⚠️ **Memory Usage**
- Each cached project context consumes memory (~10-20MB)
- LRU cache has limit (default: 10 projects)
- Old contexts evicted automatically

⚠️ **Context Loss on Switch**
- Switching projects saves/loads state
- In-memory state must be serializable
- Small overhead on each switch

⚠️ **No Concurrent Operations**
- Cannot execute tasks from multiple projects simultaneously
- Cannot compare projects side-by-side in real-time
- One project at a time architecture

---

## Implementation Details

### MCP Tool Integration

Projects are switched explicitly via MCP tool:

```python
@server.call_tool()
async def switch_project(
    project_id: str = None,
    name: str = None
) -> dict:
    """
    Switch the active project.

    Only ONE project can be active at a time.
    """
    # Find project
    if name:
        projects = await registry.list_projects()
        project = next((p for p in projects if p.name == name), None)
        project_id = project.id if project else None

    # Switch (replaces current active project)
    success = await project_manager.switch_project(project_id)

    return {"success": success, "active_project_id": project_id}
```

### All Operations Use Active Project

Every operation gets the **single** active project:

```python
@server.call_tool()
async def request_next_task(agent_id: str) -> dict:
    """Request next task for agent"""
    # Get THE active project (only one)
    active_project = await project_manager.get_active_project()
    if not active_project:
        return {"error": "No active project. Use switch_project first."}

    # Use that single project's task queue
    context = project_manager.contexts[active_project.id]
    task = await context.task_queue.get_next_task(agent_id)

    return {"success": True, "task": task}
```

### Persistence Schema

All data includes `project_id` for organization, but operations filter by the **single** active project:

```sql
-- Tasks table
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,  -- For organization/filtering
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    -- ...
);

-- When querying, always filter by the SINGLE active project
SELECT * FROM tasks
WHERE project_id = :active_project_id  -- Only one active
```

### Project Switching Flow

```
User: switch_project("project-2")
  ↓
1. Save current project state (project-1)
   - Persist task queue state
   - Save project state snapshot
   - Close kanban connection
  ↓
2. Load new project context (project-2)
   - Get ProjectContext from cache OR create new
   - Initialize kanban client for project-2
   - Load task queue
   - Restore project state
  ↓
3. Update active project reference
   - self.active_project_id = "project-2"
   - All subsequent operations use project-2
  ↓
4. Mark as recently used (LRU)
   - Move to end of OrderedDict
   - Evict old projects if cache full
```

---

## What This Is and Is NOT

### ✅ What This IS

- **Project Configuration Management:** Store configs for many projects
- **Project Switching:** Switch active project without restart
- **State Isolation:** Each project has separate state
- **LRU Caching:** Fast switching between recent projects
- **Single Active Project:** Only one project active at a time

### ❌ What This is NOT

- **Multi-Project Execution:** Cannot run multiple projects simultaneously
- **Concurrent Agent Routing:** Cannot have agents on different projects at once
- **Parallel Project Processing:** All work happens on the single active project
- **Multi-Tenancy:** No isolation between concurrent project operations (because there aren't any)

---

## Future Enhancements

To support **true multi-project concurrency** would require:

### Phase 1: Agent-Project Binding
- Associate each agent with a specific project
- Route agent requests to their project's context
- Maintain multiple active projects

### Phase 2: Concurrent Execution
- Multiple active project contexts simultaneously
- Thread-safe access to different project contexts
- Resource pooling for kanban clients

### Phase 3: Cross-Project Operations
- Task dependencies across projects
- Resource sharing between projects
- Project aggregation and reporting

**Current Status:** Not planned. Single active project meets current needs.

---

## Migration Path

### Phase 1: Add Project Registry (✅ Complete)
- Implement ProjectRegistry for storage
- Add project_id to all core models
- Update persistence schema

### Phase 2: Context Manager (✅ Complete)
- Implement ProjectContextManager
- Add LRU cache
- Integrate with MCP tools

### Phase 3: Switching Tools (✅ Complete)
- Add `switch_project` MCP tool
- Add `list_projects` MCP tool
- Add `get_current_project` tool

### Phase 4: Backward Compatibility (✅ Complete)
- Default project for single-project usage
- Migration from legacy config
- Auto-create project from old config

---

## Alternatives Considered

### 1. True Multi-Project Concurrency
**Rejected** because:
- Current use cases don't require it
- Adds significant complexity
- Resource overhead (multiple kanban connections, etc.)
- Most users work on one project at a time

**When to Reconsider:**
- Users need to compare projects in real-time
- Agents need to work on different projects simultaneously
- Cross-project task dependencies emerge

### 2. No Project Management (Single Project Only)
**Rejected** because:
- Users want to manage multiple projects
- Switching without restart is valuable
- Project isolation prevents confusion

### 3. Separate Process Per Project
**Rejected** because:
- High resource overhead (memory, CPU)
- Complex inter-process communication
- Overkill for sequential project work

### 4. Database-Level Filtering Only
**Rejected** because:
- No in-memory state isolation
- Hard to manage multiple kanban connections
- Context switching is complex
- No clear "active project" concept

---

## Related Decisions

- [ADR-0001: Layered Architecture with DDD](./0001-layered-architecture-with-ddd.md)
- [ADR-0008: SQLite as Primary Persistence](./0008-sqlite-primary-persistence.md)
- [ADR-0006: Kanban Provider Abstraction](./0006-kanban-provider-abstraction.md)

---

## References

- [LRU Cache Design](https://en.wikipedia.org/wiki/Cache_replacement_policies#LRU)
- [Context Manager Pattern](https://docs.python.org/3/reference/datamodel.html#context-managers)

---

## Metrics

After implementing project switching:
- **Context Switch Time:** ~5-10ms average
- **Memory Per Cached Project:** ~10-20MB (varies with task count)
- **LRU Cache Size:** 10 projects (configurable)
- **Active Projects:** 1 (always)
- **Stored Projects:** Unlimited (only cache limit)
- **Zero cross-contamination incidents** in testing and production

---

## Key Takeaway

Marcus supports **managing multiple projects** with **fast switching** between them, but operates on **only ONE project at a time**. This is not multi-tenancy or concurrent project execution - it's efficient single-project execution with the ability to switch projects quickly.
