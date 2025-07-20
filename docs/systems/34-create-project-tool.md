# 34. Create Project Tool System

## System Overview

The `create_project` tool is Marcus's flagship MCP (Model Context Protocol) tool that transforms natural language project descriptions into fully structured, actionable project boards with intelligent task breakdowns, dependencies, and resource allocations. It serves as the primary entry point for users to initiate new projects within the Marcus ecosystem.

### Unique Characteristics

Unlike other MCP tools in Marcus that perform synchronous, stateless operations, `create_project` is a sophisticated orchestration tool that:

1. **Manages Complex State**: Maintains project context throughout multi-stage processing
2. **Coordinates Multiple Subsystems**: Integrates NLP, AI analysis, dependency inference, and Kanban board creation
3. **Handles Asynchronous Operations**: Uses background tasks for pipeline tracking and cleanup
4. **Provides Rich Feedback**: Offers real-time progress tracking through the visualization pipeline

### MCP Integration Challenges

The tool's unique use of background tasks (`asyncio.create_task()`) for pipeline tracking creates specific challenges with the MCP protocol:

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Client Request                       │
│                  (Claude Code, VS Code)                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  create_project Tool                        │
│  • Validates parameters                                     │
│  • Creates tracking flow ID                                │
│  • Initiates background tracking ← ISSUE: Keeps alive      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    JSON-RPC Response                        │
│  • Must complete cleanly                                    │
│  • Background tasks prevent process exit                    │
│  • Client waits indefinitely                                │
└─────────────────────────────────────────────────────────────┘
```

## Architecture Deep Dive

### 1. Entry Point: MCP Tool Layer (`src/marcus_mcp/tools/nlp.py`)

The `create_project` function serves as the MCP-accessible endpoint with sophisticated parameter handling:

```python
async def create_project(
    description: str,
    project_name: str,
    state: Any,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
```

**Key Responsibilities**:

1. **Parameter Validation**: 
   - Ensures description is meaningful (not empty, not just punctuation)
   - Validates project name format and uniqueness
   - Provides helpful usage examples on validation failure

2. **Pipeline Tracking Initialization**:
   - Generates unique flow IDs for visualization
   - Creates background tracking tasks (source of MCP issues)
   - Logs events to real-time monitoring systems

3. **Error Recovery**:
   - Comprehensive try-catch with detailed error tracking
   - Fallback mechanisms for partial failures
   - User-friendly error messages with actionable guidance

### 2. Processing Layer: NaturalLanguageProjectCreator (`src/integrations/nlp_tools.py`)

This layer handles the core project creation logic:

```python
class NaturalLanguageProjectCreator(NaturalLanguageTaskCreator):
    def __init__(self, state, flow_id: Optional[str] = None):
        self.state = state
        self.flow_id = flow_id
        self.board_analyzer = BoardAnalyzer()
        self.context_detector = ContextDetector(state.events)
        self.prd_parser = AdvancedPRDParser(state.ai_engine)
```

**Processing Pipeline**:

1. **Context Detection**: Analyzes current board state to determine creation mode
2. **Constraint Building**: Maps user options to internal project constraints
3. **PRD Generation**: Uses AI to parse description into structured requirements
4. **Task Creation**: Transforms requirements into actionable tasks
5. **Dependency Inference**: Establishes logical task relationships
6. **Safety Validation**: Ensures task ordering follows best practices
7. **Kanban Integration**: Creates tasks on the board with proper metadata

### 3. Background Task Management

The tool creates three types of background tasks that cause MCP protocol issues:

#### a. Pipeline Start Tracking
```python
# Line 175 in nlp.py
asyncio.create_task(asyncio.to_thread(track_start))
```
**Purpose**: Records pipeline initiation for monitoring
**Issue**: Keeps event loop alive after response

#### b. Pipeline Completion Tracking
```python
# Line 271 in nlp.py
asyncio.create_task(asyncio.to_thread(track_completion))
```
**Purpose**: Records successful completion metrics
**Issue**: Continues running after tool returns

#### c. Background Cleanup
```python
# Line 224 in nlp_tools.py
asyncio.create_task(self._cleanup_background())
```
**Purpose**: Cleans up temporary resources and caches
**Issue**: Long-running cleanup prevents process exit

### 4. Data Flow and State Management

```
User Input
    │
    ▼
Parameter Validation
    │
    ▼
Flow ID Generation ──────► Pipeline Tracking (Background)
    │
    ▼
Context Detection
    │
    ▼
PRD Parsing (AI)
    │
    ▼
Task Generation
    │
    ▼
Dependency Inference
    │
    ▼
Safety Validation
    │
    ▼
Kanban Board Creation
    │
    ▼
Response Generation ──────► Cleanup Tasks (Background)
    │
    ▼
MCP Response
```

## Intelligence Components

### 1. Advanced PRD Parser

The PRD (Product Requirements Document) parser uses Claude to transform natural language into structured data:

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
    complexity_assessment: Dict[str, Any]
    risk_factors: List[Dict[str, Any]]
    confidence: float
```

**AI Prompt Engineering**:
- Structured output format enforcement
- Domain-specific examples for guidance
- Confidence scoring for quality assessment
- Fallback strategies for ambiguous inputs

### 2. Hybrid Dependency Inference

Combines pattern-based rules with AI analysis:

```python
# Pattern-based (fast, deterministic)
dependency_patterns = [
    {"pattern": r"setup|install|configure", "depends_on": None},
    {"pattern": r"implement|build|create", "depends_on": r"setup|design"},
    {"pattern": r"test|verify|validate", "depends_on": r"implement|build"},
    {"pattern": r"deploy|release|launch", "depends_on": r"test|verify"}
]

# AI-based (intelligent, context-aware)
ai_analysis = await self.ai_engine.analyze_dependencies(
    tasks=tasks,
    project_context=context,
    confidence_threshold=0.7
)
```

### 3. Task Classification and Safety

The safety checker enforces logical task ordering:

```python
class SafetyChecker:
    def apply_safety_checks(self, tasks: List[Task]) -> List[Task]:
        # Rule 1: Testing depends on implementation
        # Rule 2: Deployment depends on testing
        # Rule 3: Documentation can run in parallel
        # Rule 4: Infrastructure must precede dependent services
```

## Options and Complexity Handling

### User-Friendly Options Mapping

```python
options = {
    "complexity": "standard",      # prototype | standard | enterprise
    "team_size": 3,               # 1-20 developers
    "deployment": "internal",     # none | internal | production
    "deadline": "2024-12-31",     # ISO date format
    "tech_stack": ["Python", "React", "PostgreSQL"]
}
```

### Complexity-Based Task Generation

**Prototype (3-8 tasks)**:
- Minimal setup and configuration
- Core functionality only
- Basic testing
- Local deployment

**Standard (10-20 tasks)**:
- Proper architecture setup
- Full feature implementation
- Comprehensive testing
- Staging deployment

**Enterprise (25+ tasks)**:
- Microservices architecture
- Security and compliance
- Performance optimization
- Full CI/CD pipeline
- Monitoring and alerting

## Performance Characteristics

### Latency Breakdown

1. **Parameter Validation**: ~50ms
2. **Context Detection**: ~100ms
3. **AI PRD Parsing**: 2-5 seconds (primary bottleneck)
4. **Task Generation**: ~200ms
5. **Dependency Inference**: 
   - Pattern-based: ~100ms
   - AI-enhanced: 1-3 seconds
6. **Kanban Creation**: ~500ms per task
7. **Total**: 5-30 seconds depending on project size

### Resource Consumption

- **Memory**: ~50-200MB depending on project size
- **CPU**: Minimal except during AI processing
- **Network**: Multiple API calls to Claude and Kanban provider
- **Disk I/O**: Minimal (logging and caching)

## Error Handling Philosophy

The tool implements defense-in-depth error handling:

```python
# Level 1: Parameter validation with helpful messages
if not description or description.strip() in ["", ".", "?", "!"]:
    return {
        "error": "Project description cannot be empty",
        "usage": "Provide a description like: 'Create a task management app...'",
        "examples": [...]
    }

# Level 2: Contextual error wrapping
with error_context("project_creation", project_name=project_name):
    result = await create_project_internal(...)

# Level 3: Graceful degradation
try:
    ai_dependencies = await infer_dependencies_with_ai(tasks)
except AIServiceError:
    logger.warning("AI dependency inference failed, using patterns only")
    dependencies = infer_dependencies_with_patterns(tasks)

# Level 4: User-friendly error responses
except Exception as e:
    return {
        "error": "Failed to create project",
        "details": str(e),
        "suggestion": "Try simplifying your project description",
        "support": "Contact support with error ID: {}".format(error_id)
    }
```

## MCP Protocol Compliance Issues

### The Background Task Problem

The MCP protocol expects tools to:
1. Process the request synchronously or asynchronously
2. Return a complete response
3. Allow the process to exit cleanly

The `create_project` tool violates #3 by creating fire-and-forget background tasks that keep the asyncio event loop alive.

### Current Mitigation Attempts

1. **Task Cleanup on Shutdown** (lines 629-635 in server.py):
```python
finally:
    # Cancel all pending tasks to ensure clean shutdown
    pending = asyncio.all_tasks() - {asyncio.current_task()}
    for task in pending:
        task.cancel()
```

2. **MCP Context Detection** (attempted fix):
```python
# Skip tracking for MCP calls to prevent hanging
if not getattr(state, '_is_mcp_call', True):
    asyncio.create_task(asyncio.to_thread(track_start))
```

### Proper Solution Approaches

1. **Synchronous Tracking**: Make tracking operations synchronous but lightweight
2. **External Queue**: Send tracking events to external queue (Redis, RabbitMQ)
3. **Structured Concurrency**: Use `asyncio.TaskGroup` with proper lifecycle management
4. **Process Separation**: Run tracking in separate process that doesn't block MCP

## Comparison with Other MCP Tools

### Simple MCP Tools (ping, get_status, etc.)
- **Execution**: Synchronous or simple async
- **State**: Stateless
- **Background Tasks**: None
- **Response Time**: <100ms
- **Process Exit**: Clean

### create_project Tool
- **Execution**: Complex multi-stage async
- **State**: Maintains flow state throughout
- **Background Tasks**: Multiple (tracking, cleanup)
- **Response Time**: 5-30 seconds
- **Process Exit**: Blocked by background tasks

## Testing Considerations

### Unit Testing Challenges

1. **AI Mocking**: Need to mock Claude API responses consistently
2. **Async Complexity**: Multiple async operations require careful test orchestration
3. **Background Tasks**: Tests must handle or disable background tasks
4. **State Management**: Complex state makes isolated testing difficult

### Integration Testing Requirements

1. **End-to-End Flow**: Test complete project creation pipeline
2. **Error Scenarios**: Verify graceful handling of AI failures
3. **Performance**: Ensure reasonable latency for different project sizes
4. **MCP Compliance**: Verify clean process exit after response

## Future Improvements

### 1. Structured Concurrency
Replace fire-and-forget with managed task groups:
```python
async with asyncio.TaskGroup() as tg:
    tg.create_task(track_operation())
    # All tasks complete before exiting context
```

### 2. Event-Driven Architecture
Decouple tracking from request processing:
```python
await event_bus.publish("project.created", {
    "project_id": project_id,
    "task_count": len(tasks)
})
# Separate service handles tracking
```

### 3. Streaming Responses
Return progress updates during long operations:
```python
async def create_project_streaming():
    yield {"status": "parsing", "progress": 0.2}
    yield {"status": "generating", "progress": 0.5}
    yield {"status": "creating", "progress": 0.8}
    yield {"status": "complete", "result": {...}}
```

### 4. Caching Layer
Reduce AI calls for similar projects:
```python
cache_key = hash(description + str(options))
if cached_result := await cache.get(cache_key):
    return await apply_to_board(cached_result)
```

## Monitoring and Observability

### Key Metrics

1. **Success Rate**: Percentage of successful project creations
2. **Latency Distribution**: P50, P90, P99 response times
3. **AI Token Usage**: Cost tracking per project
4. **Task Quality**: User satisfaction scores
5. **Background Task Health**: Completion rates and durations

### Logging Strategy

```python
# Structured logging with correlation IDs
logger.info("project_creation_started", extra={
    "flow_id": flow_id,
    "project_name": project_name,
    "description_length": len(description),
    "options": options
})

# Performance tracking
with timer("prd_parsing"):
    prd_result = await parser.parse(description)
    
logger.info("prd_parsing_complete", extra={
    "duration_ms": timer.elapsed_ms,
    "task_count": len(prd_result.tasks)
})
```

## Conclusion

The `create_project` tool represents both the power and complexity of Marcus's natural language project management capabilities. While its sophisticated multi-stage processing pipeline enables remarkable functionality, the use of background tasks creates specific challenges with MCP protocol compliance.

Understanding these architectural decisions and their implications is crucial for:
1. Debugging hanging connections
2. Optimizing performance
3. Extending functionality
4. Maintaining MCP compliance

The tool's evolution from a simple task creator to a comprehensive project orchestrator demonstrates Marcus's ambition to bridge human intent with automated execution, even as it highlights the tensions between rich functionality and protocol constraints.