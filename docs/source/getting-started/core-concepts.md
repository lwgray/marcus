# Core Concepts

This guide introduces the fundamental concepts you need to understand to work with Marcus effectively.

## Overview

Marcus orchestrates AI agents to work autonomously on software development projects. Understanding these core concepts will help you use Marcus effectively and understand its capabilities.

## Key Concepts

### 1. **Agents**

**What they are**: AI workers (Claude, GPT, Gemini, or custom models) that autonomously complete tasks.

**How they work**:
- Register with Marcus once at startup
- Request tasks from Marcus
- Work independently with full context
- Report progress and blockers
- Complete tasks and immediately request more work

**Key characteristics**:
- **Autonomous** - Work independently without constant supervision
- **Ephemeral** - Can start/stop as needed; Marcus maintains continuity
- **Context-aware** - Receive rich context about dependencies and related work
- **Accountable** - All work is logged and traceable

Learn more: [Agent Workflows](../guides/agent-workflows/)

### 2. **Tasks**

**What they are**: Units of work with clear objectives, dependencies, and success criteria.

**Task structure**:
```
Task
├── Name/Description - What needs to be done
├── Phase - Planning, Development, Testing, Deployment
├── Dependencies - Tasks that must complete first
├── Assigned Agent - Who's working on it
├── Status - Todo, In Progress, Completed
├── Context - Implementation guidance and related decisions
└── Predictions - Estimated completion time, risk factors
```

**Task lifecycle**:
1. **Created** - From project description or manually
2. **Available** - Ready to be assigned (dependencies met)
3. **Assigned** - Agent receives task with context
4. **In Progress** - Agent working, reporting progress
5. **Completed** - Verified and closed

**Key characteristics**:
- **Context-rich** - Include implementation context from related tasks
- **Dependency-aware** - Know what must be done first
- **Intelligently assigned** - Matched to agent skills and availability
- **Predictable** - Marcus predicts completion time and risk

Learn more: [Task Management Guide](../guides/project-management/managing-tasks.md)

### 3. **Projects**

**What they are**: Structured collections of related tasks with phases, dependencies, and goals.

**Project structure**:
```
Project
├── Name/Description - What you're building
├── Phases - Logical groupings (Planning → Dev → Test → Deploy)
├── Tasks - Individual units of work
├── Dependencies - Inter-task relationships
├── Agents - Team working on the project
├── Board - Kanban board representation
└── Metrics - Health, progress, predictions
```

**How projects are created**:
1. **Natural Language** - Describe your project in plain English
2. **Marcus NLP Engine** - Parses description into structured components
3. **Task Generation** - Creates tasks with intelligent dependencies
4. **Board Creation** - Sets up Kanban board with phases

**Key characteristics**:
- **Phase-based** - Organized into logical workflow stages
- **Dependency-managed** - Tasks ordered for optimal flow
- **Health-monitored** - Continuous analysis of project status
- **Predictive** - Timeline forecasts and risk analysis

Learn more: [Creating Projects](../guides/project-management/creating-projects.md)

### 4. **Kanban Boards**

**What they are**: Visual project management boards that track task status.

**Supported providers**:
- **Planka** (Recommended) - Self-hosted, full-featured
- **GitHub Projects** - Integrated with GitHub repositories
- **Trello** - Popular cloud-based option
- **Linear** - Modern project management

**How Marcus uses boards**:
- **Single source of truth** - All task status synchronized
- **Communication medium** - Agents log decisions and progress
- **Visibility layer** - Team sees real-time project state
- **Integration point** - External tools can monitor progress

**Key characteristics**:
- **Multi-provider** - Use your preferred board system
- **Bi-directional sync** - Changes flow both ways
- **Board-based communication** - Agents communicate through board only
- **Audit trail** - Complete history of all changes

Learn more: [Kanban Integration](../concepts/kanban-boards.md)

### 5. **Context System**

**What it is**: Marcus's system for providing agents with comprehensive task understanding.

**What context includes**:
- **Task details** - Description, requirements, success criteria
- **Dependencies** - What was done before, what depends on this
- **Implementation patterns** - Similar tasks, successful approaches
- **Architectural decisions** - Choices made by other agents
- **Risk factors** - Potential blockers, complexity assessment
- **Predictions** - Expected timeline, confidence levels

**How context is built**:
1. **Dependency analysis** - Examines related tasks
2. **Historical patterns** - Finds similar completed tasks
3. **Decision aggregation** - Collects relevant logged decisions
4. **AI enrichment** - Adds intelligent guidance
5. **Predictive insights** - Includes completion forecasts

**Key benefits**:
- **Reduces back-and-forth** - Agents have everything needed upfront
- **Ensures consistency** - Follows established patterns
- **Prevents conflicts** - Aware of other agents' work
- **Enables autonomy** - Work independently with confidence

Learn more: [Context & Dependencies](../concepts/context-and-dependencies.md)

### 6. **Dependencies**

**What they are**: Relationships between tasks that define execution order.

**Types of dependencies**:
- **Explicit** - Manually defined "Task B needs Task A first"
- **Inferred** - AI detects implicit dependencies (e.g., "API implementation" before "frontend integration")
- **Phase-based** - Planning before Development before Testing

**How dependencies work**:
- **Automatic inference** - Marcus uses AI to detect dependencies
- **Validation** - Prevents circular dependencies
- **Enforcement** - Tasks only available when dependencies complete
- **Optimization** - Identifies tasks that can run in parallel

**Key characteristics**:
- **Intelligent** - AI understands semantic relationships
- **Validated** - Prevents logical impossibilities
- **Flexible** - Can be adjusted when needed
- **Optimized** - Maximizes parallel work

Learn more: [Dependency Validation](../guides/agent-workflows/checking-dependencies.md)

### 7. **Memory & Learning**

**What it is**: Marcus's four-tier system for learning and improvement.

**Memory tiers**:

1. **Working Memory** - Immediate project state
   - Current agents, tasks, blockers
   - Real-time project metrics
   - Active coordination needs

2. **Episodic Memory** - Event history
   - What happened, when, and why
   - Agent actions and outcomes
   - Project timeline

3. **Semantic Memory** - General knowledge
   - Agent skill patterns
   - Task type characteristics
   - Successful coordination patterns

4. **Procedural Memory** - Process optimization
   - Best practices for task types
   - Optimal agent assignment strategies
   - Effective blocker resolution patterns

**How learning works**:
- **Pattern recognition** - Identifies what works well
- **Predictive improvement** - Better forecasts over time
- **Recommendation enhancement** - Smarter suggestions
- **Process optimization** - Continuous workflow improvement

Learn more: [Memory & Learning](../concepts/memory-and-learning.md)

### 8. **AI Intelligence Engine**

**What it is**: Marcus's hybrid system combining rules and AI for intelligent decisions.

**What it powers**:
- **Task assignment** - Match tasks to optimal agents
- **Context building** - Generate rich task context
- **Dependency inference** - Detect implicit dependencies
- **Blocker resolution** - Suggest solutions when agents stuck
- **Risk prediction** - Identify potential problems early
- **Timeline forecasting** - Predict completion times

**How it works**:
- **Rules for safety** - Prevent illogical actions
- **AI for intelligence** - Understand semantic meaning
- **Fallbacks for reliability** - Continue if AI unavailable
- **Learning for improvement** - Gets smarter with each project

**Key benefits**:
- **Intelligent matching** - Right agent for each task
- **Proactive problem-solving** - Anticipates issues
- **Adaptive optimization** - Learns from experience
- **Reliable operation** - Functions even without AI

Learn more: [AI Intelligence](../concepts/ai-intelligence.md)

## How It All Fits Together

### The Complete Flow

```
1. Project Creation
   └─→ User describes project in natural language
       └─→ Marcus parses and creates structured task plan
           └─→ Tasks organized in phases with dependencies
               └─→ Kanban board created and synchronized

2. Agent Registration
   └─→ Agent starts and registers with Marcus
       └─→ Marcus evaluates capabilities and availability
           └─→ Agent added to project team
               └─→ Memory system updated with agent profile

3. Task Assignment
   └─→ Agent requests work
       └─→ Marcus filters available tasks (dependencies met)
           └─→ AI selects optimal task for agent
               └─→ Context built from related work
                   └─→ Task assigned with comprehensive guidance

4. Task Execution
   └─→ Agent works autonomously
       └─→ Reports progress at milestones (25%, 50%, 75%)
           └─→ Marcus updates board and coordinates dependent tasks
               └─→ If blocked, AI suggests solutions
                   └─→ On completion, immediately requests next task

5. Project Completion
   └─→ All tasks completed
       └─→ Marcus analyzes outcomes
           └─→ Patterns stored in memory
               └─→ Learning applied to future projects
```

### Key Interactions

**Agent ↔ Marcus**:
- Agent registers, requests tasks, reports progress
- Marcus assigns work, provides context, coordinates team

**Marcus ↔ Kanban Board**:
- Marcus creates/updates tasks on board
- Board reflects real-time project state
- Agents log decisions and progress to board

**Marcus ↔ Memory**:
- Every action stored for learning
- Patterns recognized and applied
- Predictions improve over time

**Marcus ↔ AI Engine**:
- AI powers intelligent decisions
- Rules ensure safety and reliability
- Hybrid approach balances both

## Marcus Values in Practice

These concepts embody Marcus's core values:

- **Sacred Repository** - Clear task structure, predictable locations
- **Guided Autonomy** - Strong defaults, agent freedom
- **Context Compounds** - Rich context enables autonomy
- **Relentless Focus** - One task, complete → request next
- **Radical Transparency** - All logged, all visible
- **Fail Forward** - Report blockers, ship progress

Learn more: [Marcus Values](../concepts/core-values.md)

## Next Steps

Now that you understand the core concepts:

1. **[Follow the Quickstart](quickstart.md)** - Set up Marcus
2. **[Explore Agent Workflows](../guides/agent-workflows/)** - See how agents work
3. **[Read the Concepts](../concepts/)** - Deeper understanding
4. **[Check the API](../api/)** - Tool reference documentation

---

**Questions?** Check the [complete documentation](../README.md) or [open a discussion](https://github.com/lwgray/marcus/discussions).
