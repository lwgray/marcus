# Pattern Learning Architecture

## Overview

The Pattern Learning System in Marcus follows a secure, API-first architecture where pattern learning features are only accessible through the visualization UI, not through MCP tools or directly by agents.

## Architecture Diagram

```
┌─────────────────────────┐
│   Visualization UI      │
│     (Vue.js)           │
└───────────┬─────────────┘
            │ HTTP/REST
            ▼
┌─────────────────────────┐
│   Pattern Learning API  │
│   /api/patterns/*      │
├─────────────────────────┤
│ - Similar Projects      │
│ - Quality Assessment    │
│ - Recommendations       │
│ - Quality Trends       │
│ - Pattern Export       │
└───────────┬─────────────┘
            │ Uses
            ▼
┌─────────────────────────┐
│  Pattern Learning Core  │
├─────────────────────────┤
│ - ProjectPatternLearner │
│ - QualityAssessor      │
│ - ProjectMonitor       │
└─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│    Data Sources        │
├─────────────────────────┤
│ - Kanban Board         │
│ - GitHub (optional)    │
│ - AI Analysis          │
└─────────────────────────┘
```

## Security Model

### Access Control

1. **No MCP Access**: Pattern learning tools are NOT available through MCP
   - Agents cannot access pattern learning features
   - Claude Desktop cannot directly query patterns
   - MCP requests for pattern tools return an error directing to the UI

2. **API-Only Access**: All pattern learning features require API authentication
   - Only the visualization UI can access pattern endpoints
   - Future: Add API key authentication for additional security

3. **Read-Only for Agents**: Agents can only:
   - Report task progress
   - Request tasks
   - View project status
   - They CANNOT trigger pattern learning or access historical patterns

## API Endpoints

All pattern learning features are exposed through REST API endpoints under `/api/patterns/`:

### GET `/api/patterns/similar-projects`
Find projects similar to current context
- Requires: project_context object
- Returns: List of similar projects with similarity scores

### GET `/api/patterns/assess-quality/<board_id>`
Get comprehensive quality assessment
- Requires: board_id
- Optional: GitHub configuration
- Returns: Quality scores and insights

### POST `/api/patterns/recommendations`
Get pattern-based recommendations
- Requires: project_context object
- Returns: List of recommendations

### GET `/api/patterns/quality-trends`
Analyze quality trends over time
- Optional: days, metric_type parameters
- Returns: Trend analysis

### GET `/api/patterns/patterns`
List all learned patterns with pagination
- Optional: page, per_page parameters
- Returns: Paginated pattern list

### GET `/api/patterns/export`
Export all patterns as JSON
- Returns: Complete pattern data for analysis

## Component Initialization

Pattern learning components are initialized when the Marcus server starts:

```python
# In src/api/pattern_learning_init.py
def init_pattern_learning_components(kanban_client, ai_engine):
    """Initialize all pattern learning components"""

    # Create pattern learner
    pattern_learner = ProjectPatternLearner(...)

    # Create quality assessor
    quality_assessor = ProjectQualityAssessor(...)

    # Create project monitor
    project_monitor = ProjectMonitor(...)

    # Initialize API with components
    init_pattern_api(pattern_learner, quality_assessor, ...)
```

## Visualization UI Integration

The Vue.js visualization UI accesses pattern learning through the API:

```javascript
// Example: Get quality assessment
const response = await fetch('/api/patterns/assess-quality/board-123');
const assessment = await response.json();

// Example: Find similar projects
const response = await fetch('/api/patterns/similar-projects', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    project_context: {
      total_tasks: 50,
      team_size: 3,
      velocity: 7.5
    }
  })
});
```

## Benefits of This Architecture

1. **Security**: Agents cannot manipulate or access sensitive pattern data
2. **Separation of Concerns**: Clear boundary between agent operations and analytics
3. **Scalability**: API can be deployed separately if needed
4. **Flexibility**: Easy to add authentication, rate limiting, or caching
5. **User Control**: All pattern learning insights require human interaction through UI

## Future Enhancements

1. **Authentication**: Add API key or JWT authentication to pattern endpoints
2. **Role-Based Access**: Different access levels for different user types
3. **Audit Logging**: Track who accesses pattern data and when
4. **Caching Layer**: Add Redis caching for expensive pattern calculations
5. **WebSocket Support**: Real-time pattern updates in the UI

## Migration Notes

If you previously had pattern learning tools in MCP:
1. Remove any MCP tool registrations for pattern learning
2. Update visualization UI to use API endpoints instead of MCP tools
3. Ensure proper CORS configuration for API access from UI
