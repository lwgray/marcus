# Marcus MVP Implementation Plan

**Last Updated**: 2025-01-11
**Status**: Not Started
**Timeline**: 6 weeks + 2-3 days (Week 5.5)
**Version**: 2.1 (Modular + REST API Completion)

---

## Overview

This document provides a high-level overview of the Marcus MVP implementation plan. The detailed day-by-day implementation instructions have been organized into weekly documents for easier navigation.

## Quick Navigation

- **[Week 1: Configuration & Foundation](implementation/WEEK_1_PLAN.md)** - Centralize configuration management
- **[Week 2: Workspace Isolation - Phase 1 (Foundation)](implementation/WEEK_2_PLAN.md)** - Add Feature entity and prepare infrastructure
- **[Week 3: Workspace Isolation - Phase 2 (Git Worktrees)](implementation/WEEK_3_PLAN.md)** - Implement git worktree-based workspace isolation
- **[Week 4: Feature Context Aggregation](implementation/WEEK_4_PLAN.md)** - Implement comprehensive feature context building
- **[Week 5: Telemetry & CATO Integration](implementation/WEEK_5_PLAN.md)** - Add user journey tracking and CATO dashboard integration
- **[Week 5.5: REST API Completion (CRITICAL)](implementation/WEEK_5.5_PLAN.md)** - Add Launch Tab REST APIs and Terminal Streaming
- **[Week 6: Production Readiness & MVP Release](implementation/WEEK_6_PLAN.md)** - Core validations, pip packaging, and MVP release

---

## Implementation Timeline

### Week 1: Configuration & Foundation
**Goal**: Centralize configuration management to enable easy deployment and packaging.

**Key Deliverables**:
- Type-safe configuration system (`src/config/marcus_config.py`)
- Validation with clear error messages
- Environment variable override support
- `config_marcus.example.json` template
- Configuration documentation
- Migration of existing code

**Status**: ⏳ Not Started
**Related Issue**: #68
**Details**: [Week 1 Plan](implementation/WEEK_1_PLAN.md)

---

### Week 2: Workspace Isolation - Phase 1 (Foundation)
**Goal**: Add Feature entity and prepare infrastructure for workspace isolation.

**Key Deliverables**:
- Project and Feature dataclasses
- Feature-aware artifact and decision logging
- Feature indexing system
- WorkspaceManager skeleton

**Status**: ⏳ Not Started
**Details**: [Week 2 Plan](implementation/WEEK_2_PLAN.md)

---

### Week 3: Workspace Isolation - Phase 2 (Git Worktrees)
**Goal**: Implement git worktree-based workspace isolation for parallel task execution.

**Key Deliverables**:
- Full WorkspaceManager implementation
- Git worktree creation and cleanup
- Workspace conflict detection
- Integration with task assignment

**Status**: ⏳ Not Started
**Details**: [Week 3 Plan](implementation/WEEK_3_PLAN.md)

---

### Week 4: Feature Context Aggregation
**Goal**: Implement comprehensive feature context building with automatic aggregation.

**Key Deliverables**:
- FeatureContextBuilder
- Git commit tracking and annotation
- Context injection system
- `get_feature_context` and `get_feature_status` MCP tools

**Status**: ⏳ Not Started
**Details**: [Week 4 Plan](implementation/WEEK_4_PLAN.md)

---

### Week 5: Telemetry & CATO Integration
**Goal**: Add user journey tracking and integrate with CATO dashboard for real-time visualization.

**Key Deliverables**:
- User journey tracking system
- Research event logging
- CATO dashboard integration API
- Real-time event broadcasting (SSE)

**Status**: ⏳ Not Started
**Details**: [Week 5 Plan](implementation/WEEK_5_PLAN.md)

---

### Week 5.5: REST API Completion (CRITICAL)
**Goal**: Complete REST API endpoints and terminal streaming infrastructure required for CATO bundling.

**Key Deliverables**:
- Launch Tab REST APIs (`POST /api/agents`, `GET /api/agents`, `POST /api/projects`, `GET /api/projects`, `POST /api/tasks`, `GET /api/tasks`)
- Terminal streaming infrastructure (TerminalManager with PTY sessions)
- Terminal streaming API (`GET /api/agents/{agent_id}/terminal/stream`, `POST /api/agents/{agent_id}/terminal/input`)
- Command injection support for agent recovery

**Status**: ⏳ Not Started
**Duration**: 2-3 days
**Details**: [Week 5.5 Plan](implementation/WEEK_5.5_PLAN.md)

**Why Critical**: Week 5 implemented `/api/cato/*` endpoints for Live/Historical tabs, but Launch and Terminals tabs need different APIs. Without Week 5.5, CATO bundling (Weeks 8-11) will have non-functional Launch and Terminals tabs.

---

### Week 6: Production Readiness & MVP Release
**Goal**: Implement core validations, pip packaging, comprehensive documentation, and prepare for MVP release.

**Key Deliverables**:
- Core validations (Issues #118-125)
- Pip packaging setup (`pip install marcus`)
- Comprehensive user documentation
- Performance testing and bug fixes
- MVP release (v0.1.0)

**Status**: ⏳ Not Started
**Details**: [Week 6 Plan](implementation/WEEK_6_PLAN.md)

---

## Architecture Overview

### Core Components

```
Marcus MVP Architecture
│
├─ Configuration System (Week 1)
│  ├─ Type-safe dataclasses
│  ├─ Validation framework
│  └─ Environment override support
│
├─ Workspace Isolation (Weeks 2-3)
│  ├─ Project & Feature entities
│  ├─ Git worktree management
│  └─ Conflict prevention
│
├─ Feature Context (Week 4)
│  ├─ FeatureContextBuilder
│  ├─ Git commit tracking
│  ├─ Artifact aggregation
│  └─ Decision history
│
├─ Telemetry & Observability (Week 5)
│  ├─ User journey tracking
│  ├─ Research event logging
│  ├─ CATO integration API (/api/cato/*)
│  └─ Real-time event streaming
│
├─ REST API Completion (Week 5.5) [CRITICAL]
│  ├─ Launch Tab APIs (/api/agents, /api/projects, /api/tasks)
│  ├─ Terminal streaming infrastructure (PTY management)
│  ├─ Terminal streaming API (/api/agents/{id}/terminal/stream)
│  └─ Command injection for agent recovery
│
└─ Production Readiness (Week 6)
   ├─ Core validations
   ├─ Pip packaging (pip install marcus)
   ├─ Comprehensive documentation
   └─ Release automation
```

### Data Flow

```
Agent Request
    ↓
MarcusServer (MCP)
    ↓
Task Orchestrator
    ↓
Workspace Manager (git worktrees)
    ↓
Feature Context Builder
    ↓
Task Execution (isolated workspace)
    ↓
Artifacts & Decisions (logged with feature_id)
    ↓
Feature Index (queryable context)
    ↓
Telemetry Events (user journey, research)
    ↓
CATO Dashboard (real-time visualization)
```

---

## Key Features

### 1. Configuration Management (Week 1)
- **Type-safe configuration** with dataclass validation
- **Single source of truth** for all settings
- **Environment variable overrides** for deployment flexibility
- **Clear validation errors** at startup

### 2. Workspace Isolation (Weeks 2-3)
- **Git worktree-based isolation** for parallel development
- **Automatic feature branch management**
- **Conflict prevention** between concurrent agents
- **Clean workspace lifecycle** (create → use → cleanup)

### 3. Feature Context Aggregation (Week 4)
- **Automatic context building** from git commits, artifacts, decisions
- **Queryable context** via `get_feature_context` tool
- **Context injection** for informed agent work
- **Feature status tracking** with progress visibility

### 4. Telemetry & Observability (Week 5)
- **User journey tracking** with milestones
- **Research event logging** for MAS studies
- **CATO integration** for real-time visualization
- **Event broadcasting** with pub-sub pattern

### 5. REST API Completion (Week 5.5) [CRITICAL]
- **Launch Tab REST APIs** for agent registration, project creation, task management
- **Terminal streaming infrastructure** with PTY session management
- **Real-time terminal output** via Server-Sent Events
- **Command injection** for stuck agent recovery

### 6. Production Readiness (Week 6)
- **Core validations** (7 critical validations implemented)
- **Pip packaging** with `pip install marcus`
- **Comprehensive documentation** (README, QUICKSTART, API Reference)
- **Release automation** with validation scripts

---

## Success Metrics

### Code Metrics
- **Files Added**: 50+
- **Lines of Code**: ~15,000
- **Tests Written**: 100+
- **Test Coverage**: 95%+
- **Documentation Pages**: 20+

### Feature Completeness
- ⏳ Configuration centralization (#68)
- ⏳ Workspace isolation with git worktrees
- ⏳ Feature context aggregation
- ⏳ Git commit tracking and annotation
- ⏳ User journey tracking
- ⏳ Research event logging
- ⏳ CATO dashboard integration
- ⏳ Real-time event broadcasting
- ⏳ Launch Tab REST APIs (Week 5.5)
- ⏳ Terminal streaming infrastructure (Week 5.5)
- ⏳ Core validations (#118-125)
- ⏳ Pip packaging
- ⏳ Comprehensive documentation

### Quality Gates
- ⏳ All unit tests pass
- ⏳ All integration tests pass
- ⏳ Test coverage >= 95%
- ⏳ All mypy checks pass
- ⏳ All pre-commit hooks pass
- ⏳ Pip install works successfully
- ⏳ Documentation complete

---

## Implementation Principles

### For Junior Engineers
Each weekly plan follows these principles:
- **Step-by-step instructions** with no assumed knowledge
- **Complete code examples** for every file
- **Explanation of "why"** for every decision
- **Test-first approach** with tests before implementation
- **Clear success criteria** for each task

### Testing Strategy
- **Unit tests** for isolated components (< 100ms)
- **Integration tests** for end-to-end workflows
- **Mock external dependencies** in unit tests
- **One logical assertion per test**
- **Descriptive test names** following `test_[what]_[when]_[expected]` pattern

### Error Handling
- **Marcus Error Framework** for user-facing errors
- **Circuit breakers** for external services
- **Retry logic** with exponential backoff
- **Graceful degradation** when features unavailable
- **Clear error messages** with actionable solutions

---

## Getting Started

### Prerequisites
- Python 3.11+
- Git
- Kanban board (Planka, GitHub Projects, or Linear)
- AI provider API key (Anthropic, OpenAI)

### Quick Start

1. **Install Marcus:**
   ```bash
   pip install marcus
   ```

2. **Configure Marcus:**
   ```bash
   cp config_marcus.example.json config_marcus.json
   # Edit config_marcus.json with your settings
   ```

3. **Set environment variables:**
   ```bash
   export ANTHROPIC_API_KEY="your-api-key" # pragma: allowlist secret
   export PLANKA_BASE_URL="http://localhost:3333"
   export PLANKA_AGENT_EMAIL="demo@demo.demo"
   export PLANKA_AGENT_PASSWORD="demo" # pragma: allowlist secret
   ```

4. **Start Marcus:**
   ```bash
   marcus start
   ```

5. **Verify installation:**
   ```bash
   curl http://localhost:4298/health
   ```

For detailed configuration options, see [Configuration Guide](../CONFIGURATION.md).

---

## Weekly Implementation Details

For detailed day-by-day implementation instructions, see the individual weekly plans:

- **[Week 1: Configuration & Foundation](implementation/WEEK_1_PLAN.md)**
  - Monday: Create configuration data structure
  - Tuesday: Add validation & environment overrides
  - Wednesday: Migrate existing code
  - Thursday: Create config_marcus.example.json
  - Friday: Testing, documentation & backward compatibility

- **[Week 2: Workspace Isolation - Phase 1](implementation/WEEK_2_PLAN.md)**
  - Monday: Add Project and Feature entities
  - Tuesday: Extend artifact and decision logging with feature_id
  - Wednesday: Artifact and decision indexing by feature
  - Thursday: Create WorkspaceManager skeleton
  - Friday: Week 2 integration & testing

- **[Week 3: Workspace Isolation - Phase 2](implementation/WEEK_3_PLAN.md)**
  - Monday: Implement git worktree creation
  - Tuesday: Implement workspace cleanup
  - Wednesday: Integrate with task assignment
  - Thursday: Add workspace conflict detection
  - Friday: Week 3 testing & documentation

- **[Week 4: Feature Context Aggregation](implementation/WEEK_4_PLAN.md)**
  - Monday: Create FeatureContextBuilder
  - Tuesday: Implement git commit tracking
  - Wednesday: Implement context injection
  - Thursday: Add get_feature_context MCP tool
  - Friday: Add get_feature_status tool & testing

- **[Week 5: Telemetry & CATO Integration](implementation/WEEK_5_PLAN.md)**
  - Monday: User journey tracking
  - Tuesday: Research event logging
  - Wednesday: CATO dashboard integration API
  - Thursday: Real-time event broadcasting
  - Friday: Week 5 testing & documentation

- **[Week 5.5: REST API Completion (CRITICAL)](implementation/WEEK_5.5_PLAN.md)**
  - Day 1: Launch Tab REST APIs (agent registration, projects, tasks)
  - Day 2-3: Terminal streaming infrastructure (PTY + SSE streaming)

- **[Week 6: Production Readiness & MVP Release](implementation/WEEK_6_PLAN.md)**
  - Monday: Core validations (Issues #118-125)
  - Tuesday: Pip packaging setup
  - Wednesday: Documentation & examples
  - Thursday: Final testing & bug fixes
  - Friday: MVP release preparation

---

## Support & Resources

### Documentation
- [Configuration Guide](../CONFIGURATION.md)
- [Installation Guide](../INSTALLATION.md)
- [API Reference](api/README.md)
- [Testing Guide](testing/MANUAL_TEST_CHECKLIST.md)

### Design Documents
- [Workspace Isolation Design](design/workspace-isolation-and-feature-context.md)
- [Feature Context Design](design/feature-context.md)
- [Telemetry Design](design/telemetry-system.md)

### Community
- [GitHub Issues](https://github.com/yourusername/marcus/issues)
- [Discussions](https://github.com/yourusername/marcus/discussions)
- [Contributing Guide](../CONTRIBUTING.md)

---

## Release Notes

### v0.1.0 (MVP Release) - 2025-01-15

**Features Added**:
- Task Orchestration with dependency management
- Workspace Isolation with git worktrees
- Feature Context with automatic aggregation
- Kanban Boards integration (Planka)
- CATO Dashboard with real-time visualization
- User Journey Tracking with milestone tracking
- Research Event Logging for MAS studies
- Event Broadcasting with pub-sub pattern
- REST APIs for Launch Tab (agent registration, projects, tasks)
- Terminal Streaming Infrastructure (PTY + SSE)
- Validation Framework (7 core validations)
- Pip Package Support (`pip install marcus`)
- Comprehensive documentation and examples

**Testing**:
- 100+ tests with 95%+ coverage
- Unit tests for all core components
- Integration tests for end-to-end workflows
- Performance tests for system scalability

**Documentation**:
- Complete API reference
- Installation guide (pip install)
- Quick start guide
- Configuration guide
- Example projects

See [CHANGELOG.md](../CHANGELOG.md) for complete release history.

---

## **Implementation Status**

⏳ **Not Started** - The 6-week + 2-3 day MVP implementation is ready to begin.

### Summary

**Week 1**: Configuration & Foundation (Not Started)
- Configuration centralization (#68)
- Type-safe configuration system
- Validation framework
- Environment variable overrides

**Week 2**: Workspace Isolation - Phase 1 (Not Started)
- Feature entity and infrastructure
- Feature-aware artifact and decision logging
- Feature indexing system
- WorkspaceManager skeleton

**Week 3**: Workspace Isolation - Phase 2 (Not Started)
- Git worktree implementation
- Workspace conflict detection
- Integration with task assignment

**Week 4**: Feature Context (Not Started)
- FeatureContextBuilder
- Git commit tracking and annotation
- get_feature_context and get_feature_status tools
- Automatic context injection

**Week 5**: Telemetry & CATO (Not Started)
- User journey tracking
- Research event logging
- CATO dashboard integration API
- Real-time event broadcasting

**Week 5.5**: REST API Completion [CRITICAL] (Not Started)
- Launch Tab REST APIs (agents, projects, tasks)
- Terminal streaming infrastructure
- PTY session management
- Command injection for agent recovery

**Week 6**: Production Readiness (Not Started)
- Core validations (#118-125)
- Pip packaging
- Comprehensive documentation
- MVP release (v0.1.0)

### Next Steps

1. **Complete MVP Weeks 1-5** following the detailed weekly plans
2. **Complete Week 5.5 (CRITICAL)** - REST APIs and terminal streaming for CATO bundling
3. **Complete Week 6** - Production readiness and MVP release
4. **Run the test suites** to verify each week's implementation
5. **Deploy via pip** using `pip install marcus`
6. **Monitor with CATO** dashboard for real-time insights

---

**Status**: Work in Progress 🚧
