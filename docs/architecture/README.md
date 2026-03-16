# Marcus Architecture Documentation

**Complete architectural documentation for the Marcus Multi-Agent Coordination System**

> **Project:** Multi-Agent Resource Coordination and Understanding System (Marcus)
> **Version:** Post-Project Analysis Phase 1
> **Codebase:** ~89,500 lines of Python across 202 modules
> **Python Version:** 3.11+

---

## 📚 Documentation Overview

This directory contains comprehensive architectural documentation for Marcus, organized into several key documents:

| Document | Purpose | Audience |
|----------|---------|----------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Complete architectural specification | Developers, architects |
| [C4_DIAGRAMS.md](./C4_DIAGRAMS.md) | Visual architecture (C4 model, sequence diagrams) | All stakeholders |
| [ARCHITECTURE_SUMMARY.md](./ARCHITECTURE_SUMMARY.md) | Quick reference and key metrics | New contributors, reviewers |
| [adr/](./adr/) | Architecture Decision Records | Decision makers, historians |
| [README_ARCHITECTURE.md](./README_ARCHITECTURE.md) | Navigation guide | New users |

---

## 🏗️ Architecture at a Glance

### System Pattern

Marcus follows a **Layered Architecture with Domain-Driven Design** principles:

```
┌─────────────────────────────────────────────────┐
│  Presentation Layer (MCP Server, CLI)          │
├─────────────────────────────────────────────────┤
│  Application Layer (Workflows, Orchestration)   │
├─────────────────────────────────────────────────┤
│  Domain Layer (Core Business Logic, Models)     │
├─────────────────────────────────────────────────┤
│  Integration Layer (Kanban, AI, External APIs)  │
├─────────────────────────────────────────────────┤
│  Infrastructure Layer (Persistence, Events)     │
├─────────────────────────────────────────────────┤
│  Monitoring Layer (Health, Metrics, Experiments)│
└─────────────────────────────────────────────────┘
```

### Key Characteristics

- **Event-Driven:** Loose coupling via publish/subscribe
- **Async-First:** All I/O operations use AsyncIO
- **Multi-Project:** Isolated state per project with LRU caching
- **Resilient:** Comprehensive error handling with retry/circuit breaker
- **Observable:** Complete audit trail and experiment tracking

---

## 🚀 Quick Start for Different Roles

### For New Contributors

**Goal:** Understand the system to start contributing

1. **Start:** [ARCHITECTURE_SUMMARY.md](./ARCHITECTURE_SUMMARY.md) - Get the big picture (10 min read)
2. **Dive In:** [ARCHITECTURE.md](./ARCHITECTURE.md) - Understand each layer (30 min read)
3. **Visualize:** [C4_DIAGRAMS.md](./C4_DIAGRAMS.md) - See how components connect
4. **Decisions:** [adr/README.md](./adr/README.md) - Understand key architectural choices

**Key Sections:**
- Layer responsibilities → [ARCHITECTURE.md#2-core-components-and-layers](./ARCHITECTURE.md#2-core-components-and-layers)
- Directory structure → [ARCHITECTURE_SUMMARY.md#directory-structure](./ARCHITECTURE_SUMMARY.md#directory-structure)
- Design patterns → [ARCHITECTURE_SUMMARY.md#design-patterns](./ARCHITECTURE_SUMMARY.md#design-patterns)

### For Feature Development

**Goal:** Build features that align with architecture

1. **Check Patterns:** [ARCHITECTURE.md](./ARCHITECTURE.md) - Find similar features
2. **Review ADRs:** [adr/README.md](./adr/README.md) - Understand constraints
3. **See Flows:** [C4_DIAGRAMS.md](./C4_DIAGRAMS.md) - Understand data/control flow
4. **Follow Guidelines:** [ARCHITECTURE.md#15-development-guidelines](./ARCHITECTURE.md#15-development-guidelines)

**Common Tasks:**
- Adding MCP tool → See [ARCHITECTURE.md#21-entry-points--infrastructure](./ARCHITECTURE.md#21-entry-points--infrastructure)
- New integration → See [ADR-0006 (Kanban Abstraction)](./adr/README.md#future-adrs-planned)
- Database changes → See [ADR-0008 (SQLite Persistence)](./adr/0008-sqlite-primary-persistence.md)

### For Architecture Review

**Goal:** Evaluate proposed changes against architecture

1. **Review ADRs:** Check relevant architectural decisions
2. **Check Compliance:** Ensure changes align with patterns
3. **Assess Impact:** Review affected layers and components
4. **Validate:** Ensure tests follow structure

**Review Checklist:**
- ✅ Follows layer boundaries?
- ✅ Uses async-first design?
- ✅ Implements proper error handling?
- ✅ Maintains multi-project isolation?
- ✅ Includes comprehensive tests?

### For Debugging

**Goal:** Understand system behavior to fix bugs

1. **Find Component:** [ARCHITECTURE.md](./ARCHITECTURE.md) - Locate the relevant subsystem
2. **See Flow:** [C4_DIAGRAMS.md](./C4_DIAGRAMS.md) - Trace execution through sequence diagrams
3. **Check Events:** [ADR-0002 (Event-Driven)](./adr/0002-event-driven-communication.md) - Understand event flow
4. **Review Errors:** [ADR-0010 (Error Framework)](./adr/0010-comprehensive-error-framework.md) - Understand error handling

**Debugging Tools:**
- Event history → SQLite `events` table
- Conversations → SQLite `conversations` table
- Task diagnostics → `src/core/task_diagnostics.py`

### For System Understanding

**Goal:** Deep understanding of Marcus architecture

1. **Read Cover-to-Cover:** [ARCHITECTURE.md](./ARCHITECTURE.md)
2. **Study Diagrams:** [C4_DIAGRAMS.md](./C4_DIAGRAMS.md)
3. **Understand Decisions:** All ADRs in [adr/](./adr/)
4. **Explore Code:** Follow directory structure in summary

---

## 📖 Document Descriptions

### [ARCHITECTURE.md](./ARCHITECTURE.md) (33 KB)

**Complete architectural specification** - The definitive reference

**Contents:**
1. Overall Architecture Pattern
2. Core Components and Layers (6 layers detailed)
3. Domain Models (30+ models documented)
4. Integration Points (Kanban, AI, NLP)
5. Data Flow and Persistence
6. Event System
7. Multi-Project Support
8. Error Handling Framework
9. Task Management
10. Agent Coordination
11. Memory System
12. Workflows
13. Testing Strategy
14. Configuration
15. Development Guidelines

**When to Use:**
- Need detailed understanding of any component
- Implementing new features
- Onboarding new developers
- Architecture decisions

---

### [C4_DIAGRAMS.md](./C4_DIAGRAMS.md) (47 KB)

**Visual architecture documentation** - See the system

**Contents:**
- C1: System Context (Marcus in ecosystem)
- C2: Container Diagram (deployment architecture)
- C3: Component Diagrams (3 major subsystems)
- Sequence Diagrams (4 key workflows)
- Deployment Architecture
- Entity Relationships
- State Machines
- Technology Stack

**When to Use:**
- Understanding system structure visually
- Explaining architecture to stakeholders
- Finding component relationships
- Tracing workflows

**Diagrams:**
1. **Project Creation** - Full workflow from description to Kanban
2. **Task Assignment** - Lease-based assignment with reconciliation
3. **Agent Coordination** - Multi-agent task execution
4. **Post-Project Analysis** - Historical data collection and analysis

---

### [ARCHITECTURE_SUMMARY.md](./ARCHITECTURE_SUMMARY.md) (9 KB)

**Quick reference guide** - Fast answers

**Contents:**
- Key Metrics (LoC, files, test coverage)
- 6-Layer Architecture Overview
- Design Patterns with Locations
- Domain Models Summary
- Critical Files
- Testing Strategy
- Configuration

**When to Use:**
- Quick lookup of facts
- Finding where code lives
- Getting overview before deep dive
- Reference during development

---

### [adr/README.md](./adr/README.md) - Architecture Decision Records

**Why decisions were made** - Historical context

**Current ADRs:**
1. [Layered Architecture with DDD](./adr/0001-layered-architecture-with-ddd.md)
2. [Event-Driven Communication](./adr/0002-event-driven-communication.md)
3. [Multi-Project Support](./adr/0003-multi-project-support.md)
4. [Async-First Design](./adr/0004-async-first-design.md)
5. [SQLite as Primary Persistence](./adr/0008-sqlite-primary-persistence.md)
6. [Comprehensive Error Framework](./adr/0010-comprehensive-error-framework.md)

**When to Use:**
- Understanding why architecture is the way it is
- Reconsidering past decisions
- Making new architectural decisions
- Learning from alternatives considered

---

## 🎯 Key Architectural Decisions

### Why Layered Architecture?

**Decision:** [ADR-0001](./adr/0001-layered-architecture-with-ddd.md)

- ✅ Clear separation of concerns
- ✅ Testability (80%+ coverage achieved)
- ✅ Maintainability as system grows
- ⚠️ Complexity for simple operations

### Why Event-Driven?

**Decision:** [ADR-0002](./adr/0002-event-driven-communication.md)

- ✅ Loose coupling between components
- ✅ Complete audit trail
- ✅ Easy to add new features
- ⚠️ Debugging complexity

### Why AsyncIO?

**Decision:** [ADR-0004](./adr/0004-async-first-design.md)

- ✅ 10x performance improvements
- ✅ Concurrent agent support
- ✅ Non-blocking I/O
- ⚠️ Learning curve

### Why SQLite?

**Decision:** [ADR-0008](./adr/0008-sqlite-primary-persistence.md)

- ✅ Single source of truth
- ✅ Powerful queries (SQL)
- ✅ ACID guarantees
- ⚠️ Single writer limitation

---

## 📊 System Statistics

**Codebase:**
- Total Lines: ~89,500
- Python Modules: 202
- Test Coverage: 80%+
- Python Version: 3.11+

**Architecture:**
- Layers: 6
- Core Packages: 33
- Domain Models: 30+
- MCP Tools: 30+

**Performance:**
- Project Creation: ~8s (10x improvement from 80s)
- Context Switch: ~5ms
- Max Concurrent Projects: 10 (configurable)
- Database Query: <10ms (typical)

---

## 🛠️ Development Workflow

### Following Architecture Guidelines

1. **Layer Placement:**
   - New domain logic → `src/core/`
   - New integration → `src/integrations/`
   - New MCP tool → `src/marcus_mcp/tools/`
   - New workflow → `src/workflows/`

2. **Design Patterns:**
   - Use event bus for cross-layer communication
   - Implement error handling with Marcus error framework
   - Use async/await for all I/O
   - Follow DDD patterns for domain models

3. **Testing:**
   - Unit tests in `tests/unit/` (mocked dependencies)
   - Integration tests in `tests/integration/` (real services)
   - Follow TDD approach
   - Maintain 80%+ coverage

4. **Documentation:**
   - Update architecture docs when structure changes
   - Create ADR for significant decisions
   - Add docstrings (numpy-style)

---

## 🔗 Related Documentation

- **Implementation Plans:** `/docs/implementation/`
- **API Reference:** `/docs/api-reference/`
- **User Guide:** `/docs/user-guide/`
- **Design Documents:** `/docs/design/`
- **Experiments:** `/docs/experiments/`

---

## 🤝 Contributing to Architecture

### When to Update Architecture Docs

Update when:
- Adding new layers or major components
- Changing component relationships
- Introducing new patterns
- Making architectural decisions
- Refactoring subsystems

### How to Update

1. **For Small Changes:**
   - Update relevant sections in ARCHITECTURE.md
   - Update diagrams if structure changed
   - Update summary if metrics changed

2. **For Major Changes:**
   - Create new ADR documenting decision
   - Update all affected diagrams
   - Update architecture document
   - Update summary and README

3. **Pull Request Process:**
   - Include architecture changes in PR description
   - Link to relevant ADRs
   - Explain impact on system

---

## 📚 Additional Resources

### External References

- [Domain-Driven Design (Eric Evans)](https://www.domainlanguage.com/ddd/)
- [Clean Architecture (Robert Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Python AsyncIO](https://docs.python.org/3/library/asyncio.html)
- [C4 Model](https://c4model.com/)
- [Architecture Decision Records](https://adr.github.io/)

### Internal References

- Main README: `/README.md`
- Contributing Guide: (to be created)
- Code of Conduct: (to be created)

---

## ❓ FAQ

**Q: Where should new domain logic go?**
A: `src/core/` - Keep domain layer pure, no external dependencies

**Q: How do I add a new integration?**
A: `src/integrations/` - Implement provider interface, see Kanban providers as example

**Q: When should I create an ADR?**
A: For any decision that affects system structure, technology choice, or patterns

**Q: How do I understand a specific workflow?**
A: Check sequence diagrams in C4_DIAGRAMS.md, then trace code from entry point

**Q: Where are MCP tools defined?**
A: `src/marcus_mcp/tools/` - Each tool group in separate file

**Q: How do I add a new database table?**
A: Create migration, update schema in ADR-0008, update models in `src/core/models.py`

---

## 📞 Getting Help

- **Architecture Questions:** Review ADRs and architecture docs
- **Implementation Questions:** Check ARCHITECTURE.md for patterns
- **Bugs:** Check task diagnostics and error monitoring
- **Features:** Review workflows and integration examples

---

**Last Updated:** 2024-11-08
**Maintained By:** Marcus Core Team
**Status:** Living Documentation

This architecture documentation is continuously updated as Marcus evolves. Always check the latest version in the repository.
