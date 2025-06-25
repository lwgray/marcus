# PM Agent Overview

## What is PM Agent?

PM Agent is an AI-powered Project Manager that acts as a central coordinator for autonomous software development teams. It bridges the gap between AI worker agents and project management tools, enabling truly autonomous software development workflows.

## Key Features

- **Dual MCP Architecture**: Acts as both MCP Server (for worker agents) and MCP Client (for kanban integration)
- **Intelligent Task Assignment**: Matches tasks to workers based on skills and priorities
- **AI-Enhanced Coordination**: Generates task instructions and blocker resolutions using Claude
- **Real-time Progress Tracking**: Updates kanban boards as work progresses
- **Autonomous Worker Support**: Enables continuous work cycles without human intervention

## How It Works

### The Workflow

1. **Worker Registration**: AI agents register with PM Agent, declaring their skills and capabilities
2. **Task Request**: Workers request their next task assignment
3. **Intelligent Matching**: PM Agent analyzes available tasks and assigns the most suitable one
4. **AI Instructions**: PM Agent generates detailed, actionable instructions for the task
5. **Progress Tracking**: Workers report progress, which PM Agent reflects on the kanban board
6. **Blocker Handling**: When blocked, workers report issues and receive AI-generated solutions
7. **Continuous Loop**: Upon completion, workers immediately request their next task

### System Components

```
┌─────────────────┐     MCP Protocol      ┌──────────────┐
│  Worker Agents  │◄──────────────────────►│   PM Agent   │
│ (Claude, etc.)  │                        │  MCP Server  │
└─────────────────┘                        └──────┬───────┘
                                                  │
                                           MCP Protocol
                                                  │
                                           ┌──────▼───────┐
                                           │ Kanban MCP   │
                                           │   Server     │
                                           └──────┬───────┘
                                                  │
                                              HTTP API
                                                  │
                                           ┌──────▼───────┐
                                           │   Planka     │
                                           │ Kanban Board │
                                           └──────────────┘
```

## Use Cases

### Autonomous Development Teams
- Multiple specialized AI agents working in parallel
- Backend, frontend, DevOps, and testing agents collaborating
- Automatic task distribution based on expertise

### Continuous Integration Workflows
- Agents automatically pick up CI/CD tasks
- Build, test, and deployment automation
- Self-healing infrastructure management

### Documentation and Maintenance
- Documentation agents keeping docs in sync with code
- Refactoring agents improving code quality
- Security agents scanning for vulnerabilities

## Benefits

1. **24/7 Development**: Agents work continuously without breaks
2. **Optimal Task Assignment**: Right agent for the right task
3. **Reduced Blockers**: AI-powered blocker resolution
4. **Full Visibility**: Real-time project status on kanban boards
5. **Scalability**: Add more agents as needed