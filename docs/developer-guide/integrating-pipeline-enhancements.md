# Integrating Pipeline Enhancement Features

This guide helps developers integrate Marcus's pipeline enhancement features into their applications and workflows.

## Architecture Overview

The pipeline enhancement system consists of several modular components:

```
┌─────────────────────────────────────────────────────┐
│                  Frontend (Vue.js)                   │
├─────────────────────────────────────────────────────┤
│              REST API / WebSocket Layer              │
├─────────────────────────────────────────────────────┤
│                   MCP Tools Layer                    │
├─────────────────────────────────────────────────────┤
│              Core Enhancement Modules                │
├──────────┬──────────┬──────────┬──────────┬────────┤
│  Replay  │ What-If  │ Compare  │ Monitor  │  Recs  │
├──────────┴──────────┴──────────┴──────────┴────────┤
│            Shared Pipeline Events Store              │
└─────────────────────────────────────────────────────┘
```

## Component Integration

### 1. Pipeline Replay Integration

The replay component allows stepping through pipeline execution events.

```python
from src.visualization.pipeline_replay import PipelineReplayController

# Initialize replay for a flow
replay = PipelineReplayController(flow_id="project-123")

# Get current state
state = replay.get_current_state()
print(f"Position: {state['position']}/{state['total_events']}")
print(f"Current stage: {state['current_event']['stage']}")

# Navigate through events
success, new_state = replay.step_forward()
if success:
    print(f"Advanced to: {new_state['current_event']['event_type']}")

# Jump to specific position
success, state = replay.jump_to_position(5)

# Access accumulated state at any point
accumulated = state['accumulated_state']
print(f"Stages completed: {accumulated['stages_completed']}")
```

### 2. What-If Analysis Integration

Simulate pipeline modifications before implementation.

```python
from src.analysis.what_if_engine import (
    WhatIfAnalysisEngine, 
    PipelineModification,
    ModificationType
)

# Initialize analysis engine
engine = WhatIfAnalysisEngine(flow_id="project-123")

# Get modifiable parameters
params = engine.get_modifiable_parameters()
print(f"Can modify: {list(params.keys())}")

# Create modifications
mods = [
    PipelineModification(
        parameter_type=ModificationType.REQUIREMENT,
        parameter_name="scalability",
        old_value=None,
        new_value="Support 10k concurrent users",
        description="Add scalability requirement"
    ),
    PipelineModification(
        parameter_type=ModificationType.PARAMETER,
        parameter_name="team_size",
        old_value=3,
        new_value=5,
        description="Increase team size"
    )
]

# Run simulation
result = await engine.simulate_variation(mods)

# Analyze impact
print(f"Task count: {result['original_metrics']['task_count']} → "
      f"{result['predicted_metrics']['task_count']}")
print(f"Cost: ${result['original_metrics']['cost']:.2f} → "
      f"${result['predicted_metrics']['cost']:.2f}")

# Compare all variations
comparison = engine.compare_all_variations()
best_cost = comparison['best_by_metric']['cost']
print(f"Most cost-effective: {best_cost['variation_id']}")
```

### 3. Pipeline Comparison Integration

Compare multiple pipeline executions to identify patterns.

```python
from src.analysis.pipeline_comparison import PipelineComparator

comparator = PipelineComparator()

# Compare multiple flows
flow_ids = ["api-v1", "api-v2", "api-v3"]
report = comparator.compare_multiple_flows(flow_ids)

# Access comparison data
for summary in report.flow_summaries:
    print(f"{summary['project_name']}: "
          f"${summary['cost']:.2f}, "
          f"{summary['task_count']} tasks, "
          f"{summary['quality_score']*100:.0f}% quality")

# Find common patterns
common_decisions = report.common_patterns['common_decisions']
for decision in common_decisions:
    print(f"Common: {decision['decision']} "
          f"(in {decision['frequency']} flows)")

# Export report
html_report = comparator.export_comparison_report(report, format="html")
with open("comparison.html", "w") as f:
    f.write(html_report)
```

### 4. Live Monitoring Integration

Monitor active pipeline executions in real-time.

```python
from src.monitoring.live_pipeline_monitor import LivePipelineMonitor

monitor = LivePipelineMonitor()

# Start monitoring
await monitor.start_monitoring()

# Get dashboard data
dashboard = monitor.get_dashboard_data()
print(f"Active flows: {dashboard['active_flows']}")
print(f"System health: {dashboard['health_summary']}")

# Track specific flow
progress = await monitor.track_flow_progress("active-flow-123")
print(f"Progress: {progress.progress_percentage:.1f}%")
print(f"ETA: {progress.eta}")
print(f"Health: {progress.health_status.status}")

# Subscribe to updates (with callback)
def on_flow_update(update):
    print(f"Flow {update.flow_id}: {update.progress_percentage:.1f}%")

monitor.subscribe_to_flow("active-flow-123", on_flow_update)
```

### 5. Error Prediction Integration

Predict and prevent pipeline failures.

```python
from src.monitoring.error_predictor import PipelineErrorPredictor

predictor = PipelineErrorPredictor()

# Predict failure risk
assessment = predictor.predict_failure_risk("active-flow-123")

print(f"Overall risk: {assessment.overall_risk*100:.0f}% "
      f"({assessment.risk_category})")

# Handle risk factors
for factor in assessment.factors:
    if factor.risk_level > 0.7:
        print(f"HIGH RISK: {factor.description}")
        print(f"Mitigation: {factor.mitigation}")

# Learn from outcomes
from src.recommendations.recommendation_engine import ProjectOutcome

outcome = ProjectOutcome(
    successful=True,
    completion_time_days=5.2,
    quality_score=0.85,
    cost=12.50
)
predictor.learn_from_outcome("completed-flow-123", "success")
```

### 6. Recommendation Engine Integration

Get intelligent recommendations based on historical data.

```python
from src.recommendations.recommendation_engine import (
    PipelineRecommendationEngine
)

engine = PipelineRecommendationEngine()

# Get recommendations
recommendations = engine.get_recommendations("project-123")

for rec in recommendations[:5]:  # Top 5
    print(f"\n{rec.type.upper()} ({rec.confidence*100:.0f}% confident)")
    print(f"→ {rec.message}")
    print(f"Impact: {rec.impact}")
    
    # Execute recommendation action if available
    if rec.action:
        result = rec.action()
        print(f"Applied: {result}")

# Find similar flows
similar = engine.find_similar_flows(engine._load_flow_data("project-123"))
for flow in similar:
    print(f"{flow['flow']['project_name']}: "
          f"{flow['similarity']*100:.0f}% similar")

# Learn from project outcome
outcome = ProjectOutcome(
    successful=True,
    completion_time_days=10,
    quality_score=0.9,
    cost=25.0
)
engine.learn_from_outcome("project-123", outcome)
```

## API Integration

### REST API Client Example

```python
import aiohttp
import asyncio

class PipelineEnhancementClient:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        await self.session.close()
    
    async def start_replay(self, flow_id):
        async with self.session.post(
            f"{self.base_url}/api/pipeline/replay/start",
            json={"flow_id": flow_id}
        ) as resp:
            return await resp.json()
    
    async def get_recommendations(self, flow_id):
        async with self.session.get(
            f"{self.base_url}/api/pipeline/recommendations/{flow_id}"
        ) as resp:
            return await resp.json()
    
    async def compare_flows(self, flow_ids):
        async with self.session.post(
            f"{self.base_url}/api/pipeline/compare",
            json={"flow_ids": flow_ids}
        ) as resp:
            return await resp.json()

# Usage
async def main():
    async with PipelineEnhancementClient() as client:
        # Get recommendations
        recs = await client.get_recommendations("project-123")
        for rec in recs['recommendations']:
            print(f"• {rec['message']}")
        
        # Compare flows
        comparison = await client.compare_flows(["flow1", "flow2"])
        print(comparison['report']['recommendations'])

asyncio.run(main())
```

### WebSocket Client Example

```python
import socketio
import asyncio

class LiveMonitorClient:
    def __init__(self, url="http://localhost:5000"):
        self.sio = socketio.AsyncClient()
        self.url = url
        
        # Register event handlers
        self.sio.on('connect', self.on_connect)
        self.sio.on('dashboard_update', self.on_dashboard_update)
        self.sio.on('flow_update', self.on_flow_update)
    
    async def connect(self):
        await self.sio.connect(self.url)
    
    async def subscribe_to_flow(self, flow_id):
        await self.sio.emit('subscribe_flow', {'flow_id': flow_id})
    
    async def on_connect(self):
        print("Connected to live monitor")
    
    async def on_dashboard_update(self, data):
        print(f"Active flows: {len(data['active_flows'])}")
        print(f"System metrics: {data['system_metrics']}")
    
    async def on_flow_update(self, data):
        print(f"Flow {data['flow_id']}: {data['progress_percentage']:.1f}%")
        if data['health_status']['status'] != 'healthy':
            print(f"⚠️  Issues: {data['health_status']['issues']}")

# Usage
async def monitor_flows():
    client = LiveMonitorClient()
    await client.connect()
    
    # Subscribe to specific flow
    await client.subscribe_to_flow("active-project-123")
    
    # Keep listening
    await asyncio.sleep(3600)  # Monitor for 1 hour

asyncio.run(monitor_flows())
```

## MCP Tool Integration

### Creating Custom MCP Tools

```python
from src.mcp.tools.pipeline_enhancement_tools import pipeline_tools
import mcp.types as types

async def my_custom_analysis_tool(arguments):
    """Custom tool that combines multiple enhancements."""
    flow_id = arguments.get("flow_id")
    
    # Get recommendations
    recs = await pipeline_tools.get_recommendations(flow_id)
    
    # Predict risk
    risk = await pipeline_tools.predict_failure_risk(flow_id)
    
    # Find similar successful flows
    similar = await pipeline_tools.find_similar_flows(flow_id, limit=3)
    
    # Combine insights
    return {
        "flow_id": flow_id,
        "top_recommendation": recs['recommendations'][0] if recs['recommendations'] else None,
        "risk_level": risk['risk_assessment']['risk_category'],
        "similar_successes": [
            f['project_name'] for f in similar['similar_flows']
        ],
        "suggested_action": _determine_action(recs, risk)
    }

def _determine_action(recs, risk):
    if risk['risk_assessment']['overall_risk'] > 0.7:
        return "Pause and address risks before continuing"
    elif recs['recommendations'] and recs['recommendations'][0]['confidence'] > 0.8:
        return f"Apply: {recs['recommendations'][0]['message']}"
    else:
        return "Continue with standard process"

# Register the tool
tool_definition = types.Tool(
    name="analyze_project_health",
    description="Comprehensive project health analysis",
    inputSchema={
        "type": "object",
        "properties": {
            "flow_id": {"type": "string", "description": "Flow to analyze"}
        },
        "required": ["flow_id"]
    }
)
```

## Frontend Integration

### Vue.js Component Example

```javascript
// PipelineReplay.vue
<template>
  <div class="pipeline-replay">
    <div class="replay-controls">
      <button @click="stepBackward" :disabled="!canGoBack">
        Previous
      </button>
      <button @click="togglePlay">
        {{ isPlaying ? 'Pause' : 'Play' }}
      </button>
      <button @click="stepForward" :disabled="!canGoForward">
        Next
      </button>
    </div>
    
    <div class="timeline">
      <input type="range" 
             v-model="position" 
             :max="maxPosition"
             @input="jumpToPosition">
      <span>{{ position + 1 }} / {{ maxPosition + 1 }}</span>
    </div>
    
    <div class="event-display">
      <h3>{{ currentEvent?.event_type }}</h3>
      <pre>{{ JSON.stringify(currentEvent?.data, null, 2) }}</pre>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      flowId: null,
      position: 0,
      maxPosition: 0,
      currentEvent: null,
      isPlaying: false,
      playInterval: null
    }
  },
  
  computed: {
    canGoBack() {
      return this.position > 0
    },
    canGoForward() {
      return this.position < this.maxPosition
    }
  },
  
  methods: {
    async startReplay(flowId) {
      const response = await fetch('/api/pipeline/replay/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ flow_id: flowId })
      })
      
      const data = await response.json()
      if (data.success) {
        this.flowId = flowId
        this.maxPosition = data.total_events - 1
        this.position = data.current_position
        this.currentEvent = data.state.current_event
      }
    },
    
    async stepForward() {
      const response = await fetch('/api/pipeline/replay/forward', {
        method: 'POST'
      })
      
      const data = await response.json()
      if (data.success) {
        this.position++
        this.currentEvent = data.state.current_event
      }
    },
    
    async stepBackward() {
      const response = await fetch('/api/pipeline/replay/backward', {
        method: 'POST'
      })
      
      const data = await response.json()
      if (data.success) {
        this.position--
        this.currentEvent = data.state.current_event
      }
    },
    
    togglePlay() {
      if (this.isPlaying) {
        clearInterval(this.playInterval)
        this.isPlaying = false
      } else {
        this.isPlaying = true
        this.playInterval = setInterval(() => {
          if (this.canGoForward) {
            this.stepForward()
          } else {
            this.togglePlay()
          }
        }, 1000)
      }
    }
  }
}
</script>
```

## Testing Integration

### Unit Test Example

```python
import pytest
from unittest.mock import Mock, patch
from src.visualization.pipeline_replay import PipelineReplayController

class TestPipelineReplayIntegration:
    @pytest.fixture
    def sample_events(self):
        return [
            {"event_id": "1", "event_type": "start", "timestamp": "2024-01-01T10:00:00"},
            {"event_id": "2", "event_type": "analysis", "timestamp": "2024-01-01T10:01:00"},
            {"event_id": "3", "event_type": "complete", "timestamp": "2024-01-01T10:02:00"}
        ]
    
    @patch('src.visualization.shared_pipeline_events.SharedPipelineEvents')
    def test_replay_navigation(self, mock_events_class, sample_events):
        mock_events = Mock()
        mock_events.get_flow_events.return_value = sample_events
        mock_events_class.return_value = mock_events
        
        replay = PipelineReplayController("test-flow")
        
        # Test forward navigation
        success, state = replay.step_forward()
        assert success
        assert state['current_event']['event_id'] == "2"
        
        # Test backward navigation
        success, state = replay.step_backward()
        assert success
        assert state['current_event']['event_id'] == "1"
```

## Performance Considerations

### Caching Strategy

```python
from functools import lru_cache
import hashlib

class CachedPipelineAnalyzer:
    @lru_cache(maxsize=100)
    def get_recommendations(self, flow_id):
        """Cache recommendations for frequently accessed flows."""
        return self.engine.get_recommendations(flow_id)
    
    @lru_cache(maxsize=50)
    def get_risk_assessment(self, flow_id, event_hash):
        """Cache risk assessments based on flow state."""
        return self.predictor.predict_failure_risk(flow_id)
    
    def _get_event_hash(self, flow_id):
        """Generate hash of current flow state for cache key."""
        events = self.shared_events.get_flow_events(flow_id)
        event_str = json.dumps(events, sort_keys=True)
        return hashlib.md5(event_str.encode()).hexdigest()
```

### Batch Processing

```python
async def batch_analyze_flows(flow_ids, batch_size=10):
    """Process flows in batches to avoid overwhelming the system."""
    results = []
    
    for i in range(0, len(flow_ids), batch_size):
        batch = flow_ids[i:i + batch_size]
        
        # Process batch concurrently
        tasks = [analyze_flow(fid) for fid in batch]
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)
        
        # Brief pause between batches
        await asyncio.sleep(0.1)
    
    return results
```

## Security Considerations

### Access Control

```python
from functools import wraps
from flask import g, abort

def require_flow_access(f):
    """Decorator to check flow access permissions."""
    @wraps(f)
    def decorated_function(flow_id, *args, **kwargs):
        # Check if user has access to this flow
        if not user_has_access(g.user, flow_id):
            abort(403, "Access denied to flow")
        return f(flow_id, *args, **kwargs)
    return decorated_function

@app.route('/api/pipeline/replay/<flow_id>')
@require_flow_access
def get_flow_replay(flow_id):
    # User has access, proceed with replay
    return replay_flow(flow_id)
```

### Data Sanitization

```python
def sanitize_flow_data(flow_data):
    """Remove sensitive information before returning to client."""
    sanitized = flow_data.copy()
    
    # Remove sensitive fields
    sensitive_fields = ['api_keys', 'credentials', 'tokens']
    for field in sensitive_fields:
        sanitized.pop(field, None)
    
    # Mask sensitive values in events
    for event in sanitized.get('events', []):
        if 'api_key' in event.get('data', {}):
            event['data']['api_key'] = '***REDACTED***'
    
    return sanitized
```

## Deployment

### Docker Integration

```dockerfile
# Dockerfile for pipeline enhancement service
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY src/ ./src/
COPY static/ ./static/
COPY templates/ ./templates/

# Expose ports
EXPOSE 5000

# Run the service
CMD ["python", "-m", "src.api.app"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pipeline-enhancement
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pipeline-enhancement
  template:
    metadata:
      labels:
        app: pipeline-enhancement
    spec:
      containers:
      - name: api
        image: marcus/pipeline-enhancement:latest
        ports:
        - containerPort: 5000
        env:
        - name: REDIS_URL
          value: redis://redis-service:6379
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: marcus-secrets
              key: database-url
```

## Monitoring and Observability

### Metrics Collection

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
replay_requests = Counter('pipeline_replay_requests_total', 
                         'Total replay requests')
whatif_simulations = Counter('whatif_simulations_total',
                           'Total what-if simulations')
recommendation_latency = Histogram('recommendation_latency_seconds',
                                 'Recommendation generation latency')
active_monitoring_sessions = Gauge('active_monitoring_sessions',
                                 'Number of active monitoring sessions')

# Use in code
@replay_requests.count_exceptions()
async def start_replay(flow_id):
    replay_requests.inc()
    # ... implementation

@recommendation_latency.time()
async def get_recommendations(flow_id):
    # ... implementation
```

## Next Steps

1. Review the [API Reference](./api-reference.md) for detailed endpoint documentation
2. Check [Example Projects](./examples/) for complete integration examples
3. Join our [Developer Community](https://github.com/anthropics/marcus/discussions) for support
4. Contribute enhancements via [Pull Requests](https://github.com/anthropics/marcus/pulls)