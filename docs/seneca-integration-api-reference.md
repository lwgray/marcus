# Seneca-Marcus Integration API Reference

## Overview

This document provides a complete API reference for all Marcus tools exposed to Seneca through the observer role. These tools enable Seneca to access predictions, analytics, and metrics for building comprehensive dashboards.

## Authentication

Before using any tools, Seneca must authenticate as an observer:

```http
POST http://localhost:4298/authenticate
Content-Type: application/json

{
  "client_id": "seneca-analytics",
  "client_type": "observer",
  "role": "viewer"
}
```

## Available Tool Categories

### 1. Prediction Tools (AI Intelligence)

These tools leverage Marcus's AI capabilities to predict future outcomes.

#### predict_completion_time
Predicts when a project will be completed with confidence intervals.

```http
POST http://localhost:4298/tools/call
{
  "name": "predict_completion_time",
  "arguments": {
    "project_id": "proj-123",     // optional, uses current if not provided
    "include_confidence": true     // optional, default: true
  }
}
```

**Response:**
```json
{
  "success": true,
  "project_id": "proj-123",
  "predicted_completion": "2024-02-15T10:00:00Z",
  "confidence_interval": {
    "low": "2024-02-10T10:00:00Z",
    "high": "2024-02-20T10:00:00Z"
  },
  "current_velocity": 3.5,
  "required_velocity": 4.2,
  "remaining_tasks": 42,
  "estimated_days": 12.5
}
```

#### predict_task_outcome
Predicts the success probability and duration for a task assignment.

```http
POST http://localhost:4298/tools/call
{
  "name": "predict_task_outcome",
  "arguments": {
    "task_id": "task-456",         // required
    "agent_id": "agent-789"        // optional, uses assigned agent if not provided
  }
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "task-456",
  "agent_id": "agent-789",
  "success_probability": 0.85,
  "estimated_duration": 24.5,
  "blockage_risk": 0.15,
  "confidence_score": 0.9,
  "method": "memory_based"
}
```

#### predict_blockage_probability
Analyzes the risk of a task becoming blocked.

```http
POST http://localhost:4298/tools/call
{
  "name": "predict_blockage_probability",
  "arguments": {
    "task_id": "task-456",         // required
    "include_mitigation": true     // optional, default: true
  }
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "task-456",
  "probability": 0.35,
  "likely_causes": [
    "Waiting for task: Authentication module",
    "Similar tasks had 3 blockages"
  ],
  "suggested_mitigations": [
    "Prioritize dependent tasks",
    "Assign senior developers to dependencies",
    "Break down complex tasks",
    "Schedule regular check-ins"
  ],
  "confidence_score": 0.8
}
```

#### predict_cascade_effects
Predicts the impact of task delays on the project.

```http
POST http://localhost:4298/tools/call
{
  "name": "predict_cascade_effects",
  "arguments": {
    "task_id": "task-456",         // required
    "delay_days": 3                // optional, default: 1
  }
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "task-456",
  "delay_days": 3,
  "affected_tasks": [
    {
      "id": "task-789",
      "title": "Frontend integration",
      "estimated_delay": 3
    }
  ],
  "total_delay_impact": 9,
  "critical_path_affected": true,
  "project_completion_impact": "2024-02-23T10:00:00Z",
  "affected_count": 3
}
```

#### get_task_assignment_score
Evaluates how well an agent matches a task.

```http
POST http://localhost:4298/tools/call
{
  "name": "get_task_assignment_score",
  "arguments": {
    "task_id": "task-456",         // required
    "agent_id": "agent-789"        // required
  }
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "task-456",
  "agent_id": "agent-789",
  "overall_score": 82.5,
  "skill_match": 0.9,
  "availability_score": 0.7,
  "historical_performance": 0.85,
  "active_tasks": 2,
  "recommendation": "assign",
  "reasoning": "Agent has 90% skill match and 2 active tasks"
}
```

### 2. Analytics Tools (Metrics Collection)

These tools provide real-time and historical metrics for dashboard visualization.

#### get_system_metrics
Returns system-wide performance metrics.

```http
POST http://localhost:4298/tools/call
{
  "name": "get_system_metrics",
  "arguments": {
    "time_window": "24h"           // optional: "1h", "24h", "7d", "30d"
  }
}
```

**Response:**
```json
{
  "success": true,
  "time_window": "24h",
  "metrics": {
    "active_agents": 5,
    "total_agents": 8,
    "total_throughput": 2.5,
    "completed_tasks": 60,
    "average_task_duration": 18.5,
    "system_health": 85.0
  },
  "timestamp": "2024-01-20T10:30:00Z"
}
```

#### get_agent_metrics
Returns performance metrics for a specific agent.

```http
POST http://localhost:4298/tools/call
{
  "name": "get_agent_metrics",
  "arguments": {
    "agent_id": "agent-789",       // required
    "time_window": "7d"            // optional: "1h", "24h", "7d", "30d"
  }
}
```

**Response:**
```json
{
  "success": true,
  "agent_id": "agent-789",
  "time_window": "7d",
  "metrics": {
    "utilization": 75.5,
    "tasks_completed": 12,
    "tasks_assigned": 15,
    "success_rate": 80.0,
    "average_task_time": 16.5,
    "total_hours_worked": 198.0,
    "skill_distribution": {
      "frontend": 5,
      "backend": 4,
      "testing": 3
    }
  },
  "timestamp": "2024-01-20T10:30:00Z"
}
```

#### get_project_metrics
Returns comprehensive project metrics including velocity and burndown data.

```http
POST http://localhost:4298/tools/call
{
  "name": "get_project_metrics",
  "arguments": {
    "project_id": "proj-123",      // optional, uses current if not provided
    "time_window": "7d"            // optional: "1h", "24h", "7d", "30d"
  }
}
```

**Response:**
```json
{
  "success": true,
  "project_id": "proj-123",
  "project_name": "E-commerce Platform",
  "time_window": "7d",
  "metrics": {
    "velocity": 3.5,
    "progress_percentage": 65.5,
    "total_tasks": 100,
    "completed_tasks": 65,
    "in_progress_tasks": 15,
    "blocked_tasks": 5,
    "blocked_task_ratio": 14.3,
    "health_score": 75.0,
    "burndown_data": [
      {
        "date": "2024-01-14",
        "remaining_tasks": 100,
        "completed_on_date": 0
      },
      {
        "date": "2024-01-15",
        "remaining_tasks": 97,
        "completed_on_date": 3
      }
    ]
  },
  "timestamp": "2024-01-20T10:30:00Z"
}
```

#### get_task_metrics
Returns aggregated task metrics with flexible grouping options.

```http
POST http://localhost:4298/tools/call
{
  "name": "get_task_metrics",
  "arguments": {
    "time_window": "30d",          // optional: "1h", "24h", "7d", "30d"
    "group_by": "status"           // optional: "status", "priority", "assignee", "label"
  }
}
```

**Response:**
```json
{
  "success": true,
  "time_window": "30d",
  "group_by": "status",
  "metrics": {
    "todo": {
      "count": 30,
      "total_hours": 0,
      "completed": 0,
      "blocked": 0,
      "completion_rate": 0.0,
      "blockage_rate": 0.0,
      "average_hours": 0
    },
    "in_progress": {
      "count": 15,
      "total_hours": 120,
      "completed": 0,
      "blocked": 2,
      "completion_rate": 0.0,
      "blockage_rate": 13.3,
      "average_hours": 0
    },
    "done": {
      "count": 65,
      "total_hours": 975,
      "completed": 65,
      "blocked": 0,
      "completion_rate": 100.0,
      "blockage_rate": 0.0,
      "average_hours": 15.0
    }
  },
  "total_tasks": 110,
  "timestamp": "2024-01-20T10:30:00Z"
}
```

## Integration Examples

### Example 1: Building a Project Dashboard

```python
# seneca/src/services/marcus_dashboard.py
import httpx
from datetime import datetime

class MarcusDashboardService:
    def __init__(self, marcus_url="http://localhost:4298"):
        self.marcus_url = marcus_url
        self.client = httpx.AsyncClient()

    async def get_project_dashboard_data(self, project_id):
        """Fetch all data needed for project dashboard."""

        # Get project metrics
        project_metrics = await self.call_tool("get_project_metrics", {
            "project_id": project_id,
            "time_window": "7d"
        })

        # Get completion prediction
        completion_prediction = await self.call_tool("predict_completion_time", {
            "project_id": project_id
        })

        # Get task breakdown
        task_breakdown = await self.call_tool("get_task_metrics", {
            "time_window": "30d",
            "group_by": "status"
        })

        return {
            "metrics": project_metrics["metrics"],
            "prediction": completion_prediction,
            "task_breakdown": task_breakdown["metrics"],
            "updated_at": datetime.now().isoformat()
        }
```

### Example 2: Agent Performance Monitor

```python
# seneca/src/services/agent_monitor.py
async def monitor_agent_performance(self, agent_id):
    """Monitor agent performance and predict issues."""

    # Get current metrics
    metrics = await self.call_tool("get_agent_metrics", {
        "agent_id": agent_id,
        "time_window": "24h"
    })

    # Check each active task for blockage risk
    active_tasks = await self.get_agent_active_tasks(agent_id)
    risk_assessments = []

    for task_id in active_tasks:
        blockage_risk = await self.call_tool("predict_blockage_probability", {
            "task_id": task_id
        })

        if blockage_risk["probability"] > 0.5:
            risk_assessments.append({
                "task_id": task_id,
                "risk": blockage_risk["probability"],
                "causes": blockage_risk["likely_causes"]
            })

    return {
        "performance": metrics["metrics"],
        "high_risk_tasks": risk_assessments
    }
```

## Rate Limiting and Best Practices

1. **Caching**: Cache prediction results for 5 minutes to avoid overloading Marcus
2. **Batch Requests**: When building dashboards, fetch all needed data in parallel
3. **Time Windows**: Use appropriate time windows - shorter for real-time, longer for trends
4. **Error Handling**: Always check `success` field and handle errors gracefully

## Error Responses

All tools return consistent error responses:

```json
{
  "success": false,
  "error": "Description of what went wrong"
}
```

Common errors:
- "No project specified or active" - Provide project_id
- "Agent {id} not found" - Check agent exists
- "Task {id} not found" - Verify task ID
- "Server state not available" - Marcus internal error
