# Task Execution Order API Specifications

## Overview

This document provides detailed API specifications for the Task Execution Order fix components. All APIs follow REST conventions and return JSON responses.

## Base URL
```
http://localhost:8080/api/v1/tasks
```

## Authentication
All endpoints require Bearer token authentication:
```
Authorization: Bearer <token>
```

## API Endpoints

### 1. Task Type Identification

#### Identify Single Task Type
```http
POST /api/v1/tasks/identify-type
Content-Type: application/json

{
    "task_name": "Create user authentication API",
    "task_description": "Build REST endpoints for user login, logout, and token refresh with JWT",
    "labels": ["backend", "api", "security"],
    "context": {
        "project_type": "web-application",
        "existing_task_types": ["design", "implementation"],
        "feature_name": "authentication"
    }
}

Response: 200 OK
{
    "task_type": "implementation",
    "confidence": 0.92,
    "reasoning": "Task identified as implementation based on keywords: 'build', 'api', 'endpoints' and context of creating functionality",
    "keyword_matches": ["build", "api", "endpoints"],
    "pattern_matches": ["build REST endpoints"],
    "alternative_types": [
        {
            "type": "design",
            "confidence": 0.08,
            "reasoning": "Some design elements present but primary focus is building"
        }
    ],
    "phase_order": 3,
    "typical_dependencies": ["design"]
}

Response: 400 Bad Request
{
    "error": "INVALID_REQUEST",
    "message": "task_name is required",
    "field": "task_name"
}
```

#### Batch Task Type Identification
```http
POST /api/v1/tasks/identify-types-batch
Content-Type: application/json

{
    "tasks": [
        {
            "id": "task-123",
            "name": "Design user interface mockups",
            "description": "Create wireframes for login and dashboard"
        },
        {
            "id": "task-124",
            "name": "Write unit tests for auth service",
            "description": "Test login, logout, and token validation"
        }
    ],
    "project_context": {
        "type": "saas-application",
        "stack": ["react", "nodejs", "postgresql"]
    }
}

Response: 200 OK
{
    "identifications": [
        {
            "task_id": "task-123",
            "task_type": "design",
            "confidence": 0.95,
            "phase_order": 1
        },
        {
            "task_id": "task-124",
            "task_type": "testing",
            "confidence": 0.98,
            "phase_order": 4
        }
    ],
    "processing_time_ms": 125
}
```

### 2. Dependency Validation

#### Validate Task Dependencies
```http
POST /api/v1/tasks/validate-dependencies
Content-Type: application/json

{
    "tasks": [
        {
            "id": "design-001",
            "name": "Design user authentication flow",
            "type": "design",
            "dependencies": []
        },
        {
            "id": "impl-001",
            "name": "Implement login API",
            "type": "implementation",
            "dependencies": ["design-001"]
        },
        {
            "id": "test-001",
            "name": "Test authentication endpoints",
            "type": "testing",
            "dependencies": []  // Missing dependency!
        }
    ],
    "validation_mode": "strict",
    "auto_fix": false
}

Response: 200 OK
{
    "is_valid": false,
    "validation_id": "val-789",
    "errors": [
        {
            "task_id": "test-001",
            "task_name": "Test authentication endpoints",
            "error_type": "missing_dependency",
            "severity": "error",
            "message": "Testing task has no implementation dependencies",
            "details": {
                "task_phase": "testing",
                "missing_phase_dependencies": ["implementation"],
                "suggested_dependencies": ["impl-001"]
            },
            "fix": {
                "action": "add_dependency",
                "target_task": "test-001",
                "dependencies_to_add": ["impl-001"]
            }
        }
    ],
    "warnings": [],
    "statistics": {
        "total_tasks": 3,
        "valid_tasks": 2,
        "error_count": 1,
        "warning_count": 0
    },
    "suggested_execution_order": [
        "design-001",
        "impl-001",
        "test-001"
    ]
}
```

#### Auto-Fix Dependencies
```http
POST /api/v1/tasks/auto-fix-dependencies
Content-Type: application/json

{
    "validation_id": "val-789",
    "apply_fixes": ["add_dependency"],
    "dry_run": true
}

Response: 200 OK
{
    "fixes_applied": [
        {
            "task_id": "test-001",
            "fix_type": "add_dependency",
            "changes": {
                "dependencies": {
                    "before": [],
                    "after": ["impl-001"]
                }
            },
            "status": "simulated"
        }
    ],
    "updated_tasks": [
        {
            "id": "test-001",
            "name": "Test authentication endpoints",
            "type": "testing",
            "dependencies": ["impl-001"]
        }
    ],
    "is_valid_after_fix": true
}
```

### 3. Phase Dependency Enforcement

#### Apply Phase Dependencies
```http
POST /api/v1/tasks/apply-phase-dependencies
Content-Type: application/json

{
    "tasks": [
        {
            "id": "feat-001-design",
            "name": "Design payment system",
            "type": "design",
            "feature": "payment-processing",
            "dependencies": []
        },
        {
            "id": "feat-001-impl",
            "name": "Implement payment API",
            "type": "implementation",
            "feature": "payment-processing",
            "dependencies": []
        }
    ],
    "enforcement_mode": "strict",
    "feature_grouping": "auto"
}

Response: 200 OK
{
    "updated_tasks": [
        {
            "id": "feat-001-design",
            "dependencies": [],
            "phase": "design",
            "phase_order": 1
        },
        {
            "id": "feat-001-impl",
            "dependencies": ["feat-001-design"],
            "phase": "implementation",
            "phase_order": 3,
            "dependencies_added": ["feat-001-design"],
            "reason": "Implementation tasks must depend on design tasks in the same feature"
        }
    ],
    "features_detected": ["payment-processing"],
    "dependencies_added": 1,
    "phase_rules_applied": [
        "design_before_implementation"
    ]
}
```

### 4. Global Dependencies

#### Apply Global Documentation Dependencies
```http
POST /api/v1/tasks/apply-global-dependencies
Content-Type: application/json

{
    "tasks": [
        {
            "id": "impl-001",
            "name": "Build user service",
            "type": "implementation"
        },
        {
            "id": "test-001",
            "name": "Test user service",
            "type": "testing"
        },
        {
            "id": "doc-001",
            "name": "Document API endpoints",
            "type": "documentation"
        }
    ],
    "rules": ["documentation_depends_on_all"]
}

Response: 200 OK
{
    "updated_tasks": [
        {
            "id": "doc-001",
            "dependencies": ["impl-001", "test-001"],
            "global_rule_applied": "documentation_depends_on_all",
            "dependencies_added": 2
        }
    ],
    "rules_applied": ["documentation_depends_on_all"],
    "total_dependencies_added": 2
}
```

### 5. Dependency Analysis

#### Get Dependency Graph
```http
GET /api/v1/tasks/dependency-graph?project_id=proj-123

Response: 200 OK
{
    "project_id": "proj-123",
    "nodes": [
        {
            "id": "design-001",
            "type": "design",
            "name": "Design authentication",
            "phase_order": 1,
            "status": "completed"
        },
        {
            "id": "impl-001",
            "type": "implementation",
            "name": "Implement auth service",
            "phase_order": 3,
            "status": "in_progress"
        }
    ],
    "edges": [
        {
            "from": "impl-001",
            "to": "design-001",
            "type": "depends_on",
            "reason": "phase_dependency"
        }
    ],
    "statistics": {
        "total_tasks": 2,
        "completed_tasks": 1,
        "blocked_tasks": 0,
        "max_parallel_tasks": 1
    },
    "critical_path": ["design-001", "impl-001"],
    "issues": []
}
```

#### Check Task Assignment Eligibility
```http
POST /api/v1/tasks/check-eligibility
Content-Type: application/json

{
    "agent_id": "agent-456",
    "task_id": "test-001",
    "completed_tasks": ["design-001", "impl-001"],
    "assigned_tasks": []
}

Response: 200 OK
{
    "eligible": true,
    "task_id": "test-001",
    "reasons": [
        "All dependencies completed",
        "Task type matches agent skills",
        "No conflicting assignments"
    ],
    "dependencies_status": {
        "total": 1,
        "completed": 1,
        "pending": 0,
        "blocked": 0
    },
    "estimated_duration_hours": 4
}

Response: 200 OK (Not Eligible)
{
    "eligible": false,
    "task_id": "test-001",
    "reasons": [
        "Missing dependency: impl-001 is not completed"
    ],
    "blocking_tasks": ["impl-001"],
    "dependencies_status": {
        "total": 1,
        "completed": 0,
        "pending": 1,
        "blocked": 0
    },
    "retry_after": "2024-01-21T15:30:00Z"
}
```

## Error Responses

### Standard Error Format
```json
{
    "error": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
        "field": "field_name",
        "value": "invalid_value",
        "constraint": "validation_rule"
    },
    "request_id": "req-123",
    "timestamp": "2024-01-21T10:30:00Z"
}
```

### Error Codes
- `INVALID_REQUEST`: Request validation failed
- `TASK_NOT_FOUND`: Specified task ID not found
- `CIRCULAR_DEPENDENCY`: Circular dependency detected
- `INVALID_TASK_TYPE`: Unknown task type specified
- `DEPENDENCY_CONFLICT`: Conflicting dependencies detected
- `UNAUTHORIZED`: Missing or invalid authentication
- `RATE_LIMITED`: Too many requests

## Rate Limiting
- 100 requests per minute per API key
- 1000 requests per hour per API key
- Headers returned: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

## Webhooks

### Dependency Violation Webhook
```http
POST https://your-webhook-url.com/dependency-violations
Content-Type: application/json
X-Marcus-Signature: sha256=...

{
    "event": "dependency_violation",
    "timestamp": "2024-01-21T10:30:00Z",
    "data": {
        "project_id": "proj-123",
        "task_id": "test-001",
        "violation_type": "assigned_before_dependency",
        "details": {
            "assigned_to": "agent-456",
            "missing_dependencies": ["impl-001"],
            "assignment_timestamp": "2024-01-21T10:29:55Z"
        }
    }
}
```

## Performance Considerations

1. **Batch Operations**: Use batch endpoints when processing multiple tasks
2. **Caching**: Dependency graphs are cached for 5 minutes
3. **Async Processing**: Large validation requests (>100 tasks) are processed asynchronously
4. **Response Compression**: All responses support gzip compression

## SDK Examples

### Python
```python
from marcus_sdk import TaskClient

client = TaskClient(api_key="your-api-key")  # pragma: allowlist secret

# Identify task type
result = client.identify_task_type(
    name="Write tests for login",
    description="Create unit tests for auth",
    labels=["testing", "backend"]
)

print(f"Type: {result.task_type} (confidence: {result.confidence})")

# Validate dependencies
validation = client.validate_dependencies(
    tasks=project_tasks,
    mode="strict"
)

if not validation.is_valid:
    for error in validation.errors:
        print(f"Error in {error.task_id}: {error.message}")
```

### JavaScript/TypeScript
```typescript
import { TaskClient } from '@marcus/task-sdk';

const client = new TaskClient({ apiKey: 'your-api-key' }); // pragma: allowlist secret

// Identify task types in batch
const identifications = await client.identifyTasksBatch({
    tasks: [
        { id: '1', name: 'Design UI', description: '...' },
        { id: '2', name: 'Build API', description: '...' }
    ]
});

// Apply phase dependencies
const updated = await client.applyPhaseDependencies({
    tasks: projectTasks,
    enforcementMode: 'strict'
});
```

## Migration Guide

For existing projects using the old dependency system:

1. Call `/api/v1/tasks/validate-dependencies` with existing tasks
2. Review validation errors and warnings
3. Use `/api/v1/tasks/auto-fix-dependencies` with `dry_run=true`
4. Apply fixes incrementally with monitoring
5. Enable webhooks for ongoing violation detection
