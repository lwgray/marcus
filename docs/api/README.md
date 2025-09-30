# API Reference

Technical reference documentation for Marcus's Model Context Protocol (MCP) tools, data models, and error handling.

## Purpose

Complete API specification for developers building agent integrations, extending Marcus, or understanding the technical interface.

## Audience

- Developers building AI agents
- System integrators connecting Marcus to other tools
- Engineers extending Marcus capabilities
- Technical users needing detailed API specs

## API Structure

Marcus exposes its capabilities through MCP (Model Context Protocol) tools organized into functional categories:

### **Core Agent Tools**
Essential tools for agent lifecycle and task management:
- `register_agent` - Register with Marcus coordination system
- `get_agent_status` - Query agent performance and health
- `list_registered_agents` - View all active agents

### **Task Management Tools**
Request and manage work assignments:
- `request_next_task` - Get optimal task assignment
- `report_task_progress` - Update progress at milestones
- `get_task_metrics` - Query task performance data
- `check_task_dependencies` - Validate dependency status
- `get_task_assignment_score` - Understand why task was assigned

### **Project Management Tools**
Create and monitor projects:
- `create_project` - Natural language project creation
- `get_project_status` - Comprehensive project health
- `list_projects` - View all projects
- `switch_project` - Change active project
- `get_current_project` - Query active project
- `add_project` - Create project programmatically
- `update_project` - Modify project details
- `remove_project` - Delete project
- `get_project_metrics` - Query project analytics

### **Support & Intelligence Tools**
Context, decisions, and artifacts:
- `ping` - Verify connectivity and health
- `get_task_context` - Rich task information
- `log_decision` - Document important decisions
- `log_artifact` - Track project artifacts
- `check_assignment_health` - Validate assignment integrity
- `authenticate` - System authentication

### **Predictive & Analytics Tools**
Forecasting and optimization:
- `predict_completion_time` - Timeline forecasts
- `predict_blockage_probability` - Risk analysis
- `predict_task_outcome` - Success prediction
- `predict_cascade_effects` - Impact analysis
- `get_agent_metrics` - Agent analytics
- `get_code_metrics` - Code quality metrics
- `get_repository_metrics` - Repository analytics
- `get_code_review_metrics` - Review performance
- `get_code_quality_metrics` - Quality trends

### **System Health Tools**
Monitoring and diagnostics:
- `get_system_metrics` - System performance
- `check_board_health` - Kanban integration health
- `get_usage_report` - Usage analytics

### **Pipeline & Workflow Tools**
Advanced workflow analysis:
- `pipeline_*` tools - Pipeline tracking and analysis
- `what_if_*` tools - Scenario planning

### **Blocker Management Tools**
Handle obstacles:
- `report_blocker` - Report and analyze blockers

## Data Models

### **Core Models**
- **Agent** - AI worker with skills, status, performance
- **Task** - Work unit with dependencies, context, predictions
- **Project** - Structured collection with phases, metrics, health
- **WorkerStatus** - Agent state and capabilities
- **TaskAssignment** - Active work assignment with lease
- **TaskDependency** - Relationship between tasks

### **Context Models**
- **TaskContext** - Rich task information
- **ProjectContext** - Project-level awareness
- **ImplementationContext** - Code and architectural guidance

### **Analytics Models**
- **TaskMetrics** - Task performance data
- **AgentMetrics** - Agent performance analytics
- **ProjectMetrics** - Project health indicators
- **PredictionResult** - Forecast with confidence

### **Communication Models**
- **Decision** - Logged architectural decision
- **Artifact** - Tracked project artifact
- **BlockerReport** - Problem analysis

## Error Handling

Marcus uses a comprehensive error framework with six tiers:

### **Error Categories**
1. **Integration Errors** - External service failures (Kanban, AI providers)
2. **Configuration Errors** - Missing credentials, invalid settings
3. **Business Logic Errors** - Workflow violations, validation failures
4. **Security Errors** - Unauthorized access, permission denied
5. **Resource Errors** - Memory exhaustion, database failures
6. **Internal Errors** - Programming errors, unexpected states

### **Error Response Format**
```json
{
  "success": false,
  "error": {
    "type": "KanbanIntegrationError",
    "message": "Failed to sync with board",
    "context": {
      "operation": "task_sync",
      "agent_id": "agent-123",
      "task_id": "task-456"
    },
    "recovery_suggestions": [
      "Check board connectivity",
      "Verify credentials",
      "Retry operation"
    ]
  }
}
```

### **Retry & Resilience**
- Automatic retries for transient failures
- Circuit breakers for external services
- Fallback mechanisms for critical operations
- Graceful degradation when services unavailable

## Request/Response Format

### **Tool Request Format**
```json
{
  "tool": "request_next_task",
  "arguments": {
    "agent_id": "agent-123",
    "project_id": "project-456"
  }
}
```

### **Success Response Format**
```json
{
  "success": true,
  "result": {
    "task": { /* task object */ },
    "context": { /* rich context */ },
    "predictions": { /* forecasts */ }
  }
}
```

## Common Integration Patterns

### **Agent Integration Pattern**
```
1. Call ping() to verify connectivity
2. Call register_agent() once at startup
3. Enter continuous loop:
   a. Call request_next_task()
   b. Call get_task_context() if dependencies exist
   c. Work on task autonomously
   d. Call report_task_progress() at milestones
   e. Call report_blocker() if stuck
   f. Call report_task_progress(100) at completion
   g. IMMEDIATELY call request_next_task()
```

### **Project Management Pattern**
```
1. Call create_project() with description
2. Call get_project_status() for overview
3. Monitor with periodic status checks
4. Use predict_* tools for forecasting
5. Act on recommendations
```

### **Debugging Pattern**
```
1. Call ping() for connectivity
2. Call get_agent_status() for health
3. Call check_assignment_health() for integrity
4. Call check_board_health() for sync status
5. Review error responses for recovery suggestions
```

## Rate Limits & Constraints

- No artificial rate limits on API calls
- Performance optimized for real-time coordination
- Bulk operations available for efficiency
- Caching used where appropriate

## Authentication

- Token-based authentication (when configured)
- API key authentication for external integrations
- Role-based access control (RBAC) for enterprise
- Workspace isolation between projects

## API Versioning

- Current version: MCP 1.0
- Backward compatibility maintained
- Deprecation warnings before breaking changes
- Migration guides for major versions

## Documentation Status

🚧 **This section is under active development**

Detailed API documentation for each tool is being created. For now, refer to:

- **[Agent Workflows](../guides/agent-workflows/)** - Agent tool usage
- **[Project Management](../guides/project-management/)** - Project tool usage
- **[Collaboration](../guides/collaboration/)** - Support tool usage
- **[Systems Documentation](../systems/)** - Implementation details

## Next Steps

- **Building an agent?** → [Agent Workflows Guide](../guides/agent-workflows/)
- **Creating projects?** → [Project Management Guide](../guides/project-management/)
- **Need examples?** → Check guide documents for real usage
- **Want deep technical details?** → [Systems Documentation](../systems/)

---

**Note**: Complete API reference with request/response examples, error codes, and integration patterns is coming soon. Current guides provide comprehensive usage information.
