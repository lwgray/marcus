# Marcus Kanban Providers API Reference

> **Type**: API  
> **Version**: 1.0.0  
> **Last Updated**: 2025-06-25

## Overview

Complete reference for integrating kanban board providers with Marcus, including the provider interface, factory pattern, and provider-specific implementations.

## Synopsis

```python
from src.integrations.kanban_factory import KanbanFactory
from src.integrations.kanban_interface import KanbanInterface

# Get the default provider based on environment
kanban_client = KanbanFactory.create_default()
await kanban_client.connect()

# Get available tasks
tasks = await kanban_client.get_available_tasks()
```

## Description

Marcus supports multiple kanban board providers through a unified interface. The system uses a factory pattern to instantiate the appropriate provider based on configuration, allowing seamless switching between different kanban systems without code changes.

## Parameters

### KanbanInterface (Abstract Base Class)

All providers must implement this interface.

| Method | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `connect()` | async | Yes | - | Establish connection to kanban service |
| `disconnect()` | async | Yes | - | Close connection gracefully |
| `get_available_tasks()` | async | Yes | - | Fetch unassigned TODO tasks |
| `get_task_by_id(task_id)` | async | Yes | - | Retrieve specific task details |
| `update_task(task_id, updates)` | async | Yes | - | Update task properties |
| `add_comment(task_id, comment)` | async | Yes | - | Add comment to task |
| `update_task_progress(task_id, progress)` | async | Yes | - | Update task progress/checklist |

### Method Details

#### connect()
```python
async def connect(self) -> None:
    """
    Establish connection to the kanban provider.
    
    Raises:
        ConnectionError: If connection fails
        AuthenticationError: If credentials are invalid
    """
```

#### get_available_tasks()
```python
async def get_available_tasks(self) -> List[Task]:
    """
    Fetch all unassigned tasks in TODO status.
    
    Returns:
        List[Task]: Available tasks for assignment
        
    Notes:
        - Only returns tasks with status=TODO
        - Excludes already assigned tasks
        - Sorted by priority and creation date
    """
```

#### update_task()
```python
async def update_task(self, task_id: str, updates: Dict[str, Any]) -> None:
    """
    Update task properties.
    
    Parameters:
        task_id: Unique task identifier
        updates: Dictionary of fields to update
        
    Valid update fields:
        - status: TaskStatus enum value
        - assigned_to: Worker ID or None
        - progress: Integer 0-100
        - blocker: Blocker description
        - completed_at: ISO timestamp
    """
```

### KanbanFactory

Factory class for creating provider instances.

| Method | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `create_default()` | static | - | - | Create provider from environment |
| `create(provider_type)` | static | - | - | Create specific provider |
| `register(name, provider_class)` | static | - | - | Register custom provider |

## Provider Implementations

### Planka Provider

Integration with self-hosted Planka boards.

#### Configuration
```python
# Environment variables
KANBAN_PROVIDER=planka
PLANKA_SERVER_URL=http://localhost:3000
PLANKA_USERNAME=admin@example.com
PLANKA_PASSWORD=secure-password
```

#### Features
- Real-time updates via WebSocket
- Rich commenting system
- Checklist support for subtasks
- Label-based skill matching
- Attachment support

#### Implementation Details
```python
class PlankaProvider(KanbanInterface):
    def __init__(self):
        self.base_url = os.getenv('PLANKA_SERVER_URL')
        self.username = os.getenv('PLANKA_USERNAME')
        self.password = os.getenv('PLANKA_PASSWORD')
        self.token = None
        self.board_id = None
```

### GitHub Provider

Integration with GitHub Issues and Projects.

#### Configuration
```python
# Environment variables
KANBAN_PROVIDER=github
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
GITHUB_OWNER=my-organization
GITHUB_REPO=my-project
```

#### Features
- Issue-based task management
- Project board integration
- Code context awareness
- Pull request linking
- Milestone tracking

#### Implementation Details
```python
class GitHubProvider(KanbanInterface):
    def __init__(self):
        self.token = os.getenv('GITHUB_TOKEN')
        self.owner = os.getenv('GITHUB_OWNER')
        self.repo = os.getenv('GITHUB_REPO')
        self.github = Github(self.token)
```

#### GitHub-Specific Methods
```python
async def get_code_context(self, issue_number: int) -> Dict:
    """Get related code files and PRs for an issue"""
    
async def link_pull_request(self, issue_number: int, pr_number: int) -> None:
    """Link an issue to a pull request"""
```

### Trello Provider

Integration with Trello boards.

#### Configuration
```python
# Environment variables
KANBAN_PROVIDER=trello
TRELLO_API_KEY=your-api-key
TRELLO_TOKEN=your-token
TRELLO_BOARD_ID=board-id
```

#### Features
- Card-based task management
- List-based workflow states
- Power-ups support
- Webhook notifications
- Due date tracking

## Return Values

### Success Response

All methods follow consistent return patterns:

```python
# get_available_tasks returns
[
    Task(
        id="5f4d3e2c1b0a98",
        name="Implement user authentication",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        # ... other fields
    ),
    # ... more tasks
]

# update_task returns
None  # Raises exception on error
```

### Error Response

```python
# Connection errors
ConnectionError("Failed to connect to Planka server")

# Authentication errors
AuthenticationError("Invalid credentials for GitHub")

# Not found errors
TaskNotFoundError("Task with ID 'task-123' not found")

# API errors
KanbanAPIError("Rate limit exceeded", status_code=429)
```

## Examples

### Basic Example
```python
# Simple task retrieval
kanban = KanbanFactory.create_default()
await kanban.connect()

tasks = await kanban.get_available_tasks()
for task in tasks:
    print(f"{task.name} - {task.priority.value}")
```

### Advanced Example
```python
# Complete task workflow with error handling
async def process_task(task_id: str, worker_id: str):
    kanban = None
    try:
        # Initialize connection
        kanban = KanbanFactory.create("github")
        await kanban.connect()
        
        # Get task details
        task = await kanban.get_task_by_id(task_id)
        
        # Assign to worker
        await kanban.update_task(task_id, {
            "status": TaskStatus.IN_PROGRESS,
            "assigned_to": worker_id
        })
        
        # Add initial comment
        await kanban.add_comment(
            task_id, 
            f"Task assigned to {worker_id}. Starting implementation."
        )
        
        # Simulate progress updates
        for progress in [25, 50, 75, 100]:
            await asyncio.sleep(60)  # Wait 1 minute
            await kanban.update_task_progress(task_id, {
                "progress": progress,
                "message": f"Progress: {progress}%"
            })
        
        # Mark complete
        await kanban.update_task(task_id, {
            "status": TaskStatus.DONE,
            "completed_at": datetime.now().isoformat()
        })
        
    except ConnectionError as e:
        print(f"Connection failed: {e}")
    except TaskNotFoundError as e:
        print(f"Task not found: {e}")
    finally:
        if kanban:
            await kanban.disconnect()
```

### Real-World Example
```python
# Custom provider implementation
class JiraProvider(KanbanInterface):
    """Custom Jira integration"""
    
    def __init__(self):
        self.server = os.getenv('JIRA_SERVER')
        self.email = os.getenv('JIRA_EMAIL')
        self.token = os.getenv('JIRA_API_TOKEN')
        self.jira = None
    
    async def connect(self):
        """Connect to Jira server"""
        self.jira = JIRA(
            server=self.server,
            basic_auth=(self.email, self.token)
        )
    
    async def get_available_tasks(self) -> List[Task]:
        """Fetch unassigned issues from Jira"""
        jql = 'project = PM AND status = "To Do" AND assignee is EMPTY'
        issues = self.jira.search_issues(jql)
        
        tasks = []
        for issue in issues:
            task = Task(
                id=issue.key,
                name=issue.fields.summary,
                description=issue.fields.description or "",
                status=TaskStatus.TODO,
                priority=self._map_priority(issue.fields.priority.name),
                assigned_to=None,
                created_at=parser.parse(issue.fields.created),
                updated_at=parser.parse(issue.fields.updated),
                due_date=parser.parse(issue.fields.duedate) if issue.fields.duedate else None,
                estimated_hours=issue.fields.timeoriginalestimate / 3600 if issue.fields.timeoriginalestimate else 8.0,
                labels=[label.name for label in issue.fields.labels]
            )
            tasks.append(task)
        
        return tasks
    
    def _map_priority(self, jira_priority: str) -> Priority:
        """Map Jira priority to Marcus priority"""
        mapping = {
            "Highest": Priority.URGENT,
            "High": Priority.HIGH,
            "Medium": Priority.MEDIUM,
            "Low": Priority.LOW,
            "Lowest": Priority.LOW
        }
        return mapping.get(jira_priority, Priority.MEDIUM)

# Register custom provider
KanbanFactory.register("jira", JiraProvider)

# Use custom provider
os.environ['KANBAN_PROVIDER'] = 'jira'
kanban = KanbanFactory.create_default()
```

## Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| `PROVIDER_NOT_FOUND` | Unknown provider type | Check KANBAN_PROVIDER value |
| `CONNECTION_FAILED` | Cannot connect to service | Verify server URL and network |
| `AUTH_FAILED` | Invalid credentials | Check API keys/tokens |
| `RATE_LIMITED` | API rate limit exceeded | Implement backoff strategy |
| `TASK_NOT_FOUND` | Task ID doesn't exist | Verify task ID is correct |
| `PERMISSION_DENIED` | Insufficient permissions | Check API token scopes |

## Notes

- All providers must be async-compatible
- Connection pooling is handled internally
- Providers should implement retry logic
- Task IDs are provider-specific strings
- Labels are used for skill matching

## Performance Considerations

### Connection Management
- Providers maintain persistent connections
- Connection pooling for HTTP-based providers
- WebSocket connections for real-time updates
- Automatic reconnection on failure

### Caching Strategy
- Task lists cached for 5 minutes
- Individual tasks cached for 1 minute
- Cache invalidated on updates
- Provider-specific cache headers respected

### Rate Limiting
| Provider | Limit | Strategy |
|----------|-------|----------|
| GitHub | 5000/hour (authenticated) | Exponential backoff |
| Trello | 100/10 seconds | Request queuing |
| Planka | No limit (self-hosted) | Concurrent requests |

## Security Considerations

- API tokens stored in environment only
- No credentials in logs or error messages
- HTTPS required for external providers
- Token scopes limited to necessary permissions

## Version History

| Version | Changes |
|---------|---------|
| 1.0.0 | Complete provider API documentation |
| 0.9.0 | Added GitHub provider |
| 0.8.0 | Added Trello provider |
| 0.7.0 | Initial Planka provider |

## See Also

- [Configuration Guide](/reference/configuration_guide)
- [Environment Variables](/reference/environment_variables)
- [System Architecture](/reference/system_architecture)
- [Provider Setup Guides](/how-to/provider_setup)