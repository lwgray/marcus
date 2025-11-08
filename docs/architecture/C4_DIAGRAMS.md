# Marcus C4 Architecture Diagrams

This document provides C4 model diagrams showing the architecture of Marcus at different levels of abstraction.

---

## C1: System Context Diagram

Marcus exists within an ecosystem of AI agents and external systems:

```
┌─────────────────────────────────────────────────────────────────────┐
│                          External World                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐              ┌──────────────────┐             │
│  │   AI Agents      │              │  Kanban Boards   │             │
│  │ (Claude, etc.)   │              │ (Planka, GitHub) │             │
│  └────────┬─────────┘              └────────┬─────────┘             │
│           │                                 │                       │
│           │◄──────MCP Protocol─────────────►│                       │
│           │                                 │                       │
│           │      ┌─────────────────────┐    │                       │
│           └─────►│  Marcus MCP Server  │◄───┘                       │
│                  │  (Multi-Project)    │                            │
│                  └──────────┬──────────┘                            │
│                             │                                       │
│  ┌──────────────────┐       │      ┌──────────────────┐            │
│  │  LLM APIs        │◄──────┴─────►│ Persistence      │            │
│  │ (Anthropic, etc) │              │ (SQLite, Files)  │            │
│  └──────────────────┘              └──────────────────┘            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Key External Systems:**
- AI Agents (Claude, custom implementations)
- Kanban Boards (Planka, GitHub Projects, Linear)
- LLM APIs (Anthropic Claude, OpenAI, Local)
- Persistent Storage (SQLite, JSON files)
- MLflow (experiment tracking)

---

## C2: Container Diagram

Marcus application broken into deployment containers:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Marcus Application                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────┐         ┌──────────────────────────────┐   │
│  │  MCP Server Container  │         │  Business Logic Container    │   │
│  │  (Presentation Layer)  │         │  (Domain & Orchestration)    │   │
│  ├────────────────────────┤         ├──────────────────────────────┤   │
│  │ HTTP/Stdio Transport   │         │ Core Domain Models           │   │
│  │ Tool Handlers          │         │ Workflows & Orchestration    │   │
│  │ Request/Response       │         │ Assignment & Leasing         │   │
│  │ Serialization          │         │ Context Management           │   │
│  │                        │         │ Error Handling & Recovery    │   │
│  │ 30+ MCP Tools          │         │ Task/Project Management      │   │
│  └────────┬───────────────┘         └────────┬───────────────────┘   │
│           │                                  │                        │
│           └──────────────┬───────────────────┘                        │
│                          │                                             │
│  ┌────────────────────────────────────────────────────────┐            │
│  │     Integration Layer Container                         │            │
│  │     (External System Abstraction)                       │            │
│  ├────────────────────────────────────────────────────────┤            │
│  │ Kanban Providers (Planka, GitHub, Linear)             │            │
│  │ AI/LLM Providers (Anthropic, OpenAI, Local)           │            │
│  │ NLP Tools & Task Parsing                              │            │
│  │ AI Analysis Engine                                     │            │
│  │ Token Tracking & Cost Attribution                      │            │
│  └────────────────────────────────────────────────────────┘            │
│                                                                          │
│  ┌────────────────────────┐         ┌──────────────────────────────┐   │
│  │  Infrastructure        │         │  Monitoring & Analytics      │   │
│  │  Container             │         │  Container                   │   │
│  ├────────────────────────┤         ├──────────────────────────────┤   │
│  │ Event System           │         │ Project Monitor              │   │
│  │ Persistence (SQLite)   │         │ Assignment Monitor           │   │
│  │ File Storage           │         │ Error Predictor              │   │
│  │ Logging & Conversation │         │ Live Pipeline Monitor        │   │
│  │ Communication Hub      │         │ Experiment Tracking (MLflow) │   │
│  │ Service Registry       │         │ Visualization System         │   │
│  └────────────────────────┘         └──────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## C3: Component Diagram (Core Domain Layer)

Deep dive into `src/core/`:

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Core Domain Layer (src/core/)                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────────────────────────┐  ┌─────────────────────┐    │
│  │  Models Component                  │  │  Context System     │    │
│  ├────────────────────────────────────┤  ├─────────────────────┤    │
│  │ Task (status, priority, deps)      │  │ TaskContext         │    │
│  │ ProjectState (health metrics)      │  │ DependentTask       │    │
│  │ WorkerStatus (agent profile)       │  │ Decision            │    │
│  │ TaskAssignment                     │  │ Context Manager     │    │
│  │ BlockerReport                      │  │ Hybrid Inference    │    │
│  │ ProjectRisk                        │  │ (AI-assisted deps)  │    │
│  │ Events                             │  │                     │    │
│  └────────────────────────────────────┘  └─────────────────────┘    │
│                                                                       │
│  ┌────────────────────────────────────┐  ┌─────────────────────┐    │
│  │  Project Management                │  │  Task Management    │    │
│  ├────────────────────────────────────┤  ├─────────────────────┤    │
│  │ ProjectContextManager              │  │ TaskDiagnostics     │    │
│  │ ProjectRegistry                    │  │ TaskGraphValidator  │    │
│  │ ProjectHistory (decisions, artifacts)│ │ TaskRecovery        │    │
│  │ Board Health Analyzer              │  │ AdaptiveDependencies│    │
│  │                                    │  │ PhaseDepEnforcer    │    │
│  └────────────────────────────────────┘  └─────────────────────┘    │
│                                                                       │
│  ┌────────────────────────────────────┐  ┌─────────────────────┐    │
│  │  Memory System                     │  │  Event System       │    │
│  ├────────────────────────────────────┤  ├─────────────────────┤    │
│  │ TaskOutcome                        │  │ Events (pub/sub)    │    │
│  │ AgentProfile (learning)            │  │ Event distribution  │    │
│  │ TaskPattern                        │  │ History storage     │    │
│  │ Memory Manager (multi-tier)        │  │ Persistence bridge  │    │
│  │ Estimation accuracy tracking       │  │                     │    │
│  └────────────────────────────────────┘  └─────────────────────┘    │
│                                                                       │
│  ┌────────────────────────────────────┐  ┌─────────────────────┐    │
│  │  Assignment Management             │  │  Error Framework    │    │
│  ├────────────────────────────────────┤  ├─────────────────────┤    │
│  │ AssignmentLease (timeout-based)    │  │ MarcusBaseError     │    │
│  │ AssignmentPersistence              │  │ TransientError      │    │
│  │ AssignmentReconciliation           │  │ IntegrationError    │    │
│  │ Lease Monitor                      │  │ BusinessLogicError  │    │
│  │                                    │  │ ConfigurationError  │    │
│  └────────────────────────────────────┘  └─────────────────────┘    │
│                                                                       │
│  ┌────────────────────────────────────┐  ┌─────────────────────┐    │
│  │  Persistence Layer                 │  │  Utilities          │    │
│  ├────────────────────────────────────┤  ├─────────────────────┤    │
│  │ FilePersistence (JSON)             │  │ Workspace Isolation │    │
│  │ SQLitePersistence (direct)         │  │ CodeAnalyzer        │    │
│  │ Collection-based organization      │  │ EventLoopLockMgr    │    │
│  │ Async-safe operations              │  │ ServiceRegistry     │    │
│  └────────────────────────────────────┘  └─────────────────────┘    │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## C3: Component Diagram (Integration Layer)

Deep dive into `src/integrations/`:

```
┌──────────────────────────────────────────────────────────────────────┐
│                  Integration Layer (src/integrations/)                │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────┐  ┌──────────────────────────────────┐  │
│  │  Kanban Abstraction      │  │  Kanban Providers                │  │
│  ├──────────────────────────┤  ├──────────────────────────────────┤  │
│  │ KanbanInterface (ABC)    │  │ Planka                           │  │
│  │ - connect()              │  │ GitHub Projects                  │  │
│  │ - get_available_tasks()  │  │ Linear                           │  │
│  │ - assign_task()          │  │ (Extensible pattern)             │  │
│  │ - update_task()          │  │                                  │  │
│  │ - add_comment()          │  │ All implement KanbanInterface    │  │
│  │                          │  │                                  │  │
│  │ KanbanFactory            │  │ Standardized Task representation │  │
│  │ Provider enumeration     │  │                                  │  │
│  └──────────────────────────┘  └──────────────────────────────────┘  │
│                                                                       │
│  ┌──────────────────────────┐  ┌──────────────────────────────────┐  │
│  │  AI/NLP Services         │  │  AI Provider Abstraction         │  │
│  ├──────────────────────────┤  ├──────────────────────────────────┤  │
│  │ NLPTaskUtils             │  │ (Defined in src/ai/providers/)   │  │
│  │ NLPBase                  │  │ BaseProvider (ABC)               │  │
│  │ NLPTools                 │  │ - generate()                     │  │
│  │ EnhancedTaskClassifier   │  │ - analyze_task()                │  │
│  │ AdaptiveDocumentation    │  │ - suggest_assignment()          │  │
│  │ AIAnalysisEngine         │  │                                  │  │
│  │ ProjectAutoSetup         │  │ Implementations:                 │  │
│  │                          │  │ - AnthropicProvider             │  │
│  │ Task parsing & analysis  │  │ - OpenAIProvider                │  │
│  │ Documentation generation │  │ - LocalProvider (Ollama)        │  │
│  │ Auto-initialization      │  │ - LLMAbstraction                │  │
│  └──────────────────────────┘  └──────────────────────────────────┘  │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## C3: Component Diagram (MCP Server & Tools)

Deep dive into `src/marcus_mcp/`:

```
┌──────────────────────────────────────────────────────────────────────┐
│              MCP Server & Tools (src/marcus_mcp/)                     │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────┐  ┌──────────────────────────────────┐  │
│  │  MCP Server              │  │  Tool Groups                     │  │
│  ├──────────────────────────┤  ├──────────────────────────────────┤  │
│  │ HTTP Transport           │  │ Task Tools                       │  │
│  │ Stdio Transport          │  │ ├── task.py (CRUD + assignment) │  │
│  │ Multi-Endpoint (Human,   │  │ ├── project_stall_analyzer.py   │  │
│  │   Agent, Analytics)      │  │ ├── scheduling.py               │  │
│  │                          │  │                                  │  │
│  │ Tool handler registry    │  │ Agent & Coordination Tools       │  │
│  │ Request/Response routing │  │ ├── agent.py (registration)     │  │
│  │ Error serialization      │  │ ├── coordinator/                │  │
│  │ Authentication middleware│  │                                  │  │
│  │                          │  │ Analysis & Monitoring Tools      │  │
│  │ Protocol compliance      │  │ ├── board_health.py             │  │
│  │ (MCP v1.0)              │  │ ├── analytics.py                 │  │
│  │                          │  │ ├── predictions.py              │  │
│  │                          │  │ ├── pipeline.py                 │  │
│  └──────────────────────────┘  │                                  │  │
│                                │ Context & Learning Tools         │  │
│                                │ ├── context.py                  │  │
│                                │ ├── experiments.py (MLflow)     │  │
│                                │ ├── predictions.py              │  │
│                                │                                  │  │
│                                │ Specialized Tools                │  │
│                                │ ├── nlp.py (task parsing)       │  │
│                                │ ├── auth.py (security)          │  │
│                                │ ├── diagnostics.py              │  │
│                                │ ├── audit_tools.py              │  │
│                                │ ├── code_metrics.py             │  │
│                                │ ├── attachment.py               │  │
│                                │ └── system.py                   │  │
│  └──────────────────────────────┘                                  │
│                                                                       │
│  ┌──────────────────────────┐  ┌──────────────────────────────────┐  │
│  │  Handlers                │  │  Coordinator                     │  │
│  ├──────────────────────────┤  ├──────────────────────────────────┤  │
│  │ Tool call dispatch       │  │ Agent coordination logic         │  │
│  │ Error handling           │  │ Task queueing                    │  │
│  │ Request validation       │  │ Auto-assignment loops           │  │
│  │ Response formatting      │  │ Monitoring orchestration        │  │
│  └──────────────────────────┘  └──────────────────────────────────┘  │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Sequence Diagrams

### Project Creation Sequence

```
Agent         Marcus           Kanban          AI Engine       History
 │              │               │                │               │
 ├─ Create ───────────────────────────────────────────────────────┤
 │ Project                      │                │               │
 │              │               │                │               │
 │              ├─ NLP Parse ──────────────────── Return Tasks ──┤
 │              │               │                │               │
 │              ├─ Create Board ───────────────────────────────┤
 │              │               │  Create Board │               │
 │              │               │◄──────────────┤               │
 │              │◄──────────────┤                │               │
 │              │               │                │               │
 │              ├─ Add Tasks ────────────────────────────────────┤
 │              │               │  Add Tasks    │               │
 │              │               │◄──────────────┤               │
 │              │◄──────────────┤                │               │
 │              │               │                │               │
 │              ├─ Register ────────────────────────────────┤
 │              │ Project        │                │ Store Metadata
 │              │                │                │◄────────────┤
 │              │                │                │             │
 │◄─────────────┤ Confirm         │                │             │
 │ Project ID   │                 │                │             │
 │              │                 │                │             │
```

### Task Assignment Sequence

```
Agent         Marcus           Kanban         AI Engine      Context      Memory
 │              │                │               │             │            │
 ├─ Get Next ────────────────────────────────────────────────────────────┤
 │ Task                           │               │             │            │
 │              │                 │               │             │            │
 │              ├─ Get Tasks ──────────────────────────────────┤          │
 │              │                 │  Available    │             │            │
 │              │                 │  Tasks        │             │            │
 │              │◄────────────────┤                │             │            │
 │              │                 │                │             │            │
 │              ├─ Analyze ──────────────────────────────┤     │            │
 │              │ Task             │               │ Insights   │            │
 │              │                  │               │◄───────────│            │
 │              │                  │               │            │            │
 │              ├─ Score Agents ────────────────────────────────┤──┐         │
 │              │                  │               │            │  │         │
 │              │                  │               │            │ Query
 │              │                  │               │            │ Profiles
 │              │◄───────────────────────────────────────────────│──┘        │
 │              │                  │               │            │ Return
 │              │                  │               │            │ Profiles
 │              ├─ Create Lease ────────────────────────────────────────────┤
 │              │                  │               │            │            │
 │              ├─ Get Context ──────────────────────────────────────┤       │
 │              │                  │               │            │ Related   │
 │              │                  │               │            │ Tasks
 │              │◄──────────────────────────────────────────────┤           │
 │              │                  │               │            │           │
 │◄─────────────┤ Task + Context    │               │            │           │
 │ Assignment   │                   │               │            │           │
 │              │                   │               │            │           │
```

### Task Completion Sequence

```
Agent         Marcus           Kanban         History        Memory         Monitor
 │              │                │               │              │             │
 ├─ Report ──────────────────────────────────────────────────────────────────┤
 │ Complete      │                │               │              │             │
 │              │                │               │              │             │
 │              ├─ Update Kanban ──────────────────────────────┤             │
 │              │                 │  Mark Done   │              │             │
 │              │                 │◄─────────────┤              │             │
 │              │◄─────────────────┤              │              │             │
 │              │                 │              │              │             │
 │              ├─ Store Decision ────────────────────────────────────────────┤
 │              │ & Artifacts       │              │  Log      │             │
 │              │                   │              │◄──────────┤             │
 │              │                   │              │           │             │
 │              ├─ Update Profile ───────────────────────────────────┤       │
 │              │                   │              │           │ Update      │
 │              │                   │              │           │ Agent       │
 │              │                   │              │           │ Profile
 │              │◄──────────────────────────────────────────────┤            │
 │              │                   │              │           │            │
 │              ├─ Trigger Monitor ───────────────────────────────────┤      │
 │              │ Update             │              │           │           │
 │              │                    │              │           │ Project    │
 │              │                    │              │           │ Health
 │              │◄───────────────────────────────────────────────┤           │
 │              │                    │              │           │            │
 │◄─────────────┤ Confirmed          │              │           │            │
 │              │                    │              │           │            │
```

### Multi-Project Switching Sequence

```
Agent         Marcus           Registry       Kanban1         Kanban2
 │              │                │              │                │
 ├─ Switch ──────────────────────────────────────────────────────┤
 │ Project                        │              │                │
 │                                │              │                │
 │              ├─ Get Context ────────────────────────────────┤
 │              │ (Project 1)      │  Find Config │                │
 │              │                  │              │                │
 │              ├─ Disconnect ──────────────────────────────┤
 │              │ Old Client        │              │ Cleanup       │
 │              │◄─────────────────┤              │                │
 │              │                  │              │                │
 │              ├─ Get Context ────────────────────────────┤
 │              │ (Project 2)      │  Find Config │                │
 │              │                  │◄─────────────────────┤        │
 │              │                  │              │      Connect  │
 │              ├─ Connect ────────────────────────────────────────┤
 │              │ New Client        │              │               │ Create
 │              │                   │              │               │ Session
 │              │                   │              │               │
 │◄─────────────┤ Ready             │              │               │
 │              │                   │              │               │
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Compose Deployment                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │  PostgreSQL      │  │  Planka Service  │  │  Marcus App  │  │
│  │  (Database)      │  │  (Kanban Board)  │  │  (MCP Server)│  │
│  └────────┬─────────┘  └────────┬─────────┘  └──────┬───────┘  │
│           │                     │                    │           │
│           │◄────────────────────┤                    │           │
│           │ (Port 5432)         │ (Port 3000)       │           │
│           │                     │                    │           │
│           │                     │ (HTTP 4298)       │           │
│           │                     ◄────────────────────┤           │
│           │                                         │           │
│           │ (HTTP)                                  │           │
│           ◄─────────────────────────────────────────┤           │
│                                                     │           │
│           │◄──────────────────────────────────────────           │
│           │ (Port 5432) Direct SQLite access                    │
│                                                     │           │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Volumes                                              │    │
│  │  - /data (marcus workspace & history)                │    │
│  │  - /logs (application logs)                          │    │
│  │  - /mlruns (MLflow experiments)                      │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Model Relationships

```
┌─────────────┐
│  Project    │  (Board + Config)
└──────┬──────┘
       │ owns
       ▼
┌─────────────────────────────┐
│  Task                       │
│ ├─ id                       │
│ ├─ name, description        │
│ ├─ status, priority         │
│ ├─ assigned_to (agent_id)   │
│ ├─ dependencies: List[Task] │
│ ├─ is_subtask, parent_id    │
│ └─ provides/requires        │
└──────┬──────┐──────┬────────┘
       │      │      │
       │      │      ├─ depends_on ──────┐
       │      │                          ▼
       │      │                   ┌─────────────┐
       │      │                   │ Task Graph  │
       │      │                   │ (Validator) │
       │      │                   └─────────────┘
       │      │
       │      └─ assigned_to ──┐
       │                       ▼
       │              ┌──────────────────┐
       │              │ WorkerStatus     │
       │              │ (Agent Profile)  │
       │              └──────────────────┘
       │
       └─ generated_by ────────┐
                               ▼
                    ┌──────────────────┐
                    │ Decision         │
                    │ ├─ what          │
                    │ ├─ why           │
                    │ ├─ impact        │
                    │ └─ confidence    │
                    └──────────────────┘

┌────────────────┐
│ TaskAssignment │
│ ├─ task_id     │
│ ├─ agent_id    │
│ ├─ lease_info  │
│ └─ context     │
└────────────────┘

┌──────────────────┐
│ ProjectState     │
│ ├─ board_id      │
│ ├─ progress      │
│ ├─ risk_level    │
│ ├─ velocity      │
│ └─ blocked_tasks │
└──────────────────┘
```

---

## State Machine Diagrams

### Task State Machine

```
    ┌─────────────────────────────────────────┐
    │            Task Lifecycle               │
    └─────────────────────────────────────────┘

            ┌──────────┐
            │   TODO   │  (Initial state)
            └─────┬────┘
                  │ assign
                  ▼
          ┌─────────────┐
          │ IN_PROGRESS │  (Agent working)
          └──┬──────┬───┘
             │      │
             │      └─ blocker ─────┐
             │                      ▼
             │              ┌─────────────┐
             │              │  BLOCKED    │  (Waiting for help)
             │              └──────┬──────┘
             │                     │
             │                     └─ unblock ──┐
             │                                  │
             └─ complete ──────┬────────────────┘
                               ▼
                         ┌──────────┐
                         │   DONE   │  (Final state)
                         └──────────┘
```

### Agent Assignment Lease State Machine

```
        ┌──────────────┐
        │   CREATED    │  (Lease initiated)
        └──────┬───────┘
               │ activate
               ▼
       ┌───────────────┐
       │   ACTIVE      │  (Agent has task)
       └──┬────────┬───┘
          │        │
          │        ├─ timeout ──────┐
          │        │                ▼
          │        │        ┌──────────────┐
          │        │        │   EXPIRED    │  (Timeout)
          │        │        └──────────────┘
          │        │
          └─ release ──┐
                       ▼
               ┌──────────────┐
               │  RELEASED    │  (Final state)
               └──────────────┘
```

---

## Technology Stack Visualization

```
┌─────────────────────────────────────────────────────────────┐
│                    Technology Layers                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Application      Python 3.11+ + Asyncio                    │
│  ────────────────────────────────────────────────────────   │
│                                                              │
│  Presentation     MCP Server (Anthropic)                    │
│  Layer            aiohttp, httpx                            │
│                   ────────────────────                       │
│                                                              │
│  Business Logic   Pydantic (validation)                     │
│  ────────────────────────────────────────────────────────   │
│                                                              │
│  Integration      anthropic, openai                         │
│  ────────────────────────────────────────────────────────   │
│                                                              │
│  Data Access      SQLite + aiofiles                         │
│  ────────────────────────────────────────────────────────   │
│                                                              │
│  DevOps           Docker + docker-compose                   │
│  ────────────────────────────────────────────────────────   │
│                                                              │
│  Testing          pytest + pytest-asyncio                   │
│  Monitoring       MLflow                                     │
│  Code Quality     black, isort, mypy (strict mode)          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```
