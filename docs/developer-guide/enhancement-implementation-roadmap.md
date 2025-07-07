# Enhancement Implementation Roadmap

## 🎯 Goal: Implement all improvements without disrupting current operations

### Week 1: Performance & Reliability (8 hours)

#### Day 1-2: Event System Performance
```python
# File: src/core/events.py
# Add fire-and-forget capability

async def publish(self, event_type: str, source: str, data: Dict[str, Any], 
                  metadata: Optional[Dict[str, Any]] = None,
                  wait_for_handlers: bool = True) -> Event:
    """
    Enhanced publish with optional async handling
    
    Args:
        wait_for_handlers: If False, handlers run in background (new)
    """
    # ... existing code ...
    
    if handlers:
        tasks = [self._create_handler_task(h, event) for h in handlers]
        
        if wait_for_handlers:
            await asyncio.gather(*tasks)
        else:
            # New: Fire and forget for performance
            for task in tasks:
                asyncio.create_task(task)
```

**Testing Plan:**
1. Add unit tests for both modes
2. Benchmark with 100 handlers
3. Verify no event loss

#### Day 3-4: Graceful Degradation
```python
# File: src/core/resilience.py (new)

from functools import wraps
import logging

logger = logging.getLogger(__name__)

def with_fallback(fallback_func):
    """Decorator for graceful degradation"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"{func.__name__} failed: {e}, using fallback")
                return await fallback_func(*args, **kwargs)
        return wrapper
    return decorator

# Apply to persistence operations
class Events:
    @with_fallback(self._store_in_memory)
    async def _persist_event(self, event):
        await self.persistence.store_event(event)
```

### Week 2: Intelligence Enhancements (12 hours)

#### Day 5-6: Memory Predictions
```python
# File: src/core/memory_enhanced.py (new)

class MemoryEnhanced(Memory):
    """Enhanced memory with better predictions"""
    
    async def predict_task_outcome_v2(self, agent_id: str, task: Task) -> Dict[str, Any]:
        """Enhanced predictions with confidence and complexity"""
        # Get base predictions
        base = await self.predict_task_outcome(agent_id, task)
        
        # Calculate confidence based on data
        agent_history = self._get_agent_history(agent_id)
        sample_size = len(agent_history)
        confidence = min(0.95, sample_size / 20.0)
        
        # Adjust for complexity
        avg_task_hours = sum(t.estimated_hours for t in agent_history) / len(agent_history) if agent_history else 10
        complexity_factor = min(2.0, task.estimated_hours / avg_task_hours)
        
        # Time decay for relevance
        recent_weight = self._calculate_recency_weight(agent_history)
        
        # Enhanced predictions
        return {
            **base,  # Keep all original fields
            "confidence": confidence,
            "complexity_factor": complexity_factor,
            "sample_size": sample_size,
            "success_probability_adjusted": base["success_probability"] * (1/complexity_factor) * recent_weight,
            "confidence_interval": {
                "lower": max(0, base["success_probability"] - (1-confidence)*0.3),
                "upper": min(1, base["success_probability"] + (1-confidence)*0.3)
            }
        }
```

#### Day 7-8: Context Intelligence
```python
# File: src/core/context_enhanced.py (new)

class ContextEnhanced(Context):
    """Enhanced context with dependency inference"""
    
    def analyze_dependencies_smart(self, tasks: List[Task], 
                                  infer_implicit: bool = True) -> Dict[str, List[str]]:
        """Analyze with optional implicit dependency detection"""
        # Start with explicit
        deps = self.analyze_dependencies(tasks)
        
        if infer_implicit:
            # Infer based on naming patterns
            for task in tasks:
                for other in tasks:
                    if task.id != other.id and self._likely_depends_on(task, other):
                        if task.id not in deps:
                            deps[task.id] = []
                        if other.id not in deps[task.id]:
                            deps[task.id].append(other.id)
                            
        return deps
    
    def _likely_depends_on(self, task: Task, other: Task) -> bool:
        """Detect implicit dependencies using NLP-lite approach"""
        # Simple heuristics for now
        task_words = set(task.name.lower().split())
        other_words = set(other.name.lower().split())
        
        # Common patterns
        patterns = [
            ("create", "update"),
            ("create", "test"),
            ("build", "deploy"),
            ("design", "implement"),
            ("api", "frontend"),
            ("database", "api")
        ]
        
        for first, second in patterns:
            if first in other_words and second in task_words:
                return True
                
        # Shared technical terms
        technical_overlap = task_words & other_words & {
            "user", "auth", "api", "database", "model", "schema"
        }
        return len(technical_overlap) >= 2
```

### Week 3: Configuration & Integration (8 hours)

#### Day 9-10: Granular Configuration
```python
# File: src/config/config_schema.py (new)

ENHANCED_CONFIG_SCHEMA = {
    "features": {
        "events": {
            "type": ["boolean", "object"],
            "properties": {
                "enabled": {"type": "boolean"},
                "store_history": {"type": "boolean", "default": True},
                "history_limit": {"type": "integer", "default": 1000},
                "async_handlers": {"type": "boolean", "default": False}
            }
        },
        "context": {
            "type": ["boolean", "object"],
            "properties": {
                "enabled": {"type": "boolean"},
                "infer_dependencies": {"type": "boolean", "default": False},
                "max_depth": {"type": "integer", "default": 3}
            }
        },
        "memory": {
            "type": ["boolean", "object"],
            "properties": {
                "enabled": {"type": "boolean"},
                "learning_rate": {"type": "number", "default": 0.1},
                "min_samples": {"type": "integer", "default": 5},
                "use_v2_predictions": {"type": "boolean", "default": False}
            }
        }
    }
}

# Update config loader
def get_feature_config(self, feature: str) -> Dict[str, Any]:
    """Get feature config with backward compatibility"""
    config = self.get(f'features.{feature}')
    
    if isinstance(config, bool):
        # Old format - convert
        return {"enabled": config}
    elif isinstance(config, dict):
        # New format - use as is
        return config
    else:
        # Not configured
        return {"enabled": False}
```

#### Day 11-12: Visibility Integration
```python
# File: src/visualization/enhanced_integration.py (new)

class EnhancedVisualizationIntegration:
    """Connect visibility to Events/Context/Memory"""
    
    def __init__(self, marcus_server):
        self.server = marcus_server
        self.setup_event_subscriptions()
        
    def setup_event_subscriptions(self):
        """Subscribe to events for real-time updates"""
        if self.server.events:
            # Real-time task updates
            self.server.events.subscribe(EventTypes.TASK_ASSIGNED, 
                                       self.on_task_assigned)
            self.server.events.subscribe(EventTypes.TASK_COMPLETED,
                                       self.on_task_completed)
            # Context updates
            self.server.events.subscribe(EventTypes.CONTEXT_UPDATED,
                                       self.on_context_updated)
                                       
    async def get_enhanced_task_view(self, task_id: str) -> Dict[str, Any]:
        """Get task with context and predictions"""
        task = await self.server.kanban_client.get_task_by_id(task_id)
        
        response = {"task": task}
        
        # Add context if available
        if self.server.context:
            context = await self.server.context.get_context(task_id, task.dependencies)
            response["context"] = context.to_dict()
            
        # Add predictions if available
        if self.server.memory and task.assigned_to:
            predictions = await self.server.memory.predict_task_outcome(
                task.assigned_to, task
            )
            response["predictions"] = predictions
            
        return response
```

### Week 4: Testing & Documentation (12 hours)

#### Day 13-14: Comprehensive Testing
```python
# File: tests/test_enhanced_features.py

@pytest.mark.asyncio
async def test_performance_improvements():
    """Test that enhancements don't degrade performance"""
    # Test event performance
    events = Events(store_history=True)
    
    # Measure sync mode
    start = time.time()
    for i in range(100):
        await events.publish("test", "source", {}, wait_for_handlers=True)
    sync_time = time.time() - start
    
    # Measure async mode  
    start = time.time()
    for i in range(100):
        await events.publish("test", "source", {}, wait_for_handlers=False)
    async_time = time.time() - start
    
    assert async_time < sync_time * 0.5  # At least 50% faster

@pytest.mark.asyncio
async def test_backward_compatibility():
    """Ensure old configs still work"""
    old_config = {"features": {"events": True}}
    new_config = {"features": {"events": {"enabled": True, "async_handlers": True}}}
    
    # Both should work
    assert get_feature_config("events", old_config)["enabled"] == True
    assert get_feature_config("events", new_config)["enabled"] == True
```

#### Day 15-16: Documentation & Rollout Plan
- Update all API documentation
- Create migration guide
- Write performance tuning guide
- Create feature flag rollout plan

## Rollout Strategy

### Phase 1: Internal Testing (Week 1-2)
- Deploy to staging environment
- Run parallel with existing system
- Collect performance metrics

### Phase 2: Beta Users (Week 3-4)
- Enable for 10% of projects
- Monitor for issues
- Gather feedback

### Phase 3: General Availability (Week 5+)
- Enable by default for new projects
- Provide migration tools for existing projects
- Deprecation notices for old methods (in 6 months)

## Success Metrics

1. **Performance**
   - Event handling: 50% faster with async mode
   - No increase in memory usage
   - <10ms overhead for predictions

2. **Accuracy**
   - Prediction confidence correlation: >0.8
   - Dependency inference accuracy: >70%
   - No false positive blockers

3. **Adoption**
   - 80% of projects using enhanced features within 3 months
   - <5 bug reports per enhancement
   - Positive feedback from 90% of users

## Risk Mitigation

1. **Feature Flags**: Every enhancement behind a flag
2. **Monitoring**: Real-time metrics for each feature
3. **Rollback Plan**: One-command disable for any feature
4. **Gradual Rollout**: Start with read-only enhancements

---

**Total Implementation Time: 40 hours (5 days)**
**Total Testing Time: 16 hours (2 days)**
**Total Documentation: 8 hours (1 day)**

**Complete rollout: 4 weeks from start**