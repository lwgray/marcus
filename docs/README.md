# 📚 Marcus Documentation

Welcome to the complete Marcus documentation! This guide helps you find exactly what you need, whether you're new to Marcus, building agents, or extending the system.

## 🎯 Quick Navigation

| I want to... | Go to... |
|--------------|----------|
| **Understand what Marcus is** | [Getting Started](#-getting-started) |
| **Learn core concepts** | [Concepts](#-concepts) |
| **Build/use an agent** | [Agent Workflows](guides/agent-workflows/) |
| **Manage projects** | [Project Management](guides/project-management/) |
| **Understand the architecture** | [Systems Documentation](#-systems-documentation) |
| **Use the API** | [API Reference](#-api-reference) |
| **See future plans** | [Roadmap](#-roadmap) |

## 📖 Documentation Structure

### 🚀 [Getting Started](getting-started/)

**Start here if you're new to Marcus.** Quick setup, core concepts, and your first project.

- **[Introduction](getting-started/introduction.md)** - Marcus's philosophy and approach
- **[Quickstart Guide](getting-started/quickstart.md)** - Get running in 5 minutes
- **[💰 FREE Local AI Setup](getting-started/setup-local-llm.md)** - Zero-cost development with Qwen2.5-Coder
- **[Core Concepts](getting-started/core-concepts.md)** - Agents, tasks, projects, and more

**Best for**: New users, evaluators, anyone starting with Marcus

---

### 💡 [Concepts](concepts/)

**Understand the "what" and "why" of Marcus.** High-level design principles without implementation details.

- **[Philosophy](concepts/philosophy.md)** - Stoic approach, BYOA, emergence
- **[Core Values](concepts/core-values.md)** - Seven principles guiding Marcus

**Key concepts covered**: Agents, Tasks, Projects, Kanban, Context, Dependencies, Memory & Learning, AI Intelligence, Error Handling

**Best for**: Understanding Marcus's design philosophy and approach

---

### 📘 [Guides](guides/)

**Learn "how" to use Marcus effectively.** Step-by-step workflows and best practices.

#### [Agent Workflows](guides/agent-workflows/)
Complete agent lifecycle from registration to task completion.

- **[Agent Workflow Overview](guides/agent-workflows/agent-workflow.md)** - Complete lifecycle
- **[Registration](guides/agent-workflows/registration.md)** - How agents join Marcus
- **[Requesting Tasks](guides/agent-workflows/requesting-tasks.md)** - Intelligent task assignment
- **[Reporting Progress](guides/agent-workflows/reporting-progress.md)** - Progress tracking
- **[Handling Blockers](guides/agent-workflows/handling-blockers.md)** - AI-powered resolution
- **[Getting Context](guides/agent-workflows/getting-context.md)** - Rich task information
- **[Checking Dependencies](guides/agent-workflows/checking-dependencies.md)** - Dependency validation

**Best for**: Agents, agent developers, understanding coordination

#### [Developer Guide](source/developer/)
Setup and workflows for contributing to Marcus.

- **[Local Development Setup](source/developer/local-development.md)** - First-time setup and directory structure
- **[Development Workflow](source/developer/development-workflow.md)** - Daily workflows (restart, rebuild, test)
- **[Configuration Reference](source/developer/configuration.md)** - All environment variables and config options

**Best for**: Contributors, developers extending Marcus

#### [Project Management](guides/project-management/)
Create, monitor, and optimize projects.

- **[Creating Projects](guides/project-management/creating-projects.md)** - Natural language → structured plans
- **[Monitoring Status](guides/project-management/monitoring-status.md)** - Project health and analytics
- **[Analyzing Health](guides/project-management/analyzing-health.md)** - System diagnostics

**Best for**: Project managers, team leads, project creators

#### [Collaboration](guides/collaboration/)
How agents coordinate and communicate.

- **[Communication Hub](guides/collaboration/communication-hub.md)** - Intelligent team coordination
- **[Logging Decisions](guides/collaboration/logging-decisions.md)** - Document architectural choices
- **[Tracking Artifacts](guides/collaboration/tracking-artifacts.md)** - Manage project artifacts

**Best for**: Teams, understanding coordination patterns

#### [Advanced](guides/advanced/)
Deep-dive topics for power users.

- **[Memory System](guides/advanced/memory-system.md)** - Four-tier learning architecture
- **[Agent Support Tools](guides/advanced/agent-support-tools.md)** - Comprehensive tool overview
- **[Agent Status](guides/advanced/agent-status.md)** - Performance monitoring
- **[Ping System](guides/advanced/ping-system.md)** - Intelligent health checking

**Best for**: Power users, system architects, researchers

---

### 🏗️ [Systems Documentation](systems/)

**Technical architecture for developers.** Deep-dive into Marcus's 53 systems organized by function.

- **[Architecture](systems/architecture/)** - MCP Server, Event System, Service Registry
- **[Intelligence](systems/intelligence/)** - AI Engine, Memory, Learning, Recommendations (6 systems)
- **[Coordination](systems/coordination/)** - Agent lifecycle, Context, Dependencies (7 systems)
- **[Project Management](systems/project-management/)** - Kanban, Analysis, Workflow (7 systems)
- **[Development](systems/development/)** - Code Analysis, API Systems (2 systems)
- **[Infrastructure](systems/infrastructure/)** - Persistence, Configuration, Resilience (9 systems)
- **[Quality](systems/quality/)** - QA, Testing, Monitoring, Health Analysis (6 systems)
- **[Operations](systems/operations/)** - Pipelines, Modes, Cost Tracking (3 systems)
- **[Security](systems/security/)** - Security framework (1 system)
- **[Visualization](systems/visualization/)** - Logging, Dashboards (2 systems)

**Best for**: Developers, system integrators, contributors

---

### 🔧 [API Reference](api/)

**Technical API specs.** MCP tools, data models, error handling.

- **Agent Tools** - register_agent, get_agent_status, etc.
- **Task Tools** - request_next_task, report_progress, etc.
- **Project Tools** - create_project, get_project_status, etc.
- **Support Tools** - ping, get_task_context, log_decision, etc.
- **Intelligence Tools** - predict_*, get_*_metrics, etc.
- **Data Models** - Agent, Task, Project, Context models
- **Error Handling** - Error types, recovery, resilience

**Best for**: API developers, integration engineers

---

### 🗺️ [Roadmap](roadmap/)

**Marcus's future.** Evolution strategy, release plans, and upcoming features.

- **[Evolution](roadmap/evolution.md)** - Path to universal software engineering assistant
- **[Public Release Roadmap](roadmap/public-release-roadmap.md)** - MVP strategy and launch plans
- **[Future Systems](roadmap/future-systems.md)** - Planned features and experimental capabilities

**Best for**: Contributors, long-term planners, researchers

---

## 🎓 Learning Paths

### **New User Path**
1. Read [Introduction](getting-started/introduction.md) - Understand philosophy
2. Follow [Quickstart](getting-started/quickstart.md) - Get installed
3. Review [Core Concepts](getting-started/core-concepts.md) - Learn fundamentals
4. Explore [Guides](guides/) - See practical usage

### **Agent Developer Path**
1. Read [Core Concepts](getting-started/core-concepts.md) - Understand system
2. Study [Agent Workflow Overview](guides/agent-workflows/agent-workflow.md) - Learn lifecycle
3. Read all [Agent Workflows](guides/agent-workflows/) - Deep-dive each operation
4. Check [API Reference](api/) - Technical specs
5. Review [Systems Documentation](systems/) - Understand internals

### **Project Manager Path**
1. Read [Introduction](getting-started/introduction.md) - Understand approach
2. Study [Creating Projects](guides/project-management/creating-projects.md) - Project setup
3. Learn [Monitoring Status](guides/project-management/monitoring-status.md) - Track progress
4. Review [Collaboration](guides/collaboration/) - Team coordination

### **System Architect Path**
1. Read [Philosophy](concepts/philosophy.md) - Design principles
2. Study [Systems Documentation](systems/) - Technical architecture
3. Review [Advanced Guides](guides/advanced/) - Deep-dive topics
4. Check [Roadmap](roadmap/) - Future direction

### **Contributor Path**
1. Read [Introduction](getting-started/introduction.md) - Philosophy
2. **💰 [Setup Free AI](getting-started/setup-local-llm.md)** - Zero-cost development (no API keys!)
3. Set up [Local Development](source/developer/local-development.md) - Development environment
4. Learn [Development Workflow](source/developer/development-workflow.md) - Daily workflows
5. Review [Systems Documentation](systems/) - Architecture
6. Check [Roadmap](roadmap/) - Contribution areas
7. See GitHub issues and discussions - Active work

---

## 📝 Documentation Standards

### **Concepts** = "What" and "Why"
High-level understanding, design principles, no implementation details

### **Guides** = "How"
Step-by-step processes, workflows, examples, best practices

### **Systems** = "Architecture"
Technical implementation, deep-dive internals, for extending Marcus

### **API** = "Reference"
Tool specs, data models, request/response formats

---

## 🤝 Contributing

Found an issue or want to improve documentation?

- **Report Issues**: [GitHub Issues](https://github.com/lwgray/marcus/issues)
- **Ask Questions**: [GitHub Discussions](https://github.com/lwgray/marcus/discussions)
- **Submit Changes**: Fork and submit a PR

---

## 🔍 Search Tips

- **Looking for a specific tool?** → [API Reference](api/)
- **Understanding a workflow?** → [Guides](guides/)
- **Deep technical details?** → [Systems](systems/)
- **Philosophy and design?** → [Concepts](concepts/)
- **Future capabilities?** → [Roadmap](roadmap/)

---

## 📊 Documentation Metrics

- **Getting Started**: 4 documents - Quick entry and core concepts
- **Concepts**: 2 documents - Philosophy and values
- **Guides**: 20+ documents - Comprehensive how-to guides
- **Systems**: 53 documents - Complete technical architecture
- **API**: Tools, models, errors - Complete reference (in development)
- **Roadmap**: 3 documents - Future vision and plans

---

## 💬 Get Help

- **📖 Read the docs** - Most questions answered here
- **💬 GitHub Discussions** - Community Q&A
- **🐛 GitHub Issues** - Bug reports and feature requests

---

## 🎯 Marcus Philosophy

> **Focus on what you control** - Task structure, context, dependencies
>
> **Accept what you cannot** - How agents choose to solve problems
>
> **Learn from what emerges** - Pattern recognition and continuous improvement
>
> **Practice transparency** - All actions visible, all decisions logged

Marcus doesn't try to control everything. It creates the conditions for success and lets intelligence emerge. This is the Stoic way of multi-agent development: pragmatic, observable, and continuously learning.

---

*"You have power over your mind - not outside events. Realize this, and you will find strength." - Marcus Aurelius*

*"Every new beginning comes from some other beginning's end." - Seneca*
