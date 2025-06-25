# Kanban Best Practices for PM Agent

## Overview

This document outlines the Kanban methodology and best practices specifically tailored for PM Agent's autonomous development workflow.

## Board Structure

### Standard Lists Configuration

1. **Backlog** - All unstarted tasks
   - Prioritized from top to bottom
   - Contains fully specified tasks
   - No limit on items

2. **Ready** - Tasks ready for agents
   - Dependencies resolved
   - Acceptance criteria defined
   - Limited to 2x active agent count

3. **In Progress** - Active development
   - One task per agent maximum
   - Clear assignment visible
   - Progress tracking enabled

4. **Review** - Completed, awaiting validation
   - Automated tests passed
   - Code review if applicable
   - Limited to prevent bottlenecks

5. **Done** - Completed tasks
   - All criteria met
   - Stakeholder accepted
   - Ready for deployment

6. **Blocked** - Tasks with impediments
   - Clear blocker description
   - Assigned owner for resolution
   - Regular review cycle

## Task Creation Guidelines

### Task Sizing
- **Maximum Duration**: 8 hours (1 agent day)
- **Minimum Duration**: 2 hours
- **Sweet Spot**: 4-6 hours
- **Rationale**: Enables daily progress visibility and reduces risk

### Task Structure
```yaml
Title: [Action] [Component] [Outcome]
Example: "Implement User Authentication API Endpoints"

Description:
  Summary: Brief overview of the task
  
  Requirements:
  - Specific requirement 1
  - Specific requirement 2
  
  Acceptance Criteria:
  - [ ] Tests pass with 80% coverage
  - [ ] API documentation updated
  - [ ] Error handling implemented
  
  Dependencies:
  - Database schema (Task #123)
  - User model (Task #124)
  
Technical Notes:
  - Use JWT for token generation
  - Follow REST conventions
  
Estimated Hours: 6
Agent Type: backend_developer
Priority: High
```

### Labeling System

#### Priority Labels
- **🔴 Critical**: Blocks other work
- **🟠 High**: Core functionality
- **🟡 Medium**: Important features
- **🟢 Low**: Nice-to-have

#### Type Labels
- **feature**: New functionality
- **bug**: Defect fix
- **tech-debt**: Refactoring
- **docs**: Documentation
- **test**: Testing tasks

#### Agent Type Labels
- **backend**: Backend development
- **frontend**: Frontend development
- **fullstack**: Full-stack tasks
- **devops**: Infrastructure/deployment
- **qa**: Testing/quality assurance
- **ai-ml**: AI/ML tasks

## Task Breakdown Methodology

### From PRD to Tasks

#### Level 1: Epics (2-4 weeks)
```
Epic: User Management System
├── User Registration
├── Authentication
├── Profile Management
└── Admin Dashboard
```

#### Level 2: Features (3-5 days)
```
Feature: User Registration
├── Registration API
├── Email Verification
├── Frontend Forms
└── Integration Tests
```

#### Level 3: Tasks (2-8 hours)
```
Task: Registration API
├── POST /api/register endpoint
├── Input validation
├── Password hashing
├── Database operations
└── Error responses
```

### Dependency Management

#### Types of Dependencies
1. **Sequential**: Task B requires Task A completion
2. **Parallel**: Tasks can run simultaneously
3. **Shared Resource**: Tasks need same resource
4. **External**: Waiting on external input

#### Dependency Documentation
```yaml
dependencies:
  hard:
    - task_id: "TASK-123"
      type: "sequential"
      reason: "Needs user model"
  soft:
    - task_id: "TASK-456"
      type: "parallel"
      reason: "Shares database schema"
```

## Workflow Rules

### WIP (Work In Progress) Limits
- **In Progress**: 1 task per agent
- **Ready**: 2x number of active agents
- **Review**: 0.5x number of active agents

### Pull vs Push System
- Agents **pull** tasks when ready
- PM Agent **never pushes** tasks to busy agents
- Automatic assignment based on skills and availability

### Task State Transitions
```
Backlog → Ready → In Progress → Review → Done
           ↓          ↓           ↓
        Blocked    Blocked    Blocked
```

### Blocked Task Protocol
1. Agent reports blocker with details
2. PM Agent attempts resolution
3. If unresolved, escalate to user
4. Document resolution for future

## Metrics and Monitoring

### Key Metrics
1. **Cycle Time**: Ready → Done duration
2. **Lead Time**: Backlog → Done duration
3. **Throughput**: Tasks completed per day
4. **WIP**: Current tasks in progress
5. **Blocker Rate**: % of tasks blocked

### Health Indicators
- **Green**: All metrics within target
- **Yellow**: One metric outside target
- **Red**: Multiple metrics failing

### Velocity Tracking
```
Week 1: 15 tasks (60 hours)
Week 2: 18 tasks (72 hours)
Week 3: 20 tasks (80 hours)
Trend: ↑ Improving
```

## Automation Rules

### Auto-Movement Triggers
1. **To Ready**: When dependencies complete
2. **To In Progress**: When agent assigned
3. **To Review**: When agent marks complete
4. **To Done**: When validation passes

### Auto-Assignment Logic
```python
def assign_task(task, available_agents):
    # Filter by required skills
    skilled_agents = filter_by_skills(available_agents, task.required_skills)
    
    # Sort by workload (ascending)
    sorted_agents = sort_by_workload(skilled_agents)
    
    # Assign to least loaded agent
    return sorted_agents[0] if sorted_agents else None
```

## Continuous Improvement

### Daily Standup Equivalent
- PM Agent generates daily summary
- Highlights blockers and risks
- Shows progress trends
- Identifies bottlenecks

### Retrospective Data
- Task estimation accuracy
- Common blocker patterns
- Agent performance metrics
- Process improvement suggestions

### Board Evolution
1. Start with basic structure
2. Add custom fields as needed
3. Refine WIP limits based on data
4. Optimize for specific project types

## Templates and Reusability

### Project Templates
```yaml
web_app_template:
  lists: [Backlog, Ready, In Progress, Review, Done]
  labels: [frontend, backend, database, api, ui]
  custom_fields:
    - story_points: number
    - agent_type: dropdown
    - environment: dropdown

mobile_app_template:
  lists: [Backlog, Ready, Dev, Test, UAT, Done]
  labels: [ios, android, backend, api, ui]
  custom_fields:
    - platform: multiselect
    - version: text
```

### Task Templates
- API Endpoint Template
- Database Migration Template
- Frontend Component Template
- Bug Fix Template
- Documentation Template

## Integration Points

### With Version Control
- Link tasks to branches
- Auto-update on PR creation
- Track commit activity
- Close tasks on merge

### With CI/CD
- Trigger builds on task start
- Update task on build status
- Deploy on task completion
- Rollback on failure

### With Communication
- Notify on assignment
- Alert on blockers
- Summary reports
- Escalation paths

## Anti-Patterns to Avoid

1. **Task Splitting**: Breaking tasks too small (< 2 hours)
2. **Task Bloat**: Creating tasks too large (> 8 hours)
3. **Vague Descriptions**: Unclear acceptance criteria
4. **Hidden Dependencies**: Not documenting relationships
5. **Stale Boards**: Not archiving completed work
6. **Ignore WIP Limits**: Overloading agents
7. **Push System**: Forcing tasks on agents

## Conclusion

These best practices ensure efficient autonomous development while maintaining visibility and control. Regular refinement based on metrics and feedback will optimize the system for each specific use case.