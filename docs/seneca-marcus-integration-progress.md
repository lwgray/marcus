# Seneca-Marcus Integration Progress

## Completed: Phase 1 - Expose Marcus Prediction Tools ✓

### What was implemented:
1. **Created `src/marcus_mcp/tools/predictions.py`** with 5 AI intelligence tools:
   - `predict_completion_time` - Project completion with confidence intervals
   - `predict_task_outcome` - Task success probability and duration estimates
   - `predict_blockage_probability` - Risk analysis with mitigation suggestions
   - `predict_cascade_effects` - Delay impact and critical path analysis
   - `get_task_assignment_score` - Agent-task fitness scoring

2. **Updated authentication roles** in `src/marcus_mcp/tools/auth.py`:
   - Added all 5 prediction tools to the "observer" role
   - This allows Seneca (authenticating as observer) to access these tools

3. **Registered tools in server** in `src/marcus_mcp/server.py`:
   - Added tool registration for all 5 prediction tools
   - Tools are available on HTTP endpoints when observer role is used

### How Seneca can use these tools:

```python
# Example: Seneca calling Marcus prediction tools via HTTP
import httpx

# Authenticate as observer
auth_response = await httpx.post(
    "http://localhost:4298/authenticate",
    json={
        "client_id": "seneca-analytics",
        "client_type": "observer",
        "role": "viewer"
    }
)

# Call prediction tool
prediction = await httpx.post(
    "http://localhost:4298/tools/call",
    json={
        "name": "predict_completion_time",
        "arguments": {
            "project_id": "project-123",
            "include_confidence": True
        }
    }
)

# Response structure:
{
    "success": true,
    "project_id": "project-123",
    "predicted_completion": "2024-02-15T10:00:00Z",
    "confidence_interval": {
        "low": "2024-02-10T10:00:00Z",
        "high": "2024-02-20T10:00:00Z"
    },
    "current_velocity": 3.5,
    "required_velocity": 4.2,
    "remaining_tasks": 42
}
```

## Next Steps: Phase 1 Continuation

### 1. Create Seneca API Endpoints (Next Task)
Location: `seneca/src/api/prediction_api.py`

```python
from src.services.marcus_client import get_marcus_client

@prediction_api.route('/project/<project_id>/completion')
async def predict_project_completion(project_id):
    client = await get_marcus_client()
    return await client.call_tool('predict_completion_time', {
        'project_id': project_id,
        'include_confidence': True
    })

@prediction_api.route('/task/<task_id>/outcome')
async def predict_task_outcome(task_id):
    client = await get_marcus_client()
    agent_id = request.args.get('agent_id')
    return await client.call_tool('predict_task_outcome', {
        'task_id': task_id,
        'agent_id': agent_id
    })
```

### 2. Add Visualization Components (After API)
Location: `seneca/src/ui/components/predictions/`

- **ProjectTimeline.vue** - Gantt chart with confidence intervals
- **TaskRiskMatrix.vue** - Risk visualization for blockage probability
- **AgentAssignmentScore.vue** - Agent-task fitness visualization
- **CascadeEffectDiagram.vue** - Dependency impact visualization

## API Reference for Implemented Tools

### 1. predict_completion_time
```json
{
    "name": "predict_completion_time",
    "arguments": {
        "project_id": "string (optional)",
        "include_confidence": "boolean (default: true)"
    },
    "returns": {
        "predicted_completion": "ISO datetime",
        "confidence_interval": {
            "low": "ISO datetime",
            "high": "ISO datetime"
        },
        "current_velocity": "number",
        "required_velocity": "number",
        "remaining_tasks": "number"
    }
}
```

### 2. predict_task_outcome
```json
{
    "name": "predict_task_outcome",
    "arguments": {
        "task_id": "string (required)",
        "agent_id": "string (optional)"
    },
    "returns": {
        "success_probability": "0-1",
        "estimated_duration": "hours",
        "blockage_risk": "0-1",
        "confidence_score": "0-1"
    }
}
```

### 3. predict_blockage_probability
```json
{
    "name": "predict_blockage_probability",
    "arguments": {
        "task_id": "string (required)",
        "include_mitigation": "boolean (default: true)"
    },
    "returns": {
        "probability": "0-1",
        "likely_causes": ["string"],
        "suggested_mitigations": ["string"],
        "confidence_score": "0-1"
    }
}
```

### 4. predict_cascade_effects
```json
{
    "name": "predict_cascade_effects",
    "arguments": {
        "task_id": "string (required)",
        "delay_days": "integer (default: 1)"
    },
    "returns": {
        "affected_tasks": [
            {
                "id": "string",
                "title": "string",
                "estimated_delay": "days"
            }
        ],
        "total_delay_impact": "days",
        "critical_path_affected": "boolean",
        "project_completion_impact": "ISO datetime"
    }
}
```

### 5. get_task_assignment_score
```json
{
    "name": "get_task_assignment_score",
    "arguments": {
        "task_id": "string (required)",
        "agent_id": "string (required)"
    },
    "returns": {
        "overall_score": "0-100",
        "skill_match": "0-1",
        "availability_score": "0-1",
        "historical_performance": "0-1",
        "recommendation": "string"
    }
}
```

## Testing the Integration

### 1. Start Marcus with multi-endpoint mode:
```bash
python -m marcus --multi
```

### 2. Test authentication and tool access:
```python
# test_predictions.py
import httpx
import asyncio

async def test_marcus_predictions():
    # Test each prediction tool
    # Verify response structures
    # Check error handling
    pass

asyncio.run(test_marcus_predictions())
```

## Architecture Notes

- Marcus predictions use fallback logic when advanced memory features are unavailable
- All predictions return a `confidence_score` to indicate reliability
- Tools gracefully handle missing project context
- HTTP transport allows for easy integration with Seneca's existing infrastructure
