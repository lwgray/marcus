# PM Agent Reference Documentation

> **Last Updated**: 2025-06-25  
> **Version**: 2.0.0

## Overview

This section contains comprehensive technical reference documentation for all PM Agent components, APIs, and configurations. Each reference document follows a consistent format with complete parameter documentation, examples, and error handling information.

## API References

### [MCP Tools API](./mcp_tools_api.md)
Complete reference for all Model Context Protocol (MCP) tools available to worker agents.

**Key Topics:**
- Tool registration and discovery
- Request/response formats
- Error handling patterns
- Real-world usage examples

**Essential Tools:**
- `register_agent` - Register new worker agents
- `request_next_task` - Get optimal task assignments
- `report_task_progress` - Update task status
- `report_blocker` - Get AI-powered help

### [Data Models API](./data_models_api.md)
Detailed documentation of all data structures used throughout the system.

**Core Models:**
- `Task` - Work item representation
- `WorkerStatus` - Agent state and capabilities
- `ProjectState` - Overall project health
- `TaskAssignment` - Task allocation records

**Enumerations:**
- `TaskStatus` - Task lifecycle states
- `Priority` - Urgency levels
- `RiskLevel` - Risk classifications

### [Kanban Providers API](./kanban_providers_api.md)
Integration guide for supported kanban board providers.

**Supported Providers:**
- Planka (self-hosted)
- GitHub Issues/Projects
- Trello
- Custom providers via plugin interface

**Key Features:**
- Unified interface across providers
- Provider-specific optimizations
- Authentication methods
- Performance characteristics

### [AI Analysis Engine API](./ai_analysis_engine_api.md)
Reference for the intelligent task management system powered by Claude AI.

**Core Capabilities:**
- Task instruction generation
- Blocker analysis and resolution
- Optimal task-worker matching
- Project health assessment
- Daily planning optimization

**Advanced Features:**
- Context-aware instructions
- Skill-based customization
- Fallback mechanisms
- Performance optimization

### [Workspace Isolation API](./workspace_isolation_api.md)
Security-focused workspace management for agent isolation.

**Security Features:**
- File system isolation
- Path validation and restrictions
- Resource limits
- Audit logging

**Management Operations:**
- Workspace creation with templates
- Access control lists
- Cleanup and rotation
- Monitoring integration

## Configuration References

### [Configuration Guide](./configuration_guide.md)
Comprehensive guide to all configuration options.

**Configuration Sections:**
- Core settings and intervals
- Risk thresholds and escalation
- Team and communication preferences
- AI model configuration
- Performance tuning

**Configuration Methods:**
- JSON configuration files
- Environment variable overrides
- Runtime parameters
- Default values and validation

### [Environment Variables](./environment_variables.md)
Complete reference for all supported environment variables.

**Variable Categories:**
- Required core variables
- Provider-specific settings
- Optional enhancements
- Development/debugging flags

**Best Practices:**
- Security considerations
- Platform-specific notes
- Docker and Kubernetes examples
- Troubleshooting guide

## Architecture References

### [System Architecture](./system_architecture.md)
Technical deep-dive into PM Agent's architecture.

**Architectural Components:**
- MCP Server implementation
- State management system
- Integration layer design
- Communication protocols

**Technical Details:**
- Data flow diagrams
- Protocol specifications
- Performance characteristics
- Scalability patterns

## Quick Reference Cards

### Common Operations

```python
# Register an agent
await mcp_client.call_tool("register_agent", {
    "agent_id": "dev-001",
    "name": "Developer",
    "role": "Backend Developer",
    "skills": ["Python", "Django"]
})

# Request a task
result = await mcp_client.call_tool("request_next_task", {
    "agent_id": "dev-001"
})

# Report progress
await mcp_client.call_tool("report_task_progress", {
    "agent_id": "dev-001",
    "task_id": "task-123",
    "status": "in_progress",
    "progress": 50
})
```

### Environment Setup

```bash
# Minimum required setup
export ANTHROPIC_API_KEY="sk-ant-..."
export KANBAN_PROVIDER="planka"
export PLANKA_SERVER_URL="http://localhost:3000"
export PLANKA_USERNAME="admin@example.com"
export PLANKA_PASSWORD="password"
```

### Error Codes Quick Reference

| Code | Meaning | Action |
|------|---------|--------|
| `AGENT_NOT_FOUND` | Agent not registered | Register agent first |
| `NO_TASKS_AVAILABLE` | No matching tasks | Wait and retry |
| `KANBAN_CONNECTION_ERROR` | Provider unreachable | Check credentials |
| `RATE_LIMITED` | API limit hit | Implement backoff |

## Best Practices

### API Usage
1. Always handle errors gracefully
2. Implement exponential backoff for retries
3. Cache responses when appropriate
4. Use batch operations where available

### Configuration
1. Use environment variables for secrets
2. Version control configuration files
3. Document all custom settings
4. Test configuration changes thoroughly

### Security
1. Never log sensitive information
2. Validate all file paths
3. Use minimal required permissions
4. Rotate API keys regularly

## Version Compatibility

| PM Agent Version | API Version | Breaking Changes |
|-----------------|-------------|------------------|
| 2.0.0 | 2.0.0 | Added workspace isolation |
| 1.5.0 | 1.5.0 | New provider interface |
| 1.0.0 | 1.0.0 | Initial release |

## Getting Help

### Documentation Search
Use the search function to find specific topics across all reference documentation.

### Common Issues
- [Troubleshooting Guide](/troubleshooting)
- [FAQ](/faq)
- [Community Forum](https://github.com/pm-agent/discussions)

### Contributing
Found an error or want to improve the documentation?
- [Documentation Guidelines](/contributing#documentation)
- [Submit an Issue](https://github.com/pm-agent/issues)
- [Pull Request Process](/contributing#pull-requests)

## Related Documentation

- [Getting Started Guide](/getting-started) - New user introduction
- [How-To Guides](/how-to) - Task-oriented guides
- [Tutorials](/tutorials) - Step-by-step learning
- [Conceptual Guides](/concepts) - Understanding PM Agent

---

*This reference documentation is automatically generated from source code and manually curated for accuracy. Last build: 2025-06-25*