# Marcus Architecture Documentation

This directory contains comprehensive architecture documentation for the Marcus Multi-Agent Resource Coordination and Understanding System.

## Documents

### 1. **ARCHITECTURE.md** (32 KB, 15 sections)
The complete architecture specification covering:

- **Overall Architecture Pattern** - Layered + Event-Driven + Domain-Driven Design
- **Core Components and Layers** - Detailed breakdown of all 12 major component layers
- **Key Domain Models** - Task, ProjectState, WorkerStatus, Decision, etc.
- **Integration Points** - Kanban boards, AI/LLM providers, MCP protocol
- **Data Flow Architecture** - Request/response flows, project lifecycle, events
- **Key Workflows** - Project creation, task assignment, agent coordination, experiments
- **Technology Stack** - Languages, frameworks, async patterns, testing approach
- **Error Handling Framework** - Error hierarchy, strategies, resilience patterns
- **Multi-Project Support** - Project registry, context management, isolation
- **Deployment Architecture** - Docker, transport modes, process management
- **Learning & Adaptation** - Memory systems, agent profiling, optimization
- **Visualization & Monitoring** - Real-time dashboards, event-driven visualization
- **Security & Isolation** - Workspace isolation, access control
- **Configuration Management** - Config sources, multi-project setup
- **Architectural Principles & Patterns** - Design principles, common patterns

**Best for:** Understanding complete architecture, implementation details, domain models

### 2. **C4_DIAGRAMS.md** (46 KB, comprehensive visual representations)
C4 model diagrams showing architecture at different abstraction levels:

- **C1: System Context Diagram** - Marcus in external ecosystem
- **C2: Container Diagram** - High-level containers and deployment units
- **C3: Component Diagrams** - Deep dives into major subsystems:
  - Core Domain Layer (src/core/)
  - Integration Layer (src/integrations/)
  - MCP Server & Tools (src/marcus_mcp/)
- **Sequence Diagrams** - Detailed interactions for:
  - Project creation flow
  - Task assignment workflow
  - Task completion and context propagation
  - Multi-project switching
- **Deployment Architecture** - Docker Compose setup
- **Data Model Relationships** - Entity relationship diagrams
- **State Machines** - Task lifecycle and lease states
- **Technology Stack Visualization** - Layered technology view

**Best for:** Visual understanding, creating additional diagrams, presentation materials

### 3. **ARCHITECTURE_SUMMARY.md** (9.2 KB, quick reference)
Quick reference guide with key information:

- **Key Metrics** - Codebase size, file count, test coverage
- **Architecture Pattern Overview** - 6-layer architecture breakdown
- **Data Flow Diagrams** - Primary flows and their sequences
- **Key Patterns** - Factory, Strategy, Observer, Adapter, etc.
- **Domain Models** - Essential entities and relationships
- **Error Handling Strategy** - Approach to resilience
- **Multi-Project Support** - LRU caching, isolation, lifecycle
- **Testing Strategy** - Test organization and requirements
- **Configuration Management** - Config loading and precedence
- **Technology Stack** - Essential dependencies
- **Key Files by Purpose** - Critical files organized by function
- **Architectural Principles** - Design philosophy
- **Critical Dependencies** - Essential libraries
- **Security Considerations** - Key security patterns

**Best for:** Quick lookup, orientation for new contributors, presentation notes

---

## How to Use This Documentation

### For Architecture Understanding
1. Start with **ARCHITECTURE_SUMMARY.md** for a quick overview
2. Read **ARCHITECTURE.md** section 1 (Overall Pattern) for context
3. Explore specific sections in **ARCHITECTURE.md** based on your interest
4. Reference **C4_DIAGRAMS.md** for visual representations

### For Implementation
1. Check **ARCHITECTURE.md** section 2 (Core Components) for module organization
2. Review **ARCHITECTURE.md** section 3 (Domain Models) for entity definitions
3. Study **ARCHITECTURE.md** section 6 (Key Workflows) for process flows
4. Reference **C4_DIAGRAMS.md** sequence diagrams for interactions

### For Creating New Components
1. Review **ARCHITECTURE.md** section 15 (Patterns) for design guidance
2. Check **ARCHITECTURE.md** section 4 (Integration Points) for adapter patterns
3. Study **ARCHITECTURE.md** section 8 (Error Handling) for error approach
4. Follow patterns in **ARCHITECTURE_SUMMARY.md** (Key Patterns)

### For Debugging & Troubleshooting
1. Check **ARCHITECTURE.md** section 5 (Data Flow) to understand request paths
2. Review **ARCHITECTURE.md** section 6 (Key Workflows) for normal execution
3. Reference **C4_DIAGRAMS.md** sequence diagrams for expected interactions
4. Study **ARCHITECTURE.md** section 8 (Error Handling) for recovery strategies

### For Adding New Features
1. Identify relevant layer in **ARCHITECTURE_SUMMARY.md** (Layer 1-6)
2. Review **ARCHITECTURE.md** section 2 (Core Components) for similar components
3. Check **ARCHITECTURE.md** section 15 (Patterns) for applicable design patterns
4. Follow test patterns from **ARCHITECTURE.md** section 7 (Testing Approach)

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: Presentation (MCP Server)                 │
│           ├── HTTP/Stdio Transport                  │
│           ├── Tool Handlers (30+ tools)             │
│           └── Request/Response Serialization        │
├─────────────────────────────────────────────────────┤
│  Layer 2: Application/Orchestration                 │
│           ├── Project Workflows                     │
│           ├── Task Assignment Orchestration         │
│           └── Operational Modes                     │
├─────────────────────────────────────────────────────┤
│  Layer 3: Domain (Core Business Logic)              │
│           ├── Task, ProjectState, WorkerStatus      │
│           ├── Context & Memory Systems              │
│           ├── Events & Pub/Sub                      │
│           ├── Multi-Project Support                 │
│           └── Error Handling & Recovery             │
├─────────────────────────────────────────────────────┤
│  Layer 4: Integration (External Systems)            │
│           ├── Kanban Abstraction                    │
│           ├── AI/LLM Providers                      │
│           ├── NLP & Task Parsing                    │
│           └── Cost Tracking                         │
├─────────────────────────────────────────────────────┤
│  Layer 5: Infrastructure                            │
│           ├── Persistence (SQLite + JSON)           │
│           ├── Logging & Conversation History        │
│           └── Communication Hub                     │
├─────────────────────────────────────────────────────┤
│  Layer 6: Monitoring & Analytics                    │
│           ├── Project/Assignment Monitoring         │
│           ├── Experiment Tracking (MLflow)          │
│           └── Visualization & Pipeline              │
└─────────────────────────────────────────────────────┘
```

## Key Design Decisions

1. **Layered Architecture** - Clear separation of concerns, easier testing
2. **Event-Driven Communication** - Loose coupling between systems
3. **Domain-Driven Design** - Rich domain models (Task, Project, Decision)
4. **Provider Pattern** - Easy to add new Kanban or AI providers
5. **Async-First** - All I/O non-blocking for better concurrency
6. **Multi-Project Isolation** - LRU-cached contexts per project
7. **Lease-Based Assignment** - Timeout-based task locking for concurrency
8. **Learning System** - Agent profiling and pattern learning from execution

## Critical Files Map

**Entry Points:**
- `/marcus` - CLI entrypoint
- `src/marcus_mcp/server.py` - MCP server initialization

**Domain Models:**
- `src/core/models.py` - Task, ProjectState, WorkerStatus, etc.

**Core Systems:**
- `src/core/context.py` - Context for task assignments
- `src/core/events.py` - Event pub/sub system
- `src/core/memory.py` - Learning system
- `src/core/persistence.py` - Storage abstraction
- `src/core/project_history.py` - Decision/artifact storage

**Integration:**
- `src/integrations/kanban_interface.py` - Kanban abstraction
- `src/ai/providers/` - AI provider implementations

**Tools/API:**
- `src/marcus_mcp/tools/` - 30+ MCP tools

**Configuration:**
- `src/config/config_loader.py` - Config loading

---

## Useful Commands for Exploration

```bash
# View architecture documentation
cat docs/ARCHITECTURE.md

# Find all files in core layer
find src/core -name "*.py" -type f | head -20

# Check total lines of code
find src -name "*.py" -type f | xargs wc -l | tail -1

# View module structure
tree -L 2 src/ -d

# Test coverage
pytest --cov=src --cov-report=term-missing

# Type checking
mypy --strict src/

# List all MCP tools
ls src/marcus_mcp/tools/

# View error hierarchy
grep "^class.*Error" src/core/error_framework.py
```

---

## Architecture Decisions Document

This documentation captures the current state of the architecture as of:
- **Date:** November 8, 2025
- **Branch:** feature/post-project-analysis-phase1
- **Codebase Size:** 89,500 LOC across 202 files

For more recent decisions or changes, check:
- Git commit history
- Open pull requests
- GitHub discussions

---

## Contributing

When modifying architecture:

1. **Document Changes** - Update relevant sections in ARCHITECTURE.md
2. **Update Diagrams** - Modify C4_DIAGRAMS.md if structure changes
3. **Sync Summary** - Keep ARCHITECTURE_SUMMARY.md in sync
4. **Code & Tests** - Follow patterns in section 15 of ARCHITECTURE.md
5. **Error Handling** - Use Marcus error framework (section 8)
6. **Type Safety** - Run mypy strict mode
7. **Test Coverage** - Maintain 80% minimum coverage

---

## Questions & Feedback

For questions about architecture:
- Check ARCHITECTURE.md for detailed explanations
- Review C4_DIAGRAMS.md for visual representations
- Consult ARCHITECTURE_SUMMARY.md for quick lookups
- Check code comments in key files
- Review git history for context of decisions

---

Generated with comprehensive codebase analysis on November 8, 2025.
