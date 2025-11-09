# Marcus ↔ Planka Integration Analysis
## Multi-Project Architecture

**Date:** 2025-11-09
**Purpose:** Understand how Marcus integrates with Planka to inform Cato MCP design with multi-project support

---

## Executive Summary

Marcus uses Planka as an external kanban board through the `kanban-mcp` MCP server. Marcus **pulls from Planka** as the source of truth for task state. Marcus **already supports multiple projects** through its project registry system.

**Key Finding:** Cato can replace Planka by implementing the same MCP interface while supporting multiple projects/boards natively.

---

## Current Architecture (Planka)

```
┌─────────────────────────────────────────────────────────────┐
│                  PLANKA (Multiple Boards)                    │
│                    (Source of Truth)                         │
│                                                              │
│  Project A Board:                    Project B Board:        │
│  ├─ Backlog (tasks)                 ├─ Backlog (tasks)     │
│  ├─ In Progress                     ├─ In Progress         │
│  ├─ Done                            ├─ Done                │
│  └─ Blocked                         └─ Blocked             │
│                                                              │
│  Each board has:                                             │
│  - board_id (unique)                                         │
│  - project_id (unique)                                       │
│  - Tasks as cards with state, comments, attachments          │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 │ MCP Protocol
                 │ (kanban-mcp translates to REST API)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│              MARCUS (Multi-Project Support)                  │
│                                                              │
│  ProjectRegistry:                                            │
│  ├─ Project A (provider: planka, board_id: 123)             │
│  ├─ Project B (provider: planka, board_id: 456)             │
│  └─ Active Project: Project A                               │
│                                                              │
│  KanbanInterface:                                            │
│  └─ Talks to active project's board via MCP                 │
│                                                              │
│  Per-Project State:                                          │
│  ├─ project_tasks (cached from active board)                │
│  ├─ agent_assignments                                       │
│  └─ project_metrics                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Marcus Multi-Project System

### 1. Project Registry

**File:** `src/project_management/registry.py` (inferred)

```python
class ProjectRegistry:
    """Manages multiple projects."""

    def __init__(self):
        self.projects: Dict[str, Project] = {}
        self.active_project_id: Optional[str] = None

    async def get_active_project(self) -> Optional[Project]:
        """Get currently active project."""
        if self.active_project_id:
            return self.projects.get(self.active_project_id)
        return None

    async def list_projects(self) -> List[Project]:
        """List all projects."""
        return list(self.projects.values())

    async def switch_project(self, project_id: str) -> bool:
        """Switch to different project."""
        if project_id in self.projects:
            self.active_project_id = project_id
            return True
        return False
```

### 2. Project Model

**File:** `src/core/models.py`

```python
@dataclass
class Project:
    project_id: str
    name: str
    provider: str  # "planka", "linear", "github", or "cato"
    provider_config: Dict[str, Any]  # Provider-specific settings
    # For Planka: {"board_id": "123", "project_id": "456"}
    # For Cato: {"view_mode": "subtasks"}

    local_path: Path
    main_branch: str
    created_at: str
```

### 3. Per-Project Board Configuration

**Current:** Each project stores board connection in `provider_config`

```json
{
  "projects": [
    {
      "project_id": "proj-task-api",
      "name": "Task Management API",
      "provider": "planka",
      "provider_config": {
        "board_id": "bd_12345",
        "project_id": "prj_67890"
      }
    },
    {
      "project_id": "proj-auth-service",
      "name": "Auth Service",
      "provider": "planka",
      "provider_config": {
        "board_id": "bd_99999",
        "project_id": "prj_88888"
      }
    }
  ]
}
```

### 4. How Marcus Switches Projects

```python
# In request_next_task or any operation
async def operation_on_project(state: Any):
    # 1. Get active project
    active_project = await state.project_registry.get_active_project()

    # 2. Configure kanban client for that project
    state.kanban_client.board_id = active_project.provider_config["board_id"]
    state.kanban_client.project_id = active_project.provider_config["project_id"]

    # 3. Refresh state from THAT board
    await state.refresh_project_state()  # Pulls from active project's board

    # 4. Work with tasks from active project
    tasks = state.project_tasks  # Filtered to active project
```

---

## Proposed Cato Multi-Project Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Marcus SQLite Database                          │
│              (Single Source of Truth)                        │
│                                                              │
│  projects table:                                             │
│  ┌────────────┬──────────────┬──────────┬─────────────────┐ │
│  │ project_id │ name         │ provider │ provider_config │ │
│  ├────────────┼──────────────┼──────────┼─────────────────┤ │
│  │ proj-A     │ Task API     │ cato     │ {...}           │ │
│  │ proj-B     │ Auth Service │ cato     │ {...}           │ │
│  │ proj-C     │ Frontend     │ planka   │ {board_id:...}  │ │
│  └────────────┴──────────────┴──────────┴─────────────────┘ │
│                                                              │
│  tasks table:                                                │
│  ┌─────────┬────────────┬──────┬────────┬──────────────┐   │
│  │ task_id │ project_id │ name │ status │ assigned_to  │   │
│  ├─────────┼────────────┼──────┼────────┼──────────────┤   │
│  │ T-1     │ proj-A     │ ...  │ TODO   │ agent-1      │   │
│  │ T-2     │ proj-A     │ ...  │ DONE   │ agent-2      │   │
│  │ T-3     │ proj-B     │ ...  │ TODO   │ NULL         │   │
│  └─────────┴────────────┴──────┴────────┴──────────────┘   │
│                                                              │
│  active_project:                                             │
│  ┌────────────┐                                              │
│  │ proj-A     │  ← Currently active                          │
│  └────────────┘                                              │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 │ Read/Write
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
┌──────────────┐   ┌─────────────────┐
│  Cato MCP    │   │  Cato UI        │
│  Server      │   │  (Multi-Board)  │
│              │   │                 │
│ Tools:       │   │ Views:          │
│ - get_tasks  │   │ ┌─────────────┐ │
│   (proj_id)  │   │ │Project      │ │
│ - switch_    │   │ │Picker       │ │
│   project    │   │ └─────────────┘ │
│ - list_      │   │                 │
│   projects   │   │ ┌─────────────┐ │
│              │   │ │Board: Proj-A│ │
│              │   │ │ • T-1 (TODO)│ │
│              │   │ │ • T-2 (DONE)│ │
│              │   │ └─────────────┘ │
│              │   │                 │
│              │   │ OR Multi-view:  │
│              │   │ ┌────┐ ┌────┐  │ │
│              │   │ │Pr-A│ │Pr-B│  │ │
│              │   │ └────┘ └────┘  │ │
└──────────────┘   └─────────────────┘
```

---

## Cato MCP Server Implementation

### Multi-Project MCP Tools

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
import sqlite3
from typing import List, Dict, Any, Optional

class CatoMCPServer:
    """
    MCP server for Cato board with multi-project support.

    Implements same interface as kanban-mcp but operates on
    Marcus's SQLite database instead of external Planka.
    """

    def __init__(self, marcus_data_path: str):
        self.server = Server("cato-mcp")
        self.db_path = f"{marcus_data_path}/marcus_state.db"
        self.active_project_id: Optional[str] = None
        self._register_tools()

    def _get_db_connection(self):
        """Get SQLite connection."""
        return sqlite3.connect(self.db_path)

    def _register_tools(self):
        """Register all MCP tools for multi-project support."""

        # ============================================================
        # PROJECT MANAGEMENT TOOLS
        # ============================================================

        @self.server.tool()
        async def cato_list_projects() -> Dict[str, Any]:
            """
            List all projects in Marcus.

            Returns
            -------
            Dict with:
                - projects: List of project objects
                - count: Number of projects
            """
            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT project_id, name, provider, provider_config
                FROM projects
                ORDER BY name
            """)

            projects = []
            for row in cursor.fetchall():
                projects.append({
                    "project_id": row[0],
                    "name": row[1],
                    "provider": row[2],
                    "provider_config": json.loads(row[3])
                })

            conn.close()

            return {
                "projects": projects,
                "count": len(projects)
            }

        @self.server.tool()
        async def cato_get_active_project() -> Dict[str, Any]:
            """
            Get currently active project.

            Returns
            -------
            Dict with project details or None if no active project
            """
            conn = self._get_db_connection()
            cursor = conn.cursor()

            # Check if we have cached active project
            if self.active_project_id:
                cursor.execute("""
                    SELECT project_id, name, provider, provider_config
                    FROM projects
                    WHERE project_id = ?
                """, (self.active_project_id,))
            else:
                # Get from state table or use first project
                cursor.execute("""
                    SELECT project_id, name, provider, provider_config
                    FROM projects
                    LIMIT 1
                """)

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    "project_id": row[0],
                    "name": row[1],
                    "provider": row[2],
                    "provider_config": json.loads(row[3])
                }
            return {"project_id": None}

        @self.server.tool()
        async def cato_switch_project(project_id: str) -> Dict[str, Any]:
            """
            Switch active project.

            Parameters
            ----------
            project_id : str
                ID of project to make active

            Returns
            -------
            Dict with success status and active project
            """
            # Verify project exists
            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT project_id FROM projects WHERE project_id = ?
            """, (project_id,))

            if cursor.fetchone():
                self.active_project_id = project_id
                conn.close()
                return {
                    "success": True,
                    "active_project": project_id
                }

            conn.close()
            return {
                "success": False,
                "error": f"Project {project_id} not found"
            }

        # ============================================================
        # TASK MANAGEMENT TOOLS (Project-Scoped)
        # ============================================================

        @self.server.tool()
        async def cato_get_all_tasks(
            project_id: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Get all tasks, optionally filtered by project.

            Parameters
            ----------
            project_id : Optional[str]
                If provided, only return tasks for this project.
                If None, use active project.

            Returns
            -------
            Dict with:
                - tasks: List of task objects
                - project_id: Project these tasks belong to
                - count: Number of tasks
            """
            # Determine which project to query
            if project_id is None:
                active_proj = await cato_get_active_project()
                project_id = active_proj.get("project_id")

            if not project_id:
                return {
                    "tasks": [],
                    "project_id": None,
                    "count": 0,
                    "error": "No project specified or active"
                }

            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    task_id, name, description, status, priority,
                    estimated_hours, created_at, labels, dependencies
                FROM tasks
                WHERE project_id = ?
                ORDER BY created_at DESC
            """, (project_id,))

            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "status": row[3],
                    "priority": row[4],
                    "estimated_hours": row[5],
                    "created_at": row[6],
                    "labels": json.loads(row[7]) if row[7] else [],
                    "dependencies": json.loads(row[8]) if row[8] else []
                })

            conn.close()

            return {
                "tasks": tasks,
                "project_id": project_id,
                "count": len(tasks)
            }

        @self.server.tool()
        async def cato_get_available_tasks(
            project_id: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Get unassigned tasks (TODO status) for a project.

            Parameters
            ----------
            project_id : Optional[str]
                If provided, tasks for this project.
                If None, use active project.

            Returns
            -------
            Dict with available tasks
            """
            # Determine which project
            if project_id is None:
                active_proj = await cato_get_active_project()
                project_id = active_proj.get("project_id")

            if not project_id:
                return {"tasks": [], "count": 0}

            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    t.task_id, t.name, t.description, t.status,
                    t.priority, t.estimated_hours, t.labels
                FROM tasks t
                LEFT JOIN assignments a ON t.task_id = a.task_id
                WHERE t.project_id = ?
                  AND t.status = 'TODO'
                  AND a.assignment_id IS NULL
                ORDER BY t.priority DESC, t.created_at
            """, (project_id,))

            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "status": row[3],
                    "priority": row[4],
                    "estimated_hours": row[5],
                    "labels": json.loads(row[6]) if row[6] else []
                })

            conn.close()

            return {
                "tasks": tasks,
                "project_id": project_id,
                "count": len(tasks)
            }

        @self.server.tool()
        async def cato_create_task(
            name: str,
            description: str = "",
            project_id: Optional[str] = None,
            priority: str = "MEDIUM",
            status: str = "TODO",
            estimated_hours: float = 0.0,
            labels: List[str] = []
        ) -> Dict[str, Any]:
            """
            Create a new task in specified project.

            Parameters
            ----------
            name : str
                Task name
            description : str
                Task description
            project_id : Optional[str]
                Project to create task in (uses active if None)
            priority : str
                Task priority (LOW, MEDIUM, HIGH, URGENT)
            status : str
                Initial status (TODO, IN_PROGRESS, DONE, BLOCKED)
            estimated_hours : float
                Estimated effort
            labels : List[str]
                Task labels/tags

            Returns
            -------
            Dict with created task_id and details
            """
            # Determine project
            if project_id is None:
                active_proj = await cato_get_active_project()
                project_id = active_proj.get("project_id")

            if not project_id:
                return {
                    "success": False,
                    "error": "No project specified or active"
                }

            # Generate task ID
            import uuid
            task_id = f"T-{uuid.uuid4().hex[:8].upper()}"

            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO tasks (
                    task_id, project_id, name, description,
                    status, priority, estimated_hours, labels,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                task_id, project_id, name, description,
                status, priority, estimated_hours,
                json.dumps(labels)
            ))

            conn.commit()
            conn.close()

            return {
                "success": True,
                "task_id": task_id,
                "project_id": project_id,
                "name": name,
                "status": status
            }

        @self.server.tool()
        async def cato_update_task(
            task_id: str,
            updates: Dict[str, Any]
        ) -> Dict[str, Any]:
            """
            Update existing task.

            Parameters
            ----------
            task_id : str
                Task to update
            updates : Dict[str, Any]
                Fields to update (name, description, status, priority, etc.)

            Returns
            -------
            Dict with success status
            """
            conn = self._get_db_connection()
            cursor = conn.cursor()

            # Build dynamic UPDATE query
            update_fields = []
            values = []

            for field, value in updates.items():
                if field in ["name", "description", "status", "priority",
                           "estimated_hours", "progress"]:
                    update_fields.append(f"{field} = ?")
                    values.append(value)
                elif field == "labels":
                    update_fields.append("labels = ?")
                    values.append(json.dumps(value))

            if not update_fields:
                return {
                    "success": False,
                    "error": "No valid fields to update"
                }

            values.append(task_id)

            query = f"""
                UPDATE tasks
                SET {', '.join(update_fields)}
                WHERE task_id = ?
            """

            cursor.execute(query, values)
            conn.commit()

            success = cursor.rowcount > 0
            conn.close()

            return {
                "success": success,
                "task_id": task_id,
                "updated_fields": list(updates.keys())
            }

        @self.server.tool()
        async def cato_move_task(
            task_id: str,
            new_status: str
        ) -> Dict[str, Any]:
            """
            Move task to different status/column.

            Parameters
            ----------
            task_id : str
                Task to move
            new_status : str
                New status (TODO, IN_PROGRESS, DONE, BLOCKED)

            Returns
            -------
            Dict with success status
            """
            return await cato_update_task(
                task_id=task_id,
                updates={"status": new_status}
            )

        @self.server.tool()
        async def cato_add_comment(
            task_id: str,
            comment: str
        ) -> Dict[str, Any]:
            """
            Add comment/decision to task.

            Stores as decision in Marcus decision log.

            Parameters
            ----------
            task_id : str
                Task to comment on
            comment : str
                Comment text

            Returns
            -------
            Dict with success status
            """
            # Store in decisions table or append to task metadata
            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO decisions (
                    task_id, decision, created_at
                ) VALUES (?, ?, datetime('now'))
            """, (task_id, comment))

            conn.commit()
            conn.close()

            return {
                "success": True,
                "task_id": task_id
            }

        # ============================================================
        # METRICS TOOLS (Project-Scoped)
        # ============================================================

        @self.server.tool()
        async def cato_get_project_metrics(
            project_id: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Get project metrics and statistics.

            Parameters
            ----------
            project_id : Optional[str]
                Project to get metrics for (uses active if None)

            Returns
            -------
            Dict with project metrics
            """
            # Determine project
            if project_id is None:
                active_proj = await cato_get_active_project()
                project_id = active_proj.get("project_id")

            if not project_id:
                return {"error": "No project specified"}

            conn = self._get_db_connection()
            cursor = conn.cursor()

            # Get task counts by status
            cursor.execute("""
                SELECT status, COUNT(*)
                FROM tasks
                WHERE project_id = ?
                GROUP BY status
            """, (project_id,))

            status_counts = {
                "TODO": 0,
                "IN_PROGRESS": 0,
                "DONE": 0,
                "BLOCKED": 0
            }

            for row in cursor.fetchall():
                status_counts[row[0]] = row[1]

            conn.close()

            total_tasks = sum(status_counts.values())
            completion_rate = (
                status_counts["DONE"] / total_tasks
                if total_tasks > 0 else 0
            )

            return {
                "project_id": project_id,
                "total_tasks": total_tasks,
                "backlog_tasks": status_counts["TODO"],
                "in_progress_tasks": status_counts["IN_PROGRESS"],
                "completed_tasks": status_counts["DONE"],
                "blocked_tasks": status_counts["BLOCKED"],
                "completion_rate": completion_rate
            }

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as streams:
            await self.server.run(*streams)

if __name__ == "__main__":
    import asyncio
    import sys

    # Get Marcus data path from args or env
    marcus_data = sys.argv[1] if len(sys.argv) > 1 else "/Users/lwgray/dev/marcus/data"

    server = CatoMCPServer(marcus_data)
    asyncio.run(server.run())
```

---

## Marcus Integration (CatoKanban Provider)

### New Provider Implementation

**File:** `src/integrations/providers/cato_kanban.py`

```python
from typing import Any, Dict, List, Optional
from src.integrations.kanban_interface import KanbanInterface, KanbanProvider
from src.integrations.cato_client import CatoClient
from src.core.models import Task

class CatoKanban(KanbanInterface):
    """
    Cato kanban board implementation with multi-project support.

    Identical interface to PlankaKanban but talks to Cato MCP server
    which reads/writes Marcus's SQLite database directly.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider = KanbanProvider.CATO
        self.client = CatoClient(config)
        self.connected = False

    async def connect(self) -> bool:
        """Connect to Cato MCP server."""
        try:
            # Test connection by listing projects
            projects = await self.client.list_projects()
            self.connected = bool(projects)
            return self.connected
        except Exception as e:
            logger.error(f"Failed to connect to Cato: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Cato."""
        self.connected = False

    async def get_available_tasks(self) -> List[Task]:
        """Get unassigned tasks from active project."""
        if not self.connected:
            await self.connect()

        return await self.client.get_available_tasks()

    async def get_all_tasks(self) -> List[Task]:
        """Get all tasks from active project."""
        if not self.connected:
            await self.connect()

        return await self.client.get_all_tasks()

    # ... all other KanbanInterface methods
    # (same signatures as PlankaKanban, just call CatoClient)
```

### CatoClient (MCP Communication)

**File:** `src/integrations/cato_client.py`

```python
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
import json

class CatoClient:
    """Low-level MCP client for Cato server."""

    def __init__(self, config: Dict[str, Any]):
        self.marcus_data_path = config.get(
            "marcus_data_path",
            "/Users/lwgray/dev/marcus/data"
        )

        self._server_params = StdioServerParameters(
            command="python",
            args=["-m", "cato.backend.mcp_server", self.marcus_data_path]
        )

    async def list_projects(self) -> List[Dict]:
        """List all projects."""
        async with stdio_client(self._server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "cato_list_projects",
                    arguments={}
                )

                data = json.loads(result.content[0].text)
                return data["projects"]

    async def get_all_tasks(self, project_id: Optional[str] = None) -> List[Task]:
        """Get all tasks for project."""
        async with stdio_client(self._server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "cato_get_all_tasks",
                    arguments={"project_id": project_id} if project_id else {}
                )

                data = json.loads(result.content[0].text)

                # Convert to Marcus Task objects
                return [self._parse_task(t) for t in data["tasks"]]

    def _parse_task(self, task_data: Dict) -> Task:
        """Convert Cato task dict to Marcus Task object."""
        # Same parsing logic as KanbanClient
        ...
```

---

## Cato Frontend (Multi-Project UI)

### Project Switcher Component

```typescript
// components/ProjectSwitcher.tsx

import React from 'react';

interface Project {
  project_id: string;
  name: string;
  provider: string;
}

export function ProjectSwitcher() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);

  useEffect(() => {
    // Load projects from Cato API
    fetch('/api/projects')
      .then(r => r.json())
      .then(data => {
        setProjects(data.projects);
        setActiveProjectId(data.active_project_id);
      });
  }, []);

  const switchProject = async (projectId: string) => {
    // Tell backend to switch active project
    await fetch('/api/projects/switch', {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId })
    });

    setActiveProjectId(projectId);

    // Refresh board data
    window.location.reload();
  };

  return (
    <select
      value={activeProjectId || ''}
      onChange={(e) => switchProject(e.target.value)}
      className="project-switcher"
    >
      {projects.map(p => (
        <option key={p.project_id} value={p.project_id}>
          {p.name} ({p.provider})
        </option>
      ))}
    </select>
  );
}
```

### Multi-Board Dashboard View

```typescript
// components/MultiProjectDashboard.tsx

export function MultiProjectDashboard() {
  const [viewMode, setViewMode] = useState<'single' | 'multi'>('single');
  const [projects, setProjects] = useState<Project[]>([]);

  return (
    <div className="dashboard">
      <div className="toolbar">
        <ProjectSwitcher />

        <button onClick={() => setViewMode(
          viewMode === 'single' ? 'multi' : 'single'
        )}>
          {viewMode === 'single' ? 'Show All Boards' : 'Show Active Board'}
        </button>
      </div>

      {viewMode === 'single' ? (
        <Board projectId={activeProjectId} />
      ) : (
        <div className="multi-board-grid">
          {projects.map(p => (
            <MiniBoard
              key={p.project_id}
              projectId={p.project_id}
              projectName={p.name}
            />
          ))}
        </div>
      )}
    </div>
  );
}
```

### Cato Backend API (Multi-Project Endpoints)

```python
# cato/backend/api.py

from fastapi import FastAPI

app = FastAPI()

# Global reference to Cato MCP client
# (or create new client per request)
from cato.backend.cato_client import CatoClient

cato_client = CatoClient()

@app.get("/api/projects")
async def list_projects():
    """List all projects."""
    projects = await cato_client.list_projects()
    active_project = await cato_client.get_active_project()

    return {
        "projects": projects,
        "active_project_id": active_project.get("project_id")
    }

@app.post("/api/projects/switch")
async def switch_project(request: dict):
    """Switch active project."""
    project_id = request.get("project_id")
    result = await cato_client.switch_project(project_id)
    return result

@app.get("/api/projects/{project_id}/tasks")
async def get_project_tasks(project_id: str):
    """Get tasks for specific project."""
    tasks = await cato_client.get_all_tasks(project_id=project_id)
    return {"tasks": tasks}

@app.get("/api/snapshot")
async def get_snapshot(project_id: Optional[str] = None):
    """
    Get snapshot for visualization.

    If project_id provided, snapshot for that project.
    Otherwise, snapshot for active project.
    """
    # Use existing Aggregator but filter by project
    snapshot = aggregator.create_snapshot(
        project_id=project_id,
        view_mode="subtasks"
    )
    return snapshot.to_dict()
```

---

## Configuration Changes

### Marcus Config (Multi-Project)

**File:** `config_marcus.json`

```json
{
  "kanban": {
    "provider": "cato",
    "marcus_data_path": "/Users/lwgray/dev/marcus/data"
  },
  "projects": [
    {
      "project_id": "proj-task-api",
      "name": "Task Management API",
      "provider": "cato",
      "active": true
    },
    {
      "project_id": "proj-auth-service",
      "name": "Authentication Service",
      "provider": "cato",
      "active": false
    },
    {
      "project_id": "proj-legacy",
      "name": "Legacy System",
      "provider": "planka",
      "provider_config": {
        "board_id": "bd_12345",
        "project_id": "prj_67890"
      },
      "active": false
    }
  ]
}
```

**Key Features:**
- Multiple projects configured
- Each can use different provider (cato, planka, linear, github)
- One project marked as `active`
- Mixed providers supported (Cato for new, Planka for legacy)

---

## Comparison: Before and After

### Before (Planka Multi-Project)

```
Setup for each project:
1. Create new Planka board manually
2. Create lists (Backlog, In Progress, Done, Blocked)
3. Get board_id and project_id from Planka
4. Add to config_marcus.json
5. Switch project via API or config edit

Storage: Each project in separate Planka board (Postgres)
```

### After (Cato Multi-Project)

```
Setup for each project:
1. Create project via Marcus or Cato UI
2. Projects automatically stored in Marcus SQLite
3. Switch project via Cato dropdown

Storage: All projects in single Marcus SQLite database
```

---

## Benefits Summary

### 1. **Simplified Multi-Project Management**
- All projects in one database
- No manual board setup per project
- Switch projects via UI dropdown
- No board_id/project_id configuration needed

### 2. **Unified Data Model**
- Single SQLite database for all projects
- No data duplication
- Cross-project queries possible
- Consistent data structure

### 3. **Flexible Provider Support**
- Can use Cato for most projects
- Keep Planka for specific projects if needed
- Mix and match per project
- Easy migration path

### 4. **Better UX**
- Visual project switcher
- Multi-board dashboard view
- See all projects at a glance
- Drag-drop between projects (future)

### 5. **Developer Experience**
- One setup command for all projects
- No Docker per project
- Local SQLite = easy debugging
- Consistent API across providers

---

## Implementation Roadmap

### Phase 1: Cato MCP Server (1-2 days)
- [ ] Create `cato/backend/mcp_server.py`
- [ ] Implement project management tools:
  - `cato_list_projects`
  - `cato_get_active_project`
  - `cato_switch_project`
- [ ] Implement task tools (project-scoped):
  - `cato_get_all_tasks(project_id)`
  - `cato_get_available_tasks(project_id)`
  - `cato_create_task(project_id, ...)`
  - `cato_update_task(...)`
  - `cato_move_task(...)`
- [ ] Test with Marcus SQLite database

### Phase 2: Marcus Integration (1 day)
- [ ] Create `CatoKanban` provider
- [ ] Create `CatoClient` MCP client
- [ ] Add `CATO` to `KanbanProvider` enum
- [ ] Update config loading
- [ ] Test provider switching

### Phase 3: Cato Frontend Multi-Project (2-3 days)
- [ ] Create ProjectSwitcher component
- [ ] Update Aggregator to filter by project
- [ ] Add project-scoped API endpoints
- [ ] Multi-board dashboard view
- [ ] Project management UI (create/edit projects)

### Phase 4: Testing & Documentation (1 day)
- [ ] Test multi-project workflows
- [ ] Test mixed providers (Cato + Planka)
- [ ] Write migration guide (Planka → Cato)
- [ ] Update user documentation

### Phase 5: Bundled Deployment (1 day)
- [ ] Create `marcus start` command
- [ ] Auto-start Cato MCP + Frontend
- [ ] Setup wizard for first run
- [ ] Packaging and distribution

**Total Estimated Time:** 1 week (5-7 days)

---

## Migration Path

### For Users Currently on Planka

**Option A: Gradual Migration**
```json
{
  "projects": [
    {
      "name": "New Project",
      "provider": "cato"  // New projects use Cato
    },
    {
      "name": "Legacy Project",
      "provider": "planka",  // Keep existing on Planka
      "provider_config": {"board_id": "..."}
    }
  ]
}
```

**Option B: Full Migration**
```bash
# Export from Planka
marcus export --project=proj-A --format=json

# Import to Cato (Marcus SQLite)
marcus import --file=proj-A.json --provider=cato

# Switch provider in config
# "provider": "planka" → "provider": "cato"

# Remove Planka containers
docker-compose down
```

---

## Conclusion

**Marcus already has multi-project support via ProjectRegistry.**

**Cato MCP Server can replace Planka while supporting multiple projects/boards by:**

1. ✅ Implementing project-scoped MCP tools (`project_id` parameter)
2. ✅ Reading from Marcus SQLite (all projects in one DB)
3. ✅ Providing project switcher in UI
4. ✅ Supporting mixed providers (Cato + Planka + Linear + GitHub)
5. ✅ Maintaining same `KanbanInterface` abstraction

**Key Architectural Insight:**

The `KanbanInterface` abstraction was designed for exactly this - multiple providers with the same interface. Adding Cato as a provider that reads/writes Marcus SQLite is a perfect fit for this architecture.

**Next Step:** Implement `CatoMCPServer` with multi-project support.
