# Cato MCP Integration Plan - Beginner-Friendly Guide

**Date:** 2025-11-09
**Goal:** Make Marcus easier to set up by replacing Planka with Cato
**Timeline:** 6 weeks
**For:** Junior engineers and contributors

---

## Table of Contents

1. [What Problem Are We Solving?](#what-problem-are-we-solving)
2. [Big Picture: How Everything Fits Together](#big-picture-how-everything-fits-together)
3. [The 6 Stages (Week by Week)](#the-6-stages-week-by-week)
4. [Glossary: Important Terms Explained](#glossary-important-terms-explained)
5. [How to Get Started](#how-to-get-started)

---

## What Problem Are We Solving?

### Current Problem: Setup is Too Complex

**Right now**, to use Marcus with a visual board, users need to:

1. Install Docker Desktop
2. Run Docker Compose (starts 3 services)
3. Wait for PostgreSQL to start
4. Wait for Planka to start
5. Configure Marcus to talk to Planka
6. Open multiple terminals

**Time:** 30+ minutes | **Difficulty:** Hard for beginners

### Our Goal: Make Setup Simple

**After this project**, users will:

1. Run `pip install marcus-cato`
2. Run `marcus start`

**Time:** Under 5 minutes | **Difficulty:** Easy for anyone

### Why This Matters

- **For new users**: Can try Marcus immediately without Docker knowledge
- **For experienced users**: Can choose Planka if they want the advanced features
- **For developers**: Less debugging "why won't Planka connect?" issues

---

## Big Picture: How Everything Fits Together

### Key Components Explained

Think of this like a restaurant:

- **Marcus** = The kitchen (does the work, coordinates tasks)
- **Board (Planka/Cato)** = The menu board (shows what needs to be done)
- **Agents** = The chefs (read the board, do the tasks, report back)

### Current Architecture (Planka)

```
Marcus Kitchen
    ↓ (asks: "What tasks are available?")
kanban-mcp (Translator)
    ↓ (translates to restaurant language)
Planka Menu Board (Node.js app)
    ↓ (stores data in)
PostgreSQL Database

Setup: Need to start 3 different restaurants (services)!
```

**Why it's complex:**
- 3 separate programs running (Marcus, Planka, PostgreSQL)
- Each needs configuration
- If one breaks, everything stops

### New Architecture (Cato)

```
Marcus Kitchen ←──────────┐
    ↓                     │
    ↓ (MCP protocol)      │ (reads/writes directly)
    ↓                     │
Cato MCP Server ──────────┤
    ↑                     │
    │ (API)               ↓
    │              Marcus SQLite Database
Cato Web UI              (already exists!)
```

**Why it's simple:**
- Only 1 database (Marcus already has it)
- Cato reads/writes Marcus's database directly
- No Docker required
- Start everything with one command

### What is MCP? (Explained Simply)

**MCP = Model Context Protocol**

Think of it like a **universal translator** for AI tools:

- **Without MCP**: Every tool speaks a different language (HTTP, gRPC, WebSockets)
- **With MCP**: All tools speak the same language (MCP)

**Example:**
```python
# Marcus wants to get tasks from the board
result = await mcp_client.call_tool(
    "cato_get_all_tasks",  # What function to call
    arguments={"project_id": "123"}  # What info to send
)
# Result comes back in standard format
```

**Why Marcus uses MCP:**
- Consistent way to talk to boards (Planka, GitHub, Linear, Cato)
- Easy to add new boards (just implement MCP tools)
- Reliable (if one fails, switch to another)

---

## The 6 Stages (Week by Week)

### 🎯 Stage 0: Planning & Setup (Week 1)

**Goal:** Understand what we need to build and set up our workspace

**What You'll Learn:**
- How Marcus stores data in SQLite
- What MCP tools we need to create
- How to set up a test environment

#### Tasks (In Plain English)

**0.1 Set Up Your Workspace**
```bash
# Start from the main branch
git checkout develop
git pull origin develop

# Create your own branch to work on
git checkout -b feature/cato-mcp-integration

# Verify you can run Marcus and Cato locally
marcus --version
cd /Users/lwgray/dev/cato && npm start
```

**What success looks like:** Both Marcus and Cato run without errors

---

**0.2 Understand Marcus's Database**

Marcus stores everything in a SQLite database. Think of it like an Excel file with multiple sheets:

| Table Name | What It Stores | Example |
|------------|---------------|---------|
| `projects` | Project info | "Build Website", "Fix Bugs" |
| `tasks` | Task details | "Create homepage", "Fix login" |
| `agents` | Agent info | "agent_claude", "agent_coder" |
| `decisions` | Why choices were made | "Used React because..." |
| `artifacts` | Files created | "design.png", "code.py" |

**Your Job:**
1. Open Marcus's SQLite database
2. Look at each table
3. Write down what columns exist
4. Create a document showing how Planka concepts map to Marcus tables

**Example Mapping:**
```
Planka Board  → Marcus Project
Planka List   → Task Status (TODO, IN_PROGRESS, DONE)
Planka Card   → Marcus Task
Planka Comment → Marcus Decision
```

**Tool to use:**
```bash
# Open Marcus database
sqlite3 /Users/lwgray/dev/marcus/data/marcus.db

# Show all tables
.tables

# See what's in the tasks table
SELECT * FROM tasks LIMIT 5;
```

**Deliverable:** Create `docs/specs/DATABASE_MAPPING.md`

---

**0.3 Design the MCP Tools**

MCP tools are like functions that Cato will provide to Marcus. Think of them like a restaurant menu:

**Read-Only Tools** (Marcus asks, Cato answers)
- `cato_list_projects()` - "Show me all projects"
- `cato_get_all_tasks(project_id)` - "Show me all tasks for project X"
- `cato_get_task(task_id)` - "Show me details for task Y"

**Write Tools** (Marcus tells Cato to change things)
- `cato_create_task(name, description, ...)` - "Create a new task"
- `cato_update_task(task_id, updates)` - "Change task details"
- `cato_move_task(task_id, new_status)` - "Move task to DONE"

**Your Job:**
1. List all the tools Cato needs (look at what Planka does)
2. For each tool, define:
   - **Input:** What information does it need?
   - **Output:** What does it return?
   - **Errors:** What can go wrong?

**Example Tool Specification:**
```markdown
## cato_create_task

**Description:** Creates a new task in the specified project

**Inputs:**
- `project_id` (string, required) - Which project to add task to
- `name` (string, required) - Task name (max 200 chars)
- `description` (string, optional) - Task details
- `status` (string, optional) - TODO, IN_PROGRESS, DONE (default: TODO)
- `priority` (number, optional) - 1-5 (default: 3)

**Output:**
```json
{
  "success": true,
  "task": {
    "id": "task_123",
    "name": "Create homepage",
    "status": "TODO",
    "created_at": "2025-11-09T10:00:00Z"
  }
}
```

**Possible Errors:**
- `ProjectNotFound` - project_id doesn't exist
- `InvalidInput` - name is empty or too long
- `DatabaseError` - Database write failed
```

**Deliverable:** Create `docs/specs/CATO_MCP_SPECIFICATION.md`

---

**0.4 Create Test Data**

Before building anything, create fake data to test with:

```sql
-- Create test project
INSERT INTO projects (id, name, description, status)
VALUES ('proj_1', 'Test Project', 'For testing Cato MCP', 'active');

-- Create test tasks
INSERT INTO tasks (id, project_id, name, status, priority)
VALUES
  ('task_1', 'proj_1', 'First task', 'TODO', 3),
  ('task_2', 'proj_1', 'Second task', 'IN_PROGRESS', 5),
  ('task_3', 'proj_1', 'Third task', 'DONE', 2);

-- Create test agent
INSERT INTO agents (id, name, status)
VALUES ('agent_test', 'Test Agent', 'active');
```

**Deliverable:** Create `tests/fixtures/cato_test_data.sql`

---

**Week 1 Checklist:**
- [ ] Feature branch created
- [ ] Database schema documented
- [ ] MCP tool specification written
- [ ] Test data created
- [ ] Test environment working (can run Marcus + read database)

**Time Estimate:** 10-15 hours total

---

### 🔍 Stage 1: Read-Only MCP Server (Week 2)

**Goal:** Build a Cato MCP server that can READ data from Marcus's database

**Think of it like:** Building a librarian that can find books but can't add new ones yet

#### What You'll Build

A Python program (`cato/backend/mcp_server.py`) that:
1. Connects to Marcus's SQLite database
2. Provides MCP tools to read data
3. Returns data in a format Marcus understands

#### Step-by-Step Tasks

**1.1 Create the Basic Server Structure**

```python
# cato/backend/mcp_server.py
import sqlite3
from mcp.server import Server
from typing import Dict, Any, List

class CatoMCPServer:
    """
    Cato MCP Server - Provides MCP tools to access Marcus data.

    This server allows Marcus to query tasks, projects, and agents
    from the Marcus SQLite database using the MCP protocol.
    """

    def __init__(self, database_path: str):
        """
        Initialize the Cato MCP server.

        Parameters
        ----------
        database_path : str
            Path to Marcus SQLite database
            Example: "/Users/lwgray/dev/marcus/data/marcus.db"
        """
        self.server = Server("cato-mcp")  # Create MCP server
        self.db_path = database_path  # Store database path
        self._register_tools()  # Register all MCP tools

    def _get_db_connection(self) -> sqlite3.Connection:
        """
        Get a connection to the Marcus database.

        Returns
        -------
        sqlite3.Connection
            Database connection with row factory for dict results
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dicts
        return conn
```

**What each part does:**
- `Server("cato-mcp")` - Creates an MCP server named "cato-mcp"
- `self.db_path` - Stores where the database is located
- `_get_db_connection()` - Opens the database file
- `row_factory` - Makes results come back as dictionaries (easier to work with)

---

**1.2 Implement Your First MCP Tool: List Projects**

```python
def _register_tools(self):
    """Register all MCP tools with the server."""

    @self.server.tool()
    async def cato_list_projects() -> Dict[str, Any]:
        """
        List all projects in Marcus.

        Returns
        -------
        Dict[str, Any]
            {
                "success": true,
                "projects": [
                    {"id": "proj_1", "name": "My Project", ...},
                    ...
                ]
            }
        """
        try:
            # Open database connection
            conn = self._get_db_connection()
            cursor = conn.cursor()

            # Query all projects
            cursor.execute("""
                SELECT id, name, description, status, created_at
                FROM projects
                WHERE status != 'archived'
                ORDER BY created_at DESC
            """)

            # Get results
            projects = [dict(row) for row in cursor.fetchall()]

            # Close connection
            conn.close()

            # Return success response
            return {
                "success": True,
                "projects": projects,
                "count": len(projects)
            }

        except Exception as e:
            # If something goes wrong, return error
            return {
                "success": False,
                "error": str(e),
                "error_type": "DatabaseError"
            }
```

**Line-by-line explanation:**

1. `@self.server.tool()` - Tells MCP "this is a tool Marcus can call"
2. `async def cato_list_projects()` - Defines the tool (async because MCP uses async)
3. `conn = self._get_db_connection()` - Open database
4. `cursor.execute(...)` - Run SQL query
5. `projects = [dict(row) for row in cursor.fetchall()]` - Convert results to list of dicts
6. `return {"success": True, ...}` - Send data back to Marcus
7. `except Exception as e` - Catch errors and return them nicely

---

**1.3 Test Your Tool**

Create a test file to verify your tool works:

```python
# tests/unit/mcp_server/test_read_tools.py
import pytest
from cato.backend.mcp_server import CatoMCPServer

class TestCatoMCPServerReadTools:
    """Tests for Cato MCP Server read operations."""

    @pytest.fixture
    def server(self, tmp_path):
        """Create a test server with test database."""
        # Create test database
        db_path = tmp_path / "test_marcus.db"

        # Set up test data
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE projects (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                status TEXT,
                created_at TEXT
            )
        """)
        cursor.execute("""
            INSERT INTO projects VALUES
            ('proj_1', 'Test Project', 'A test', 'active', '2025-11-09')
        """)
        conn.commit()
        conn.close()

        # Create server
        return CatoMCPServer(str(db_path))

    @pytest.mark.asyncio
    async def test_list_projects_success(self, server):
        """Test listing projects returns data correctly."""
        # Call the tool
        result = await server._tools["cato_list_projects"]()

        # Check result
        assert result["success"] is True
        assert result["count"] == 1
        assert result["projects"][0]["name"] == "Test Project"

    @pytest.mark.asyncio
    async def test_list_projects_empty_database(self, tmp_path):
        """Test listing projects when database is empty."""
        # Create empty database
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE projects (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                status TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Create server and test
        server = CatoMCPServer(str(db_path))
        result = await server._tools["cato_list_projects"]()

        assert result["success"] is True
        assert result["count"] == 0
```

**Run the test:**
```bash
pytest tests/unit/mcp_server/test_read_tools.py -v
```

---

**1.4 Implement All Read Tools**

Following the same pattern, implement these tools:

| Tool Name | What It Does | SQL Query Hint |
|-----------|-------------|----------------|
| `cato_get_all_tasks` | Get all tasks for a project | `SELECT * FROM tasks WHERE project_id = ?` |
| `cato_get_task` | Get one task by ID | `SELECT * FROM tasks WHERE id = ?` |
| `cato_get_available_tasks` | Get unassigned tasks | `SELECT * FROM tasks WHERE assigned_to IS NULL` |
| `cato_search_tasks` | Search tasks by keyword | `SELECT * FROM tasks WHERE name LIKE ?` |
| `cato_get_project_metrics` | Count tasks by status | `SELECT status, COUNT(*) FROM tasks GROUP BY status` |

**Example - Get All Tasks:**
```python
@self.server.tool()
async def cato_get_all_tasks(project_id: str) -> Dict[str, Any]:
    """
    Get all tasks for a specific project.

    Parameters
    ----------
    project_id : str
        The project ID to get tasks for

    Returns
    -------
    Dict[str, Any]
        {"success": true, "tasks": [...]}
    """
    try:
        conn = self._get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, description, status, priority,
                   assigned_to, created_at, updated_at
            FROM tasks
            WHERE project_id = ?
            ORDER BY priority DESC, created_at ASC
        """, (project_id,))

        tasks = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return {"success": True, "tasks": tasks, "count": len(tasks)}

    except Exception as e:
        return {"success": False, "error": str(e)}
```

**Note the `?` in SQL:** This prevents SQL injection attacks (security!)

---

**Week 2 Checklist:**
- [ ] CatoMCPServer class created
- [ ] All 6+ read tools implemented
- [ ] Unit tests written for each tool (85%+ coverage)
- [ ] Tests pass locally
- [ ] Can query test database successfully

**Time Estimate:** 20-25 hours

---

### ✍️ Stage 2: Write Operations (Week 3)

**Goal:** Add the ability for Marcus to CREATE, UPDATE, and DELETE tasks through Cato

**Think of it like:** Now the librarian can add new books and update book info

#### Why Write Operations Are Harder

Read operations just look at data. Write operations CHANGE data, so we need to:
1. **Validate inputs** (don't allow empty task names)
2. **Handle errors** (what if the project doesn't exist?)
3. **Prevent conflicts** (what if two agents edit the same task?)
4. **Use transactions** (either everything saves or nothing does)

#### Key Concept: Database Transactions

Think of a transaction like a shopping cart:
- You add items (SQL INSERT/UPDATE statements)
- If checkout succeeds, items are purchased (COMMIT)
- If payment fails, cart is cleared (ROLLBACK)

**Example:**
```python
conn = sqlite3.connect("database.db")
try:
    # Start transaction (automatic in Python)
    cursor = conn.cursor()

    # Do multiple things
    cursor.execute("INSERT INTO tasks ...")
    cursor.execute("UPDATE projects SET task_count = task_count + 1 ...")

    # Everything worked! Save changes
    conn.commit()

except Exception as e:
    # Something failed! Undo everything
    conn.rollback()
    raise e

finally:
    conn.close()
```

#### Step-by-Step Tasks

**2.1 Create Task Tool**

```python
@self.server.tool()
async def cato_create_task(
    project_id: str,
    name: str,
    description: str = "",
    status: str = "TODO",
    priority: int = 3
) -> Dict[str, Any]:
    """
    Create a new task in the specified project.

    Parameters
    ----------
    project_id : str
        Project to add task to
    name : str
        Task name (required, max 200 characters)
    description : str, optional
        Task description
    status : str, optional
        Initial status (TODO, IN_PROGRESS, DONE, BLOCKED)
    priority : int, optional
        Priority 1-5 (default: 3)

    Returns
    -------
    Dict[str, Any]
        {"success": true, "task": {...}}
    """
    # Step 1: Validate inputs
    if not name or len(name) > 200:
        return {
            "success": False,
            "error": "Task name required (max 200 chars)",
            "error_type": "ValidationError"
        }

    if status not in ["TODO", "IN_PROGRESS", "DONE", "BLOCKED"]:
        return {
            "success": False,
            "error": f"Invalid status: {status}",
            "error_type": "ValidationError"
        }

    if not (1 <= priority <= 5):
        return {
            "success": False,
            "error": "Priority must be 1-5",
            "error_type": "ValidationError"
        }

    # Step 2: Create task
    try:
        conn = self._get_db_connection()
        cursor = conn.cursor()

        # Check project exists
        cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            conn.close()
            return {
                "success": False,
                "error": f"Project not found: {project_id}",
                "error_type": "NotFoundError"
            }

        # Generate task ID
        import uuid
        task_id = f"task_{uuid.uuid4().hex[:8]}"

        # Get current timestamp
        from datetime import datetime
        now = datetime.utcnow().isoformat()

        # Insert task (transaction starts automatically)
        cursor.execute("""
            INSERT INTO tasks
            (id, project_id, name, description, status, priority,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (task_id, project_id, name, description, status,
              priority, now, now))

        # Save changes
        conn.commit()

        # Get the created task
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task = dict(cursor.fetchone())

        conn.close()

        return {
            "success": True,
            "task": task,
            "message": f"Task created: {task_id}"
        }

    except sqlite3.IntegrityError as e:
        conn.rollback()
        conn.close()
        return {
            "success": False,
            "error": "Database constraint violation",
            "error_type": "DatabaseError",
            "details": str(e)
        }

    except Exception as e:
        conn.rollback()
        conn.close()
        return {
            "success": False,
            "error": "Failed to create task",
            "error_type": "DatabaseError",
            "details": str(e)
        }
```

**What's new here:**
- **Validation:** Check inputs before touching database
- **Error handling:** Different errors for different problems
- **UUID generation:** Creates unique IDs for tasks
- **Transactions:** `conn.commit()` saves, `conn.rollback()` undoes
- **Return created object:** Marcus needs to know the task ID

---

**2.2 Update Task Tool**

```python
@self.server.tool()
async def cato_update_task(
    task_id: str,
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update an existing task.

    Parameters
    ----------
    task_id : str
        Task ID to update
    updates : Dict[str, Any]
        Fields to update, e.g., {"name": "New name", "status": "DONE"}

    Returns
    -------
    Dict[str, Any]
        {"success": true, "task": {...}}
    """
    # Allowed fields to update
    allowed_fields = [
        "name", "description", "status", "priority",
        "assigned_to", "estimated_hours"
    ]

    # Filter out invalid fields
    valid_updates = {
        k: v for k, v in updates.items()
        if k in allowed_fields
    }

    if not valid_updates:
        return {
            "success": False,
            "error": "No valid fields to update",
            "error_type": "ValidationError"
        }

    try:
        conn = self._get_db_connection()
        cursor = conn.cursor()

        # Check task exists
        cursor.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
        if not cursor.fetchone():
            conn.close()
            return {
                "success": False,
                "error": f"Task not found: {task_id}",
                "error_type": "NotFoundError"
            }

        # Build UPDATE query dynamically
        set_clause = ", ".join([f"{k} = ?" for k in valid_updates.keys()])
        values = list(valid_updates.values())

        # Add updated_at timestamp
        from datetime import datetime
        now = datetime.utcnow().isoformat()
        set_clause += ", updated_at = ?"
        values.append(now)
        values.append(task_id)

        # Execute update
        cursor.execute(f"""
            UPDATE tasks
            SET {set_clause}
            WHERE id = ?
        """, values)

        conn.commit()

        # Get updated task
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task = dict(cursor.fetchone())

        conn.close()

        return {
            "success": True,
            "task": task,
            "updated_fields": list(valid_updates.keys())
        }

    except Exception as e:
        conn.rollback()
        conn.close()
        return {
            "success": False,
            "error": "Failed to update task",
            "error_type": "DatabaseError",
            "details": str(e)
        }
```

**Dynamic SQL building:**
- `set_clause = "name = ?, status = ?"` (built from updates dict)
- `values = ["New name", "DONE"]` (corresponding values)
- This lets us update any combination of fields

---

**2.3 Handle Concurrent Writes (Advanced)**

**Problem:** What if two agents try to update the same task at the same time?

```
Agent A: Read task (version 1)
Agent B: Read task (version 1)
Agent A: Update task (now version 2)
Agent B: Update task (overwrites Agent A's changes!) ❌
```

**Solution: Optimistic Locking**

Add a `version` column to tasks:

```python
# When updating, check version hasn't changed
cursor.execute("""
    UPDATE tasks
    SET name = ?, status = ?, version = version + 1, updated_at = ?
    WHERE id = ? AND version = ?
""", (new_name, new_status, now, task_id, expected_version))

# Check if update succeeded
if cursor.rowcount == 0:
    # Either task doesn't exist OR version changed
    cursor.execute("SELECT version FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if row:
        return {
            "success": False,
            "error": "Task was modified by another process",
            "error_type": "ConcurrentModificationError",
            "current_version": row[0]
        }
```

**How it works:**
1. Read task (includes version number)
2. Update only if version matches
3. If version changed, someone else updated it - return error
4. Client can retry with new version

---

**2.4 Testing Write Operations**

Write tests that verify:
1. **Success cases** - Task created/updated correctly
2. **Validation errors** - Invalid inputs rejected
3. **Not found errors** - Updating non-existent tasks fails
4. **Concurrent writes** - Two updates don't clobber each other

```python
# tests/unit/mcp_server/test_write_tools.py
class TestCatoMCPServerWriteTools:
    """Tests for write operations."""

    @pytest.mark.asyncio
    async def test_create_task_success(self, server, test_project):
        """Test creating a task with valid inputs."""
        result = await server._tools["cato_create_task"](
            project_id=test_project["id"],
            name="New task",
            description="Task description",
            status="TODO",
            priority=5
        )

        assert result["success"] is True
        assert result["task"]["name"] == "New task"
        assert result["task"]["priority"] == 5

    @pytest.mark.asyncio
    async def test_create_task_invalid_name(self, server, test_project):
        """Test that empty task name is rejected."""
        result = await server._tools["cato_create_task"](
            project_id=test_project["id"],
            name="",  # Empty name (invalid)
            description="Test"
        )

        assert result["success"] is False
        assert result["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_create_task_project_not_found(self, server):
        """Test that creating task in non-existent project fails."""
        result = await server._tools["cato_create_task"](
            project_id="fake_project_id",
            name="Task"
        )

        assert result["success"] is False
        assert result["error_type"] == "NotFoundError"

    @pytest.mark.asyncio
    async def test_concurrent_task_updates(self, server, test_task):
        """Test that concurrent updates are handled safely."""
        # Simulate two agents reading the same task
        task_id = test_task["id"]
        version = test_task["version"]

        # Agent A updates
        result1 = await server._tools["cato_update_task"](
            task_id=task_id,
            updates={"name": "Agent A's change"},
            version=version
        )
        assert result1["success"] is True

        # Agent B tries to update with old version (should fail)
        result2 = await server._tools["cato_update_task"](
            task_id=task_id,
            updates={"name": "Agent B's change"},
            version=version  # Old version!
        )
        assert result2["success"] is False
        assert result2["error_type"] == "ConcurrentModificationError"
```

---

**Week 3 Checklist:**
- [ ] Create task tool implemented
- [ ] Update task tool implemented
- [ ] Move task (change status) tool implemented
- [ ] Delete task tool implemented
- [ ] Assign task tool implemented
- [ ] Transaction handling working
- [ ] Optimistic locking implemented
- [ ] 90%+ test coverage for write tools
- [ ] Integration tests pass

**Time Estimate:** 25-30 hours

---

### 🔌 Stage 3: Connect Marcus to Cato (Week 4)

**Goal:** Make Marcus use Cato MCP server instead of Planka

**Think of it like:** Plugging in a new printer - it should work just like the old one

#### Understanding Marcus's KanbanInterface

Marcus has an abstract class called `KanbanInterface` that defines what ANY kanban board must do:

```python
# src/integrations/kanban_interface.py
class KanbanInterface(ABC):
    """Abstract interface for kanban board providers."""

    @abstractmethod
    async def get_all_tasks(self) -> List[Task]:
        """Get all tasks from the board."""
        pass

    @abstractmethod
    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """Create a new task."""
        pass

    @abstractmethod
    async def update_task(self, task_id: str, updates: Dict) -> Task:
        """Update an existing task."""
        pass

    # ... more methods
```

**Current providers:**
- `PlankaKanban` - Talks to Planka
- `LinearKanban` - Talks to Linear
- `GitHubKanban` - Talks to GitHub Projects

**We're adding:**
- `CatoKanban` - Talks to Cato MCP server

#### Step-by-Step Tasks

**3.1 Create CatoClient (Low-Level MCP Communication)**

First, create a client that knows how to call Cato MCP tools:

```python
# src/integrations/cato_client.py
"""
Cato MCP Client - Low-level client for calling Cato MCP tools.
"""
from typing import Dict, Any, List, Optional
from mcp import ClientSession, StdioServerParameters, stdio_client
import logging

logger = logging.getLogger(__name__)


class CatoClient:
    """
    Client for communicating with Cato MCP server.

    This client handles the MCP protocol details and provides
    simple methods to call Cato's MCP tools.

    Examples
    --------
    >>> client = CatoClient()
    >>> projects = await client.list_projects()
    >>> tasks = await client.get_all_tasks(project_id="proj_123")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Cato MCP client.

        Parameters
        ----------
        config : Dict[str, Any], optional
            Configuration for Cato MCP server
            {
                "cato_server_path": "/path/to/cato/backend/mcp_server.py",
                "marcus_db_path": "/path/to/marcus/data/marcus.db"
            }
        """
        self.config = config or {}

        # Path to Cato MCP server script
        self.server_path = self.config.get(
            "cato_server_path",
            "/Users/lwgray/dev/cato/backend/mcp_server.py"
        )

        # Path to Marcus database
        self.db_path = self.config.get(
            "marcus_db_path",
            "/Users/lwgray/dev/marcus/data/marcus.db"
        )

        # MCP server parameters
        self._server_params = StdioServerParameters(
            command="python",
            args=[self.server_path, "--db", self.db_path],
            env=None
        )

    async def _call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call a Cato MCP tool.

        Parameters
        ----------
        tool_name : str
            Name of MCP tool (e.g., "cato_list_projects")
        arguments : Dict[str, Any]
            Tool arguments

        Returns
        -------
        Dict[str, Any]
            Tool response

        Raises
        ------
        Exception
            If MCP call fails
        """
        try:
            # Create new MCP session for this call
            async with stdio_client(self._server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize MCP session
                    await session.initialize()

                    # Call the tool
                    result = await session.call_tool(
                        tool_name,
                        arguments=arguments
                    )

                    # Parse response
                    if hasattr(result, 'content') and result.content:
                        import json
                        return json.loads(result.content[0].text)

                    return {}

        except Exception as e:
            logger.error(f"MCP call failed: {tool_name} - {e}")
            raise

    # ========================================
    # Project Methods
    # ========================================

    async def list_projects(self) -> List[Dict[str, Any]]:
        """
        List all projects.

        Returns
        -------
        List[Dict[str, Any]]
            List of project dictionaries
        """
        result = await self._call_tool("cato_list_projects", {})
        if result.get("success"):
            return result.get("projects", [])
        raise Exception(f"Failed to list projects: {result.get('error')}")

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        Get a specific project by ID.

        Parameters
        ----------
        project_id : str
            Project ID

        Returns
        -------
        Dict[str, Any]
            Project data
        """
        result = await self._call_tool("cato_get_project", {"project_id": project_id})
        if result.get("success"):
            return result.get("project")
        raise Exception(f"Failed to get project: {result.get('error')}")

    # ========================================
    # Task Methods
    # ========================================

    async def get_all_tasks(
        self,
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all tasks, optionally filtered by project.

        Parameters
        ----------
        project_id : str, optional
            Filter by project ID

        Returns
        -------
        List[Dict[str, Any]]
            List of task dictionaries
        """
        args = {"project_id": project_id} if project_id else {}
        result = await self._call_tool("cato_get_all_tasks", args)

        if result.get("success"):
            return result.get("tasks", [])
        raise Exception(f"Failed to get tasks: {result.get('error')}")

    async def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new task.

        Parameters
        ----------
        task_data : Dict[str, Any]
            Task data (project_id, name, description, etc.)

        Returns
        -------
        Dict[str, Any]
            Created task data
        """
        result = await self._call_tool("cato_create_task", task_data)

        if result.get("success"):
            return result.get("task")
        raise Exception(f"Failed to create task: {result.get('error')}")

    async def update_task(
        self,
        task_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing task.

        Parameters
        ----------
        task_id : str
            Task ID to update
        updates : Dict[str, Any]
            Fields to update

        Returns
        -------
        Dict[str, Any]
            Updated task data
        """
        result = await self._call_tool(
            "cato_update_task",
            {"task_id": task_id, "updates": updates}
        )

        if result.get("success"):
            return result.get("task")
        raise Exception(f"Failed to update task: {result.get('error')}")
```

**Key patterns:**
- `_call_tool()` - Handles all MCP communication details
- Public methods (`list_projects()`, `get_all_tasks()`) - Simple wrappers
- Error handling - Raise exceptions if tool call fails
- Session management - Creates new session for each call (reliability)

---

**3.2 Create CatoKanban Provider**

Now implement the KanbanInterface using CatoClient:

```python
# src/integrations/providers/cato_kanban.py
"""
Cato Kanban Provider - Implements KanbanInterface using Cato MCP.
"""
from typing import Dict, Any, List, Optional
from src.integrations.kanban_interface import KanbanInterface
from src.integrations.cato_client import CatoClient
from src.core.models import Task
import logging

logger = logging.getLogger(__name__)


class CatoKanban(KanbanInterface):
    """
    Kanban provider that uses Cato MCP server.

    This provider allows Marcus to use Cato as its kanban board,
    reading and writing tasks via the Cato MCP server.

    Examples
    --------
    >>> # In config_marcus.json
    >>> {
    >>>     "kanban_provider": "cato",
    >>>     "cato_config": {
    >>>         "server_path": "/path/to/cato/backend/mcp_server.py",
    >>>         "db_path": "/path/to/marcus/data/marcus.db"
    >>>     }
    >>> }
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Cato kanban provider.

        Parameters
        ----------
        config : Dict[str, Any]
            Configuration from Marcus config file
        """
        self.config = config
        self.client = CatoClient(config.get("cato_config", {}))
        self.current_project_id: Optional[str] = None

        logger.info("Initialized Cato kanban provider")

    async def get_all_tasks(self) -> List[Task]:
        """
        Get all tasks from current project.

        Returns
        -------
        List[Task]
            List of Task objects
        """
        try:
            # Get raw task data from Cato
            task_dicts = await self.client.get_all_tasks(
                project_id=self.current_project_id
            )

            # Convert to Marcus Task objects
            tasks = [self._dict_to_task(t) for t in task_dicts]

            logger.info(f"Retrieved {len(tasks)} tasks from Cato")
            return tasks

        except Exception as e:
            logger.error(f"Failed to get tasks: {e}")
            return []

    async def get_available_tasks(self) -> List[Task]:
        """
        Get unassigned tasks from current project.

        Returns
        -------
        List[Task]
            List of unassigned Task objects
        """
        all_tasks = await self.get_all_tasks()
        available = [t for t in all_tasks if not t.assigned_to]

        logger.info(f"Found {len(available)} available tasks")
        return available

    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """
        Create a new task in current project.

        Parameters
        ----------
        task_data : Dict[str, Any]
            Task data (name, description, priority, etc.)

        Returns
        -------
        Task
            Created Task object
        """
        # Add current project ID
        task_data["project_id"] = self.current_project_id

        # Create via Cato
        task_dict = await self.client.create_task(task_data)
        task = self._dict_to_task(task_dict)

        logger.info(f"Created task: {task.id} - {task.name}")
        return task

    async def update_task(
        self,
        task_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Task]:
        """
        Update an existing task.

        Parameters
        ----------
        task_id : str
            Task ID to update
        updates : Dict[str, Any]
            Fields to update

        Returns
        -------
        Task or None
            Updated Task object, or None if failed
        """
        try:
            task_dict = await self.client.update_task(task_id, updates)
            task = self._dict_to_task(task_dict)

            logger.info(f"Updated task: {task_id}")
            return task

        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            return None

    async def move_task_to_column(
        self,
        task_id: str,
        column_name: str
    ) -> bool:
        """
        Move task to a different status column.

        Parameters
        ----------
        task_id : str
            Task ID to move
        column_name : str
            New status (TODO, IN_PROGRESS, DONE, BLOCKED)

        Returns
        -------
        bool
            True if successful, False otherwise
        """
        try:
            await self.client.update_task(
                task_id,
                {"status": column_name}
            )

            logger.info(f"Moved task {task_id} to {column_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to move task: {e}")
            return False

    async def set_active_project(self, project_id: str) -> bool:
        """
        Set the active project for this provider.

        Parameters
        ----------
        project_id : str
            Project ID to activate

        Returns
        -------
        bool
            True if successful
        """
        try:
            # Verify project exists
            project = await self.client.get_project(project_id)
            self.current_project_id = project_id

            logger.info(f"Set active project: {project_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to set active project: {e}")
            return False

    def _dict_to_task(self, task_dict: Dict[str, Any]) -> Task:
        """
        Convert dictionary from Cato to Marcus Task object.

        Parameters
        ----------
        task_dict : Dict[str, Any]
            Task dictionary from Cato MCP

        Returns
        -------
        Task
            Marcus Task object
        """
        return Task(
            id=task_dict["id"],
            name=task_dict["name"],
            description=task_dict.get("description", ""),
            status=task_dict.get("status", "TODO"),
            priority=task_dict.get("priority", 3),
            assigned_to=task_dict.get("assigned_to"),
            project_id=task_dict.get("project_id"),
            created_at=task_dict.get("created_at"),
            updated_at=task_dict.get("updated_at"),
            # ... map other fields
        )
```

**Key responsibilities:**
- **Translate:** Convert between Cato dicts and Marcus Task objects
- **Project context:** Track which project we're working on
- **Error handling:** Log errors, return empty lists instead of crashing
- **Clean interface:** Marcus doesn't need to know about MCP

---

**3.3 Register Cato Provider**

Tell Marcus about the new provider:

```python
# src/integrations/providers/__init__.py
from enum import Enum

class KanbanProvider(Enum):
    """Available kanban board providers."""
    PLANKA = "planka"
    LINEAR = "linear"
    GITHUB = "github"
    CATO = "cato"  # Add this


# src/integrations/kanban_factory.py
def create_kanban_provider(config: Dict[str, Any]) -> KanbanInterface:
    """
    Create a kanban provider based on configuration.

    Parameters
    ----------
    config : Dict[str, Any]
        Marcus configuration

    Returns
    -------
    KanbanInterface
        Initialized kanban provider
    """
    provider_name = config.get("kanban_provider", "planka")

    if provider_name == "cato":
        from src.integrations.providers.cato_kanban import CatoKanban
        return CatoKanban(config)

    elif provider_name == "planka":
        from src.integrations.providers.planka_kanban import PlankaKanban
        return PlankaKanban(config)

    # ... other providers

    else:
        raise ValueError(f"Unknown kanban provider: {provider_name}")
```

---

**3.4 Update Marcus Configuration**

Users can now choose Cato in `config_marcus.json`:

```json
{
  "kanban_provider": "cato",
  "cato_config": {
    "server_path": "/Users/lwgray/dev/cato/backend/mcp_server.py",
    "db_path": "/Users/lwgray/dev/marcus/data/marcus.db"
  },
  "active_project_id": "proj_123"
}
```

Or stick with Planka:

```json
{
  "kanban_provider": "planka",
  "planka_config": {
    "board_name": "Marcus Development"
  }
}
```

---

**3.5 Test Marcus with Cato**

Write integration tests that verify the full stack works:

```python
# tests/integration/test_marcus_cato.py
"""
Integration tests for Marcus + Cato MCP integration.
"""
import pytest
from src.integrations.providers.cato_kanban import CatoKanban
from src.marcus_mcp.tools.task import request_next_task

class TestMarcusCatoIntegration:
    """Test Marcus can use Cato as kanban provider."""

    @pytest.mark.asyncio
    async def test_agent_can_request_task(self, marcus_state):
        """Test agent requesting task via Marcus using Cato."""
        # Configure Marcus to use Cato
        marcus_state.config["kanban_provider"] = "cato"
        marcus_state.config["cato_config"] = {
            "db_path": "/path/to/test/marcus.db"
        }

        # Create test project and task in database
        # ... setup code ...

        # Agent requests next task
        result = await request_next_task(
            agent_id="test_agent",
            state=marcus_state
        )

        # Verify agent got a task
        assert result["success"] is True
        assert result["task"] is not None
        assert result["task"]["name"] == "Test task"

    @pytest.mark.asyncio
    async def test_task_progress_updates(self, marcus_state):
        """Test reporting task progress via Cato."""
        # ... test task progress reporting ...

    @pytest.mark.asyncio
    async def test_project_switching(self, marcus_state):
        """Test switching between projects."""
        # ... test project switching ...
```

---

**Week 4 Checklist:**
- [ ] CatoClient implemented
- [ ] CatoKanban provider implemented
- [ ] CATO added to KanbanProvider enum
- [ ] Provider factory updated
- [ ] Configuration schema updated
- [ ] Unit tests for CatoClient (85%+ coverage)
- [ ] Unit tests for CatoKanban (85%+ coverage)
- [ ] Integration tests pass
- [ ] Can switch between Planka and Cato via config
- [ ] All existing Marcus tests still pass

**Time Estimate:** 20-25 hours

---

### 🎨 Stage 4: Improve Cato UI (Week 5)

**Goal:** Update Cato's frontend to support multiple projects and task editing

**Think of it like:** Making the board interactive instead of just a display

#### Current Cato Limitations

Right now, Cato:
- ✅ Shows one project at a time (read-only)
- ❌ Can't switch between projects
- ❌ Can't create or edit tasks
- ❌ Doesn't update in real-time

#### What We're Adding

1. **Project switcher** - Dropdown to select project
2. **Multi-project dashboard** - See multiple projects at once
3. **Task creation** - Add new tasks from UI
4. **Drag-and-drop** - Move tasks between columns
5. **Task editing** - Click to edit task details

#### Step-by-Step Tasks

**4.1 Create Project Switcher Component**

```typescript
// cato/frontend/src/components/ProjectSwitcher.tsx
import React, { useState, useEffect } from 'react';

interface Project {
  id: string;
  name: string;
  description: string;
  status: string;
}

interface ProjectSwitcherProps {
  currentProjectId: string;
  onProjectChange: (projectId: string) => void;
}

export const ProjectSwitcher: React.FC<ProjectSwitcherProps> = ({
  currentProjectId,
  onProjectChange
}) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  // Load projects when component mounts
  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      // Call Cato backend API
      const response = await fetch('http://localhost:4301/api/projects');
      const data = await response.json();
      setProjects(data.projects);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load projects:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return <div>Loading projects...</div>;
  }

  return (
    <div className="project-switcher">
      <label htmlFor="project-select">Project:</label>
      <select
        id="project-select"
        value={currentProjectId}
        onChange={(e) => onProjectChange(e.target.value)}
      >
        {projects.map((project) => (
          <option key={project.id} value={project.id}>
            {project.name}
          </option>
        ))}
      </select>
    </div>
  );
};
```

**How it works:**
1. `useEffect()` - Runs when component loads, fetches projects
2. `fetchProjects()` - Calls backend API to get project list
3. `<select>` - Dropdown showing all projects
4. `onChange` - When user selects project, calls parent component

---

**4.2 Add Backend API Endpoints**

```python
# cato/backend/api.py
from fastapi import FastAPI, HTTPException
from typing import Dict, Any, List
from .aggregator import Aggregator

app = FastAPI()
aggregator = Aggregator()

@app.get("/api/projects")
async def list_projects() -> Dict[str, Any]:
    """
    List all projects.

    Returns
    -------
    Dict[str, Any]
        {"projects": [...]}
    """
    try:
        # Get projects from Marcus database
        projects = aggregator.get_projects()
        return {"projects": projects}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str) -> Dict[str, Any]:
    """
    Get a specific project.

    Parameters
    ----------
    project_id : str
        Project ID

    Returns
    -------
    Dict[str, Any]
        {"project": {...}}
    """
    project = aggregator.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project}

@app.get("/api/projects/{project_id}/tasks")
async def get_project_tasks(project_id: str) -> Dict[str, Any]:
    """
    Get all tasks for a project.

    Parameters
    ----------
    project_id : str
        Project ID

    Returns
    -------
    Dict[str, Any]
        {"tasks": [...]}
    """
    tasks = aggregator.get_tasks(project_id=project_id)
    return {"tasks": tasks}

@app.post("/api/projects/{project_id}/tasks")
async def create_task(
    project_id: str,
    task_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a new task.

    Parameters
    ----------
    project_id : str
        Project to add task to
    task_data : Dict[str, Any]
        Task details

    Returns
    -------
    Dict[str, Any]
        {"task": {...}}
    """
    task_data["project_id"] = project_id
    task = aggregator.create_task(task_data)
    return {"task": task}

@app.put("/api/tasks/{task_id}")
async def update_task(
    task_id: str,
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update a task.

    Parameters
    ----------
    task_id : str
        Task ID
    updates : Dict[str, Any]
        Fields to update

    Returns
    -------
    Dict[str, Any]
        {"task": {...}}
    """
    task = aggregator.update_task(task_id, updates)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": task}
```

---

**4.3 Add Drag-and-Drop**

Use `react-beautiful-dnd` library for drag-and-drop:

```typescript
// cato/frontend/src/components/TaskBoard.tsx
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';

export const TaskBoard: React.FC = () => {
  const [columns, setColumns] = useState({
    TODO: [],
    IN_PROGRESS: [],
    DONE: []
  });

  const onDragEnd = async (result) => {
    if (!result.destination) return;

    const { source, destination, draggableId } = result;

    // If dropped in same column, do nothing
    if (source.droppableId === destination.droppableId) return;

    // Update UI immediately (optimistic update)
    const newColumns = { ...columns };
    const task = newColumns[source.droppableId].find(t => t.id === draggableId);
    newColumns[source.droppableId] = newColumns[source.droppableId].filter(
      t => t.id !== draggableId
    );
    newColumns[destination.droppableId].push(task);
    setColumns(newColumns);

    // Update backend
    try {
      await fetch(`http://localhost:4301/api/tasks/${draggableId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: destination.droppableId })
      });
    } catch (error) {
      console.error('Failed to update task:', error);
      // Revert UI on error
      setColumns(columns);
    }
  };

  return (
    <DragDropContext onDragEnd={onDragEnd}>
      {Object.entries(columns).map(([columnId, tasks]) => (
        <Droppable droppableId={columnId} key={columnId}>
          {(provided) => (
            <div
              ref={provided.innerRef}
              {...provided.droppableProps}
              className="task-column"
            >
              <h2>{columnId}</h2>
              {tasks.map((task, index) => (
                <Draggable draggableId={task.id} index={index} key={task.id}>
                  {(provided) => (
                    <div
                      ref={provided.innerRef}
                      {...provided.draggableProps}
                      {...provided.dragHandleProps}
                      className="task-card"
                    >
                      <h3>{task.name}</h3>
                      <p>{task.description}</p>
                    </div>
                  )}
                </Draggable>
              ))}
              {provided.placeholder}
            </div>
          )}
        </Droppable>
      ))}
    </DragDropContext>
  );
};
```

**What happens:**
1. User drags task from TODO to IN_PROGRESS
2. UI updates immediately (feels fast!)
3. Backend call updates database
4. If backend fails, UI reverts (error handling)

---

**4.4 Add Task Creation Modal**

```typescript
// cato/frontend/src/components/TaskCreateModal.tsx
import React, { useState } from 'react';
import { Modal, Button, Form } from 'react-bootstrap';

interface TaskCreateModalProps {
  projectId: string;
  show: boolean;
  onClose: () => void;
  onTaskCreated: (task: any) => void;
}

export const TaskCreateModal: React.FC<TaskCreateModalProps> = ({
  projectId,
  show,
  onClose,
  onTaskCreated
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (!name.trim()) {
      setError('Task name is required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(
        `http://localhost:4301/api/projects/${projectId}/tasks`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, description, priority })
        }
      );

      if (!response.ok) {
        throw new Error('Failed to create task');
      }

      const data = await response.json();
      onTaskCreated(data.task);

      // Reset form
      setName('');
      setDescription('');
      setPriority(3);
      onClose();

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal show={show} onHide={onClose}>
      <Modal.Header closeButton>
        <Modal.Title>Create New Task</Modal.Title>
      </Modal.Header>

      <Modal.Body>
        <Form onSubmit={handleSubmit}>
          <Form.Group>
            <Form.Label>Task Name *</Form.Label>
            <Form.Control
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter task name"
              required
            />
          </Form.Group>

          <Form.Group>
            <Form.Label>Description</Form.Label>
            <Form.Control
              as="textarea"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter task description"
            />
          </Form.Group>

          <Form.Group>
            <Form.Label>Priority (1-5)</Form.Label>
            <Form.Control
              type="number"
              min="1"
              max="5"
              value={priority}
              onChange={(e) => setPriority(parseInt(e.target.value))}
            />
          </Form.Group>

          {error && <div className="alert alert-danger">{error}</div>}

          <Button type="submit" disabled={loading}>
            {loading ? 'Creating...' : 'Create Task'}
          </Button>
        </Form>
      </Modal.Body>
    </Modal>
  );
};
```

---

**Week 5 Checklist:**
- [ ] ProjectSwitcher component created
- [ ] Backend API endpoints implemented
- [ ] Drag-and-drop working
- [ ] Task creation modal working
- [ ] Task editing modal working
- [ ] Multi-project dashboard view
- [ ] Real-time updates (WebSocket or polling)
- [ ] Frontend tests written (React Testing Library)
- [ ] E2E tests written (Playwright)
- [ ] 80%+ test coverage for new components

**Time Estimate:** 25-30 hours

---

### 🔄 Stage 5: Migration & Setup Tools (Week 5-6)

**Goal:** Make it easy for users to switch from Planka to Cato

**Think of it like:** Moving from one house to another - need to pack, move, and unpack

#### What We're Building

1. **`marcus migrate`** - Command to migrate data from Planka to Cato
2. **`marcus start`** - One command to start everything
3. **Setup wizard** - Interactive first-run experience
4. **Documentation** - Step-by-step guides

#### Step-by-Step Tasks

**5.1 Create Migration Command**

```python
# src/cli/commands/migrate.py
"""
Marcus migration command - Migrate data between kanban providers.
"""
import click
import asyncio
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


@click.command()
@click.option('--from', 'source_provider',
              type=click.Choice(['planka', 'linear', 'github']),
              required=True,
              help='Source kanban provider to migrate from')
@click.option('--to', 'dest_provider',
              type=click.Choice(['cato', 'planka']),
              default='cato',
              help='Destination kanban provider (default: cato)')
@click.option('--project', 'project_id',
              help='Specific project to migrate (default: all)')
@click.option('--dry-run', is_flag=True,
              help='Show what would be migrated without doing it')
@click.option('--backup/--no-backup', default=True,
              help='Create backup before migration (default: yes)')
def migrate(
    source_provider: str,
    dest_provider: str,
    project_id: str | None,
    dry_run: bool,
    backup: bool
) -> None:
    """
    Migrate data from one kanban provider to another.

    Examples:

        # Migrate all data from Planka to Cato
        marcus migrate --from planka --to cato

        # Migrate specific project
        marcus migrate --from planka --to cato --project proj_123

        # See what would be migrated (don't actually do it)
        marcus migrate --from planka --to cato --dry-run
    """
    click.echo(f"Migrating from {source_provider} to {dest_provider}...")

    asyncio.run(run_migration(
        source_provider,
        dest_provider,
        project_id,
        dry_run,
        backup
    ))


async def run_migration(
    source: str,
    dest: str,
    project_id: str | None,
    dry_run: bool,
    backup: bool
) -> None:
    """
    Execute the migration.

    Parameters
    ----------
    source : str
        Source provider name
    dest : str
        Destination provider name
    project_id : str | None
        Specific project or None for all
    dry_run : bool
        If True, don't actually migrate
    backup : bool
        If True, create backup first
    """
    # Step 1: Create backup
    if backup and not dry_run:
        click.echo("Creating backup...")
        backup_path = await create_backup()
        click.echo(f"Backup saved to: {backup_path}")

    # Step 2: Load source provider
    click.echo(f"Connecting to {source}...")
    source_kanban = create_kanban_provider({"kanban_provider": source})

    # Step 3: Load destination provider
    click.echo(f"Connecting to {dest}...")
    dest_kanban = create_kanban_provider({"kanban_provider": dest})

    # Step 4: Fetch data from source
    click.echo("Fetching data from source...")
    projects = await fetch_projects(source_kanban, project_id)

    # Show summary
    total_tasks = sum(len(p.tasks) for p in projects)
    click.echo(f"\nFound {len(projects)} projects with {total_tasks} tasks")

    if dry_run:
        click.echo("\n[DRY RUN] Would migrate:")
        for project in projects:
            click.echo(f"  - {project.name} ({len(project.tasks)} tasks)")
        click.echo("\nRun without --dry-run to perform migration")
        return

    # Step 5: Confirm with user
    if not click.confirm(f"\nMigrate {len(projects)} projects to {dest}?"):
        click.echo("Migration cancelled")
        return

    # Step 6: Migrate data
    click.echo("\nMigrating...")
    with click.progressbar(projects, label='Projects') as bar:
        for project in bar:
            try:
                await migrate_project(project, dest_kanban)
            except Exception as e:
                logger.error(f"Failed to migrate {project.name}: {e}")
                click.echo(f"\n  ERROR: {project.name} failed")

    # Step 7: Verify migration
    click.echo("\nVerifying migration...")
    success = await verify_migration(projects, dest_kanban)

    if success:
        click.echo(f"\n✓ Migration complete! All {len(projects)} projects migrated.")
        click.echo(f"\nUpdate your config to use {dest}:")
        click.echo(f'  "kanban_provider": "{dest}"')
    else:
        click.echo(f"\n⚠ Migration completed with errors. Check logs.")
        click.echo(f"Backup available at: {backup_path}")


async def migrate_project(project: Any, dest_kanban: Any) -> None:
    """
    Migrate a single project.

    Parameters
    ----------
    project : Any
        Project data to migrate
    dest_kanban : Any
        Destination kanban provider
    """
    # Create project in destination
    await dest_kanban.create_project({
        "name": project.name,
        "description": project.description,
        "status": project.status
    })

    # Migrate all tasks
    for task in project.tasks:
        await dest_kanban.create_task({
            "project_id": project.id,
            "name": task.name,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "assigned_to": task.assigned_to
        })

    # Migrate decisions/artifacts
    for decision in project.decisions:
        await dest_kanban.add_decision({
            "task_id": decision.task_id,
            "content": decision.content,
            "timestamp": decision.timestamp
        })
```

**User experience:**
```bash
$ marcus migrate --from planka --to cato

Migrating from planka to cato...
Creating backup...
Backup saved to: /Users/lwgray/.marcus/backups/2025-11-09-143022.db

Connecting to planka...
Connecting to cato...
Fetching data from source...

Found 3 projects with 47 tasks
  - Marcus Development (15 tasks)
  - Cato Integration (22 tasks)
  - Test Project (10 tasks)

Migrate 3 projects to cato? [y/N]: y

Migrating...
Projects [####################################] 3/3

Verifying migration...

✓ Migration complete! All 3 projects migrated.

Update your config to use cato:
  "kanban_provider": "cato"
```

---

**5.2 Create `marcus start` Command**

```python
# src/cli/commands/start.py
"""
Marcus start command - Start Marcus and Cato with one command.
"""
import click
import subprocess
import time
import sys

@click.command()
@click.option('--port', default=5173, help='Cato frontend port')
@click.option('--api-port', default=4301, help='Cato backend port')
@click.option('--no-ui', is_flag=True, help='Start without Cato UI')
def start(port: int, api_port: int, no_ui: bool) -> None:
    """
    Start Marcus and Cato in one command.

    This command:
    1. Checks if Cato is installed
    2. Starts Cato MCP server
    3. Starts Cato frontend (unless --no-ui)
    4. Starts Marcus MCP server

    Examples:

        # Start everything
        marcus start

        # Start without UI (headless)
        marcus start --no-ui
    """
    click.echo("Starting Marcus + Cato...")

    processes = []

    try:
        # Step 1: Check Cato installation
        if not check_cato_installed():
            click.echo("Cato not found. Install with:")
            click.echo("  pip install marcus-cato")
            sys.exit(1)

        # Step 2: Start Cato MCP server
        click.echo("Starting Cato MCP server...")
        cato_mcp = subprocess.Popen(
            ["python", "-m", "cato.backend.mcp_server"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append(("Cato MCP", cato_mcp))
        time.sleep(2)  # Wait for startup

        # Step 3: Start Cato frontend (if requested)
        if not no_ui:
            click.echo(f"Starting Cato UI on http://localhost:{port}")
            cato_ui = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd="/path/to/cato/frontend",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            processes.append(("Cato UI", cato_ui))
            time.sleep(3)

        # Step 4: Start Marcus MCP server
        click.echo("Starting Marcus MCP server...")
        marcus = subprocess.Popen(
            ["python", "-m", "src.marcus_mcp.server"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append(("Marcus", marcus))
        time.sleep(2)

        # Success!
        click.echo("\n✓ All services started!")
        if not no_ui:
            click.echo(f"\n  Cato UI: http://localhost:{port}")
        click.echo("  Marcus MCP: Running")
        click.echo("\nPress Ctrl+C to stop all services")

        # Wait for Ctrl+C
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            click.echo("\n\nStopping services...")
            for name, proc in processes:
                click.echo(f"  Stopping {name}...")
                proc.terminate()
                proc.wait()
            click.echo("All services stopped")

    except Exception as e:
        click.echo(f"\nError: {e}")
        # Clean up processes
        for name, proc in processes:
            proc.terminate()
        sys.exit(1)
```

**User experience:**
```bash
$ marcus start

Starting Marcus + Cato...
Starting Cato MCP server...
Starting Cato UI on http://localhost:5173
Starting Marcus MCP server...

✓ All services started!

  Cato UI: http://localhost:5173
  Marcus MCP: Running

Press Ctrl+C to stop all services
```

---

**5.3 Create Setup Wizard**

```python
# src/cli/commands/init.py
"""
Marcus initialization wizard - Interactive first-run setup.
"""
import click
import json
from pathlib import Path

@click.command()
def init() -> None:
    """
    Interactive setup wizard for Marcus.

    Guides you through:
    - Choosing kanban provider
    - Configuring provider settings
    - Creating first project
    """
    click.echo("Welcome to Marcus! Let's get you set up.\n")

    # Step 1: Choose provider
    click.echo("Which kanban board do you want to use?")
    provider = click.prompt(
        "Choose provider",
        type=click.Choice(['cato', 'planka', 'linear', 'github']),
        default='cato'
    )

    config = {"kanban_provider": provider}

    # Step 2: Provider-specific config
    if provider == "cato":
        click.echo("\n✓ Cato selected - No Docker required!")
        click.echo("Cato will use Marcus's existing SQLite database.")

        db_path = click.prompt(
            "Marcus database path",
            default="/Users/lwgray/dev/marcus/data/marcus.db"
        )
        config["cato_config"] = {"db_path": db_path}

    elif provider == "planka":
        click.echo("\nPlanka requires Docker. Make sure you have:")
        click.echo("  - Docker Desktop installed and running")
        click.echo("  - Planka running via docker-compose")

        board_name = click.prompt("Planka board name")
        config["planka_config"] = {"board_name": board_name}

    # Step 3: Create first project
    if click.confirm("\nCreate your first project?"):
        project_name = click.prompt("Project name")
        project_desc = click.prompt("Project description", default="")

        # Will create project after config is saved
        config["first_project"] = {
            "name": project_name,
            "description": project_desc
        }

    # Step 4: Save config
    config_path = Path("config_marcus.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    click.echo(f"\n✓ Configuration saved to {config_path}")

    # Step 5: Next steps
    click.echo("\nYou're all set! Next steps:")
    click.echo("  1. Start Marcus:")
    click.echo("     $ marcus start")
    click.echo("\n  2. Open Cato UI:")
    click.echo("     http://localhost:5173")
    click.echo("\n  3. Check out the docs:")
    click.echo("     https://marcus.dev/docs/getting-started")
```

**User experience:**
```bash
$ marcus init

Welcome to Marcus! Let's get you set up.

Which kanban board do you want to use?
Choose provider [cato/planka/linear/github] (cato): cato

✓ Cato selected - No Docker required!
Cato will use Marcus's existing SQLite database.
Marcus database path [/Users/lwgray/dev/marcus/data/marcus.db]:

Create your first project? [y/N]: y
Project name: My Awesome App
Project description: Building an awesome application

✓ Configuration saved to config_marcus.json

You're all set! Next steps:
  1. Start Marcus:
     $ marcus start

  2. Open Cato UI:
     http://localhost:5173

  3. Check out the docs:
     https://marcus.dev/docs/getting-started
```

---

**Week 5-6 Checklist:**
- [ ] `marcus migrate` command implemented
- [ ] Migration validation (verify no data loss)
- [ ] `marcus start` command implemented
- [ ] `marcus init` setup wizard implemented
- [ ] Backup/restore functionality
- [ ] Health checks for all services
- [ ] Cross-platform testing (Mac, Linux, Windows)
- [ ] User documentation written
- [ ] Video tutorial recorded (5 minutes)

**Time Estimate:** 20-25 hours

---

### ✅ Stage 6: Testing & Release (Week 6)

**Goal:** Make sure everything works, fix bugs, release to users

**Think of it like:** Quality control before shipping a product

#### Testing Checklist

**Unit Tests** (Already done in previous stages)
- [ ] All Cato MCP tools (read & write)
- [ ] CatoClient methods
- [ ] CatoKanban provider
- [ ] CLI commands
- [ ] Frontend components

**Integration Tests**
- [ ] Marcus → Cato MCP → SQLite (full stack)
- [ ] Agent requests task via Marcus using Cato
- [ ] Task progress updates via Cato
- [ ] Project switching
- [ ] Concurrent operations

**End-to-End Tests**
- [ ] Complete workflow: Create project → Add tasks → Assign to agent → Complete tasks
- [ ] Migration: Planka → Cato with data verification
- [ ] Multi-user scenario: 3 agents working on same project
- [ ] UI workflows: Drag-drop, create task, edit task

**Performance Tests**
- [ ] 1000+ tasks: Query performance <100ms
- [ ] 10+ projects: UI remains responsive
- [ ] Concurrent writes: 50 ops/sec
- [ ] Memory usage: <200MB for typical workload

**Security Tests**
- [ ] SQL injection attempts blocked
- [ ] XSS attempts in task names/descriptions
- [ ] Input validation on all APIs
- [ ] No secrets in logs

**Cross-Platform Tests**
- [ ] Mac (Intel + Apple Silicon)
- [ ] Linux (Ubuntu 22.04+)
- [ ] Windows 11 with WSL2

---

#### Bug Fix Process

1. **Triage bugs** by severity:
   - **P0 (Critical)**: Blocks all users, data loss - Fix immediately
   - **P1 (High)**: Blocks many users - Fix this week
   - **P2 (Medium)**: Minor issues - Fix before release
   - **P3 (Low)**: Nice to have - Defer to next release

2. **Fix workflow**:
   ```
   1. Write test that reproduces bug
   2. Fix the bug
   3. Verify test passes
   4. Run full test suite (ensure no regressions)
   5. Commit with bug number: "fix: Handle empty task list (closes #42)"
   ```

3. **Regression testing**:
   - Run all existing tests after each fix
   - Check related features (e.g., if fixing task creation, test task updates too)

---

#### Documentation Checklist

**User Documentation**
- [ ] Getting Started Guide (5-minute quick start)
- [ ] Configuration Reference (all options explained)
- [ ] Migration Guide (Planka → Cato)
- [ ] Troubleshooting Guide (common issues)
- [ ] FAQ (frequently asked questions)

**Developer Documentation**
- [ ] Architecture Overview (how components fit together)
- [ ] API Reference (all MCP tools documented)
- [ ] Contributing Guide (how to add features)
- [ ] Testing Guide (how to run tests)

**Video Tutorials**
- [ ] 5-minute setup (recorded screen demo)
- [ ] Task management basics
- [ ] Multi-project workflow

---

#### Release Process

**1. Version Bump**
```bash
# Update version in setup.py, package.json
# Version format: MAJOR.MINOR.PATCH (e.g., 2.0.0)
```

**2. Create Changelog**
```markdown
# Changelog

## [2.0.0] - 2025-12-23

### Added
- Cato MCP integration (no Docker required!)
- Multi-project support in Cato UI
- Drag-and-drop task management
- `marcus migrate` command
- `marcus start` single-command startup
- Interactive setup wizard

### Changed
- Default kanban provider is now Cato (Planka still supported)
- Improved task query performance (3x faster)

### Fixed
- Concurrent task updates now use optimistic locking
- Project switching preserves filter state

### Breaking Changes
- Configuration format updated (see migration guide)
```

**3. Create Release Branch**
```bash
git checkout develop
git pull
git checkout -b release/2.0.0
```

**4. Final Testing**
- Run full test suite on all platforms
- Manual testing of key workflows
- Load testing with large datasets

**5. Merge to Main**
```bash
git checkout main
git merge release/2.0.0
git tag v2.0.0
git push origin main --tags
```

**6. Publish Packages**
```bash
# Python package
python setup.py sdist bdist_wheel
twine upload dist/*

# NPM package (Cato)
cd cato/frontend
npm publish
```

**7. Announce Release**
- GitHub release with changelog
- Blog post
- Social media
- Email to users list

---

**Week 6 Checklist:**
- [ ] All tests passing (90%+ coverage)
- [ ] Zero P0/P1 bugs
- [ ] Documentation complete
- [ ] Video tutorial recorded
- [ ] Release notes written
- [ ] Packages published
- [ ] Release announced

**Time Estimate:** 20-25 hours

---

## Glossary: Important Terms Explained

### Technical Terms

**MCP (Model Context Protocol)**
- A standard way for AI tools to talk to each other
- Like USB-C for AI tools - one connector works with everything
- Marcus uses MCP to talk to different kanban boards

**SQLite**
- A database stored in a single file (like an Excel file)
- Marcus already uses SQLite to store data
- Fast, reliable, no server needed

**KanbanInterface**
- An abstract class (blueprint) in Marcus
- Defines what every kanban provider must do
- Makes it easy to add new providers (just follow the blueprint)

**Provider**
- A specific implementation of KanbanInterface
- Examples: PlankaKanban, CatoKanban, LinearKanban
- Marcus can use any provider that implements the interface

**Transaction**
- A group of database operations that succeed or fail together
- Like a shopping cart: either all items checkout or none do
- Prevents partial updates (data corruption)

**Optimistic Locking**
- Strategy for handling concurrent edits
- Each record has a version number
- Update only succeeds if version matches (no one else changed it)

**Async/Await**
- Python pattern for concurrent operations
- `async def` defines an async function
- `await` pauses until operation completes
- Allows multiple operations without blocking

**Fixture (Testing)**
- Test data or setup code used by multiple tests
- Defined once, reused everywhere
- Example: `@pytest.fixture def test_database()`

### Architecture Terms

**Read-Only vs Write Operations**
- **Read**: Just looks at data (SELECT queries)
- **Write**: Changes data (INSERT, UPDATE, DELETE)
- Writes are harder: validation, errors, concurrency

**Frontend vs Backend**
- **Frontend**: What users see (React UI, runs in browser)
- **Backend**: Logic and data (Python/FastAPI, runs on server)
- **API**: How frontend and backend talk (HTTP requests)

**Integration Testing**
- Tests that verify multiple components work together
- Example: Marcus → Cato MCP → SQLite (full chain)
- Catches issues unit tests miss

**End-to-End (E2E) Testing**
- Tests complete user workflows
- Example: User creates project, adds tasks, completes them
- Simulates real usage

**Migration**
- Moving data from one system to another
- Example: Planka → Cato
- Must preserve all data (no loss)

### Development Terms

**Feature Branch**
- A separate copy of code for developing a feature
- Work independently without affecting main code
- Merge when done

**Pull Request (PR)**
- Request to merge your branch into main
- Others review code before merging
- Ensures quality

**CI/CD (Continuous Integration/Continuous Deployment)**
- Automated testing and deployment
- Tests run automatically on every commit
- Catches bugs early

**Test Coverage**
- Percentage of code tested by unit tests
- 85%+ is good
- Higher coverage = more confidence

---

## How to Get Started

### Prerequisites

Before starting, make sure you have:

1. **Python 3.10+** installed
   ```bash
   python --version  # Should show 3.10 or higher
   ```

2. **Node.js 18+** (for Cato frontend)
   ```bash
   node --version  # Should show 18.0 or higher
   ```

3. **Git** for version control
   ```bash
   git --version
   ```

4. **Marcus repository** cloned
   ```bash
   git clone https://github.com/lwgray/marcus.git
   cd marcus
   ```

5. **Cato repository** cloned
   ```bash
   git clone https://github.com/lwgray/cato.git
   cd cato
   ```

6. **Understanding of**:
   - Basic Python (functions, classes, async/await)
   - Basic SQL (SELECT, INSERT, UPDATE)
   - Basic React (components, hooks) - for frontend work
   - Git basics (clone, branch, commit, push)

### Development Environment Setup

```bash
# 1. Create Python virtual environment
cd /Users/lwgray/dev/marcus
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install Marcus dependencies
pip install -e .
pip install -r requirements-dev.txt  # Testing tools

# 3. Install Cato dependencies
cd /Users/lwgray/dev/cato
npm install

# 4. Verify everything works
python -m pytest tests/unit/  # Run some tests
marcus --version  # Check Marcus CLI
```

### Recommended Tools

- **VS Code** - IDE with Python and React support
- **DBeaver** - SQL database viewer (for examining SQLite)
- **Postman** - API testing tool
- **pytest** - Python testing framework
- **React DevTools** - Browser extension for debugging React

### Getting Help

When stuck:

1. **Read the code** - Look at similar implementations (PlankaKanban)
2. **Check the docs** - This plan, Marcus README, MCP docs
3. **Ask questions** - GitHub Discussions, team chat
4. **Write a test** - Often helps understand how something works
5. **Take a break** - Fresh eyes help solve problems

### Next Steps

1. **Read this plan thoroughly** - Understand the big picture
2. **Set up development environment** - Get everything running locally
3. **Start Stage 0** - Create feature branch, explore database
4. **Take it one task at a time** - Don't try to do everything at once
5. **Test frequently** - Write tests, run tests, verify your work

---

## Summary: What We're Building

We're making Marcus easier to use by:

1. **Replacing Planka** (requires Docker) with **Cato** (no Docker)
2. **Reducing setup time** from 30+ minutes to <5 minutes
3. **Adding multi-project support** so users can manage multiple projects
4. **Creating migration tools** so existing users can switch easily
5. **Maintaining backward compatibility** so Planka still works if users want it

**Timeline:** 6 weeks from planning to release
**Approach:** Incremental stages, extensive testing, clear documentation
**Goal:** Make Marcus accessible to beginners while keeping power user features

---

**Questions or Feedback?**
- Open an issue: https://github.com/lwgray/marcus/issues
- Join discussions: https://github.com/lwgray/marcus/discussions
- Email: lwgray@example.com

Good luck! 🚀
