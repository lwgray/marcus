# Workspace Isolation Implementation Plan

## Overview
This plan addresses the security issue where autonomous client agents can access the PM Agent's source code. The solution implements proper workspace isolation to ensure clients only operate in their designated project directories.

## Problem Statement
- PM Agent runs in its installation directory (e.g., `/Users/lwgray/dev/pm-agent`)
- Client agents inherit this working directory
- When connections fail, clients explore PM Agent's code (security breach)
- No clear separation between PM Agent installation and managed projects

## Proposed Architecture

### Key Principles
1. **Dynamic Path Detection**: PM Agent automatically detects its installation path
2. **Explicit Workspaces**: Project directories must be explicitly configured
3. **Forbidden Paths**: PM Agent directory is automatically forbidden to all clients
4. **Portable Design**: Works regardless of where PM Agent is installed

### Task Breakdown & Dependencies

#### Phase 1: Analysis & Design

**Task 1.1: Analyze current client workspace behavior**
- Understand how clients determine their working directory
- Document current security vulnerabilities
- Map all file access patterns in client code
- *No dependencies*

**Task 1.2: Design portable workspace isolation architecture**
- Create WorkspaceManager design
- Define configuration schema for project workspaces
- Design security boundary enforcement
- *Depends on: Task 1.1*

#### Phase 2: Core Implementation

**Task 2.1: Implement WorkspaceManager class**
```python
class WorkspaceManager:
    - Auto-detect PM Agent installation path
    - Manage forbidden paths dynamically
    - Handle multiple project workspaces
    - Validate workspace configurations
```
- *Depends on: Task 1.2*

**Task 2.2: Update configuration system**
- Move config to `~/.config/pm-agent/` or use env vars
- Add project workspace configuration section
- Remove working directory dependencies
- *Depends on: Task 1.2*

**Task 2.3: Modify task assignments**
- Add `workspace_path` field to TaskAssignment model
- Include `forbidden_paths` in task data
- Update task allocation to assign workspaces
- *Depends on: Task 2.1*

#### Phase 3: Security & Validation

**Task 3.1: Implement client sandbox validation**
- Add pre-operation path validation
- Reject any access to forbidden paths
- Create security violation logging
- *Depends on: Tasks 2.1, 2.3*

**Task 3.2: Create workspace setup validation**
- Check for path overlap with PM Agent
- Validate workspace exists and is accessible
- Ensure git worktree compatibility
- *Depends on: Task 2.1*

#### Phase 4: Testing

**Task 4.1: Write comprehensive tests**
- Test forbidden path protection
- Verify multi-agent workspace isolation
- Test configuration portability
- Validate security boundaries
- *Depends on: All Phase 2 & 3 tasks*

#### Phase 5: Documentation & Migration

**Task 5.1: Update documentation**
- Installation and setup guide
- Workspace configuration examples
- Security model explanation
- Troubleshooting guide
- *Depends on: Task 4.1*

**Task 5.2: Create migration tooling**
- Script to migrate existing configurations
- Update MCP registration commands
- Provide rollback capability
- *Depends on: Task 5.1*

## Implementation Details

### Configuration Schema
```json
{
  "pm_agent": {
    "board_id": "...",
    "project_id": "..."
  },
  "project": {
    "name": "My Project",
    "workspaces": {
      "main": "~/projects/my-project",
      "agents": {
        "frontend": "~/projects/my-project-frontend",
        "backend": "~/projects/my-project-backend",
        "testing": "~/projects/my-project-testing"
      }
    }
  }
}
```

### Security Implementation
```python
# In WorkspaceManager
def validate_path(self, requested_path):
    absolute_path = os.path.abspath(requested_path)
    for forbidden in self.forbidden_paths:
        if absolute_path.startswith(forbidden):
            raise SecurityError(f"Access denied: {requested_path}")
    return absolute_path
```

### MCP Configuration Update
Instead of:
```bash
claude mcp add pm-agent -s user -d /path/to/pm-agent -- python -m src.pm_agent_mvp_fixed
```

Use:
```bash
claude mcp add pm-agent -s user -- python -m src.pm_agent_mvp_fixed
# Working directory doesn't matter - config specifies project locations
```

## Commit Strategy
1. After Phase 1: "docs: Add workspace isolation design and analysis"
2. After Task 2.1: "feat: Implement WorkspaceManager for client isolation"
3. After Task 2.2: "refactor: Move configuration to XDG directory"
4. After Task 2.3: "feat: Add workspace paths to task assignments"
5. After Phase 3: "security: Implement client workspace sandboxing"
6. After Phase 4: "test: Add comprehensive workspace isolation tests"
7. After Phase 5: "docs: Complete workspace isolation documentation"

## Success Criteria
- [ ] Clients cannot access PM Agent installation directory
- [ ] Each agent works in its designated workspace
- [ ] Configuration is portable across installations
- [ ] Security violations are logged and prevented
- [ ] Migration path for existing users
- [ ] Comprehensive test coverage