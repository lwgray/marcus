# PM Agent - Next Steps: User Journey & GitHub Integration

## Overview

This document outlines the complete user journey for PM Agent, including the new GitHub Projects integration as an alternative to Planka, and the comprehensive project setup workflow.

## User Journey - Complete Workflow

### 1. **Install and Configure Infrastructure** - **USER**
- Install kanban-mcp server
- Set up either:
  - Planka (self-hosted kanban board)
  - GitHub repository with Projects enabled
- Install and configure PM Agent
- Configure PM Agent with chosen backend (Planka or GitHub)

### 2. **Create Project Documentation** - **USER**

#### Required Documents:

**Product Requirements Document (PRD)** - What the product should do
- User stories and use cases
- Functional requirements
- Non-functional requirements
- Acceptance criteria

**Product Specification** - How the product will be built
- Technical architecture
- API specifications
- Database schema
- UI/UX specifications

**Project Configuration** - Project metadata and settings
```yaml
project:
  name: "Smart Task Calendar"
  type: "web-application"  # mobile-app, api, library, etc.
  scope: "mvp"  # mvp, full-product, prototype
  
environments:
  development: true
  staging: true
  production: true
  
deployment:
  hosting: "aws"  # self-hosted, heroku, vercel, etc.
  regions: ["us-east-1", "eu-west-1"]
  
resources:
  budget: "$50k"
  timeline: "3 months"
  team_size: "flexible"  # or specific number
  
technical:
  stack: ["python", "react", "postgresql"]
  integrations: ["google-calendar", "slack"]
  compliance: ["GDPR", "SOC2"]
  
github:
  create_repo: true
  repo_name: "smart-task-calendar"
  visibility: "private"
  enable_projects: true
  enable_actions: true
```

### 3. **Project Analysis & Board Setup** - **PM AGENT**
- Analyze PRD and specifications using AI
- Break down into epics, features, and tasks
- Identify dependencies and priorities
- Create kanban board structure
- Populate backlog with tasks
- Set up environments (dev/staging/prod) tasks
- Create GitHub repository if requested
- Generate resource estimates and timeline

### 4. **Review and Approve** - **USER + PM AGENT**

#### Multi-Channel Review Options:

**Option A: Direct Board Editing**
- User reviews board directly in Planka/GitHub Projects
- Makes changes using the native UI
- PM Agent monitors changes and updates internal model

**Option B: Report-Based Review**
- PM Agent provides detailed markdown/JSON reports
- User reviews offline and provides feedback list
- PM Agent batch-processes changes

**Option C: Conversational Review**
- User discusses changes with PM Agent via chat
- Natural language commands for modifications
- Context-aware suggestions

**Option D: API-Based Review**
- Programmatic review via PM Agent API
- Bulk operations via scripts
- CI/CD integration

#### Approval Process:
1. PM Agent generates summary report
2. User reviews generated tasks and structure
3. User can modify, add, or remove tasks
4. User provides approval (via UI, chat, or API)
5. PM Agent locks board for agent execution

### 5. **Agent Registration** - **AGENT**
- Agents register with PM Agent
- Declare skills and capabilities
- PM Agent tracks available workforce

### 6. **Task Execution Cycle** - **AGENT/PM AGENT**
- **AGENT**: Request next task
- **PM AGENT**: Assign based on priority/skills/dependencies
- **AGENT**: Execute and report progress
- **PM AGENT**: Update board and manage workflow
- **PM AGENT**: Handle blockers and dependencies

### 7. **Monitor & Guide** - **USER**
- Monitor progress dashboards
- View GitHub Project status (if using GitHub backend)
- Provide clarifications when needed
- Adjust priorities if necessary
- Review completed work

### 8. **Delivery** - **PM AGENT/USER**
- **PM AGENT**: Validate completion criteria
- **PM AGENT**: Generate delivery report
- **USER**: Accept deliverables
- **PM AGENT**: Archive project data

## GitHub Integration Details

### User Workflow for GitHub Backend

1. **Create Command Issue**
   ```markdown
   Title: PM: Build todo app with authentication
   
   Body:
   Create a todo application with the following features:
   - User registration and login
   - Create, read, update, delete todos
   - Mark todos as complete
   - Filter by status
   
   Tech stack: React frontend, Python Flask backend, PostgreSQL
   ```

2. **PM Agent Response**
   - Polls for issues with "pm-command" label
   - Analyzes requirements
   - Creates tasks in GitHub Projects
   - Comments on issue with task summary
   - Asks for approval

3. **User Approval**
   - Reviews generated GitHub Project board
   - Makes any adjustments directly in GitHub
   - Comments "approved" on original issue

4. **Execution Begins**
   - PM Agent starts assigning tasks to agents
   - Progress tracked via GitHub issues
   - Updates posted as issue comments

### Implementation Architecture

```
Planka Backend          GitHub Backend
     |                       |
     v                       v
BaseKanbanInterface (Abstract)
     |
     v
  PM Agent Core
     |
     v
  MCP Server Interface
     |
     v
  Worker Agents
```

### Configuration Examples

**Planka Configuration:**
```json
{
  "kanban": {
    "backend": "planka"
  },
  "planka": {
    "base_url": "http://localhost:3333",
    "email": "demo@demo.demo",
    "password": "demo"
  }
}
```

**GitHub Configuration:**
```json
{
  "kanban": {
    "backend": "github"
  },
  "github": {
    "token": "${GITHUB_TOKEN}",
    "repo_owner": "your-username",
    "repo_name": "your-repo",
    "project_title": "Autonomous Development"
  }
}
```

## Kanban Best Practices for PM Agent

### Board Structure
1. **Lists**: Backlog → Ready → In Progress → Review → Done → Archived
2. **Task Size**: Maximum 8 hours per task (1 day of agent work)
3. **Dependencies**: Explicitly marked and tracked
4. **Labels**: Priority (High/Medium/Low), Agent Type, Environment

### Task Breakdown Methodology
1. **Epic Level**: Major features (2-4 weeks)
2. **Feature Level**: Deliverable components (3-5 days)
3. **Task Level**: Atomic work units (2-8 hours)

### Reproducible Board Setup
- Template-based board creation
- Automated task generation from PRD
- Consistent naming conventions
- Standard label sets

## Implementation Priority

### Phase 1: Core GitHub Integration
1. Create `base_kanban.py` interface
2. Implement `github_projects.py` client
3. Update configuration system
4. Test with simple projects

### Phase 2: Enhanced Features
1. GitHub command monitoring
2. Automated project analysis
3. Resource estimation
4. Multi-environment support

### Phase 3: Advanced Capabilities
1. Real-time synchronization
2. Advanced reporting
3. Multiple backend support
4. Project templates

## Benefits Summary

### For Users
- **Flexibility**: Choose between Planka or GitHub
- **Familiarity**: Use existing GitHub workflow
- **Visibility**: Everything in one platform
- **No Licensing**: GitHub Projects is free for public repos

### For PM Agent
- **Extensibility**: Easy to add new backends
- **Maintainability**: Clean abstraction layer
- **Compatibility**: Works with existing agent infrastructure
- **Scalability**: Supports multiple concurrent projects

## Next Actions

1. **Immediate**:
   - Implement base kanban interface
   - Create GitHub Projects client
   - Update documentation

2. **Short-term**:
   - Add command monitoring
   - Create project templates
   - Implement approval workflow

3. **Long-term**:
   - Add more backend options (Linear, Jira)
   - Enhance AI project analysis
   - Build project marketplace

## Templates Needed

1. **PRD Template** - Structured requirements format
2. **Product Spec Template** - Technical specification format
3. **Project Config Template** - YAML configuration
4. **Task Templates** - Common task patterns
5. **Approval Templates** - Review checklists

This comprehensive approach transforms PM Agent from a Planka-specific tool to a flexible project orchestration system that can work with multiple backends while maintaining its core autonomous agent coordination capabilities.