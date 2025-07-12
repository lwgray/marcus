# Pattern Learning MCP Tools API Reference

## Overview

The Pattern Learning MCP tools provide external access to Marcus's pattern learning and quality assessment capabilities through the Model Context Protocol (MCP). These tools enable integration with Claude Desktop and other MCP-compatible clients.

## Available Tools

### get_similar_projects

Find projects with similar patterns to a given project context.

#### Tool Definition

```json
{
  "name": "get_similar_projects",
  "description": "Find similar projects based on patterns",
  "inputSchema": {
    "type": "object",
    "properties": {
      "project_context": {
        "type": "object",
        "description": "Current project information",
        "properties": {
          "total_tasks": {"type": "integer"},
          "team_size": {"type": "integer"},
          "velocity": {"type": "number"},
          "technology_stack": {
            "type": "array",
            "items": {"type": "string"}
          }
        }
      },
      "min_similarity": {
        "type": "number",
        "description": "Minimum similarity score (0-1)",
        "default": 0.7
      }
    },
    "required": ["project_context"]
  }
}
```

#### Example Request

```json
{
  "project_context": {
    "total_tasks": 45,
    "team_size": 3,
    "velocity": 8.5,
    "technology_stack": ["python", "fastapi", "react"]
  },
  "min_similarity": 0.75
}
```

#### Example Response

```json
{
  "similar_projects": [
    {
      "project_name": "E-Commerce Platform",
      "similarity_score": 0.87,
      "outcome": {
        "successful": true,
        "completion_time_days": 42,
        "quality_score": 0.89
      },
      "key_patterns": {
        "team_size": 3,
        "avg_velocity": 9.2,
        "tech_overlap": ["python", "react"]
      }
    }
  ]
}
```

### assess_project_quality

Get comprehensive quality assessment for a project.

#### Tool Definition

```json
{
  "name": "assess_project_quality",
  "description": "Assess project quality across multiple dimensions",
  "inputSchema": {
    "type": "object",
    "properties": {
      "board_id": {
        "type": "string",
        "description": "Kanban board ID"
      }
    },
    "required": ["board_id"]
  }
}
```

#### Example Request

```json
{
  "board_id": "project-123"
}
```

#### Example Response

```json
{
  "assessment": {
    "project_name": "Mobile App Development",
    "overall_score": 0.82,
    "code_quality_score": 0.85,
    "process_quality_score": 0.78,
    "delivery_quality_score": 0.80,
    "team_quality_score": 0.84,
    "quality_insights": [
      "Strong code review practices with 95% PR coverage",
      "Consistent velocity throughout project lifecycle",
      "Well-balanced workload across team members"
    ],
    "improvement_areas": [
      "Increase test coverage from 72% to target 80%",
      "Reduce average PR review time from 28 to 24 hours"
    ],
    "success_prediction": {
      "is_successful": true,
      "confidence": 0.87
    }
  }
}
```

### get_pattern_recommendations

Get recommendations based on learned patterns.

#### Tool Definition

```json
{
  "name": "get_pattern_recommendations",
  "description": "Get pattern-based recommendations for project improvement",
  "inputSchema": {
    "type": "object",
    "properties": {
      "project_context": {
        "type": "object",
        "description": "Current project context",
        "properties": {
          "total_tasks": {"type": "integer"},
          "team_size": {"type": "integer"},
          "velocity": {"type": "number"},
          "completion_percent": {"type": "number"}
        }
      },
      "recommendation_type": {
        "type": "string",
        "enum": ["team", "velocity", "quality", "risk"],
        "description": "Type of recommendations needed"
      }
    },
    "required": ["project_context"]
  }
}
```

#### Example Request

```json
{
  "project_context": {
    "total_tasks": 50,
    "team_size": 2,
    "velocity": 4.0,
    "completion_percent": 45
  },
  "recommendation_type": "velocity"
}
```

#### Example Response

```json
{
  "recommendations": [
    {
      "type": "velocity_improvement",
      "confidence": 0.78,
      "message": "Team velocity (4.0 tasks/week) below successful project average",
      "impact": "Faster delivery and improved project momentum",
      "suggestions": [
        "Consider adding 1 more team member based on similar projects",
        "Implement pair programming for complex tasks",
        "Review and optimize task dependencies"
      ],
      "supporting_data": {
        "current_velocity": 4.0,
        "target_velocity": 7.5,
        "based_on_projects": 12
      }
    }
  ]
}
```

### get_quality_trends

Analyze quality trends across recent projects.

#### Tool Definition

```json
{
  "name": "get_quality_trends",
  "description": "Get quality trends across projects over time",
  "inputSchema": {
    "type": "object",
    "properties": {
      "days": {
        "type": "integer",
        "description": "Number of days to analyze",
        "default": 30
      },
      "metric_type": {
        "type": "string",
        "enum": ["overall", "code", "process", "delivery", "team"],
        "description": "Quality metric to analyze",
        "default": "overall"
      }
    }
  }
}
```

#### Example Request

```json
{
  "days": 90,
  "metric_type": "code"
}
```

#### Example Response

```json
{
  "trends": {
    "period": "Last 90 days",
    "metric": "code_quality",
    "average_score": 0.79,
    "trend_direction": "improving",
    "monthly_averages": {
      "month_1": 0.75,
      "month_2": 0.78,
      "month_3": 0.82
    },
    "top_improvements": [
      "Test coverage increased from 68% to 81%",
      "Code review coverage improved to 95%"
    ],
    "areas_needing_attention": [
      "Documentation coverage declining",
      "Technical debt score increasing"
    ],
    "projects_analyzed": 15
  }
}
```

## Error Responses

All tools follow a consistent error response format:

```json
{
  "error": {
    "type": "ValidationError|NotFoundError|ProcessingError",
    "message": "Human-readable error description",
    "details": {
      "field": "Additional context about the error"
    }
  }
}
```

### Common Error Types

1. **ValidationError**: Invalid input parameters
2. **NotFoundError**: Requested resource not found
3. **ProcessingError**: Error during pattern analysis
4. **IntegrationError**: External service (GitHub) issues

## Authentication

Pattern learning MCP tools inherit authentication from the Marcus MCP server configuration. No additional authentication is required.

## Rate Limiting

- **get_similar_projects**: 100 requests per minute
- **assess_project_quality**: 20 requests per minute (due to GitHub API calls)
- **get_pattern_recommendations**: 100 requests per minute
- **get_quality_trends**: 50 requests per minute

## Best Practices

### 1. Efficient Context Provision

Provide complete project context for better recommendations:

```json
{
  "project_context": {
    "total_tasks": 40,
    "team_size": 3,
    "velocity": 7.5,
    "completion_percent": 60,
    "technology_stack": ["python", "react"],
    "blocked_tasks": 2,
    "overdue_tasks": 5
  }
}
```

### 2. Caching Responses

Quality assessments and trend data can be cached for 5-15 minutes to reduce API calls.

### 3. Error Handling

Always handle potential errors gracefully:

```python
try:
    response = await mcp_client.call_tool(
        "assess_project_quality",
        {"board_id": "project-123"}
    )
except MCPError as e:
    if e.error_type == "NotFoundError":
        # Handle missing project
    else:
        # Handle other errors
```

### 4. Batch Requests

When analyzing multiple projects, batch similar requests:

```python
# Good: Single request for trends
trends = await get_quality_trends(days=90)

# Avoid: Multiple individual project assessments in loop
for project_id in project_ids:
    assessment = await assess_project_quality(board_id=project_id)
```

## Integration Examples

### Claude Desktop Configuration

Add to your Claude Desktop MCP configuration:

```json
{
  "marcus": {
    "command": "npm",
    "args": ["run", "mcp-server"],
    "env": {
      "MARCUS_PATTERN_LEARNING_ENABLED": "true"
    }
  }
}
```

### Python MCP Client

```python
from mcp import MCPClient

async def analyze_project_patterns():
    client = MCPClient("marcus")

    # Get quality assessment
    assessment = await client.call_tool(
        "assess_project_quality",
        {"board_id": "my-project"}
    )

    # Find similar successful projects
    similar = await client.call_tool(
        "get_similar_projects",
        {
            "project_context": {
                "total_tasks": assessment["total_tasks"],
                "team_size": assessment["team_size"],
                "velocity": assessment["velocity"]
            },
            "min_similarity": 0.8
        }
    )

    # Get recommendations
    recommendations = await client.call_tool(
        "get_pattern_recommendations",
        {"project_context": similar["project_context"]}
    )

    return {
        "assessment": assessment,
        "similar_projects": similar,
        "recommendations": recommendations
    }
```

## Changelog

### v1.0.0 (2024-01-10)
- Initial release with four pattern learning tools
- GitHub integration support
- AI-powered insights

### Future Enhancements
- Real-time pattern matching
- Predictive success scoring
- Cross-organization benchmarking
- Custom pattern definitions
