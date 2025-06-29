# How Marcus Works

This guide explains how Marcus coordinates AI agents to build software projects, using simple concepts anyone can understand.

## The Big Picture

Imagine a classroom where:
- The **teacher** (Marcus) assigns homework to students
- Each **student** (AI Worker) has different strengths
- The **assignment board** (Kanban Board) tracks all the work
- Students work independently but toward a common goal

That's exactly how Marcus works!

## Core Components

### 1. The Task Board (Where Work Lives)

Marcus integrates with popular task management tools:

```
GitHub Projects    Linear    Planka
      ↓             ↓         ↓
      └─────────────┴─────────┘
                 ↓
           Marcus PM Agent
```

You create tasks on your preferred board, just like you normally would. Marcus reads these tasks and understands what needs to be done.

### 2. The PM Agent (The Brain)

The PM Agent is Marcus's intelligence center. It:

- **Reads** tasks from your board
- **Analyzes** what type of work each task requires
- **Assigns** tasks to the best-suited AI worker
- **Monitors** progress and handles issues
- **Updates** the board with status changes

### 3. AI Workers (The Builders)

AI Workers are autonomous agents (like Claude) that:

- **Register** their capabilities with Marcus
- **Request** work assignments
- **Execute** tasks independently
- **Report** progress at key milestones
- **Ask for help** when blocked

## The Task Lifecycle

Here's what happens when you create a task:

```
1. You Create Task
   "Build user authentication system"
   Labels: [backend, api, security]
   
2. Marcus Analyzes
   - Reads task requirements
   - Identifies needed skills
   - Checks available workers
   
3. Smart Assignment
   - Finds worker with backend experience
   - Assigns task to best match
   - Provides context from related tasks
   
4. Worker Executes
   - Plans the implementation
   - Writes code
   - Tests functionality
   - Commits to Git
   
5. Progress Updates
   - 25%: "Created user model"
   - 50%: "Added authentication endpoints"  
   - 75%: "Implemented JWT tokens"
   - 100%: "All tests passing"
   
6. Task Completion
   - Worker marks complete
   - Marcus updates board
   - You review the work
```

## Intelligence Features

### Smart Task Assignment

Marcus doesn't randomly assign tasks. It considers:

- **Worker Skills**: What each AI is good at
- **Task Requirements**: What the task needs
- **Current Workload**: Who's available
- **Past Performance**: Success with similar tasks
- **Dependencies**: What needs to be done first

### Context Awareness

Workers aren't working blind. Marcus provides:

- **Related Commits**: What's been built already
- **Project Structure**: How code is organized
- **Dependencies**: What other tasks connect
- **Standards**: Coding conventions to follow

### Blocker Resolution

When workers get stuck, Marcus helps by:

1. **Analyzing the Problem**: Understanding what went wrong
2. **Suggesting Solutions**: Providing specific fixes
3. **Finding Alternatives**: Different approaches to try
4. **Escalating if Needed**: Alerting you to critical issues

## Real-World Example

Let's say you want to build a TODO application:

### Step 1: Create Tasks
```
- [ ] Set up database schema
- [ ] Create REST API endpoints  
- [ ] Build user interface
- [ ] Add authentication
- [ ] Write tests
```

### Step 2: Marcus Assigns Work
```
Worker-1 (Backend Specialist) gets:
  → Set up database schema
  → Create REST API endpoints

Worker-2 (Frontend Expert) gets:
  → Build user interface

Worker-3 (Security Focus) gets:
  → Add authentication
  
Worker-4 (Testing Pro) gets:
  → Write tests
```

### Step 3: Parallel Progress

All workers can work simultaneously:
- Worker-1 creates the database and API
- Worker-2 builds the UI (mocking the API initially)
- Worker-3 prepares authentication (coordinating with Worker-1)
- Worker-4 writes test frameworks

### Step 4: Integration

As pieces complete, Marcus ensures:
- The UI connects to the real API
- Authentication integrates properly
- Tests cover all new features
- Everything works together

## Why This Works

### 1. Parallel Development
Multiple AI agents work simultaneously, dramatically speeding up development.

### 2. Specialized Skills
Each agent can focus on what it does best, improving quality.

### 3. Continuous Progress
Work continues 24/7 without human intervention needed.

### 4. Intelligent Coordination
Marcus ensures all pieces fit together properly.

### 5. Human Oversight
You maintain control while automating the implementation.

## Common Patterns

### The Startup Sprint
```
You: Create 20 tasks for MVP
Marcus: Assigns to 5 workers
Result: MVP ready in hours, not weeks
```

### The Bug Fix Brigade
```
You: Label issues as 'bug'
Marcus: Prioritizes and assigns
Result: Bugs fixed systematically
```

### The Feature Factory
```
You: Define feature requirements
Marcus: Breaks down and distributes
Result: Features built in parallel
```

## What Marcus Doesn't Do

- **Make Business Decisions**: You decide what to build
- **Replace Human Creativity**: You design the solution
- **Handle Legal/Ethical Issues**: You ensure compliance
- **Deploy to Production**: You control releases

## Summary

Marcus is like having a smart project manager who:
1. Never sleeps
2. Perfectly tracks every detail
3. Knows each worker's strengths
4. Coordinates complex projects
5. Helps workers when they're stuck

It turns your task board into a self-building project where AI agents collaborate to bring your ideas to life.

Ready to try it? Head to the [Getting Started Guide](getting-started.md)!