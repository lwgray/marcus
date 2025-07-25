# Marcus Role-Based Access Control Design

## Overview

Marcus serves multiple types of clients with different needs. This document defines the roles, their scenarios, and appropriate tool access.

## Client Roles & Scenarios

### 1. **Observer** (Read-Only Analytics)
**Primary User**: Seneca (observability tool), monitoring dashboards, managers

**Scenarios**:
- Monitor project progress and health
- Analyze agent performance and productivity
- Track task completion rates and bottlenecks
- Generate reports and visualizations
- Watch real-time activity without interfering

**Needs**:
- Read access to all project data
- Access to analytics and monitoring tools
- Cannot modify anything
- Cannot assign or claim tasks

### 2. **Developer** (Human Users)
**Primary User**: Human developers using Claude, CLI tools, IDEs

**Scenarios**:
- Create new projects from natural language
- Add features to existing projects
- Monitor their project's progress
- Switch between projects they own/participate in
- View task details and dependencies
- Cannot directly assign tasks (that's Marcus's job)

**Needs**:
- Project creation and management
- Feature specification
- Read access to all project data
- Cannot directly manipulate agent assignments

### 3. **Agent** (Automated Workers)
**Primary User**: AI coding agents, automated workers

**Scenarios**:
- Request work assignments from Marcus
- Report progress on assigned tasks
- Report blockers when stuck
- Log architectural decisions
- Store artifacts (specs, designs)
- Access task context and dependencies

**Needs**:
- Task lifecycle management
- Context access for assigned work
- Collaboration tools (decisions, artifacts)
- Cannot see other agents' tasks or manipulate assignments

### 4. **Admin** (System Administrators)
**Primary User**: Marcus system administrators

**Scenarios**:
- Full system access
- Debug issues
- Manual cleanup operations
- System configuration
- Access to all tools

**Needs**:
- Complete access to all tools
- System maintenance capabilities

## Tool Categorization

### Public Tools (Available to Everyone)
These tools are safe for any client:
- `ping` - Basic connectivity check
- `authenticate` - Client authentication

### Read-Only Tools (Safe for Observers)
These provide information without side effects:
- `get_project_status` - Current project metrics
- `list_projects` - Available projects
- `get_current_project` - Active project info
- `list_registered_agents` - Agent roster
- `get_agent_status` - Individual agent info
- `check_board_health` - Board health metrics
- `check_task_dependencies` - Task relationships
- All pipeline tools (dashboard, flow, reports, compare, replay)
- `remove_project` - Delete projects (PMs need this)
- `check_assignment_health` - Debug assignments

### Project Management Tools (For Developers)
These create or modify project structure:
- `create_project` - Create new project from NLP
- `add_feature` - Add feature to project
- `switch_project` - Change active project
- `add_project` - Add existing project
- `update_project` - Modify project config

### Agent Workflow Tools (For Agents Only)
These are the core agent work cycle:
- `register_agent` - Register themselves
- `request_next_task` - Get work assignment
- `report_task_progress` - Update progress
- `report_blocker` - Report impediments
- `get_task_context` - Get full context
- `log_decision` - Document choices
- `log_artifact` - Store work products

### Admin Tools (System Level)
These are potentially dangerous:
- `ping` with special commands (cleanup, reset)
- Direct database manipulation (future)
- Configuration changes (future)

## Security Considerations

**Important**: Marcus is an open-source tool. Role-based access is designed for:
- **Organization**: Preventing accidental misuse of tools
- **Clarity**: Making it clear what each client type should do
- **Audit Trail**: Tracking who does what for debugging
- **NOT Security**: Anyone with access to run Marcus has full control

### Real Security Happens At:
1. **Infrastructure Level**: Who can access the server running Marcus
2. **Network Level**: Firewall rules, VPNs, private networks
3. **OS Level**: File permissions, user access controls
4. **Deployment Level**: Kubernetes RBAC, Cloud IAM, reverse proxies

### Role-Based Access Benefits:
1. **Prevents Accidents**: Agents won't accidentally delete projects
2. **Clear Interfaces**: Each client type knows its available tools
3. **Usage Tracking**: Audit logs show patterns and issues
4. **Tool Discovery**: Clients can see what tools they have access to

## Implementation Strategy

1. **Phase 1**: Basic roles (Observer, Developer, Agent)
2. **Phase 2**: Admin role for tracking (no auth needed)
3. **Phase 3**: Enhanced audit logging and usage analytics

## Example Registrations

```python
# Seneca authenticates as observer
await authenticate(
    client_id="seneca-prod-001",
    client_type="observer",
    role="analytics",
    metadata={"tool": "seneca", "version": "1.0"}
)

# Claude authenticates as developer
await authenticate(
    client_id="claude-user-john",
    client_type="developer",
    role="frontend",
    metadata={"user": "john@company.com"}
)

# Agent authenticates (then calls register_agent)
await authenticate(
    client_id="agent-backend-01",
    client_type="agent",
    role="backend",
    metadata={"model": "claude-3", "skills": ["python", "fastapi"]}
)

# Admin authenticates (no additional security - access controlled at deployment level)
await authenticate(
    client_id="admin-marcus",
    client_type="admin",
    role="system_admin",
    metadata={"user": "admin@company.com", "purpose": "system_maintenance"}
)
```
