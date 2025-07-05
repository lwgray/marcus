# Marcus Agent Interaction Guidelines

## Overview
This document outlines the requirements and best practices for agents interacting with Marcus, the MCP service that coordinates AI agent software development.

## Core Requirements (Must-Haves)

### 1. Constantly Request Work
- Agents must actively poll Marcus for new tasks
- No idle time - when a task completes, immediately request the next one
- Use the appropriate MCP endpoints to fetch available tasks

### 2. Report Progress
- Provide regular status updates during task execution
- Report progress at meaningful checkpoints (e.g., after each subtask completion)
- Include percentage complete when possible
- Update task status: `pending` → `in_progress` → `completed`

### 3. Report Blockers
- Immediately report any blocking issues to Marcus
- Blocker reports must include:
  - What is blocked
  - What approaches were attempted
  - What assistance is needed
  - Estimated impact on timeline
- Don't waste cycles on blocked tasks - report and move to next available task

## Best Practices (Nice-to-Haves)

### 1. Test-Driven Development (TDD)
- Write tests before implementing features
- Ensure all code has corresponding test coverage
- Run tests after each implementation change
- Marcus may reject task completion without adequate tests

### 2. Documentation Philosophy
- Document code purpose, not just mechanics
- Update existing documentation when modifying code
- Include examples in documentation where helpful
- Follow project-specific documentation standards

### 3. Error Handling Framework
- Use consistent error handling patterns across all code
- Propagate errors with meaningful context
- Log errors appropriately for debugging
- Never silently fail - always report errors to Marcus

### 4. Git Workflow and Pull Requests
- Always work in feature branches, not directly on main/master
- Create a new branch for each task using format: `task-{task_id}-{brief-description}`
- Commit frequently with clear, descriptive messages
- Submit Pull Requests with the task_ID in the title and description
- PR title format: `[Task #{task_id}] Brief description of changes`
- Include in PR description:
  - Link to the Marcus task
  - Summary of changes
  - Test results
  - Any additional context for reviewers
- This enables context-aware code review and traceability between tasks and code changes

## Additional Considerations

### Context Preservation
- Provide sufficient context for task handoffs
- Document:
  - Current approach and reasoning
  - Key decisions made
  - Failed approaches (prevent duplicate effort)
  - Next steps if task is incomplete

### Communication Format
- Use standardized message formats for Marcus communication
- Include timestamp, agent ID, and task ID in all messages
- Keep messages concise but complete

## Example Workflow
```
1. Agent requests task from Marcus
2. Marcus assigns task with ID and requirements
3. Agent creates feature branch: git checkout -b task-1234-add-user-auth
4. Agent updates status to "in_progress"
5. Agent provides progress update at 25% complete
6. Agent commits work: git commit -m "[Task #1234] Add user authentication module"
7. Agent encounters blocker, reports to Marcus
8. Marcus provides guidance or reassigns
9. Agent completes task, runs tests
10. Agent creates PR: "[Task #1234] Add user authentication"
11. Agent reports completion with results and PR link
12. Agent immediately requests next task
```