# Marcus MCP Tools Quick Reference

## 🤖 Agent Management

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `register_agent` | Register new AI agent | `agent_id`, `name`, `role`, `skills[]` |
| `get_agent_status` | Check agent's current work | `agent_id` |
| `list_registered_agents` | List all agents | None |

## 📋 Task Management

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `request_next_task` | Get optimal task assignment | `agent_id` |
| `report_task_progress` | Update task progress | `agent_id`, `task_id`, `status`, `progress`, `message` |
| `report_blocker` | Report blocking issue | `agent_id`, `task_id`, `blocker_description`, `severity` |

## 📊 Project Monitoring

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `get_project_status` | Get project metrics | None |

## 🏥 System Health

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ping` | Check connectivity | `echo` (optional) |
| `check_assignment_health` | Verify system health | None |

## 🧠 Natural Language (AI-Powered)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `create_project` | Create project from description | `description`, `project_name`, `options{}` |
| `add_feature` | Add feature to existing project | `feature_description`, `integration_point` |

## Status Values

### Task Status
- `in_progress` - Currently being worked on
- `completed` - Successfully finished
- `blocked` - Cannot proceed

### Severity Levels
- `low` - Minor issue, can work around
- `medium` - Significant issue, needs attention
- `high` - Critical blocker, urgent

### Integration Points (for add_feature)
- `auto_detect` - AI determines best approach
- `after_current` - Sequential after current work
- `parallel` - Can be done alongside current work
- `new_phase` - Requires new project phase

## Common Workflows

### 1. Agent Onboarding
```bash
register_agent → request_next_task → report_task_progress
```

### 2. Task Lifecycle
```bash
request_next_task → report_task_progress (multiple) → report_task_progress(completed)
```

### 3. Handling Blockers
```bash
report_blocker → (resolve issue) → report_task_progress
```

### 4. Project Creation
```bash
create_project → list_registered_agents → (agents request tasks)
```

### 5. Feature Addition
```bash
get_project_status → add_feature → (new tasks available)
```

## Response Format

### Success Response
```json
{
  "success": true,
  "data": "...",
  "message": "Operation successful"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Description of what went wrong",
  "error_code": "ERROR_CODE"
}
```

## File Locations

- **Core Tools**: `/marcus_mcp_server.py` (lines 456-1180)
- **NLP Tools**: `/src/integrations/mcp_natural_language_tools.py` (lines 516-650)
- **Tool Registration**: `/marcus_mcp_server.py` (lines 201-371)

## Tips

1. **Always check `success` field** in responses before proceeding
2. **Report progress regularly** - every 25% is a good rule
3. **Be specific** in natural language descriptions for better AI results
4. **Register agents with accurate skills** for optimal task matching
5. **Report blockers immediately** with detailed descriptions