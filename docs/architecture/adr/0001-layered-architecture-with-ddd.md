# ADR 0001: Layered Architecture with Domain-Driven Design

**Status:** Accepted

**Date:** 2024-11 (Initial Implementation)

**Deciders:** Marcus Core Team

---

## Context

Marcus is a multi-agent coordination system that needs to:
- Manage complex task workflows across multiple projects
- Integrate with multiple external systems (Kanban providers, AI/LLM services)
- Provide clear separation of concerns for maintainability
- Scale to handle multiple concurrent projects and agents
- Support extensibility for new features and integrations

We needed an architectural pattern that would provide:
1. Clear boundaries between different system concerns
2. Testability and maintainability
3. Flexibility to add new integrations without affecting core logic
4. Rich domain models that encapsulate business rules
5. Independent evolution of different layers

---

## Decision

We will adopt a **Layered Architecture with Domain-Driven Design (DDD)** principles, organized into six distinct layers:

### Layer Structure

1. **Presentation Layer** (MCP Server, CLI)
   - MCP protocol implementation with 30+ tools
   - CLI interface for direct user interaction
   - Transport modes: HTTP, stdio, multi-endpoint

2. **Application Layer** (Workflows, Orchestration)
   - Project creation workflow
   - Task assignment workflow
   - Agent coordination logic
   - Experiment tracking

3. **Domain Layer** (Core Business Logic)
   - Rich domain models (Task, Agent, Project, Memory)
   - Business rules and invariants
   - Domain events
   - Task dependency graphs

4. **Integration Layer** (External Services)
   - Kanban provider abstraction (Planka, GitHub, Linear)
   - AI/LLM provider abstraction (OpenAI, Anthropic, Ollama)
   - NLP parsing services

5. **Infrastructure Layer** (Technical Concerns)
   - SQLite persistence
   - File system operations
   - Event bus implementation
   - Logging and monitoring

6. **Monitoring Layer** (Observability)
   - Health checks
   - Experiment tracking (MLflow)
   - Performance metrics
   - Error monitoring

### Domain-Driven Design Principles

- **Bounded Contexts:** Clear separation between Project Management, Agent Coordination, Task Execution, and Integration contexts
- **Aggregates:** Task (with subtasks), Project (with state), Agent (with workspace)
- **Value Objects:** TaskStatus, Priority, AgentRole
- **Domain Events:** TaskCreated, TaskAssigned, TaskCompleted, ProjectStateChanged
- **Repositories:** Task persistence, Project history, Assignment storage

---

## Consequences

### Positive

✅ **Clear Separation of Concerns**
- Each layer has well-defined responsibilities
- Changes in one layer rarely affect others
- Easy to understand system structure

✅ **Testability**
- Unit tests can focus on individual layers
- Mock external dependencies easily
- 80%+ test coverage achieved

✅ **Maintainability**
- New developers can understand the system quickly
- Changes are localized to specific layers
- Refactoring is safer with clear boundaries

✅ **Extensibility**
- New Kanban providers added without core changes
- New AI providers integrated via abstraction layer
- New MCP tools added independently

✅ **Rich Domain Model**
- Business logic lives in domain entities
- Complex rules encapsulated in domain objects
- Type safety with Python 3.11+ type hints

✅ **Independent Evolution**
- Infrastructure can be swapped (SQLite → PostgreSQL)
- Integration protocols can change independently
- UI/API can evolve without domain changes

### Negative

⚠️ **Complexity for Simple Operations**
- Some operations cross multiple layers
- Requires understanding the full layer stack
- More code than a monolithic approach

⚠️ **Potential Performance Overhead**
- Data transformations between layers
- Multiple abstraction layers can add latency
- Mitigation: Async-first design, caching

⚠️ **Learning Curve**
- New contributors need to understand DDD concepts
- Layer boundaries must be respected
- Mitigation: Comprehensive documentation

⚠️ **Risk of Anemic Domain Models**
- Temptation to put logic in application layer
- Requires discipline to keep domain rich
- Mitigation: Code reviews, architectural guidelines

---

## Implementation Details

### Directory Structure
```
src/
├── marcus_mcp/          # Presentation Layer
│   └── server.py
├── workflows/           # Application Layer
│   ├── project_creation_workflow.py
│   └── task_assignment_workflow.py
├── core/                # Domain Layer
│   ├── models.py
│   ├── events.py
│   └── memory.py
├── integrations/        # Integration Layer
│   ├── kanban/
│   └── ai/
└── infrastructure/      # Infrastructure Layer
    └── persistence.py
```

### Layer Communication Rules

1. **Dependency Direction:** Outer layers depend on inner layers
   - Presentation → Application → Domain
   - Integration → Domain
   - Infrastructure → Domain

2. **Domain Independence:** Domain layer has NO dependencies on outer layers
   - Pure business logic
   - Framework-agnostic
   - No infrastructure concerns

3. **Abstractions at Boundaries:** Interfaces define layer contracts
   - `KanbanProvider` interface for integrations
   - `LLMProvider` interface for AI services
   - `Repository` interfaces for persistence

---

## Alternatives Considered

### 1. Microservices Architecture
**Rejected** because:
- Overkill for current scale (~90k LoC)
- Operational complexity (deployment, monitoring)
- Network latency between services
- Single codebase easier to maintain

**When to Reconsider:**
- Team size > 20 developers
- Need independent deployment of components
- Horizontal scaling requirements

### 2. Clean Architecture (Hexagonal/Ports & Adapters)
**Partially Adopted:**
- We use the abstraction principles (ports/adapters)
- Integration layer acts as adapters
- Domain layer is the core hexagon

**Why Not Pure Hexagonal:**
- Adds complexity without clear benefits for our use case
- Layered architecture is more familiar to Python developers
- We get the key benefits (testability, flexibility) with simpler structure

### 3. Monolithic Architecture
**Rejected** because:
- Tight coupling makes changes risky
- Hard to test individual components
- Difficult to swap integrations
- Poor separation of concerns

---

## Related Decisions

- [ADR-0002: Event-Driven Communication](./0002-event-driven-communication.md)
- [ADR-0003: Multi-Project Support](./0003-multi-project-support.md)
- [ADR-0004: Async-First Design](./0004-async-first-design.md)
- [ADR-0008: SQLite as Primary Persistence](./0008-sqlite-primary-persistence.md)

---

## References

- [Domain-Driven Design by Eric Evans](https://www.domainlanguage.com/ddd/)
- [Clean Architecture by Robert Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Layered Architecture Pattern](https://www.oreilly.com/library/view/software-architecture-patterns/9781491971437/ch01.html)

---

## Notes

This architecture has served Marcus well through:
- Initial MVP (3 weeks)
- Post-project analysis implementation (3 phases)
- Multi-project support
- 202 Python modules, ~89,500 LoC
- 80%+ test coverage maintained

The key to success has been **discipline in maintaining layer boundaries** and **investing in clear abstractions**.
