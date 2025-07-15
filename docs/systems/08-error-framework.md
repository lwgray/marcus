# Marcus Error Framework System

## Executive Summary

The Marcus Error Framework is a comprehensive, autonomous agent-optimized error handling system that provides structured exception hierarchies, intelligent recovery strategies, circuit breaker patterns, and real-time monitoring capabilities. Unlike traditional error handling systems designed for human-operated applications, this framework is specifically engineered for autonomous agent environments where errors must be self-diagnosing, self-recovering, and provide actionable intelligence for both automated retry logic and human escalation.

## System Architecture

### Core Components

The Error Framework consists of four primary modules operating in concert:

```
Marcus Error Framework Architecture
├── error_framework.py (Core Exception System)
│   ├── MarcusBaseError (Base Exception Class)
│   ├── ErrorContext (Rich Contextual Information)
│   ├── RemediationSuggestion (Recovery Guidance)
│   └── Error Type Hierarchy (Domain-Specific Exceptions)
├── error_strategies.py (Recovery Strategies)
│   ├── RetryHandler (Exponential Backoff & Jitter)
│   ├── CircuitBreaker (Cascade Failure Prevention)
│   ├── FallbackHandler (Graceful Degradation)
│   └── ErrorAggregator (Batch Operation Handling)
├── error_responses.py (Format Adapters)
│   ├── MCP Protocol Responses
│   ├── JSON API Responses
│   ├── User-Friendly Messages
│   └── Logging & Monitoring Formats
└── error_monitoring.py (Intelligence & Analytics)
    ├── Pattern Detection Engine
    ├── Correlation Analysis
    ├── Health Scoring Algorithm
    └── Alert Management System
```

### Error Type Taxonomy

The framework implements a sophisticated six-tier error classification system:

**Tier 1: Transient Errors** (Auto-recoverable)
- `NetworkTimeoutError`: Network operations exceeding time limits
- `ServiceUnavailableError`: Temporary external service outages
- `RateLimitError`: API rate limit violations with retry timing
- `TemporaryResourceError`: Temporary system resource exhaustion

**Tier 2: Configuration Errors** (User-resolvable)
- `MissingCredentialsError`: Absent authentication credentials
- `InvalidConfigurationError`: Malformed configuration values
- `MissingDependencyError`: Required dependencies not installed
- `EnvironmentError`: Incorrect environment setup

**Tier 3: Business Logic Errors** (Logic violations)
- `TaskAssignmentError`: Task allocation conflicts or impossibilities
- `WorkflowViolationError`: Workflow state machine violations
- `ValidationError`: Data validation failures
- `StateConflictError`: System state inconsistencies

**Tier 4: Integration Errors** (External service issues)
- `KanbanIntegrationError`: Kanban board connectivity/operation failures
- `AIProviderError`: AI service integration failures
- `AuthenticationError`: External service authentication failures
- `ExternalServiceError`: Generic external service errors

**Tier 5: Security Errors** (Critical security events)
- `AuthorizationError`: Permission/authorization violations
- `WorkspaceSecurityError`: Workspace isolation breaches
- `PermissionError`: File/resource permission violations

**Tier 6: System Errors** (Critical infrastructure failures)
- `ResourceExhaustionError`: System resource depletion
- `CorruptedStateError`: Data corruption detection
- `DatabaseError`: Database operation failures
- `CriticalDependencyError`: Essential system component failures

## Marcus Ecosystem Integration

### Position in System Architecture

The Error Framework operates as a cross-cutting concern throughout the Marcus ecosystem:

1. **MCP Server Layer**: All MCP tool calls are wrapped with error handling for consistent response formatting
2. **Agent Workflow Layer**: Task assignment, progress reporting, and blocker handling utilize error context and retry strategies
3. **Integration Layer**: External service calls (Kanban, AI providers) are protected by circuit breakers and fallback mechanisms
4. **Core Processing Layer**: Business logic operations leverage validation and state conflict detection
5. **Monitoring Layer**: All errors feed into the monitoring system for pattern analysis and health scoring

### Workflow Integration Points

The Error Framework intercepts and enhances error handling at key workflow stages:

```
Typical Agent Workflow Error Integration:
create_project → register_agent → request_next_task → report_progress → report_blocker → finish_task
      ↓              ↓                    ↓                  ↓               ↓            ↓
Configuration    Business Logic      Integration        Business Logic   Integration   Integration
   Errors          Errors             Errors             Errors          Errors        Errors
      ↓              ↓                    ↓                  ↓               ↓            ↓
   No Retry    Validation &         Circuit Breaker    Context Logging  AI-Powered   Final Cleanup
               State Checking        & Retry Logic      & Monitoring    Suggestions   & Reporting
```

## Error Context System

### Rich Contextual Information

Every Marcus error carries comprehensive context through the `ErrorContext` class:

```python
@dataclass
class ErrorContext:
    # Operation identification
    operation: str = ""                    # What was being attempted
    operation_id: str = uuid4()           # Unique operation identifier

    # Agent context
    agent_id: Optional[str] = None        # Which agent encountered the error
    task_id: Optional[str] = None         # Current task being processed
    agent_state: Optional[Dict] = None    # Agent's current state snapshot

    # System context
    timestamp: datetime = now()           # When error occurred
    correlation_id: str = uuid4()         # For tracing related operations
    system_state: Optional[Dict] = None   # System resource state

    # Integration context
    integration_name: Optional[str] = None    # External service involved
    integration_state: Optional[Dict] = None  # Service-specific state

    # Extensible context
    user_context: Optional[Dict] = None       # User-specific information
    custom_context: Optional[Dict] = None     # Operation-specific data
```

### Context Automation

The framework provides automatic context injection through the `error_context` context manager:

```python
with error_context("kanban_sync", agent_id="agent_123", task_id="task_456"):
    # Any MarcusBaseError raised here automatically includes context
    sync_task_with_kanban()
```

## Intelligence & Recovery Strategies

### Retry Logic with Exponential Backoff

The retry system implements sophisticated backoff strategies:

```python
class RetryConfig:
    max_attempts: int = 3               # Maximum retry attempts
    base_delay: float = 1.0            # Initial delay in seconds
    max_delay: float = 60.0            # Maximum delay cap
    multiplier: float = 2.0            # Exponential multiplier
    jitter: bool = True                # Add randomization
    retry_on: tuple = (TransientError,) # Which error types to retry
    stop_on: tuple = ()                # Error types that stop retries
```

**Jitter Algorithm**: `delay = base_delay * (multiplier ^ attempt) + random(0, delay * 0.1)`

**Benefits**:
- Prevents thundering herd problems
- Adapts to different error types
- Configurable per operation type
- Automatic classification of retryable errors

### Circuit Breaker Pattern

Prevents cascading failures through intelligent service protection:

```python
class CircuitBreakerStates:
    CLOSED: Normal operation, errors tracked
    OPEN: Service blocked, failing fast
    HALF_OPEN: Testing if service recovered
```

**State Transitions**:
- CLOSED → OPEN: After `failure_threshold` consecutive failures
- OPEN → HALF_OPEN: After `timeout` duration expires
- HALF_OPEN → CLOSED: After `success_threshold` consecutive successes
- HALF_OPEN → OPEN: On any failure during testing

**Autonomous Benefits**:
- Prevents agents from hammering failing services
- Automatic recovery testing
- Service health awareness
- Resource conservation

### Fallback Mechanisms

Graceful degradation through priority-ordered fallback functions:

```python
fallback_handler = FallbackHandler("task_creation")
fallback_handler.add_fallback(create_task_locally, priority=1)      # Try first
fallback_handler.add_fallback(queue_for_later, priority=2)         # Then this
fallback_handler.add_fallback(use_cached_template, priority=3)     # Finally this
```

**Fallback Strategy Selection**:
1. Primary function attempted
2. On failure, fallbacks tried in priority order
3. First successful fallback result returned
4. If all fail, cached results used if available
5. If no cache, enhanced error with exhausted fallback information

## Real-Time Monitoring & Pattern Detection

### Error Pattern Detection

The monitoring system identifies four categories of error patterns:

**1. Frequency Patterns**: Same error type occurring repeatedly
```
Threshold: 5+ occurrences within 10 minutes
Detection: Error type fingerprinting
Action: Pattern alert with error type analysis
```

**2. Burst Patterns**: High error volume in short timeframe
```
Threshold: 10+ errors within 5 minutes (any type)
Detection: Time-window error counting
Action: System stability alert
```

**3. Agent-Specific Patterns**: High error rate from individual agents
```
Threshold: 20+ errors from single agent within 30 minutes
Detection: Agent ID error aggregation
Action: Agent health check recommendation
```

**4. Cascade Patterns**: Related errors occurring in sequence
```
Threshold: 3+ similar errors with 70%+ similarity within 5 minutes
Detection: Multi-dimensional error similarity scoring
Action: Root cause investigation trigger
```

### Error Similarity Algorithm

The framework calculates error similarity using weighted factors:

```python
def calculate_similarity(error1, error2) -> float:
    factors = []
    if error1.error_type == error2.error_type: factors.append(0.4)      # 40% weight
    if error1.operation == error2.operation: factors.append(0.3)        # 30% weight
    if error1.integration == error2.integration: factors.append(0.2)    # 20% weight
    if abs(error1.timestamp - error2.timestamp) < 60s: factors.append(0.1)  # 10% weight
    return sum(factors)  # 0.0 to 1.0 similarity score
```

### Health Scoring Algorithm

System health calculated as weighted score (0-100):

```python
health_score = 100
if error_rate_per_minute > 10: health_score -= 30
elif error_rate_per_minute > 5: health_score -= 15
elif error_rate_per_minute > 2: health_score -= 5
if critical_errors > 0: health_score -= 25
health_score -= active_patterns * 10  # 10 points per active pattern
health_score = max(0, health_score)
```

**Health Status Mapping**:
- 90-100: Excellent
- 75-89: Good
- 50-74: Fair
- 25-49: Poor
- 0-24: Critical

## Response Format Adapters

### MCP Protocol Format

Optimized for Claude Code agent consumption:

```json
{
  "success": false,
  "error": {
    "code": "KANBAN_INTEGRATION_ERROR",
    "message": "Failed to create task on board 'Development'",
    "type": "KanbanIntegrationError",
    "severity": "medium",
    "retryable": true,
    "context": {
      "operation": "create_task",
      "correlation_id": "corr_abc123",
      "agent_id": "agent_dev_001",
      "task_id": "task_456"
    },
    "remediation": {
      "immediate": "Retry task creation with exponential backoff",
      "fallback": "Create task locally and sync when service recovers",
      "retry": "Automatic retry in 2.5 seconds (attempt 2/3)"
    }
  }
}
```

### User-Friendly Format

Human-readable error presentation:

```
Unable to create task on Kanban board due to service timeout.

💡 What to do: The system will retry automatically in 30 seconds
🔄 Alternative: Task has been created locally and will sync when the service recovers
🔁 Retry: This is attempt 2 of 3 - if all attempts fail, the task will remain in local queue
```

### Logging Format

Structured for log analysis and debugging:

```json
{
  "level": "error",
  "timestamp": "2025-07-14T15:30:45.123Z",
  "error_code": "KANBAN_INTEGRATION_ERROR",
  "error_type": "KanbanIntegrationError",
  "correlation_id": "corr_abc123",
  "operation": "create_task",
  "agent_id": "agent_dev_001",
  "task_id": "task_456",
  "integration": "planka_board",
  "retryable": true,
  "severity": "medium",
  "caused_by": "requests.exceptions.Timeout",
  "custom_context": {
    "board_id": "board_789",
    "task_title": "Implement user authentication"
  }
}
```

## Workflow Stage Integration

### create_project Stage
**Error Types**: Configuration, Validation
**Handling**:
- Immediate validation of project parameters
- Configuration error detection and user guidance
- No retries (user input required)
- Clear remediation instructions

### register_agent Stage
**Error Types**: Business Logic, System
**Handling**:
- Agent ID validation and conflict detection
- Capability matching verification
- State initialization error recovery
- Agent registry consistency checking

### request_next_task Stage
**Error Types**: Integration, Business Logic, Transient
**Handling**:
- Kanban integration with circuit breaker protection
- Task assignment algorithm error recovery
- AI-powered task matching with fallbacks
- Dependency conflict resolution

### report_progress Stage
**Error Types**: Integration, Validation, Transient
**Handling**:
- Progress validation against task constraints
- Kanban sync with retry logic
- State consistency verification
- Context preservation for correlation

### report_blocker Stage
**Error Types**: Integration, AI Provider, Business Logic
**Handling**:
- AI-powered suggestion generation with fallbacks
- Blocker classification and severity assessment
- Escalation path determination
- Context aggregation for pattern analysis

### finish_task Stage
**Error Types**: Integration, System, Validation
**Handling**:
- Task completion validation
- Final state synchronization
- Cleanup operation error handling
- Correlation group closure

## Simple vs Complex Task Handling

### Simple Tasks (< 3 dependencies, single agent)
**Error Strategy**:
- Basic retry logic (3 attempts, 1s base delay)
- Simple circuit breaker (5 failure threshold)
- Minimal context collection
- Standard monitoring

```python
@with_retry(RetryConfig(max_attempts=3, base_delay=1.0))
async def handle_simple_task():
    # Lightweight error handling
    pass
```

### Complex Tasks (> 3 dependencies, multi-agent coordination)
**Error Strategy**:
- Enhanced retry logic (5 attempts, 2s base delay)
- Sensitive circuit breaker (3 failure threshold)
- Rich context collection including dependency state
- Enhanced monitoring with pattern correlation

```python
@with_retry(RetryConfig(max_attempts=5, base_delay=2.0))
async def handle_complex_task():
    with error_context("complex_task",
                      agent_id=agent_id,
                      task_id=task_id,
                      custom_context={"dependencies": dep_list}):
        # Enhanced error handling with dependency awareness
        pass
```

**Complex Task Enhancements**:
- Dependency state tracking in error context
- Multi-agent error correlation
- Cascade failure prevention
- Enhanced pattern detection sensitivity

## Board-Specific Considerations

### Kanban Provider Abstraction
The Error Framework integrates with Marcus's Kanban provider abstraction layer:

**Planka Provider Errors**:
- Connection timeouts: 30s timeout with 3 retries
- Authentication failures: No retry, immediate credential refresh
- Rate limiting: Exponential backoff with provider-specific limits
- Board access errors: Permission validation and fallback board selection

**Generic Kanban Errors**:
- Provider detection and capability matching
- Failover between multiple configured providers
- Provider-specific error code translation
- Board synchronization conflict resolution

### Board State Consistency
**Error Scenarios**:
- Task creation conflicts during multi-agent operations
- Board state drift during network partitions
- Concurrent modification conflicts
- Board access permission changes

**Resolution Strategies**:
- Optimistic locking with conflict detection
- Last-writer-wins with conflict notification
- Manual merge conflict resolution
- Fallback to local state with delayed sync

## Technical Implementation Details

### Error Context Propagation

The framework uses thread-local storage and async context variables for automatic context propagation:

```python
from contextvars import ContextVar

current_error_context: ContextVar[Optional[ErrorContext]] = ContextVar(
    'current_error_context', default=None
)

@contextmanager
def error_context(operation: str, **context_kwargs):
    context = ErrorContext(operation=operation, **context_kwargs)
    token = current_error_context.set(context)
    try:
        yield context
    finally:
        current_error_context.reset(token)
```

### Memory Management

The monitoring system implements intelligent memory management:

```python
class ErrorMonitor:
    def __init__(self):
        self.error_history: deque = deque(maxlen=10000)  # Ring buffer
        self.pattern_cleanup_threshold = timedelta(days=7)
        self.correlation_timeout = timedelta(hours=24)

    def _cleanup_old_data(self):
        # Automatic cleanup of old patterns and correlations
        # Prevents memory leaks in long-running agents
        pass
```

### Async/Sync Compatibility

The framework provides seamless async/sync compatibility:

```python
def with_retry(config: RetryConfig = None):
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Async implementation
            pass

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Sync implementation using asyncio.run()
            pass

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
```

### Serialization Safety

All error data structures are designed for safe JSON serialization:

```python
@dataclass
class ErrorContext:
    def to_dict(self) -> Dict[str, Any]:
        return {
            'operation': self.operation,
            'timestamp': self.timestamp.isoformat(),
            'custom_context': self.custom_context or {}
        }
```

## Pros and Cons Analysis

### Advantages

**1. Autonomous Agent Optimization**
- Self-diagnosing errors with actionable remediation
- Automatic retry and recovery strategies
- Context-aware error handling
- Pattern detection for proactive issue identification

**2. Comprehensive Error Intelligence**
- Rich contextual information for debugging
- Multi-dimensional error correlation
- Real-time health monitoring and scoring
- Predictive pattern analysis

**3. Integration-Friendly Design**
- Multiple response format adapters
- Seamless legacy code integration
- Configurable retry and circuit breaker policies
- Extensible error type hierarchy

**4. Production-Ready Features**
- Memory-efficient monitoring with cleanup
- Thread-safe and async-compatible
- Structured logging integration
- Security-conscious sensitive data handling

**5. Developer Experience**
- Decorator-based easy integration
- Context manager automatic error enhancement
- Clear error type classification
- Comprehensive remediation suggestions

### Disadvantages

**1. Complexity Overhead**
- Substantial codebase complexity for simple applications
- Learning curve for new developers
- Additional memory footprint for monitoring
- Configuration complexity for advanced features

**2. Performance Considerations**
- Context collection overhead on every error
- Monitoring system background processing
- Pattern detection computational cost
- Serialization overhead for error responses

**3. Framework Lock-in**
- Marcus-specific error types create vendor lock-in
- Migration complexity from existing error handling
- Dependency on Marcus ecosystem components
- Framework-specific debugging knowledge required

**4. Configuration Complexity**
- Multiple configuration layers (retry, circuit breaker, monitoring)
- Environment-specific tuning requirements
- Provider-specific error mapping complexity
- Fine-tuning required for optimal performance

## Design Rationale

### Why This Approach Was Chosen

**1. Autonomous Agent Requirements**
Traditional error handling systems assume human operators who can interpret error messages and take corrective action. Marcus agents require:
- Machine-interpretable error classifications
- Automatic recovery strategies
- Rich context for correlation across operations
- Predictive pattern analysis for proactive issue resolution

**2. Microservices-Style Error Handling**
The framework treats each component (Kanban integration, AI providers, task assignment) as independent services requiring:
- Circuit breaker protection against cascade failures
- Service-specific retry strategies
- Fallback mechanisms for graceful degradation
- Health monitoring and automatic service discovery

**3. Observable System Design**
Error handling as a first-class observability concern:
- Every error contributes to system health understanding
- Pattern detection enables proactive issue resolution
- Error correlation provides root cause analysis
- Health scoring guides system optimization

**4. Developer Experience Priority**
Balancing power with usability:
- Decorator-based integration for minimal code changes
- Context managers for automatic error enhancement
- Clear error type hierarchy for easy classification
- Multiple response formats for different consumption patterns

### Alternative Approaches Considered

**1. Simple Exception Hierarchy**
*Rejected*: Insufficient for autonomous agent needs
- No automatic retry logic
- No context preservation
- No pattern detection capabilities
- No service protection mechanisms

**2. External Error Management Service**
*Rejected*: Added complexity and latency
- Network dependency for error handling
- Additional service to maintain and monitor
- Latency impact on error processing
- Single point of failure

**3. Framework-Agnostic Error Handling**
*Rejected*: Generic solutions lack domain specificity
- No Marcus-specific error types
- No integration with agent workflow
- No Kanban provider awareness
- No AI provider error handling

## Evolution and Future Roadmap

### Short-term Evolution (3-6 months)

**1. Enhanced AI Integration**
- GPT-4 powered error analysis and remediation suggestions
- Automatic root cause analysis using error correlations
- Predictive error modeling based on historical patterns
- Context-aware error severity adjustment

**2. Advanced Pattern Detection**
- Machine learning-based pattern recognition
- Seasonal and cyclical error pattern detection
- Cross-agent error correlation analysis
- Predictive failure forecasting

**3. Performance Optimizations**
- Streaming error data processing
- Compressed error history storage
- Lazy error context evaluation
- Background pattern analysis

### Medium-term Evolution (6-12 months)

**1. Distributed Error Management**
- Multi-instance error correlation
- Distributed circuit breaker coordination
- Global system health aggregation
- Cross-deployment error pattern sharing

**2. Self-Healing Capabilities**
- Automatic configuration adjustment based on error patterns
- Dynamic retry strategy optimization
- Self-tuning circuit breaker thresholds
- Autonomous remediation action execution

**3. Advanced Monitoring Integration**
- Prometheus metrics export
- Grafana dashboard templates
- AlertManager integration
- Custom metric collection and analysis

### Long-term Evolution (1+ years)

**1. Predictive Error Prevention**
- Pre-error condition detection
- Proactive remediation action triggering
- Resource usage prediction and scaling
- Failure cascade prevention

**2. Cross-System Error Learning**
- Error pattern sharing between Marcus instances
- Community-driven error knowledge base
- Automated error handling best practice evolution
- Cross-domain error pattern recognition

**3. Advanced Recovery Strategies**
- AI-powered custom recovery strategy generation
- Dynamic fallback chain optimization
- Context-aware recovery strategy selection
- Self-evolving error handling policies

## Integration Examples

### MCP Tool Integration

```python
async def mcp_create_task(arguments: Dict[str, Any]) -> Dict[str, Any]:
    try:
        with error_context("mcp_create_task",
                          custom_context={"tool": "create_task", "args": arguments}):
            result = await task_service.create_task(arguments)
            return {"success": True, "result": result}

    except Exception as e:
        return handle_mcp_tool_error(e, "create_task", arguments)
```

### Agent Workflow Integration

```python
@with_retry(RetryConfig(max_attempts=3))
@with_circuit_breaker("kanban_service")
async def sync_agent_progress(agent_id: str, task_id: str, progress: int):
    with error_context("progress_sync", agent_id=agent_id, task_id=task_id):
        await kanban_provider.update_task_progress(task_id, progress)
        record_agent_event("progress_updated", agent_id, {"task_id": task_id, "progress": progress})
```

### Legacy Code Migration

```python
# Before: Basic error handling
try:
    result = external_service_call()
    return {"success": True, "data": result}
except Exception as e:
    logger.error(f"Service call failed: {e}")
    return {"success": False, "error": str(e)}

# After: Marcus Error Framework
@with_retry()
@with_circuit_breaker("external_service")
async def safe_external_service_call():
    with error_context("external_service_call"):
        return await external_service_call()

try:
    result = await safe_external_service_call()
    return {"success": True, "data": result}
except Exception as e:
    return create_error_response(e, ResponseFormat.MCP)
```

## Conclusion

The Marcus Error Framework represents a paradigm shift from reactive error handling to proactive error intelligence. By treating errors as valuable system intelligence rather than mere exceptions, the framework enables autonomous agents to operate more reliably, recover more intelligently, and provide better visibility into system health.

The framework's multi-tiered approach—from simple retry logic to sophisticated pattern detection—allows it to scale from basic error recovery to advanced system intelligence. Its integration with the broader Marcus ecosystem ensures that error handling is not an afterthought but a core system capability that enhances every aspect of autonomous agent operation.

As Marcus continues to evolve toward more sophisticated autonomous operation, the Error Framework provides the foundation for self-healing, self-monitoring, and self-optimizing agent systems that can operate reliably in complex, distributed environments with minimal human intervention.
