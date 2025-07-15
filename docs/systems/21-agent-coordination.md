# Agent Coordination System

## Overview

The Agent Coordination System is the orchestration layer of Marcus that manages the lifecycle and task assignment of autonomous AI agents. It serves as the central nervous system for coordinating multiple AI workers, ensuring optimal task distribution, preventing conflicts, and maintaining system coherence across distributed work.

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     Agent Coordination System                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Agent Mgmt    │  │ Task Assignment │  │   Assignment    │ │
│  │   (register,    │  │ (AI-powered     │  │  Persistence    │ │
│  │    status)      │  │  matching)      │  │  (durability)   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Progress      │  │    Blocker      │  │   Assignment    │ │
│  │   Tracking      │  │   Resolution    │  │   Monitoring    │ │
│  │  (milestones)   │  │ (AI suggestions)│  │  (health check) │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Kanban Board  │  │  AI Engine      │  │  Memory System  │
│   (planka/gh)   │  │  (task match)   │  │  (predictions)  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Key Modules

1. **Agent Management** (`src/marcus_mcp/tools/agent.py`)
   - Agent registration and capability tracking
   - Status monitoring and availability management
   - Skill-based agent classification

2. **Task Assignment Engine** (`src/core/ai_powered_task_assignment.py`)
   - AI-powered optimal task selection
   - Multi-phase assignment algorithm
   - Dependency-aware scheduling

3. **Assignment Persistence** (`src/core/assignment_persistence.py`)
   - Atomic task assignment storage
   - Cross-restart assignment recovery
   - Conflict prevention mechanisms

4. **Assignment Monitoring** (`src/monitoring/assignment_monitor.py`)
   - Real-time state reversion detection
   - Health checking and reconciliation
   - Assignment drift prevention

## Marcus Ecosystem Integration

### Position in Marcus Architecture

The Agent Coordination System sits at the intersection of several major subsystems:

- **Above**: MCP Server Layer (tool exposure)
- **Peers**: Context System, Memory System, AI Engine
- **Below**: Kanban Integration, Persistence Layer
- **Integrates With**: Communication Hub, Event System, Monitoring

### Data Flow

```
Agent Request → MCP Tool → Coordination Engine → AI Analysis → Assignment Decision
     ↓              ↓              ↓               ↓              ↓
Registration  →  Capability   → Task Matching → Optimization → Kanban Update
     ↓              ↓              ↓               ↓              ↓
 Status Track  → Progress Mon. → Context Inject → Memory Record → Persistence
```

## Workflow Integration

### Typical Agent Lifecycle

1. **Project Creation** (`create_project`)
   - Kanban board initialization
   - Task decomposition and prioritization
   - Dependency graph construction

2. **Agent Registration** (`register_agent`)
   ```python
   await register_agent(
       agent_id="dev-001",
       name="Alice Backend",
       role="Backend Developer",
       skills=["Python", "FastAPI", "PostgreSQL"]
   )
   ```

3. **Task Request Loop** (`request_next_task`)
   - AI-powered task selection
   - Context and dependency injection
   - Implementation guidance generation
   - Assignment persistence

4. **Progress Reporting** (`report_progress`)
   - Milestone tracking (25%, 50%, 75%, 100%)
   - Status synchronization with Kanban
   - Memory system feedback

5. **Blocker Resolution** (`report_blocker`)
   - AI-powered analysis and suggestions
   - Severity-based escalation
   - Alternative solution paths

6. **Task Completion** (`finish_task`)
   - Code analysis (GitHub projects)
   - Performance tracking
   - Next task preparation

## Special System Characteristics

### AI-Powered Intelligence

Unlike traditional task schedulers, Marcus uses multi-phase AI analysis:

**Phase 1: Safety Filtering**
- Prevents deployment before implementation
- Validates dependency completion
- Blocks unsafe task sequences

**Phase 2: Dependency Analysis**
- Critical path identification
- Unblocking task prioritization
- Cascade impact prediction

**Phase 3: Agent-Task Matching**
- Skill compatibility scoring
- Performance history analysis
- Context-aware recommendations

**Phase 4: Predictive Impact**
- Timeline optimization
- Risk mitigation assessment
- Resource allocation planning

### Tiered Instruction Generation

The system builds context-aware instructions dynamically:

```python
def build_tiered_instructions(
    base_instructions: str,
    task: Task,
    context_data: Optional[Dict],
    dependency_awareness: Optional[str],
    predictions: Optional[Dict]
) -> str:
    # Layer 1: Base instructions (always)
    # Layer 2: Implementation context (if GitHub)
    # Layer 3: Dependency awareness (if dependents exist)
    # Layer 4: Decision logging (if high impact)
    # Layer 5: Predictions and warnings (if Memory enabled)
    # Layer 6: Task-specific guidance (based on labels)
```

### Assignment Durability

Persistent assignment tracking prevents:
- Double assignment across restarts
- Task state inconsistencies
- Agent confusion during system recovery

## Technical Implementation

### Core Data Models

```python
@dataclass
class WorkerStatus:
    worker_id: str
    name: str
    role: str
    skills: List[str]
    current_tasks: List[Task]
    completed_tasks_count: int
    performance_score: float
    availability: Dict[str, bool]

@dataclass
class TaskAssignment:
    task_id: str
    task_name: str
    instructions: str
    assigned_to: str
    assigned_at: datetime
    estimated_hours: float
    priority: Priority
```

### Assignment Algorithm

```python
async def find_optimal_task_for_agent(
    agent_id: str,
    agent_info: Dict[str, Any],
    available_tasks: List[Task],
    assigned_task_ids: Set[str]
) -> Optional[Task]:

    # Multi-phase scoring
    safety_scores = await _filter_safe_tasks(tasks)
    dependency_scores = await _analyze_dependencies(tasks)
    ai_scores = await _get_ai_recommendations(tasks, agent_info)
    impact_scores = await _predict_task_impact(tasks)

    # Weighted combination
    weights = {
        "skill_match": 0.15,
        "priority": 0.15,
        "dependencies": 0.25,
        "ai_recommendation": 0.30,
        "impact": 0.15
    }

    return _select_best_task(tasks, scores, weights)
```

### State Synchronization

```python
class AssignmentMonitor:
    """Continuous monitoring for assignment consistency"""

    async def _check_for_reversions(self):
        # Detect state reversions
        # Handle missing tasks
        # Reconcile inconsistencies
        # Alert on repeated issues
```

## System Advantages

### Strengths

1. **Intelligence**: AI-powered matching vs. simple skill/priority scoring
2. **Durability**: Persistent assignments survive system restarts
3. **Context-Aware**: Integrates implementation history and dependencies
4. **Predictive**: Forecasts completion times and potential blockers
5. **Self-Healing**: Monitors and corrects assignment drift
6. **Scalable**: Handles multiple agents and complex dependency graphs

### Design Rationale

**Why AI-Powered Assignment?**
- Traditional schedulers optimize for resource utilization
- Marcus optimizes for project success and agent development
- AI considers factors humans miss (performance trends, context patterns)

**Why Persistent Assignments?**
- Agents work across extended timeframes
- System restarts shouldn't lose work context
- Multiple Marcus instances need coordination

**Why Real-Time Monitoring?**
- External changes to Kanban boards create drift
- Human intervention can disrupt agent workflows
- Early detection prevents compound problems

## Task Complexity Handling

### Simple Tasks
- Direct skill matching
- Basic priority scoring
- Minimal context injection

### Complex Tasks
- Full AI analysis pipeline
- Extensive context building
- Dependency cascade analysis
- Performance trajectory consideration

### Decision Matrix

```
Task Complexity | Dependency Count | AI Analysis | Context Layers
─────────────────┼──────────────────┼─────────────┼───────────────
Simple           | 0-1              | Basic       | 1-2 layers
Moderate         | 2-4              | Enhanced    | 3-4 layers
Complex          | 5+               | Full        | 5-6 layers
```

## Board-Specific Considerations

### Planka Integration
- Real-time WebSocket updates
- Card status synchronization
- Comment-based progress tracking
- Label-based skill matching

### GitHub Integration
- Issue-based task management
- Pull request workflow integration
- Code analysis for completed tasks
- Implementation context extraction

### Provider Abstraction
```python
class KanbanInterface:
    async def get_available_tasks(self) -> List[Task]
    async def update_task(self, task_id: str, updates: Dict)
    async def add_comment(self, task_id: str, comment: str)
```

## Seneca Integration

While the coordination system doesn't directly integrate with Seneca (a philosophy AI), it provides the infrastructure for philosophical agents:

- **Capability Registration**: Seneca agents register with specialized skills
- **Task Type Routing**: Philosophy-related tasks routed to appropriate agents
- **Context Preservation**: Maintains conversation context across philosophical discussions
- **Progress Tracking**: Monitors philosophical analysis milestones

## Current Limitations

### Performance Bottlenecks
- AI analysis adds latency to task assignment
- Multiple context lookups for complex tasks
- Synchronous assignment lock prevents parallelism

### Scalability Concerns
- Linear search through available tasks
- In-memory state doesn't scale beyond ~100 agents
- No agent load balancing across Marcus instances

### Missing Features
- Agent skill learning from task outcomes
- Dynamic agent spawning based on workload
- Cross-project agent sharing
- Agent specialization recommendations

## Future Evolution

### Planned Enhancements

**Phase 1: Performance Optimization**
- Async assignment pipeline
- Task indexing and filtering
- Agent pool management

**Phase 2: Advanced Intelligence**
- Machine learning for assignment optimization
- Agent performance prediction
- Dynamic skill inference

**Phase 3: Distributed Coordination**
- Multi-instance agent coordination
- Cross-project agent migration
- Federated assignment consensus

**Phase 4: Autonomous Management**
- Self-organizing agent teams
- Automatic agent provisioning
- Adaptive assignment algorithms

### Long-Term Vision

The Agent Coordination System will evolve from a centralized scheduler to a distributed mesh of intelligent agents that self-organize around project goals, learn from each other's experiences, and adapt their coordination patterns to optimize for both individual growth and collective success.

## Technical Metrics

### Performance Characteristics
- **Assignment Latency**: 200-500ms (with AI analysis)
- **State Consistency**: 99.9% (with monitoring)
- **Recovery Time**: < 30 seconds (after restart)
- **Throughput**: 50+ concurrent assignments

### Monitoring Endpoints
- `/api/agents/status` - Agent availability and performance
- `/api/assignments/health` - Assignment system health
- `/api/assignments/metrics` - Coordination metrics and trends

### Error Rates
- **Assignment Conflicts**: < 0.1% (with persistence)
- **State Drift**: < 1% (with monitoring)
- **AI Analysis Failures**: < 5% (with fallback)

The Agent Coordination System represents Marcus's commitment to intelligent, context-aware task management that treats AI agents as sophisticated workers capable of growth, learning, and autonomous decision-making within a structured coordination framework.
