# PM Agent AI Analysis Engine API Reference

> **Type**: API  
> **Version**: 1.0.0  
> **Last Updated**: 2025-06-25

## Overview

Complete reference for the AI Analysis Engine that powers intelligent task assignment, instruction generation, and blocker resolution in PM Agent.

## Synopsis

```python
from src.integrations.ai_analysis_engine_fixed import AIAnalysisEngine

# Initialize engine
ai_engine = AIAnalysisEngine()

# Generate task instructions
instructions = await ai_engine.generate_task_instructions(
    task=task,
    worker=worker,
    previous_implementations=context
)
```

## Description

The AI Analysis Engine leverages Claude AI to provide intelligent project management capabilities. It analyzes tasks, worker skills, and project context to generate personalized instructions, resolve blockers, and optimize task assignments. The engine includes fallback mechanisms for reliability and caching for performance.

## Parameters

### AIAnalysisEngine Class

Core AI analysis functionality.

| Method | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `__init__()` | constructor | - | - | Initialize with API key from environment |
| `generate_task_instructions()` | async | Yes | - | Create detailed task instructions |
| `analyze_blocker()` | async | Yes | - | Provide blocker solutions |
| `suggest_optimal_assignment()` | async | Yes | - | Match tasks to workers |
| `analyze_project_health()` | async | Yes | - | Assess project status |
| `generate_daily_plan()` | async | Yes | - | Create daily work plans |

### Method Details

#### generate_task_instructions()

Generates personalized, detailed instructions for a task.

```python
async def generate_task_instructions(
    self,
    task: Task,
    worker: Optional[WorkerStatus] = None,
    previous_implementations: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate detailed implementation instructions.
    
    Parameters:
        task: Task to generate instructions for
        worker: Optional worker info for personalization
        previous_implementations: Context from similar tasks
        
    Returns:
        Detailed, step-by-step instructions
        
    Raises:
        AnthropicError: If AI API fails
    """
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task` | Task | Yes | - | Task requiring instructions |
| `worker` | WorkerStatus | No | None | Worker for skill-based customization |
| `previous_implementations` | Dict | No | None | Code context from dependencies |

##### Return Format
```
Step-by-step instructions:

1. **Setup Phase** (15 minutes)
   - Review existing authentication module at `src/auth.py`
   - Set up test environment with mock database

2. **Implementation** (2 hours)
   - Create JWT token generation in `src/auth/tokens.py`
   - Implement refresh token logic
   - Add token validation middleware

3. **Testing** (45 minutes)
   - Write unit tests for token generation
   - Test expiration handling
   - Verify refresh flow

4. **Documentation** (30 minutes)
   - Update API documentation
   - Add usage examples
```

#### analyze_blocker()

Provides intelligent solutions for reported blockers.

```python
async def analyze_blocker(
    self,
    blocker_description: str,
    task: Optional[Task] = None,
    worker: Optional[WorkerStatus] = None,
    severity: str = "medium"
) -> str:
    """
    Analyze blocker and suggest solutions.
    
    Parameters:
        blocker_description: Detailed blocker description
        task: Optional task context
        worker: Optional worker context
        severity: Blocker severity level
        
    Returns:
        Actionable suggestions to resolve blocker
    """
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `blocker_description` | string | Yes | - | Detailed description of the issue |
| `task` | Task | No | None | Task being blocked |
| `worker` | WorkerStatus | No | None | Worker experiencing blocker |
| `severity` | string | No | "medium" | Severity: low, medium, high |

##### Return Format
```
Blocker Analysis: Database Connection Timeout

Root Cause:
The PostgreSQL connection is timing out likely due to network issues or misconfiguration.

Immediate Solutions:
1. Check database server status: `pg_isready -h localhost -p 5432`
2. Verify connection string in `.env` file
3. Test direct connection: `psql -h localhost -U postgres`

Alternative Approaches:
- Use SQLite for local development temporarily
- Mock database responses for testing
- Check Docker container if using containerized DB

Escalation Path:
If unresolved in 2 hours, contact DevOps team for infrastructure support.
```

#### suggest_optimal_assignment()

Matches tasks to workers based on skills and availability.

```python
async def suggest_optimal_assignment(
    self,
    tasks: List[Task],
    workers: List[WorkerStatus]
) -> List[Dict[str, Any]]:
    """
    Suggest optimal task-worker assignments.
    
    Parameters:
        tasks: Available tasks to assign
        workers: Available workers
        
    Returns:
        List of assignment recommendations with scores
    """
```

##### Return Format
```python
[
    {
        "task_id": "task-123",
        "task_name": "Implement OAuth2",
        "suggested_worker": "backend-dev-001",
        "worker_name": "Alice Smith",
        "match_score": 0.95,
        "reasoning": "Strong OAuth experience, available capacity",
        "estimated_completion": "2024-01-22T15:00:00Z"
    }
]
```

#### analyze_project_health()

Comprehensive project health assessment.

```python
async def analyze_project_health(
    self,
    project_state: ProjectState,
    recent_activities: List[Dict[str, Any]],
    team_status: List[WorkerStatus]
) -> Dict[str, Any]:
    """
    Analyze overall project health.
    
    Parameters:
        project_state: Current project metrics
        recent_activities: Recent task activities
        team_status: Team member statuses
        
    Returns:
        Comprehensive health analysis
    """
```

##### Return Format
```python
{
    "health_status": "yellow",  # green, yellow, red
    "confidence_level": 0.8,
    "timeline_prediction": {
        "estimated_completion": "2024-02-15",
        "confidence": 0.75,
        "risk_factors": ["3 blocked tasks", "Key developer on vacation"]
    },
    "recommendations": [
        {
            "priority": "high",
            "action": "Unblock authentication tasks",
            "impact": "Unlocks 5 dependent tasks"
        }
    ],
    "team_insights": {
        "utilization": 0.85,
        "bottlenecks": ["Frontend capacity at 95%"],
        "recommendations": ["Consider load balancing React tasks"]
    }
}
```

#### generate_daily_plan()

Creates optimized daily work plans.

```python
async def generate_daily_plan(
    self,
    workers: List[WorkerStatus],
    available_tasks: List[Task],
    constraints: Optional[Dict[str, Any]] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate daily work plan for team.
    
    Parameters:
        workers: Team members
        available_tasks: Tasks to distribute
        constraints: Optional scheduling constraints
        
    Returns:
        Personalized daily plans per worker
    """
```

## Return Values

### Success Response

All methods return structured data appropriate to their function:

```python
# Instruction generation
instructions = "1. First, set up your environment...\n2. Implement the feature..."

# Blocker analysis
suggestions = "Try these solutions:\n1. Check connection string...\n2. Verify firewall..."

# Health analysis
analysis = {
    "health_status": "green",
    "recommendations": [...]
}
```

### Error Response

```python
# API errors
AnthropicError("API rate limit exceeded")

# Validation errors
ValueError("Task must have a name and description")

# Fallback responses
"[Fallback] Basic task instructions based on task type..."
```

## Examples

### Basic Example
```python
# Simple instruction generation
ai_engine = AIAnalysisEngine()

task = Task(
    id="task-123",
    name="Add user registration",
    description="Implement user registration with email verification",
    # ... other fields
)

instructions = await ai_engine.generate_task_instructions(task)
print(instructions)
```

### Advanced Example
```python
# Complete AI-powered workflow
class IntelligentTaskManager:
    def __init__(self):
        self.ai_engine = AIAnalysisEngine()
        self.kanban = KanbanFactory.create_default()
    
    async def assign_task_intelligently(
        self, 
        task_id: str, 
        available_workers: List[WorkerStatus]
    ):
        # Get task details
        task = await self.kanban.get_task_by_id(task_id)
        
        # Find best worker match
        assignments = await self.ai_engine.suggest_optimal_assignment(
            [task], 
            available_workers
        )
        
        if not assignments:
            return None
            
        best_match = assignments[0]
        worker_id = best_match["suggested_worker"]
        
        # Generate personalized instructions
        worker = next(w for w in available_workers if w.worker_id == worker_id)
        instructions = await self.ai_engine.generate_task_instructions(
            task, 
            worker
        )
        
        # Create assignment
        return {
            "task_id": task_id,
            "worker_id": worker_id,
            "instructions": instructions,
            "confidence": best_match["match_score"]
        }
```

### Real-World Example
```python
# Production AI engine with monitoring and fallbacks
class ProductionAIEngine(AIAnalysisEngine):
    def __init__(self):
        super().__init__()
        self.metrics = MetricsCollector()
        self.cache = RedisCache()
    
    async def generate_task_instructions(
        self, 
        task: Task, 
        worker: Optional[WorkerStatus] = None,
        previous_implementations: Optional[Dict] = None
    ) -> str:
        # Check cache first
        cache_key = f"instructions:{task.id}:{worker.worker_id if worker else 'none'}"
        cached = await self.cache.get(cache_key)
        if cached:
            self.metrics.increment("cache_hits")
            return cached
        
        # Track API usage
        start_time = time.time()
        
        try:
            # Try primary AI
            instructions = await super().generate_task_instructions(
                task, worker, previous_implementations
            )
            
            # Cache successful response
            await self.cache.set(cache_key, instructions, ttl=3600)
            
            # Record metrics
            self.metrics.record_latency("ai_instructions", time.time() - start_time)
            self.metrics.increment("ai_success")
            
            return instructions
            
        except AnthropicError as e:
            # Track failures
            self.metrics.increment("ai_failures")
            
            # Use fallback
            if "rate_limit" in str(e):
                self.metrics.increment("rate_limits")
                
            return self._generate_fallback_instructions(task, worker)
    
    def _generate_fallback_instructions(
        self, 
        task: Task, 
        worker: Optional[WorkerStatus]
    ) -> str:
        """Enhanced fallback with templates"""
        
        # Task type detection
        task_type = self._detect_task_type(task)
        
        # Load template
        template = self.load_template(task_type)
        
        # Customize for worker
        if worker and worker.skills:
            template = self._customize_for_skills(template, worker.skills)
        
        return template.format(
            task_name=task.name,
            description=task.description,
            estimated_hours=task.estimated_hours
        )
```

## Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| `ANTHROPIC_API_ERROR` | AI API request failed | Check API key and status |
| `RATE_LIMIT_EXCEEDED` | Too many requests | Implement backoff/caching |
| `INVALID_TASK_DATA` | Task missing required fields | Validate task before calling |
| `TIMEOUT_ERROR` | AI request timed out | Retry or use fallback |
| `INSUFFICIENT_CONTEXT` | Not enough data for analysis | Provide more context |

## Notes

- All methods are async and should be awaited
- API key must be set via ANTHROPIC_API_KEY env var
- Includes automatic retry with exponential backoff
- Fallback mechanisms ensure reliability
- Responses are optimized for developer comprehension

## Performance Considerations

### Caching Strategy
- Instructions cached for 1 hour per task/worker combo
- Blocker solutions cached for 15 minutes
- Health analysis cached for 5 minutes
- Cache invalidated on task updates

### API Optimization
- Batches multiple analyses when possible
- Uses streaming for long responses
- Implements request queuing
- Respects rate limits automatically

### Response Times
| Operation | Average | Maximum |
|-----------|---------|---------|
| Generate instructions | 2-3s | 10s |
| Analyze blocker | 1-2s | 5s |
| Project health | 3-5s | 15s |
| Daily planning | 5-10s | 30s |

## Configuration

### Model Selection
```python
# In config file or environment
{
    "ai_settings": {
        "model": "claude-3-sonnet-20241022",
        "temperature": 0.7,
        "max_tokens": 2000
    }
}
```

### Fallback Configuration
```python
{
    "ai_settings": {
        "enable_fallback": true,
        "fallback_delay_ms": 5000,
        "retry_attempts": 3
    }
}
```

## Version History

| Version | Changes |
|---------|---------|
| 1.0.0 | Complete AI engine documentation |
| 0.9.0 | Added project health analysis |
| 0.8.0 | Added daily planning |
| 0.7.0 | Initial release with core features |

## See Also

- [Configuration Guide](/reference/configuration_guide)
- [MCP Tools API](/reference/mcp_tools_api)
- [Task Assignment Guide](/how-to/task_assignment)
- [AI Best Practices](/how-to/ai_best_practices)