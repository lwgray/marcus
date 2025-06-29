# Marcus add_feature Tool Usage Guide

The `add_feature` tool allows you to add new features to an existing project using natural language descriptions. It intelligently generates tasks, detects integration points, and maintains logical dependencies.

## Prerequisites

- An existing project with tasks must be present
- The kanban client must support the `create_task` method
- Marcus MCP server must be running

## Basic Usage

```python
# Simple feature addition
result = await add_feature_natural_language(
    feature_description="Add user profile management",
    integration_point="auto_detect"
)
```

## Parameters

- `feature_description` (required): Natural language description of the feature to add
- `integration_point` (optional): Where to integrate the feature
  - `"auto_detect"` (default): Automatically detect integration points
  - Any other string: Manually specify the integration phase

## Examples

### 1. Adding an API Feature

```python
result = await add_feature_natural_language(
    feature_description="Add REST API for managing user preferences"
)
```

This will generate tasks like:
- Design REST API for managing user preferences
- Create database schema for REST API for managing user preferences  
- Implement backend for REST API for managing user preferences
- Test REST API for managing user preferences
- Document REST API for managing user preferences

### 2. Adding a UI Feature

```python
result = await add_feature_natural_language(
    feature_description="Create admin dashboard UI with analytics"
)
```

This will generate tasks like:
- Design admin dashboard UI with analytics
- Build UI components for admin dashboard UI with analytics
- Test admin dashboard UI with analytics
- Document admin dashboard UI with analytics

### 3. Adding Authentication Feature

```python
result = await add_feature_natural_language(
    feature_description="Implement two-factor authentication system"
)
```

This will generate security-focused tasks:
- Design two-factor authentication system
- Implement backend for two-factor authentication system
- Implement security for two-factor authentication system
- Test two-factor authentication system
- Document two-factor authentication system

### 4. Adding Integration Feature

```python
result = await add_feature_natural_language(
    feature_description="Integrate with Slack for notifications"
)
```

This will generate integration-specific tasks:
- Design Integrate with Slack for notifications
- Build integration layer for Integrate with Slack for notifications
- Test Integrate with Slack for notifications
- Document Integrate with Slack for notifications

## Response Format

The tool returns a dictionary with:

```python
{
    "success": True,  # Whether the operation succeeded
    "tasks_created": 5,  # Number of tasks created
    "integration_points": ["2", "5"],  # Task IDs that new tasks depend on
    "integration_detected": True,  # Whether auto-detection was used
    "confidence": 0.85,  # Confidence level of integration detection
    "feature_phase": "development"  # Detected project phase
}
```

Error response:
```python
{
    "success": False,
    "error": "Description of what went wrong"
}
```

## Task Enrichment

All generated tasks are automatically enriched with:
- Improved naming based on context
- Appropriate labels based on feature type
- Hour estimates based on task complexity
- Priority adjustment based on keywords (urgent, critical, etc.)
- Dependencies on related existing tasks

## Fallback Behavior

When the AI engine is unavailable, the tool uses intelligent fallbacks:

1. **Task Generation**: Analyzes keywords to determine feature type and generates appropriate tasks
2. **Integration Detection**: Examines existing task status and labels to determine project phase
3. **Dependency Mapping**: Matches feature task labels with existing task labels

## Error Handling

The tool validates:
- Feature description is not empty
- Kanban client supports task creation
- An existing project is present
- All required dependencies are available

## Best Practices

1. **Be Specific**: More detailed descriptions lead to better task generation
   - Good: "Add user profile page with avatar upload and bio editing"
   - Poor: "Add profile"

2. **Include Technical Details**: Mention specific technologies when relevant
   - "Create React component for user dashboard"
   - "Implement GraphQL API for real-time chat"

3. **Specify Requirements**: Include performance or security requirements
   - "Add secure file upload with virus scanning"
   - "Implement high-performance search with caching"

4. **Let Auto-Detection Work**: Use `integration_point="auto_detect"` unless you have specific requirements

## Integration with Existing Projects

The tool automatically:
- Detects authentication dependencies for user-related features
- Links API features to existing backend tasks
- Connects UI features to relevant frontend tasks
- Ensures testing tasks depend on implementation tasks
- Prevents deployment tasks from being created prematurely