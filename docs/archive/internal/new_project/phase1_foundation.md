# Phase 1: Foundation (Weeks 1-4)

> **Why This Phase Matters**: This phase implements the basic intelligence to prevent Marcus from ever assigning "Deploy to production" before there's anything to deploy.

## Overview
Phase 1 establishes the core infrastructure for Marcus's hybrid approach, implementing basic versions of Creator and Adaptive modes, the context detection system, and mode switching capabilities. This phase focuses on proving the concept with minimal viable features.

## Goals
- Implement context detection to understand board state and user needs
- Build basic Creator Mode with template-based project generation
- Build basic Adaptive Mode for simple task coordination
- Create mode switching interface for explicit mode changes
- Establish foundation for future intelligence layers

## Week 1-2: Context Detection System

### 1.1 Board State Analyzer
**File**: `src/detection/board_analyzer.py`

```python
class BoardAnalyzer:
    """Analyzes kanban board state to determine optimal Marcus mode"""
    
    async def analyze_board(self, board_id: str) -> BoardState:
        """
        Analyze board characteristics:
        - Task count and distribution
        - Metadata completeness (descriptions, labels, estimates)
        - Organization level (chaos → structured)
        - Workflow indicators
        """
        
    async def calculate_structure_score(self, tasks: List[Task]) -> float:
        """
        Score 0-1 indicating how well-structured the board is:
        - 0.0-0.3: Chaotic (just task titles)
        - 0.3-0.6: Basic (some organization)
        - 0.6-0.8: Good (clear structure)
        - 0.8-1.0: Excellent (full metadata)
        """
        
    async def detect_workflow_patterns(self, tasks: List[Task]) -> WorkflowPattern:
        """
        Detect how the team works:
        - Sequential: Tasks completed one by one
        - Parallel: Multiple tasks in progress
        - Phased: Clear phase boundaries
        - Ad-hoc: No clear pattern
        """
```

### 1.2 Context Detector
**File**: `src/detection/context_detector.py`

```python
class ContextDetector:
    """Determines which Marcus mode would be most helpful"""
    
    async def detect_optimal_mode(self) -> MarcusMode:
        """
        Decision tree for mode selection:
        1. Check board state
        2. Check recent user interactions
        3. Check explicit preferences
        4. Make recommendation
        """
        
    async def detect_user_intent(self, message: str) -> UserIntent:
        """
        Parse user messages for intent:
        - CREATE: "create project", "new tasks", "from PRD"
        - ORGANIZE: "organize", "structure", "clean up"
        - COORDINATE: "assign", "next task", "who should"
        """
```

### 1.3 Mode Registry
**File**: `src/orchestration/mode_registry.py`

```python
class ModeRegistry:
    """Registry of available Marcus modes"""
    
    def __init__(self):
        self.modes = {
            MarcusMode.CREATOR: CreatorMode(),
            MarcusMode.ENRICHER: None,  # Phase 2
            MarcusMode.ADAPTIVE: AdaptiveMode()
        }
        self.current_mode = MarcusMode.ADAPTIVE
        
    async def switch_mode(self, mode: MarcusMode, reason: str = None):
        """Switch Marcus to a different operating mode"""
        
    async def get_current_mode(self) -> MarcusMode:
        """Get the currently active mode"""
```

## Week 2-3: Basic Creator Mode

### 2.1 Template Library
**File**: `src/modes/creator/template_library.py`

```python
class ProjectTemplate:
    """Base class for project templates"""
    
    def __init__(self):
        self.name = ""
        self.description = ""
        self.phases = []
        self.default_tasks = []
        
class WebAppTemplate(ProjectTemplate):
    """Template for full-stack web applications"""
    
    def __init__(self):
        super().__init__()
        self.name = "Full-Stack Web Application"
        self.phases = ["Setup", "Backend", "Frontend", "Integration", "Deployment"]
        self.default_tasks = [
            {
                "phase": "Setup",
                "tasks": [
                    {"name": "Initialize repository", "estimate": 1},
                    {"name": "Set up development environment", "estimate": 2},
                    {"name": "Configure build tools", "estimate": 2}
                ]
            },
            {
                "phase": "Backend",
                "tasks": [
                    {"name": "Design database schema", "estimate": 4},
                    {"name": "Create data models", "estimate": 6},
                    {"name": "Implement API endpoints", "estimate": 16},
                    {"name": "Add authentication", "estimate": 8}
                ]
            }
            # ... more phases
        ]
```

### 2.2 Task Generator
**File**: `src/modes/creator/task_generator.py`

```python
class TaskGenerator:
    """Generates task structures from templates or requirements"""
    
    async def generate_from_template(
        self, 
        template: ProjectTemplate, 
        customizations: Dict[str, Any]
    ) -> List[Task]:
        """
        Generate tasks from template with customizations:
        - Scale estimates based on project size
        - Add/remove tasks based on requirements
        - Set appropriate labels and metadata
        """
        
    async def create_task_hierarchy(self, tasks: List[Dict]) -> List[Task]:
        """
        Create proper task objects with:
        - Unique IDs
        - Dependencies based on phase
        - Proper labels and estimates
        - Descriptions from template
        """
```

### 2.3 Interactive Creator
**File**: `src/modes/creator/interactive_creator.py`

```python
class InteractiveCreator:
    """Handles interactive project creation flow"""
    
    async def start_creation_flow(self, initial_request: str = None):
        """
        Interactive project creation:
        1. Understand project type
        2. Gather requirements
        3. Suggest approach
        4. Create tasks
        """
        
    async def gather_requirements(self) -> ProjectRequirements:
        """
        Ask clarifying questions:
        - Project type and size
        - Technical preferences
        - Team size and skills
        - Timeline constraints
        """
        
    async def present_plan(self, plan: ProjectPlan) -> bool:
        """
        Present the plan to user:
        - Summary of phases and tasks
        - Timeline estimate
        - Required skills
        - Get approval or modifications
        """
```

## Week 3-4: Basic Adaptive Mode

### 3.1 Simple Task Coordinator
**File**: `src/modes/adaptive/task_coordinator.py`

```python
class SimpleTaskCoordinator:
    """Basic task coordination without changing board structure"""
    
    async def find_next_task(self, agent: Agent) -> Optional[Task]:
        """
        Simple task selection:
        1. Get unassigned tasks
        2. Filter by agent skills
        3. Sort by priority/age
        4. Return best match
        """
        
    async def match_skills(self, task: Task, agent: Agent) -> float:
        """
        Calculate skill match score:
        - Compare task labels to agent skills
        - Consider partial matches
        - Weight by importance
        """
```

### 3.2 Assignment Tracker
**File**: `src/modes/adaptive/assignment_tracker.py`

```python
class AssignmentTracker:
    """Tracks task assignments and progress"""
    
    def __init__(self):
        self.assignments = {}  # agent_id -> task_id
        self.history = []      # Historical assignments
        
    async def assign_task(self, task_id: str, agent_id: str):
        """Record task assignment"""
        
    async def complete_task(self, task_id: str, agent_id: str):
        """Record task completion"""
        
    async def get_agent_workload(self, agent_id: str) -> Workload:
        """Get current workload for an agent"""
```

### 3.3 Basic Workflow Adapter
**File**: `src/modes/adaptive/workflow_adapter.py`

```python
class BasicWorkflowAdapter:
    """Adapts to different workflow styles"""
    
    async def detect_workflow_style(self, board_history: List[Event]) -> WorkflowStyle:
        """
        Detect from historical data:
        - How tasks move through board
        - Assignment patterns
        - Completion patterns
        """
        
    async def adapt_coordination(self, style: WorkflowStyle):
        """
        Adjust coordination based on style:
        - Scrum: Respect sprint boundaries
        - Kanban: Continuous flow
        - Waterfall: Phase gates
        """
```

## Week 4: Mode Switching & Integration

### 4.1 Mode Switching Interface
**File**: `src/orchestration/mode_switcher.py`

```python
@tool
async def switch_mode(mode: str, reason: str = None):
    """
    Allow users to explicitly switch Marcus modes
    
    Args:
        mode: "creator", "enricher", or "adaptive"
        reason: Optional reason for switching
        
    Returns:
        Confirmation of mode switch
    """
    
@tool  
async def current_mode():
    """
    Show current Marcus operating mode
    
    Returns:
        Current mode and capabilities
    """
```

### 4.2 Unified Interface
**File**: `src/orchestration/marcus_interface.py`

```python
class MarcusInterface:
    """Unified interface that delegates to appropriate mode"""
    
    async def handle_request(self, request: Request) -> Response:
        """
        Route requests to appropriate mode:
        1. Detect context if needed
        2. Switch mode if appropriate
        3. Delegate to mode handler
        4. Return response
        """
        
    async def handle_mode_transition(self, from_mode: MarcusMode, to_mode: MarcusMode):
        """
        Smooth transitions between modes:
        - Save state from current mode
        - Initialize new mode with context
        - Notify user of switch
        """
```

### 4.3 State Management
**File**: `src/orchestration/state_manager.py`

```python
class StateManager:
    """Manages state across mode switches"""
    
    def __init__(self):
        self.global_state = {}  # Shared across modes
        self.mode_states = {}   # Mode-specific state
        
    async def save_mode_state(self, mode: MarcusMode, state: Dict):
        """Save state when leaving a mode"""
        
    async def restore_mode_state(self, mode: MarcusMode) -> Dict:
        """Restore state when entering a mode"""
        
    async def get_context(self) -> Context:
        """Get current context for decision making"""
```

## Testing Plan

### Unit Tests
- Board analyzer correctly scores structure
- Context detector chooses appropriate modes
- Template generation produces valid tasks
- Task coordinator makes sensible assignments

### Integration Tests
- Mode switching preserves state
- Creator mode successfully creates projects
- Adaptive mode works with various board states
- Context detection handles edge cases

### User Acceptance Tests
- Users can explicitly switch modes
- Mode recommendations make sense
- Basic project creation works
- Task coordination is helpful

## Success Criteria

### Quantitative
- Context detection accuracy > 80%
- Template project creation < 30 seconds
- Task assignment success rate > 70%
- Mode switching < 2 seconds

### Qualitative
- Users understand the three modes
- Mode switches feel natural
- Templates cover common projects
- Assignments make sense

## Dependencies

### Technical
- Kanban integration (existing)
- AI engine (basic version)
- Database for state
- MCP framework

### Resources
- 2 developers full-time
- AI API access
- Test environments
- User feedback group

## Risks & Mitigation

### Risk 1: Mode Confusion
**Mitigation**: Clear UI indicators, explanations, and documentation

### Risk 2: Poor Context Detection
**Mitigation**: Allow manual override, collect feedback for improvement

### Risk 3: Limited Templates
**Mitigation**: Start with most common, plan for expansion

### Risk 4: State Management Complexity
**Mitigation**: Simple state model, extensive testing

## Deliverables

### Week 1
- [ ] Board analyzer implementation
- [ ] Context detector implementation
- [ ] Basic mode registry

### Week 2  
- [ ] Template library (3 templates)
- [ ] Task generator
- [ ] Interactive creator flow

### Week 3
- [ ] Simple task coordinator
- [ ] Assignment tracker
- [ ] Basic workflow adapter

### Week 4
- [ ] Mode switching tools
- [ ] Unified interface
- [ ] State management
- [ ] Integration testing

## Next Phase Preview

Phase 2 will build on this foundation by:
- Adding Enricher Mode for improving existing boards
- Implementing AI-powered PRD analysis
- Building dependency inference engine
- Creating learning system basics