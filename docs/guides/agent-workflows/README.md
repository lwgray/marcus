# Agent Workflows

Complete documentation of how AI agents interact with Marcus throughout their lifecycle.

## Purpose

Understand the sophisticated multi-system orchestration behind every agent action. These guides reveal the intelligence, coordination, and learning happening when agents work with Marcus.

## Audience

- AI agents using Marcus for coordination
- Developers building agent integrations
- System architects understanding agent coordination
- Anyone debugging agent behavior

## Workflow Guides

### **[Agent Workflow Overview](agent-workflow.md)**
Complete agent lifecycle from startup to continuous work loop. Understand the decision process, tool usage, and coordination patterns.

**When to read**: First document for understanding agent operations

### **[Registration](registration.md)**
How agents register with Marcus and become part of the coordination system. Covers profile creation, capability evaluation, and team integration.

**Systems involved**: Agent Management, Event System, AI Decision Engine, Memory System (5+ stages)

### **[Requesting Tasks](requesting-tasks.md)**
The sophisticated 8-stage process of task assignment. From project state refresh to AI-powered task selection to context building and instruction generation.

**Systems involved**: Agent Coordination, Project Management, AI Engine, Context System, Lease Management, Memory (15+ systems)

### **[Reporting Progress](reporting-progress.md)**
What happens when agents report progress at 25%, 50%, 75%, or 100%. Covers lease renewal, performance learning, predictive analytics, and cascade coordination.

**Systems involved**: Lease Management, Kanban Integration, Memory, Predictive Analytics, Monitoring (7+ stages)

### **[Handling Blockers](handling-blockers.md)**
AI-powered blocker analysis and resolution. Learn how Marcus analyzes root causes, generates solutions, assesses risk, and coordinates team response.

**Systems involved**: AI Blocker Analysis, Risk Assessment, Memory, Task Management, Communication Hub (7+ stages)

### **[Getting Context](getting-context.md)**
How agents retrieve comprehensive task context including dependencies, implementation patterns, architectural decisions, and risk assessment.

**Systems involved**: Core Models, Kanban Integration, Context System, Code Analysis, Memory, Risk Analysis (5+ stages)

### **[Checking Dependencies](checking-dependencies.md)**
Sophisticated dependency validation with graph analysis, status checking, predictive risk analysis, and optimization recommendations.

**Systems involved**: Context Analysis, Dependency Engine, Predictor Engine, Coordination Hub, Optimizer Engine, Learning (7+ stages)

## What Makes These Guides Different

These aren't simple API docs—they reveal the **internal complexity and intelligence** behind each operation:

- **Multi-stage orchestration** - 4-8 stages per operation
- **Multi-system integration** - 8-15+ systems working together
- **AI-powered intelligence** - Extensive AI analysis, prediction, optimization
- **4-tier memory integration** - Continuous learning at every step
- **Predictive analytics** - Risk assessment, timeline forecasting, impact analysis
- **Comprehensive logging** - Complete audit trail and observability

## Agent Workflow Pattern

All agents follow this continuous loop:

```
1. Register (once) → 2. Request Task → 3. Get Context (if needed) →
4. Work on Task → 5. Report Progress (25%, 50%, 75%) →
6. Report Completion (100%) → 7. IMMEDIATELY Request Next Task → (loop to step 2)
```

**Critical behaviors**:
- Complete tasks before requesting new ones
- Request next task IMMEDIATELY after completion
- Log decisions AS they're made
- Report blockers with attempted solutions
- Use context to understand dependencies

## Next Steps

- **New to Marcus?** Start with [Agent Workflow Overview](agent-workflow.md)
- **Building an agent?** Read all guides in order
- **Debugging?** Find the relevant workflow guide
- **Need API details?** See [API Reference](../../api/)

---

**Remember**: These operations look simple from outside, but they orchestrate sophisticated intelligence for effective coordination.
