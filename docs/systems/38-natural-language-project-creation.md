# 38. Natural Language Project Creation System

## System Overview

The Natural Language Project Creation System is Marcus's intelligent project initialization pipeline that transforms human-readable project descriptions into fully structured, actionable task hierarchies on kanban boards. This system acts as the primary interface between natural language intent and Marcus's task execution ecosystem, treating every project description—from casual requests to formal specifications—as a Product Requirements Document (PRD).

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Input Layer                         │
│                   (MCP Tool: create_project)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                Natural Language Processing Layer                 │
│              (NaturalLanguageProjectCreator)                    │
│  • Context Detection    • Mode Selection    • Orchestration     │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    PRD Analysis Layer                           │
│                  (AdvancedPRDParser)                           │
│  • AI-Powered Analysis  • Requirement Extraction               │
│  • Task Hierarchy Generation  • Dependency Inference           │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                   Task Creation Layer                           │
│  • Safety Checks  • Priority Assignment  • Time Estimation      │
│  • Metadata Enrichment  • Kanban Integration                   │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. MCP Tool Interface (`/src/marcus_mcp/tools/nlp.py`)

Entry point for natural language project creation:

```python
async def create_project(
    description: str,
    project_name: str,
    options: Optional[Dict[str, Any]],
    state: Any
) -> Dict[str, Any]:
    """
    Args:
        description: Natural language project description
        project_name: Name for the project board
        options: Configuration including:
            - complexity: "prototype" | "standard" | "enterprise"
            - deployment: "none" | "internal" | "production"
            - team_size: 1-20
            - tech_stack: ["Python", "React", etc.]
            - deadline: ISO date string
    """
```

### 2. Natural Language Project Creator (`/src/integrations/nlp_tools.py`)

Orchestrates the conversion pipeline:

```python
class NaturalLanguageProjectCreator(NaturalLanguageTaskCreator):
    def __init__(self, kanban_client, ai_engine):
        self.prd_parser = AdvancedPRDParser()
        self.board_analyzer = BoardAnalyzer()
        self.context_detector = ContextDetector()
```

### 3. Advanced PRD Parser (`/src/ai/advanced/prd/advanced_parser.py`)

The intelligence engine that analyzes and converts:

```python
class AdvancedPRDParser:
    async def parse_prd_to_tasks(
        self, prd_content: str, constraints: ProjectConstraints
    ) -> TaskGenerationResult
```

## PRD-to-Task Conversion Pipeline

### Phase 1: Deep PRD Analysis

The system extracts **seven key components** from the input:

```python
@dataclass
class PRDAnalysis:
    functional_requirements: List[Dict[str, Any]]
    non_functional_requirements: List[Dict[str, Any]]
    technical_constraints: List[str]
    business_objectives: List[str]
    user_personas: List[Dict[str, Any]]
    success_metrics: List[str]
    implementation_approach: str
    complexity_assessment: Dict[str, str]
    risk_factors: List[Dict[str, Any]]
    confidence: float
```

**What it extracts:**

1. **Functional Requirements**
   - Features the system must have
   - User stories and capabilities
   - Core functionality

2. **Non-Functional Requirements (NFRs)**
   - Performance targets
   - Security requirements
   - Scalability needs
   - Usability standards

3. **Technical Constraints**
   - Technology stack limitations
   - Integration requirements
   - Platform restrictions

4. **Business Objectives**
   - Project goals
   - Success criteria
   - Business value

### Phase 2: Big Decisions

The system makes **five critical decisions**:

#### Decision 1: Project Complexity Classification
```python
if project_size in ["prototype", "mvp"]:
    # Minimal tasks, quick iteration
    max_tasks = 8
elif project_size in ["standard", "medium"]:
    # Balanced approach
    max_tasks = 20
else:  # enterprise
    # Comprehensive coverage
    max_tasks = 50+
```

#### Decision 2: NFR Inclusion
```python
def _filter_nfrs_by_size(self, nfrs, project_size):
    if project_size in ["prototype", "mvp"]:
        return nfrs[:1]  # Only essential NFRs
    elif project_size in ["standard"]:
        return nfrs[:2]  # Key NFRs
    else:
        return nfrs  # All NFRs
```

#### Decision 3: Task Granularity
- **Prototype**: High-level tasks only
- **Standard**: Balanced breakdown
- **Enterprise**: Detailed subtasks

#### Decision 4: Dependency Complexity
- Simple linear dependencies for prototypes
- Cross-functional dependencies for standard
- Full dependency graph for enterprise

#### Decision 5: Infrastructure Requirements
```python
if deployment_target == "local":
    # No deployment tasks
elif deployment_target == "dev":
    # Basic CI/CD
elif deployment_target == "prod":
    # Full deployment pipeline, monitoring, scaling
```

### Phase 3: Task Hierarchy Generation

Creates a multi-level task structure:

```
Epic Level:
├── epic_functional (User Features)
├── epic_non_functional (NFRs)
├── epic_infrastructure (Setup)
└── epic_deployment (Deploy)

Task Level:
├── task_{req_id}_design
├── task_{req_id}_implement
├── task_{req_id}_test
└── task_{req_id}_document
```

### Phase 4: Intelligent Enhancement

Each task receives:

1. **Contextual Details**
   - Descriptions based on project type
   - Technology-specific implementation notes
   - Integration requirements

2. **Smart Dependencies**
   - Design → Implementation → Testing
   - Cross-feature dependencies
   - Infrastructure prerequisites

3. **Resource Allocation**
   - Time estimates based on complexity
   - Skill requirements
   - Priority assignments

## Adjustable Dials and Toggles

### 1. Project Size/Complexity Dial
```python
options = {
    "complexity": "prototype"  # Affects everything
}
```
- Controls task count, depth, and infrastructure needs
- Impacts NFR inclusion and dependency complexity

### 2. Deployment Target Toggle
```python
options = {
    "deployment": "none" | "internal" | "production"
}
```
- Determines infrastructure task generation
- Controls monitoring and scaling requirements

### 3. Team Size Parameter
```python
options = {
    "team_size": 5  # 1-20
}
```
- Affects task parallelization
- Influences time estimates

### 4. Technology Stack Filter
```python
options = {
    "tech_stack": ["Python", "React", "PostgreSQL"]
}
```
- Guides implementation task details
- Determines setup requirements

### 5. AI Analysis Depth
```python
context = SimpleContext(max_tokens=2000)  # Adjustable
```
- Controls analysis thoroughness
- Affects extraction quality

## Workflow Integration

```mermaid
graph LR
    A[User Input] --> B[Context Detection]
    B --> C[PRD Analysis]
    C --> D[Task Generation]
    D --> E[Safety Checks]
    E --> F[Dependency Mapping]
    F --> G[Kanban Creation]
    G --> H[Agent Assignment]
```

## Special Features

### 1. Intelligent Defaults
If users don't specify NFRs, the system infers based on project type:
- E-commerce → Security, Payment compliance
- API service → Performance, Rate limiting
- Mobile app → Offline support, Battery efficiency

### 2. Safety Mechanisms
```python
async def apply_safety_checks(self, tasks):
    # Ensures logical ordering
    tasks = apply_implementation_dependencies(tasks)
    tasks = apply_testing_dependencies(tasks)
    tasks = apply_deployment_dependencies(tasks)
```

### 3. Adaptive Task Naming
Tasks are named based on context:
- Generic: "Implement user authentication"
- Context-aware: "Implement OAuth2 authentication with Google SSO"

## Error Handling

Uses Marcus Error Framework for graceful degradation:

```python
try:
    tasks = await self.process_natural_language(description)
except Exception as e:
    raise BusinessLogicError(
        "Failed to generate tasks from description",
        context=ErrorContext(
            operation="create_project",
            description_length=len(description)
        )
    )
```

## Pros and Cons

### Pros
- **Intelligent**: AI understands context and fills gaps
- **Flexible**: Handles everything from one-line to formal PRDs
- **Configurable**: Multiple dials for different project types
- **Safe**: Built-in dependency and ordering checks

### Cons
- **AI Dependent**: Quality depends on LLM performance
- **Opinionated**: Makes assumptions about project structure
- **Token Limited**: Very large PRDs may be truncated
- **Learning Curve**: Options and their effects aren't always obvious

## Technical Implementation Details

### Task Metadata Storage
```python
self._task_metadata[task["id"]] = {
    "original_name": task["name"],
    "type": task["type"],
    "epic_id": epic_id,
    "description": task.get("description", ""),
    "nfr_data": task.get("nfr_data", {}),
    "requirement": original_requirement
}
```

### Pipeline Tracking
```python
# Synchronous tracking to prevent MCP hanging
track_start()  # Not asyncio.create_task()
```

### NFR Processing
```python
# Unique descriptions preserved through pipeline
nfr_description = nfr.get("description", "")
tasks.append({
    "id": f"nfr_task_{nfr_id}",
    "name": f"Implement {nfr_name}",
    "description": nfr_description,  # Preserved!
})
```

## Future Evolution

### Planned Enhancements
1. **Template Library**: Pre-built patterns for common project types
2. **Learning System**: Improve based on successful projects
3. **Multi-Language PRDs**: Support non-English descriptions
4. **Visual PRD Input**: Diagrams and mockups as input

### Potential Toggles
1. **Risk Tolerance**: Conservative vs aggressive task generation
2. **Parallelization Strategy**: Team size optimization
3. **Cost Optimization**: Budget-aware task generation
4. **Compliance Mode**: Industry-specific requirements

## Integration with Marcus Ecosystem

### Kanban Integration
- Creates tasks via `KanbanClientWithCreate`
- Respects board column structure
- Maintains task relationships

### Agent Assignment
- Tasks tagged with skill requirements
- Priority-based assignment queue
- Load balancing considerations

### Seneca Visualization
- Pipeline events tracked for debugging
- Task creation flow visible
- Dependency graphs rendered

## Configuration Examples

### Minimal Prototype
```python
await create_project(
    description="Simple todo app",
    project_name="Todo MVP",
    options={"complexity": "prototype"}
)
```

### Standard Web App
```python
await create_project(
    description="E-commerce platform with user accounts...",
    project_name="ShopHub",
    options={
        "complexity": "standard",
        "deployment": "internal",
        "tech_stack": ["Django", "React", "PostgreSQL"]
    }
)
```

### Enterprise System
```python
await create_project(
    description="Banking microservices platform...",
    project_name="FinCore",
    options={
        "complexity": "enterprise",
        "deployment": "production",
        "team_size": 12,
        "deadline": "2024-06-01"
    }
)
```

## Design Rationale

The system treats all input as PRDs because:
1. **Consistency**: Uniform processing pipeline
2. **Intelligence**: AI can infer missing sections
3. **Completeness**: Ensures nothing is overlooked
4. **Flexibility**: Works with any input quality

The multi-phase pipeline ensures:
1. **Understanding**: Deep analysis before task generation
2. **Structure**: Consistent task hierarchies
3. **Safety**: Logical dependencies and ordering
4. **Quality**: Enriched tasks with context

This approach transforms Marcus from a task executor to an intelligent project planner that understands intent and generates comprehensive, executable project plans from natural language.
