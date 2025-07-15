# Operational Modes System - Technical Documentation

## Overview

The Operational Modes system is Marcus's intelligent mode-switching architecture that adapts its behavior based on board state, user intent, and project context. It implements three distinct operational modes (Creator, Enricher, Adaptive) that each handle different stages of project management, from initial project generation to intelligent task coordination.

## System Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Operational Modes System                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Creator Mode   │  │ Enricher Mode   │  │ Adaptive Mode   │ │
│  │                 │  │                 │  │                 │ │
│  │ • Template Lib  │  │ • Task Enricher │  │ • Dependency    │ │
│  │ • Task Gen      │  │ • Board Org     │  │   Resolution    │ │
│  │ • Project Types │  │ • Metadata      │  │ • Skill Match   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│           │                     │                     │         │
│           └─────────┬───────────┴─────────┬───────────┘         │
│                     │                     │                     │
│              ┌─────────────────┐   ┌─────────────────┐          │
│              │  Mode Registry  │   │ Context Detector│          │
│              │                 │   │                 │          │
│              │ • Mode Switching│   │ • Board Analysis│          │
│              │ • State Persist │   │ • Intent Detect │          │
│              │ • History Track │   │ • Mode Recommend│          │
│              └─────────────────┘   └─────────────────┘          │
│                     │                     │                     │
│              ┌─────────────────────────────────────────┐        │
│              │           Hybrid Tools (MCP)            │        │
│              │                                         │        │
│              │ • API Gateway                           │        │
│              │ • Tool Definitions                      │        │
│              │ • Cross-Mode Operations                 │        │
│              └─────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Context-Aware Switching**: Modes switch automatically based on board state analysis
2. **State Persistence**: Each mode maintains state across switches
3. **Dependency-Driven Logic**: Prevents illogical task assignments (e.g., deployment before development)
4. **Template-Based Generation**: Standardized project structures with customization
5. **Intelligent Coordination**: Skills-based task assignment with dependency respect

## Mode Definitions

### 1. Creator Mode (`src/modes/creator/`)

**Purpose**: Generate structured projects from templates or descriptions to prevent chaotic task creation.

**Core Problem Solved**: Eliminates the "Deploy to production" before any code exists scenario by generating properly ordered, dependency-aware task structures.

**Components**:
- **BasicCreatorMode**: Main orchestrator for project generation
- **TaskGenerator**: Converts templates into Task objects with proper dependencies
- **TemplateLibrary**: Pre-built project templates (WebApp, API, Mobile)

**Key Features**:
- **Template System**: Three built-in templates (Web, API, Mobile) with configurable project sizes (MVP → Enterprise)
- **Dependency Resolution**: Automatic dependency detection between tasks based on logical patterns
- **Size Scaling**: Task estimates automatically adjust based on project complexity
- **Phase Organization**: Tasks organized into logical development phases

**Technical Implementation**:
```python
# Template structure with dependency patterns
LOGICAL_DEPENDENCY_PATTERNS = [
    {
        'pattern': r'(setup|init|configure)',
        'blocks_until_complete': r'(implement|build|test|deploy)'
    },
    {
        'pattern': r'(implement|build)',
        'blocks_until_complete': r'(test|deploy)'
    }
]
```

**Project Size Multipliers**:
- MVP: 0.5x base estimates
- Small: 0.7x
- Medium: 1.0x (baseline)
- Large: 1.5x
- Enterprise: 2.0x

### 2. Enricher Mode (`src/modes/enricher/`)

**Purpose**: Transform chaotic existing boards into organized, metadata-rich structures.

**Core Problem Solved**: Takes existing poorly-defined tasks and adds structure, dependencies, estimates, and organization without losing existing work.

**Components**:
- **BasicEnricher**: Simple pattern-based task improvement
- **TaskEnricher**: Advanced metadata generation with board context
- **BoardOrganizer**: Multiple organization strategies (phase, component, feature, priority)

**Key Features**:
- **Task Classification**: Automatic categorization using regex patterns and keywords
- **Metadata Generation**: Adds descriptions, estimates, labels, acceptance criteria
- **Organization Strategies**: Multiple ways to structure boards with confidence scoring
- **Dependency Inference**: Suggests logical dependencies based on task content

**Technical Implementation**:
```python
# Task pattern recognition for enrichment
task_patterns = {
    'backend': {
        'patterns': [r'api', r'server', r'backend', r'endpoint'],
        'base_hours': 8,
        'labels': ['backend', 'api'],
        'typical_dependencies': ['design']
    }
}
```

**Organization Strategies**:
1. **Phase-based**: Planning → Development → Testing → Deployment
2. **Component-based**: Frontend, Backend, Database, Infrastructure
3. **Feature-based**: Groups by functional features
4. **Priority-based**: Urgent → High → Medium → Low

### 3. Adaptive Mode (`src/modes/adaptive/`)

**Purpose**: Intelligent task coordination that respects dependencies and prevents illogical assignments.

**Core Problem Solved**: The primary issue Marcus was built to solve - preventing "Deploy to production" from being assigned when development isn't complete.

**Components**:
- **BasicAdaptiveMode**: Core coordination logic with dependency checking

**Key Features**:
- **Dependency Blocking**: Hard blocks on both explicit dependencies and logical patterns
- **Skill Matching**: Scores tasks based on agent capabilities
- **Preference Learning**: Adapts to agent performance over time
- **Unblocking Analysis**: Identifies what's preventing task completion

**Technical Implementation**:
```python
# Core dependency checking logic
async def _is_task_unblocked(self, task, all_tasks, assigned_tasks):
    # Check explicit dependencies
    for dep_id in task.dependencies:
        dep_task = next((t for t in all_tasks if t.id == dep_id), None)
        if dep_task and dep_task.status != TaskStatus.DONE:
            return False

    # Check logical dependency patterns
    for pattern in self.LOGICAL_DEPENDENCY_PATTERNS:
        if self._matches_blocked_pattern(task, pattern):
            if self._has_incomplete_blockers(task, all_tasks, pattern):
                return False

    return True
```

**Scoring Algorithm**:
- Skill Match: 40% weight
- Priority: 30% weight
- Unblocking Value: 20% weight
- Agent Preference: 10% weight

## Context Detection and Mode Switching

### BoardAnalyzer (`src/detection/board_analyzer.py`)

Analyzes board state to determine optimal mode:

**Metrics Calculated**:
- Structure Score: Completeness of metadata across tasks
- Workflow Pattern: Sequential, Parallel, Phased, or Ad-hoc
- Phase Detection: Identifies development phases present
- Component Detection: Identifies system components

**State Classification**:
- **Empty Board** → Creator Mode recommended
- **Chaotic Board** (low structure score) → Enricher Mode recommended
- **Well-Structured Board** → Adaptive Mode recommended

### ContextDetector (`src/detection/context_detector.py`)

Analyzes user intent and recommends mode switches:

**Intent Detection Patterns**:
```python
INTENT_PATTERNS = {
    UserIntent.CREATE: [r"create.*project", r"new.*project", r"start.*from.*scratch"],
    UserIntent.ORGANIZE: [r"organize", r"structure", r"clean.*up"],
    UserIntent.COORDINATE: [r"assign", r"next.*task", r"who.*should"]
}
```

### ModeRegistry (`src/orchestration/mode_registry.py`)

Manages mode lifecycle and state persistence:

**Features**:
- Mode switching with state preservation
- Switch history tracking
- Capability reporting per mode
- Automatic mode suggestions

## Marcus Ecosystem Integration

### Position in Marcus Workflow

The Operational Modes system sits at the core of the Marcus workflow:

```
User Request → Context Detection → Mode Selection → Mode-Specific Logic → Board Updates
                     ↓
1. create_project → Creator Mode → Template Generation → Tasks Created
2. register_agent → Adaptive Mode → Agent Registration → Ready for Assignment
3. request_next_task → Adaptive Mode → Dependency Check → Task Assignment
4. report_progress → Adaptive Mode → Progress Update → Dependency Recalculation
5. report_blocker → Adaptive Mode → Blocker Analysis → Alternative Suggestions
6. finish_task → Adaptive Mode → Completion → Unblock Dependent Tasks
```

### MCP Integration (`src/orchestration/hybrid_tools.py`)

Exposes mode functionality through MCP tools:

**Tool Categories**:
- **Mode Management**: `switch_mode`, `analyze_board_context`
- **Project Creation**: `create_project_from_template`, `create_project_from_description`
- **Task Coordination**: `get_next_task_intelligent`, `get_blocking_analysis`

### Board-Specific Considerations

**Kanban Integration**:
- Tasks created through templates automatically appear on board
- Dependency relationships maintained through task IDs
- Status updates trigger dependency recalculation
- Cross-board project support (planned)

**Multiple Project Support**:
- Each mode can handle multiple concurrent projects
- Project context preserved in task metadata
- Cross-project dependency detection (future enhancement)

## Technical Implementation Details

### State Management

Each mode implements state persistence:

```python
class ModeInterface:
    async def initialize(self, saved_state: Dict[str, Any]) -> None
    async def get_state(self) -> Dict[str, Any]
    async def get_status(self) -> Dict[str, Any]
```

**State Contents**:
- **Creator**: Active project, generated tasks, template customizations
- **Enricher**: Enrichment plans, organization strategies, metadata caches
- **Adaptive**: Assignment preferences, blocked tasks, agent histories

### Dependency Resolution Algorithm

**Multi-Layer Dependency Checking**:

1. **Explicit Dependencies**: Direct task ID references
2. **Logical Patterns**: Regex-based pattern matching for task relationships
3. **Phase Dependencies**: Cross-phase dependency validation
4. **Component Dependencies**: Component interaction requirements

```python
LOGICAL_DEPENDENCY_PATTERNS = [
    # Setup blocks everything until complete
    {
        'pattern': r'(setup|init|configure|install)',
        'blocks_until_complete': r'(implement|build|create|develop|test|deploy)'
    },
    # Implementation blocks testing
    {
        'pattern': r'(implement|build|create|develop)',
        'blocks_until_complete': r'(test|qa|verify)'
    },
    # Testing blocks deployment
    {
        'pattern': r'(test|qa|quality|verify)',
        'blocks_until_complete': r'(deploy|release|launch|production)'
    }
]
```

### Template System Architecture

**Template Hierarchy**:
```
ProjectTemplate
├── phases: List[PhaseTemplate]
│   ├── tasks: List[TaskTemplate]
│   └── order: int
└── size_adjustments: Dict[ProjectSize, float]
```

**Built-in Templates**:
1. **WebAppTemplate**: Full-stack web application (6 phases, 20+ tasks)
2. **APIServiceTemplate**: Backend API service (5 phases, 12+ tasks)
3. **MobileAppTemplate**: Mobile application (4 phases, 15+ tasks)

### Error Handling and Resilience

**Dependency Validation**:
- Circular dependency detection
- Cross-phase dependency validation
- Missing dependency resolution
- Invalid assignment prevention

**Mode Switch Safety**:
- State validation before switching
- Rollback capability on switch failure
- Mode availability checking
- User confirmation for destructive operations

## Advantages and Limitations

### Advantages

1. **Solves Core Problem**: Eliminates illogical task assignments through dependency-aware coordination
2. **Progressive Enhancement**: Works with existing boards, doesn't require restructuring
3. **Template Standardization**: Provides proven project structures out-of-the-box
4. **Context Awareness**: Automatically adapts behavior based on board state
5. **Skill-Based Assignment**: Matches tasks to agent capabilities effectively
6. **State Persistence**: Maintains context across mode switches
7. **Extensible Architecture**: Easy to add new modes, templates, or organization strategies

### Current Limitations

1. **Enricher Mode Implementation**: Currently Phase 2 - only basic enricher available
2. **Limited AI Integration**: Template selection and enrichment use rule-based logic
3. **Single Board Focus**: Multi-board project management not fully implemented
4. **Agent Skill Modeling**: Simple keyword-based skill matching
5. **Dependency Inference**: Logical patterns may miss domain-specific dependencies
6. **Real-time Collaboration**: No live updates during multi-agent coordination

### Why This Approach

**Design Rationale**:

1. **Mode-Based Architecture**: Different project states need fundamentally different approaches
2. **Template-First**: Proven structures prevent common pitfalls and reduce setup time
3. **Dependency-Centric**: The core value proposition requires bulletproof dependency handling
4. **Progressive Enhancement**: Must work with existing workflows without disruption
5. **Context-Driven**: Automatic mode switching reduces cognitive load on users

**Alternative Approaches Considered**:
- **Single-Mode System**: Too rigid for diverse project states
- **Always-Enricher**: Doesn't solve empty board problem
- **Always-Creator**: Can't handle existing chaotic boards
- **Manual Mode Selection**: Increases user friction and complexity

## Future Evolution

### Phase 2 Enhancements

1. **AI-Powered Enricher**:
   - LLM-based task analysis and improvement
   - Intelligent dependency inference
   - Natural language acceptance criteria generation

2. **Advanced Templates**:
   - Industry-specific templates (e-commerce, SaaS, data science)
   - Custom template creation and sharing
   - Template version control

3. **Smart Agent Matching**:
   - Machine learning-based skill assessment
   - Performance history analysis
   - Workload balancing

### Phase 3 Vision

1. **Multi-Board Orchestration**:
   - Cross-project dependency management
   - Resource allocation across projects
   - Portfolio-level optimization

2. **Predictive Analytics**:
   - Project timeline prediction
   - Risk assessment and mitigation
   - Capacity planning

3. **Integration Ecosystem**:
   - IDE plugins for task context
   - CI/CD pipeline integration
   - Third-party tool connectors

### Handling Simple vs Complex Tasks

**Simple Tasks** (Adaptive Mode):
- Direct skill-based assignment
- Minimal dependency checking
- Fast assignment decisions
- Basic preference learning

**Complex Tasks** (Creator/Enricher Mode):
- Multi-step decomposition
- Comprehensive dependency analysis
- Template-based structure
- Rich metadata generation

**Complexity Detection**:
```python
def detect_task_complexity(task):
    complexity_indicators = [
        len(task.description) > 200,
        len(task.labels) > 3,
        task.estimated_hours > 8,
        len(task.dependencies) > 2,
        'complex' in task.name.lower()
    ]
    return sum(complexity_indicators) >= 2
```

## Integration with Seneca

**Current Integration**: Limited - Seneca operates as a separate agent coordinator

**Planned Integration**:
- Seneca as meta-coordinator managing mode switches
- Operational Modes as Seneca's decision-making engine
- Cross-system dependency tracking
- Unified agent skill modeling

**Architecture Vision**:
```
Seneca (Meta-Coordinator)
    ↓
Operational Modes (Decision Engine)
    ↓
Individual Agents (Task Execution)
```

## Typical Usage Scenarios

### Scenario 1: New Project Creation
```
1. Empty board detected → Auto-switch to Creator Mode
2. User: "Create a web app for e-commerce"
3. Creator Mode: Analyzes description → Suggests WebApp template
4. Template generates 25 tasks across 6 phases
5. Dependencies automatically established
6. Auto-switch to Adaptive Mode for coordination
```

### Scenario 2: Chaotic Board Organization
```
1. Board analysis: 50 tasks, low structure score → Suggest Enricher Mode
2. Enricher analyzes tasks → Identifies 3 organization strategies
3. User selects phase-based organization
4. Tasks automatically categorized and enhanced
5. Dependencies inferred and established
6. Switch to Adaptive Mode for ongoing coordination
```

### Scenario 3: Ongoing Coordination
```
1. Agent requests task → Adaptive Mode activated
2. Dependency analysis: Check 15 available tasks
3. 8 tasks blocked by incomplete dependencies
4. 7 tasks available, scored by skill match
5. Best task assigned with reasoning
6. Progress updates trigger dependency recalculation
```

This Operational Modes system represents Marcus's core intelligence, ensuring that the chaotic "deploy before building" problem is systematically prevented while providing the flexibility to handle projects at any stage of development.
