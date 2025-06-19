# 📝 PM Agent Architecture Decision Log

## Overview
This document tracks major architectural decisions and changes made to PM Agent.

## Decision Record

### 2024-01-18: Multi-Provider Kanban Support

**Context**: Originally PM Agent only supported Planka. Users requested support for other kanban systems.

**Decision**: Implement provider abstraction layer supporting GitHub, Linear, and Planka.

**Implementation**:
- Created `KanbanInterface` abstract base class
- Implemented providers: `GitHubKanban`, `LinearKanban`, `PlankaKanban`
- Added `KanbanFactory` for provider selection
- Environment variable `KANBAN_PROVIDER` selects provider

**Rationale**:
- GitHub: Free, API-rich, includes code awareness
- Linear: Professional features, good API
- Planka: Self-hosted option (with licensing caveats)

### 2024-01-18: GitHub Code Awareness Feature

**Context**: Workers completing tasks in isolation couldn't see what APIs/models other workers created.

**Decision**: Add code analysis for GitHub provider to extract implementation details.

**Implementation**:
- Created `CodeAnalyzer` component
- Enhanced `AIAnalysisEngine` to include previous implementations
- Updated worker prompts to emphasize documentation

**Benefits**:
- Workers can see previous API endpoints, models, schemas
- Reduces integration conflicts
- Improves code consistency

### 2024-01-18: MCP Server v2 with Correct Tool Registration

**Context**: Original MCP server used deprecated `@server.tool()` decorator pattern.

**Decision**: Rewrite MCP server using current MCP protocol patterns.

**Implementation**:
- Created `pm_agent_mcp_server_v2.py`
- Uses `@server.list_tools()` and `@server.call_tool()` handlers
- Maintains backward compatibility

**Files**:
- Old: `pm_agent_mvp_fixed.py` (deprecated)
- New: `pm_agent_mcp_server_v2.py` (current)

### 2024-01-18: Remote MCP Access via SSE

**Context**: Need for remote PM Agent access while addressing Planka licensing concerns.

**Decision**: Implement SSE (Server-Sent Events) transport for remote MCP access.

**Implementation**:
- Created `pm_agent_sse_server.py` with FastAPI
- Added authentication via bearer tokens
- Separate `docker-compose.remote.yml` without Planka

**Security**:
- Bearer token authentication
- No Planka in remote deployments
- SSL/TLS recommended for production

### 2024-01-18: Planka Licensing Restrictions

**Context**: Planka uses AGPL license which has strict requirements for network services.

**Decision**: Restrict Planka to local use only, promote GitHub/Linear for remote.

**Implementation**:
- Planka hidden behind Docker profile `local-planka`
- Clear warnings in start script
- Separate remote deployment config
- Comprehensive licensing documentation

**Documentation**:
- `LICENSING.md` - Full licensing explanation
- `DEPLOYMENT_GUIDE.md` - Decision tree for providers
- Updated README with licensing notes

### 2024-01-18: Docker-First Deployment Strategy

**Context**: Complex dependencies and MCP server requirements made setup difficult.

**Decision**: Provide Docker as primary deployment method.

**Implementation**:
- Updated `docker-compose.yml` with profiles
- Created `start.sh` convenience script
- Multiple deployment modes (basic, demo, full, remote)
- Environment-based configuration

**Benefits**:
- 30-second setup time
- No dependency management
- Consistent environments
- Easy provider switching

## Future Decisions Needed

1. **Provider Data Migration**: How to move tasks between providers?
2. **Multi-Provider Support**: Should PM Agent support multiple providers simultaneously?
3. **Authentication Strategy**: OAuth vs API keys for remote access?
4. **Visualization Architecture**: Should it be part of core or separate service?

## Decision-Making Principles

1. **Simplicity First**: Easy setup and usage over complex features
2. **License Compliance**: Respect all licenses, protect users from violations
3. **Provider Agnostic**: Core PM Agent shouldn't depend on specific provider
4. **Security by Default**: Secure configurations out of the box
5. **Documentation Driven**: Document decisions and changes clearly