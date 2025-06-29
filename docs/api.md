# Marcus API Overview

Marcus provides several APIs for integrating with external systems and building custom tooling. This guide provides an overview of all available APIs.

## API Categories

### 1. PM Agent REST API
The core API for managing projects, tasks, and agents.

**Base URL:** `http://localhost:8000/api`

**Key Endpoints:**
- `/health` - System health check
- `/agents` - Agent management
- `/tasks` - Task operations
- `/projects` - Project management
- `/metrics` - Performance metrics

[Full PM Agent API Reference →](reference/mcp_tools_api.md)

### 2. MCP (Model Context Protocol) Tools
Tools for AI agents to interact with Marcus programmatically.

**Available Tools:**
- `register_agent` - Register a new agent
- `request_next_task` - Get task assignment
- `report_task_progress` - Update task progress
- `report_blocker` - Report blocking issues
- `get_project_status` - Get project overview
- `get_agent_status` - Get agent information

[Full MCP Tools Reference →](mcp_tools/marcus_mcp_tools_reference.md)

### 3. Kanban Provider APIs
Interfaces for different task board providers.

**Supported Providers:**
- GitHub Projects API
- Linear API
- Planka API (local only)

[Full Provider API Reference →](reference/kanban_providers_api.md)

### 4. AI Analysis Engine API
APIs for task analysis and intelligent assignment.

**Key Features:**
- Task complexity analysis
- Skill matching
- Workload balancing
- Blocker resolution

[Full AI Engine API Reference →](reference/ai_analysis_engine_api.md)

### 5. Data Models API
Core data structures and schemas.

**Main Models:**
- Agent
- Task
- Project
- TaskProgress
- Blocker

[Full Data Models Reference →](reference/data_models_api.md)

## Quick Start Examples

### Register an Agent

```python
import requests

response = requests.post('http://localhost:8000/api/agents/register', json={
    'agent_id': 'worker-1',
    'name': 'Backend Specialist',
    'capabilities': ['python', 'api', 'database'],
    'system_prompt': 'You are a backend development expert...'
})
```

### Request a Task

```python
response = requests.post('http://localhost:8000/api/tasks/request', json={
    'agent_id': 'worker-1'
})

task = response.json()
print(f"Assigned task: {task['title']}")
```

### Report Progress

```python
response = requests.post('http://localhost:8000/api/tasks/progress', json={
    'agent_id': 'worker-1',
    'task_id': task['id'],
    'progress_percentage': 50,
    'message': 'Completed database schema'
})
```

## Authentication

### API Key Authentication

Include your API key in the Authorization header:

```python
headers = {
    'Authorization': 'Bearer your-api-key-here',
    'Content-Type': 'application/json'
}
```

### Environment Variables

Configure authentication in your `.env` file:

```bash
API_KEY=your-api-key-here
API_SECRET=your-secret-here
```

## Rate Limiting

Default rate limits:
- 100 requests per minute per API key
- 1000 requests per hour per API key
- Burst allowance of 10 requests

Headers returned:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Time when limit resets

## Error Handling

### Standard Error Response

```json
{
    "error": {
        "code": "TASK_NOT_FOUND",
        "message": "Task with ID 123 not found",
        "details": {
            "task_id": 123,
            "suggestion": "Check if task exists in the board"
        }
    },
    "status": 404
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `INVALID_REQUEST` | 400 | Malformed request data |
| `UNAUTHORIZED` | 401 | Missing or invalid API key |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource doesn't exist |
| `CONFLICT` | 409 | Resource conflict |
| `RATE_LIMITED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal server error |

## WebSocket API

For real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.on('message', (data) => {
    const event = JSON.parse(data);
    console.log('Event:', event.type, event.payload);
});

// Subscribe to task updates
ws.send(JSON.stringify({
    type: 'subscribe',
    channel: 'tasks'
}));
```

### Event Types

- `task.created` - New task added
- `task.assigned` - Task assigned to agent
- `task.progress` - Progress update
- `task.completed` - Task finished
- `agent.registered` - New agent joined
- `agent.offline` - Agent disconnected

## SDK Support

### Python SDK

```bash
pip install marcus-sdk
```

```python
from marcus import MarcusClient

client = MarcusClient(api_key='your-key')

# Register agent
agent = client.agents.register(
    agent_id='worker-1',
    capabilities=['python', 'api']
)

# Get next task
task = client.tasks.request_next(agent.id)
```

### JavaScript SDK

```bash
npm install @marcus/sdk
```

```javascript
import { MarcusClient } from '@marcus/sdk';

const client = new MarcusClient({ apiKey: 'your-key' });

// Register agent
const agent = await client.agents.register({
    agentId: 'worker-1',
    capabilities: ['javascript', 'frontend']
});
```

## API Versioning

Marcus uses URL-based versioning:

- Current version: `v1`
- Base URL: `http://localhost:8000/api/v1`
- Legacy support: 6 months after new version

Version header:
```
X-API-Version: 1.0
```

## GraphQL API (Beta)

Alternative to REST API:

```graphql
query GetAgentTasks($agentId: ID!) {
    agent(id: $agentId) {
        id
        name
        currentTask {
            id
            title
            progress
        }
        completedTasks {
            count
            items {
                id
                title
                completedAt
            }
        }
    }
}
```

Endpoint: `http://localhost:8000/graphql`

## API Testing

### Using cURL

```bash
# Health check
curl http://localhost:8000/api/health

# Register agent
curl -X POST http://localhost:8000/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "test-1", "capabilities": ["python"]}'
```

### Using Postman

Import our Postman collection:
- [Marcus API Collection](https://postman.com/marcus-api)
- Includes all endpoints with examples
- Environment variables for easy setup

## Best Practices

1. **Always handle errors gracefully**
   - Check status codes
   - Parse error messages
   - Implement retry logic

2. **Use appropriate timeouts**
   - Default: 30 seconds
   - Long operations: 5 minutes
   - WebSocket ping: 30 seconds

3. **Batch operations when possible**
   - Use bulk endpoints
   - Reduce API calls
   - Improve performance

4. **Cache responses appropriately**
   - Agent data: 5 minutes
   - Project status: 1 minute
   - Static data: 1 hour

## Next Steps

- Explore [MCP Tools](mcp_tools/mcp_tools_quick_reference.md) for agent integration
- Read [API Security](how-to/security-best-practices.md) best practices
- Try our [Interactive API Explorer](https://api.marcus.ai/explorer)
- Join our [API Discord Channel](https://discord.gg/marcus-api)