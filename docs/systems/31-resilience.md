# Resilience System

## Overview

The Resilience System is Marcus's foundational reliability layer that ensures the platform continues operating gracefully even when individual components fail. It implements three core resilience patterns: graceful degradation with fallbacks, retry logic with exponential backoff, and circuit breakers for external service protection. This system is critical to Marcus's reliability promise - that agent workflows continue even when enhanced features or external dependencies become unavailable.

## Architecture

The resilience system is implemented as a decorator-based framework in `src/core/resilience.py` that provides:

### Core Components

1. **Retry Mechanism (`with_retry`)**
   - Configurable exponential backoff with jitter
   - Maximum attempt limits and delay caps
   - Support for both sync and async functions
   - Intelligent delay calculation with random jitter to prevent thundering herd

2. **Circuit Breaker (`with_circuit_breaker`)**
   - Three-state pattern: closed, open, half-open
   - Failure threshold tracking
   - Automatic recovery timeout with half-open testing
   - Global circuit breaker registry for consistent state

3. **Fallback System (`with_fallback`)**
   - Graceful degradation to alternative implementations
   - Automatic function signature detection (sync/async)
   - Configurable error logging
   - Seamless integration with existing code

4. **Graceful Degradation Context Manager**
   - Programmatic control over primary/fallback execution
   - Error state tracking
   - Flexible function composition

### Configuration Classes

```python
@dataclass
class RetryConfig:
    max_attempts: int = 3          # Total retry attempts
    base_delay: float = 1.0        # Initial delay in seconds
    max_delay: float = 60.0        # Maximum delay cap
    exponential_base: float = 2.0  # Backoff multiplier
    jitter: bool = True            # Add randomization

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5              # Failures before opening
    recovery_timeout: float = 60.0         # Seconds before half-open
    expected_exception: type = Exception    # Exception type to track
```

## Integration with Marcus Ecosystem

### Core System Integration

The resilience system is deeply integrated into Marcus's core systems:

1. **Context System (`src/core/context.py`)**
   - Uses `@with_fallback` for persistence operations
   - Ensures context data is never lost even if storage fails
   - Falls back to logging warnings when persistence unavailable

2. **Memory System (`src/core/memory_advanced.py`)**
   - Protects ML prediction services with fallbacks
   - Returns error objects when prediction services fail
   - Maintains agent profiles even with storage issues

3. **Event System (`src/core/events.py`)**
   - Uses `resilient_persistence` for event storage
   - Logs warnings when events cannot be persisted
   - Ensures event processing continues without storage

4. **Dependency Inference (`src/intelligence/dependency_inferer_hybrid.py`)**
   - Applies retry logic to AI service calls
   - Falls back to heuristic methods when AI unavailable
   - Maintains dependency detection even with service failures

### Pre-configured Decorators

The system provides common-use decorators:

```python
# For data persistence operations
resilient_persistence = with_fallback(
    lambda *args, **kwargs: logger.warning("Persistence unavailable, data not saved"),
    log_errors=True
)

# For external API calls
resilient_external_call = with_retry(RetryConfig(max_attempts=3, base_delay=1.0))

# For AI provider interactions
resilient_ai_call = with_circuit_breaker(
    "ai_provider",
    CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30.0)
)
```

## Workflow Integration

### Marcus Agent Workflow Position

In the typical Marcus scenario flow:

1. **create_project** → Resilience protects project metadata persistence
2. **register_agent** → Resilience ensures agent registration survives storage failures
3. **request_next_task** → Circuit breakers protect AI-enhanced task selection
4. **report_progress** → Fallbacks ensure progress is tracked even with storage issues
5. **report_blocker** → Retry logic ensures blocker reports reach the system
6. **finish_task** → Resilience guarantees task completion is recorded

The resilience system operates at the infrastructure level, transparently protecting all these operations without requiring explicit handling by agents or users.

### Invocation Points

The resilience system is invoked automatically through decorators at these critical points:

- **Context Persistence**: When saving implementation details or decisions
- **Memory Operations**: During agent profile updates and ML predictions
- **Event Processing**: For all event storage and retrieval
- **AI Service Calls**: When requesting dependency analysis or task insights
- **External Integrations**: For Kanban provider interactions

## What Makes This System Special

### 1. Zero-Disruption Integration
Unlike traditional resilience frameworks that require explicit error handling, Marcus's resilience system operates transparently through decorators. Existing code gains resilience without modification.

### 2. Intelligent Failure Detection
The circuit breaker system tracks specific exception types and provides half-open testing to verify service recovery. This prevents cascading failures while enabling rapid recovery.

### 3. Adaptive Retry Logic
The exponential backoff with jitter prevents thundering herd problems while adapting to varying service response times. The system learns from failure patterns.

### 4. Graceful Degradation Philosophy
Instead of failing hard, the system maintains core functionality by falling back to simpler implementations. This ensures Marcus remains usable even when advanced features fail.

### 5. Observability Integration
All resilience events are logged with appropriate severity levels, providing operational visibility into system health and failure patterns.

## Technical Implementation Details

### State Management

Circuit breakers maintain state in a global registry:

```python
_circuit_breakers: Dict[str, CircuitBreaker] = {}
```

Each circuit breaker tracks:
- `failure_count`: Number of consecutive failures
- `last_failure_time`: Timestamp of most recent failure
- `state`: Current state (closed/open/half-open)

### Async/Sync Function Detection

The system automatically detects function types using `asyncio.iscoroutinefunction()` and provides appropriate wrappers, ensuring seamless integration with Marcus's mixed sync/async architecture.

### Jitter Implementation

Random jitter is applied using:

```python
if config.jitter:
    delay *= (0.5 + random.random())  # 50%-150% of calculated delay
```

This prevents synchronized retry storms when multiple components fail simultaneously.

### Error Propagation

The system carefully preserves original exception types and messages while adding resilience behavior. This ensures debugging remains effective even with resilience layers active.

## Simple vs Complex Task Handling

### Simple Tasks
For straightforward operations, resilience provides:
- Basic retry for transient failures
- Fallback to logging when persistence fails
- Minimal overhead with fast-path execution

### Complex Tasks
For sophisticated operations involving AI or multiple services:
- Circuit breakers prevent cascade failures
- Multi-layer fallbacks (AI → heuristic → basic)
- Extended retry windows for expensive operations
- Context preservation across failure boundaries

## Board-Specific Considerations

### Provider Abstraction
The resilience system works transparently across different Kanban providers:
- Trello: Protects against API rate limits
- Linear: Handles authentication token refresh
- File-based: Ensures filesystem operations complete
- Memory: Provides consistent interface even without persistence

### State Synchronization
Circuit breaker state is maintained globally, ensuring consistent behavior across multiple board operations within the same Marcus instance.

## Integration with Seneca

While Seneca (the AI coach) is not directly integrated with the resilience system, it benefits from resilience protections:

- **AI Provider Circuit Breakers**: Protect Seneca's LLM calls
- **Fallback Coaching**: When AI unavailable, falls back to rule-based suggestions
- **Persistent Learning**: Coaching history survives storage failures through resilient persistence

## Pros and Cons

### Advantages

1. **Transparent Integration**: No code changes required for resilience
2. **Comprehensive Coverage**: Protects all critical system components
3. **Intelligent Behavior**: Learns from failure patterns and adapts
4. **Operational Visibility**: Provides clear logging of resilience events
5. **Performance Conscious**: Minimal overhead during normal operation
6. **Flexible Configuration**: Easily tunable for different use cases

### Disadvantages

1. **Hidden Complexity**: Resilience behavior may mask underlying issues
2. **State Management**: Circuit breaker state is process-local only
3. **Configuration Complexity**: Many tunable parameters require expertise
4. **Debugging Challenges**: Additional abstraction layer complicates debugging
5. **Memory Usage**: Global circuit breaker registry grows over time
6. **Limited Metrics**: No built-in metrics collection for resilience events

## Why This Approach Was Chosen

### Design Philosophy
Marcus prioritizes **availability over consistency** for enhanced features. The core agent workflow must never fail due to auxiliary system problems. This resilience-first approach ensures:

1. **Agent Productivity**: Agents continue working even with service degradation
2. **User Experience**: Marcus remains responsive under all conditions
3. **Operational Simplicity**: Self-healing reduces manual intervention needs
4. **Development Velocity**: Teams can deploy improvements without fear of breaking core workflows

### Alternative Approaches Considered

1. **Circuit Breaker Libraries**: Rejected due to heavyweight dependencies
2. **Service Mesh Resilience**: Too complex for single-process deployment
3. **Manual Error Handling**: Too error-prone and inconsistent
4. **Database-backed State**: Adds dependency where resilience should remove them

### Implementation Trade-offs

The decorator approach was chosen because:
- **Minimal Cognitive Load**: Developers don't need to think about resilience
- **Consistent Application**: No missed resilience opportunities
- **Easy Testing**: Decorators can be disabled for unit tests
- **Clear Separation**: Resilience logic separated from business logic

## Future Evolution

### Planned Enhancements

1. **Distributed Circuit Breakers**: Share state across Marcus instances
2. **Adaptive Configuration**: ML-driven parameter tuning based on failure patterns
3. **Metrics Collection**: Integration with monitoring systems
4. **Health Endpoints**: Expose circuit breaker states for observability
5. **Bulk Operations**: Optimized resilience for batch processing
6. **Resource-Aware Fallbacks**: Consider system load when choosing fallback strategies

### Scaling Considerations

As Marcus evolves to support larger deployments:

1. **Circuit Breaker Persistence**: Store state in external cache (Redis)
2. **Rate Limiting Integration**: Coordinate with rate limiting systems
3. **Regional Fallbacks**: Geographic distribution of fallback services
4. **Priority-Based Resilience**: Different resilience levels for different operation types

### Integration Opportunities

1. **Chaos Engineering**: Built-in failure injection for testing
2. **A/B Testing**: Resilience strategy comparison
3. **Dependency Mapping**: Automatic service dependency discovery
4. **Predictive Failure**: ML-based failure prediction and preemptive circuit breaking

## Monitoring and Observability

### Current Logging

The system provides structured logging at key points:
- Circuit breaker state changes (WARNING level)
- Retry attempts with timing (DEBUG level)
- Fallback activations (WARNING level)
- Final failure events (ERROR level)

### Recommended Monitoring

For production deployments, monitor:
- Circuit breaker state distribution across services
- Retry success rates and timing patterns
- Fallback activation frequency
- Overall system resilience health score

### Alerting Thresholds

Consider alerting on:
- Circuit breakers remaining open for > 5 minutes
- Fallback activation rate > 10% for any service
- Retry exhaustion rate > 5% for critical operations
- Multiple circuit breakers opening simultaneously

## Conclusion

The Resilience System represents Marcus's commitment to reliability-first design. By providing transparent, comprehensive resilience patterns, it ensures that enhanced features never compromise core functionality. This foundation enables Marcus to deliver consistent value to users while supporting continuous innovation and feature development.

The system's decorator-based approach makes resilience a natural part of development rather than an afterthought, establishing patterns that scale with the platform's growth. As Marcus evolves, the resilience system will continue adapting to new challenges while maintaining its core promise: keeping agents productive regardless of infrastructure conditions.
