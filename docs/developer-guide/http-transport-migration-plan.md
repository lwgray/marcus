# HTTP Transport Migration Plan for Marcus MCP

## Overview

This document outlines the plan to migrate Marcus from stdio transport to HTTP/Streamable HTTP transport to solve Claude interruption issues.

## Current MCP Tools Inventory

### Agent Management Tools (8 tools)
- `register_agent` - Register a new agent with the Marcus system
- `get_agent_status` - Get status and current assignment for an agent
- `list_registered_agents` - List all registered agents (human only)
- `request_next_task` - Request the next optimal task assignment
- `report_task_progress` - Report progress on a task
- `report_blocker` - Report a blocker on a task
- `get_project_status` - Get current project status and metrics
- `check_assignment_health` - Check assignment tracking health (human only)

### Board Health Tools (2 tools)
- `check_board_health` - Analyze overall board health
- `check_task_dependencies` - Check dependencies for a specific task

### System Tools (1 tool)
- `ping` - Check Marcus status with special commands (health/cleanup/reset)

### Context Tools (3 tools)
- `log_decision` - Log architectural decisions
- `get_task_context` - Get full context for a task
- `log_artifact` - Store artifacts with smart location management

### Project Management Tools (6 tools - human only)
- `list_projects` - List all available projects
- `switch_project` - Switch to a different project
- `get_current_project` - Get the currently active project
- `add_project` - Add a new project configuration
- `remove_project` - Remove a project from the registry
- `update_project` - Update project configuration

### Natural Language Tools (2 tools)
- `create_project` - Create complete project from natural language
- `add_feature` - Add feature to existing project

### Pipeline Enhancement Tools (13 tools - human only)
- `pipeline_replay_start` - Start replay session
- `pipeline_replay_forward` - Step forward in replay
- `pipeline_replay_backward` - Step backward in replay
- `pipeline_replay_jump` - Jump to specific position
- `what_if_start` - Start what-if analysis
- `what_if_simulate` - Simulate with modifications
- `what_if_compare` - Compare scenarios
- `pipeline_compare` - Compare multiple flows
- `pipeline_report` - Generate pipeline report
- `pipeline_monitor_dashboard` - Get live dashboard
- `pipeline_monitor_flow` - Track flow progress
- `pipeline_predict_risk` - Predict failure risk
- `pipeline_find_similar` - Find similar flows

**Total: 35 MCP tools**

## Migration Steps

### Phase 1: Infrastructure Setup

1. **Install FastMCP dependencies**
   - Ensure `mcp.server.fastmcp` is available
   - May need to update MCP SDK version

2. **Create HTTP server module**
   - New file: `src/marcus_mcp/http_server.py`
   - Convert existing server.py to use FastMCP
   - Add transport configuration options

3. **Update launch scripts**
   - Create `run_http_server.py` for HTTP mode
   - Keep existing stdio mode for backward compatibility
   - Add command-line argument to choose transport

### Phase 2: Code Migration

1. **Convert server initialization**
   ```python
   # From:
   async with stdio_server() as server:
       await server.run()

   # To:
   from mcp.server.fastmcp import FastMCP
   mcp = FastMCP("marcus")
   ```

2. **Migrate tool registrations**
   - Convert from `@server.list_tools()` to `@mcp.tool()`
   - Update tool handlers to FastMCP format
   - Ensure all 35 tools are properly registered

3. **Update state management**
   - FastMCP may handle state differently
   - Ensure MarcusServer state is accessible to tools
   - Consider session management for multi-client support

### Phase 3: Authentication & Security

1. **Add authentication layer**
   - Implement token verification
   - Add API key support
   - Configure CORS and security headers

2. **Session management**
   - Implement session tracking
   - Handle reconnections gracefully
   - Clean up orphaned sessions

### Phase 4: Configuration Updates

1. **Update Claude configuration**
   ```json
   {
     "mcpServers": {
       "marcus": {
         "url": "http://localhost:8080/mcp",
         "headers": {
           "Authorization": "Bearer ${MARCUS_API_KEY}"
         }
       }
     }
   }
   ```

2. **Update documentation**
   - Installation instructions
   - Configuration guide
   - Migration guide for existing users

### Phase 5: Testing & Validation

1. **Test all 35 tools**
   - Verify each tool works over HTTP
   - Test interruption recovery
   - Validate session persistence

2. **Performance testing**
   - Compare stdio vs HTTP performance
   - Test with multiple concurrent clients
   - Verify resource usage

3. **Integration testing**
   - Test with Claude Code
   - Verify authentication works
   - Test error handling

## Files to Modify

1. **Core server files:**
   - `/src/marcus_mcp/server.py` - Main server implementation
   - `/src/marcus_mcp/__main__.py` - Entry point
   - `/src/marcus_mcp/handlers.py` - Tool handlers

2. **New files to create:**
   - `/src/marcus_mcp/http_server.py` - HTTP server implementation
   - `/src/marcus_mcp/auth.py` - Authentication middleware
   - `/run_http_server.py` - HTTP server launcher

3. **Configuration files:**
   - `/pyproject.toml` - Add FastMCP dependencies
   - `/docs/user-guide/configuration.md` - Update docs

4. **Test files:**
   - Create HTTP transport tests
   - Update existing tests for dual transport

## Risk Mitigation

1. **Backward compatibility**
   - Keep stdio transport as default initially
   - Allow users to choose transport mode
   - Provide migration period

2. **Rollback plan**
   - Feature branch allows easy revert
   - Empty commit marks stable state
   - Keep stdio code intact during migration

3. **Gradual rollout**
   - Test with small group first
   - Monitor for issues
   - Full rollout after validation

## Success Criteria

1. All 35 MCP tools work over HTTP transport
2. Claude interruptions don't break connections
3. Sessions persist across reconnections
4. Authentication prevents unauthorized access
5. Performance is acceptable (< 10% overhead vs stdio)
6. Documentation is complete and accurate

## MCP Client Connections Strategy

### Current MCP Client Dependencies

1. **Planka (kanban-mcp)**
   - Uses stdio transport via `KanbanClient`
   - Located in: `src/integrations/kanban_client.py`
   - Critical for task management

2. **GitHub (github-mcp)**
   - Accessed through `GitHubMCPInterface`
   - Located in: `src/integrations/github_mcp_interface.py`
   - Used for code analysis and PR integration

3. **Seneca (deployment companion)**
   - Marcus's deployment and infrastructure management tool
   - Identified through ping commands

### Hybrid Transport Architecture

Marcus will operate with dual transport modes:

1. **Server Mode (HTTP)**
   - Marcus serves MCP tools over HTTP to Claude/other clients
   - Benefits: Session persistence, reconnection support
   - Solves the interruption problem

2. **Client Mode (stdio)**
   - Marcus connects to other MCP servers using stdio
   - Maintains compatibility with existing MCP ecosystem
   - No changes needed to kanban-mcp, github-mcp

### Implementation Details

```python
# Marcus server (HTTP mode)
fastmcp = FastMCP("marcus")
# Serves tools over HTTP

# Marcus as client (stdio mode)
from mcp.client.stdio import stdio_client
# Connects to kanban-mcp, github-mcp via stdio
```

### No Changes Required

The beautiful part: **No changes needed to client connections!**

- `KanbanClient` continues using stdio to connect to kanban-mcp
- `GitHubMCPInterface` continues using stdio to connect to github-mcp
- Worker clients can choose HTTP or stdio to connect to Marcus

The transport used by Marcus as a server is completely independent from the transport it uses as a client.

### Configuration

```json
{
  "transport": {
    "type": "http",  // How Marcus serves
    "http": { ... }
  },
  "mcp_clients": {
    "kanban": {
      "transport": "stdio"  // How Marcus connects to kanban-mcp
    },
    "github": {
      "transport": "stdio"  // How Marcus connects to github-mcp
    }
  }
}
```

## Timeline Estimate

- Phase 1: 2-3 hours (infrastructure setup)
- Phase 2: 4-6 hours (code migration)
- Phase 3: 2-3 hours (auth & security)
- Phase 4: 1-2 hours (configuration)
- Phase 5: 3-4 hours (testing)

**Total: 12-18 hours of development**
