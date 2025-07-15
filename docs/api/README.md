# 🔌 Marcus API Documentation

Marcus provides APIs through the **MCP (Model Context Protocol)** interface, specifically designed for AI agent coordination.

## 🎯 **Quick Reference**

### **Core Agent Tools**
| Tool | Purpose | Usage |
|------|---------|-------|
| `register_agent` | Register agent capabilities | Called once at startup |
| `request_next_task` | Get next task assignment | Called continuously in work loop |
| `report_task_progress` | Update task progress | Called at 25%, 50%, 75%, 100% |
| `report_blocker` | Report blockers for AI help | Called when stuck |
| `get_task_context` | Get context for dependencies | Called before starting work |
| `log_decision` | Document architectural choices | Called when making decisions |

### **Project Management Tools**
| Tool | Purpose | Usage |
|------|---------|-------|
| `create_project` | Generate project from description | Human-initiated project creation |
| `get_project_status` | Get overall project health | Status monitoring |
| `get_agent_status` | Get specific agent status | Agent monitoring |

---

## 🤖 **Agent Workflow API**

### **1. Agent Registration**
```python
# Register agent with Marcus
register_agent(
    agent_id="claude-001",
    name="Claude Backend Developer",
    skills=["python", "fastapi", "postgresql", "testing"]
)
```

**Parameters:**
- `agent_id` (string): Unique identifier for the agent
- `name` (string): Human-readable agent name
- `skills` (array): List of technologies/skills the agent can handle

**Response:**
```json
{
  "success": true,
  "agent_id": "claude-001",
  "assigned_branch": "agent-claude-001"
}
```

### **2. Task Request & Assignment**
```python
# Request next task from Marcus
task = request_next_task(agent_id="claude-001")
```

**Response (with task):**
```json
{
  "success": true,
  "task": {
    "id": "task-001",
    "title": "Create User model",
    "description": "Implement User model with authentication...",
    "priority": "high",
    "labels": ["backend", "database"],
    "dependencies": ["task-setup"],
    "context": {
      "previous_implementations": [],
      "architectural_decisions": [],
      "recommended_patterns": []
    },
    "instructions": "# Implementation Context\n..."
  }
}
```

**Response (no tasks):**
```json
{
  "success": true,
  "task": null,
  "message": "No tasks available"
}
```

### **3. Progress Reporting**
```python
# Report progress at milestones
report_task_progress(
    agent_id="claude-001",
    task_id="task-001",
    progress=50,
    status="in_progress",
    message="Implemented User model, working on authentication"
)
```

**Parameters:**
- `agent_id` (string): Your agent ID
- `task_id` (string): Current task ID
- `progress` (integer): Progress percentage (0-100)
- `status` (string): `"in_progress"`, `"completed"`, `"blocked"`
- `message` (string): Detailed progress description

### **4. Blocker Reporting**
```python
# Report blockers for AI assistance
suggestions = report_blocker(
    agent_id="claude-001",
    task_id="task-001",
    blocker_description="Database connection failing with SSL error",
    severity="high"
)
```

**Response:**
```json
{
  "success": true,
  "suggestions": [
    "Try adding sslmode=require to connection string",
    "Check if SSL certificates are properly configured",
    "Consider using connection pooling"
  ],
  "escalated": false
}
```

### **5. Context Retrieval**
```python
# Get context for dependent tasks
context = get_task_context(task_id="task-setup")
```

**Response:**
```json
{
  "success": true,
  "context": {
    "task_id": "task-setup",
    "implementation_summary": "Created FastAPI project structure with PostgreSQL",
    "endpoints_created": ["/health", "/api/v1"],
    "models_created": ["BaseModel"],
    "decisions": [
      {
        "what": "Use FastAPI over Flask",
        "why": "Better async support and auto-documentation",
        "impact": "All API endpoints will follow FastAPI patterns"
      }
    ],
    "files_modified": ["main.py", "models.py", "requirements.txt"]
  }
}
```

### **6. Decision Logging**
```python
# Log architectural decisions
log_decision(
    agent_id="claude-001",
    task_id="task-001",
    decision="I chose PostgreSQL because we need ACID transactions. This affects all data models."
)
```

---

## 🏗️ **Project Management API**

### **Project Creation**
```python
# Create project from natural language description
project = create_project(
    description="Build a todo app with React frontend and FastAPI backend",
    complexity="medium"
)
```

**Response:**
```json
{
  "success": true,
  "project": {
    "id": "proj-001",
    "name": "Todo App Development",
    "tasks_created": 12,
    "estimated_duration": "2-3 weeks",
    "technologies": ["React", "FastAPI", "PostgreSQL"]
  }
}
```

### **Status Monitoring**
```python
# Get overall project status
status = get_project_status()
```

**Response:**
```json
{
  "success": true,
  "project": {
    "total_tasks": 15,
    "completed_tasks": 8,
    "in_progress_tasks": 2,
    "blocked_tasks": 1,
    "active_agents": 3,
    "estimated_completion": "2024-02-15",
    "health_score": 85
  }
}
```

---

## 📋 **Data Models**

### **Task Object**
```json
{
  "id": "task-001",
  "title": "Create User Authentication",
  "description": "Implement JWT-based user authentication...",
  "status": "todo|in_progress|completed|blocked",
  "priority": "low|medium|high|urgent",
  "assignee": "claude-001",
  "labels": ["backend", "security", "api"],
  "dependencies": ["task-setup", "task-database"],
  "created_at": "2024-01-15T10:00:00Z",
  "due_date": "2024-01-20T17:00:00Z",
  "context": { /* Rich context object */ }
}
```

### **Agent Object**
```json
{
  "id": "claude-001",
  "name": "Claude Backend Developer",
  "status": "idle|working|blocked",
  "skills": ["python", "fastapi", "postgresql"],
  "current_task": "task-001",
  "completed_tasks": 5,
  "success_rate": 95.2,
  "branch": "agent-claude-001"
}
```

---

## 🔥 **Advanced Features**

### **Context-Aware Task Assignment**
Marcus automatically provides rich context with each task:

- **Previous Implementations** - What other agents have built
- **Architectural Decisions** - Design choices that affect your work
- **Recommended Patterns** - Suggested approaches based on learning
- **Dependencies** - Detailed info about prerequisite tasks

### **Intelligent Error Recovery**
When you report blockers, Marcus:

1. **Analyzes the error** using AI
2. **Suggests specific solutions** based on context
3. **Escalates to human** if critical
4. **Learns from resolution** for future issues

### **Continuous Learning**
Marcus learns from every project:

- **Successful patterns** are identified and recommended
- **Common errors** are predicted and prevented
- **Agent preferences** are learned and accommodated
- **Task estimation** improves over time

---

## 🚨 **Error Handling**

### **Common Error Responses**
```json
{
  "success": false,
  "error": {
    "type": "TaskNotFound",
    "message": "Task task-999 does not exist",
    "code": "TASK_NOT_FOUND"
  }
}
```

### **Error Types**
- `AGENT_NOT_REGISTERED` - Agent must register first
- `TASK_NOT_FOUND` - Invalid task ID
- `INVALID_STATUS` - Invalid status value
- `DEPENDENCY_NOT_MET` - Required dependency not completed
- `PERMISSION_DENIED` - Agent not authorized for task

---

## 🔧 **Integration Examples**

### **Claude Code Integration**
```bash
# Add Marcus to Claude Code
claude mcp add /path/to/python /path/to/marcus/src/marcus_mcp/server.py

# Use Agent_prompt.md as system prompt for continuous work loop
```

### **Python Client Example**
```python
from marcus.worker.client import WorkerMCPClient

async def agent_workflow():
    client = WorkerMCPClient()

    # Register
    await client.register_agent(
        agent_id="my-agent",
        name="Python Developer",
        skills=["python", "fastapi", "testing"]
    )

    # Continuous work loop
    while True:
        task = await client.request_next_task("my-agent")
        if not task:
            break

        # Work on task...
        await client.report_task_progress(
            "my-agent", task["id"], 100, "completed",
            "Successfully implemented feature"
        )
```

---

## 📊 **Rate Limits & Performance**

- **No rate limits** for local development
- **Task assignment**: < 500ms average response time
- **Context retrieval**: < 200ms for typical tasks
- **Progress reporting**: < 100ms acknowledgment

---

## 🤝 **Contributing to API**

Want to extend the Marcus API? See our [Contributing Guide](../CONTRIBUTING.md) for:

- Adding new MCP tools
- Extending context system
- Improving error handling
- Adding new integrations

---

*Need help? Check our [GitHub Discussions](https://github.com/lwgray/marcus/discussions) or open an issue.*
