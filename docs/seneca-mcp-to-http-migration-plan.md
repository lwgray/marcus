# Seneca MCP to HTTP Transport Migration Plan

## Executive Summary

This document provides a comprehensive analysis of Seneca's current MCP connection to Marcus and a detailed migration plan to move from stdio transport to HTTP transport.

## Current Architecture Analysis

### 1. Connection Method
- **Transport**: stdio (standard input/output)
- **Protocol**: MCP (Model Context Protocol)
- **Client**: `mcp` Python package with `stdio_client`
- **Server Discovery**: Auto-discovery via `.marcus/services/marcus_*.json` files

### 2. Main Components

#### MCP Client (`src/mcp_client/marcus_client.py`)
- **Class**: `MarcusClient`
- **Connection**: Uses `StdioServerParameters` and `stdio_client` from MCP package
- **Session Management**: Maintains `ClientSession` for tool calls
- **Auto-discovery**: Scans for running Marcus instances via service registry files

#### Entry Points
1. **CLI**: `seneca_cli.py` - Command-line interface
2. **Server**: `src/seneca_server.py` - Main Flask application
3. **Startup**: `start_seneca.py` - Server launcher

#### API Integration
- **Location**: `src/api/` directory
- **Key APIs**:
  - `agent_management_api.py` - Agent operations
  - `conversation_api.py` - Conversation data (log-based)
  - `project_management_api.py` - Project management
  - `websocket` support for real-time updates

### 3. MCP Tools Used from Marcus

The following Marcus MCP tools are actively used by Seneca:

1. **`ping`** - Connection health check and identification
2. **`get_project_status`** - Retrieve current project state
3. **`list_registered_agents`** - Get all registered agents
4. **`get_agent_status`** - Individual agent status
5. **`get_conversations`** - Conversation history (appears unused in favor of log reading)
6. **`register_agent`** - Register new agents
7. **`request_next_task`** - Task assignment
8. **`report_task_progress`** - Progress updates
9. **`report_blocker`** - Blocker reporting
10. **`create_project`** - Project creation

### 4. Data Flow

1. **Real-time Data**: MCP tools → Marcus → Seneca
2. **Historical Data**: Direct log file reading from `MARCUS_LOG_DIR`
3. **WebSocket**: Flask-SocketIO for UI updates

## Migration Strategy

### Phase 1: Parallel Implementation (Recommended)

#### 1.1 Create HTTP Client Adapter
```python
# src/mcp_client/marcus_http_client.py
class MarcusHttpClient:
    """HTTP-based client for Marcus MCP server"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or self._discover_http_endpoint()
        self.session = aiohttp.ClientSession()

    async def call_tool(self, tool_name: str, arguments: Dict = None):
        """Call Marcus tool via HTTP"""
        # Implementation details below
```

#### 1.2 Implement Transport Abstraction
```python
# src/mcp_client/marcus_client_factory.py
class MarcusClientFactory:
    @staticmethod
    def create_client(transport: str = "auto"):
        if transport == "http":
            return MarcusHttpClient()
        elif transport == "stdio":
            return MarcusClient()
        else:  # auto
            # Try HTTP first, fallback to stdio
```

### Phase 2: HTTP Client Implementation

#### 2.1 Core Components Needed

1. **HTTP Session Management**
   - Use `aiohttp` for async HTTP calls
   - Implement connection pooling
   - Handle authentication if required

2. **Request/Response Format**
   ```python
   # Standard MCP over HTTP format
   {
       "jsonrpc": "2.0",
       "method": "tools/call",
       "params": {
           "name": "tool_name",
           "arguments": {...}
       },
       "id": "unique-request-id"
   }
   ```

3. **Service Discovery Enhancement**
   - Update discovery to include HTTP endpoints
   - Read `http_endpoint` from service registry files

#### 2.2 Implementation Details

```python
async def call_tool(self, tool_name: str, arguments: Dict = None):
    """Call MCP tool via HTTP"""
    request_data = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments or {}
        },
        "id": str(uuid.uuid4())
    }

    async with self.session.post(
        f"{self.base_url}/mcp",
        json=request_data,
        headers={"Content-Type": "application/json"}
    ) as response:
        result = await response.json()

        if "error" in result:
            raise MCPError(result["error"])

        return result["result"]["content"][0]["text"]
```

### Phase 3: Migration Steps

#### 3.1 Update Configuration
```python
# config.py additions
self.marcus_transport = self._get_config('MARCUS_TRANSPORT', default='auto')
self.marcus_http_url = self._get_config('MARCUS_HTTP_URL', default=None)
```

#### 3.2 Modify Server Initialization
```python
# seneca_server.py
async def connect_to_marcus():
    transport = config.marcus_transport

    if transport == "http" or (transport == "auto" and config.marcus_http_url):
        marcus_client = MarcusHttpClient(config.marcus_http_url)
    else:
        marcus_client = MarcusClient(marcus_server)

    # Rest remains the same
```

#### 3.3 Update API Endpoints
- No changes needed - APIs use the abstract client interface
- Ensure all `await marcus_client.call_tool()` calls work with both transports

### Phase 4: Testing Strategy

#### 4.1 Unit Tests
```python
# tests/test_marcus_http_client.py
class TestMarcusHttpClient:
    async def test_call_tool(self, mock_aiohttp):
        client = MarcusHttpClient("http://localhost:8080")
        result = await client.call_tool("ping", {"echo": "test"})
        assert result["echo"] == "test"
```

#### 4.2 Integration Tests
1. Test both transports in parallel
2. Verify feature parity
3. Performance comparison
4. Error handling validation

#### 4.3 Migration Testing
1. Start with HTTP in development
2. Run parallel tests with both transports
3. Monitor for discrepancies
4. Gradual rollout by environment

### Phase 5: Deployment Plan

#### 5.1 Environment Variables
```bash
# Development - test HTTP
export MARCUS_TRANSPORT=http
export MARCUS_HTTP_URL=http://localhost:3000/mcp

# Staging - auto with HTTP preference
export MARCUS_TRANSPORT=auto

# Production - gradual rollout
export MARCUS_TRANSPORT=stdio  # Initially
# Then switch to auto/http after validation
```

#### 5.2 Rollback Strategy
1. Keep stdio implementation intact
2. Use feature flags for transport selection
3. Monitor error rates and performance
4. Quick revert via environment variable

### Phase 6: Cleanup (Post-Migration)

1. Remove stdio-specific code
2. Update documentation
3. Remove MCP stdio dependencies
4. Simplify client to HTTP-only

## Benefits of HTTP Transport

1. **Scalability**: Multiple Seneca instances can connect to one Marcus
2. **Network Flexibility**: Cross-machine communication
3. **Load Balancing**: Can use standard HTTP load balancers
4. **Monitoring**: Standard HTTP metrics and logging
5. **Security**: HTTPS, authentication headers, API keys
6. **Simplicity**: No process management, standard HTTP clients

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance degradation | Medium | Benchmark both transports, optimize HTTP client |
| Network failures | High | Implement retries, circuit breakers |
| Compatibility issues | Medium | Extensive testing, gradual rollout |
| Security concerns | High | Use HTTPS, implement authentication |

## Timeline Estimate

- **Phase 1-2**: 1 week - Implement HTTP client
- **Phase 3**: 3 days - Integration and configuration
- **Phase 4**: 1 week - Testing and validation
- **Phase 5**: 2 weeks - Gradual deployment
- **Phase 6**: 3 days - Cleanup

**Total**: ~4-5 weeks for complete migration

## Conclusion

The migration from stdio to HTTP transport is straightforward due to Seneca's well-architected client abstraction. The parallel implementation approach minimizes risk while allowing thorough testing. The benefits of HTTP transport significantly outweigh the migration effort, especially for production deployments requiring scalability and network flexibility.
