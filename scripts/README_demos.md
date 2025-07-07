# Marcus Enhanced Features Demonstration Scripts

This directory contains demonstration scripts for the enhanced Marcus features including the Visibility System, Context System, Memory System, and Dependency Awareness.

## Available Demonstrations

### 1. Visibility System Demo
```bash
python scripts/demo_visibility_system.py
```

Shows how the visibility system provides real-time insights through event integration:
- Real-time event monitoring and statistics
- Agent activity tracking
- Feature usage analytics
- Event filtering and pattern detection
- Integration with Context and Memory systems

### 2. Context System Demo
```bash
python scripts/demo_context_system.py
```

Demonstrates intelligent dependency management and knowledge sharing:
- Automatic dependency inference from task names/labels
- Circular dependency detection and resolution
- Optimal task ordering with parallelization opportunities
- Architectural decision tracking
- Implementation sharing between agents

### 3. Memory System Demo
```bash
python scripts/demo_memory_system.py
```

Shows how the memory system learns and predicts:
- Agent performance predictions with confidence intervals
- Continuous learning from task outcomes
- Risk analysis and complexity factors
- Pattern detection in failures and successes
- Time-based relevance weighting

### 4. Dependency Awareness Demo
```bash
python scripts/demo_dependency_awareness.py
```

Illustrates how Marcus prevents illogical task assignments:
- Problems with priority-only task ordering
- Pattern-based dependency inference
- Hybrid inference with AI enhancement
- Real-world workflow support

### 5. Hybrid Dependency Inference Demo
```bash
python scripts/demo_hybrid_inference.py
```

Technical demonstration of the hybrid inference system:
- Pattern-only vs AI-only vs Hybrid comparison
- Configurable confidence thresholds
- Caching effectiveness
- API call reduction metrics

### 6. Inference Method Comparison
```bash
python scripts/compare_inference_methods.py
```

Comprehensive comparison of different inference approaches:
- Performance benchmarks
- Cost analysis
- Accuracy estimates
- Recommendations for different scenarios

## Running All Demos

To run all demonstrations in sequence:

```bash
# Run each demo individually to see detailed output
python scripts/demo_visibility_system.py
python scripts/demo_context_system.py
python scripts/demo_memory_system.py
python scripts/demo_dependency_awareness.py
```

## Key Benefits Demonstrated

### Visibility System
- **Real-time Monitoring**: Track all system events as they happen
- **Historical Analysis**: Query and analyze past events
- **Pattern Detection**: Identify trends and anomalies
- **Integration Hub**: Unified view across all Marcus systems

### Context System
- **Smart Dependencies**: Automatically infers task relationships
- **Knowledge Sharing**: Propagates implementations and decisions
- **Cycle Prevention**: Detects and resolves circular dependencies
- **Optimal Ordering**: Determines best task execution sequence

### Memory System
- **Intelligent Predictions**: Success probability and duration estimates
- **Continuous Learning**: Improves predictions over time
- **Risk Analysis**: Identifies potential blockers and issues
- **Agent Specialization**: Discovers agent strengths and weaknesses

### Dependency Awareness
- **Logical Ordering**: Prevents "deploy before build" scenarios
- **Efficiency**: Identifies parallelization opportunities
- **Quality**: Ensures proper development sequence
- **Flexibility**: Adapts to different development workflows

## Configuration

The demonstrations use in-memory storage by default. To use persistent storage or modify behavior, update the configuration in `config_marcus.json`:

```json
{
  "features": {
    "events": {
      "enabled": true,
      "store_history": true,
      "async_handlers": true
    },
    "context": {
      "enabled": true,
      "infer_dependencies": true
    },
    "memory": {
      "enabled": true,
      "use_v2_predictions": true
    }
  },
  "hybrid_inference": {
    "pattern_confidence_threshold": 0.8,
    "enable_ai_inference": true
  }
}
```

## Notes

- These demos use simulated data to illustrate features
- Some demos include mock AI responses for illustration
- All features are designed to work with real Marcus deployments
- Performance metrics in demos are representative but may vary in production