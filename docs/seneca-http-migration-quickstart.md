# Seneca HTTP Migration Quick Start Guide

## Current Status

Marcus is now running with HTTP transport support on port 8080 (conflicting with Seneca). Here's how to complete the migration:

## Step 1: Update Marcus Configuration

Since port 8080 is already used by Seneca, update Marcus to use a different port. In `config_marcus.json`:

```json
"transport": {
  "type": "http",
  "http": {
    "host": "127.0.0.1",
    "port": 3000,
    "path": "/mcp",
    "log_level": "info"
  }
}
```

Then restart Marcus:
```bash
python run_marcus.py --http
```

## Step 2: Quick Test

Use the provided test script to verify HTTP connectivity:

```bash
python test_http_transport.py
```

## Step 3: Minimal Seneca Update

Create a new file `src/mcp_client/marcus_http_client.py` with the minimal implementation:

```python
import aiohttp
import json
import uuid
from typing import Dict, Any, Optional

class MarcusHttpClient:
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url
        self.session = None
        self.connected = False

    async def connect(self, auto_discover: bool = True) -> bool:
        try:
            self.session = aiohttp.ClientSession()
            result = await self.ping()
            self.connected = True
            return True
        except:
            return False

    async def disconnect(self):
        if self.session:
            await self.session.close()
        self.connected = False

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            },
            "id": str(uuid.uuid4())
        }

        async with self.session.post(f"{self.base_url}/mcp", json=request_data) as response:
            result = await response.json()
            if "error" in result:
                return {"error": result["error"]["message"]}

            content = result.get("result", {}).get("content", [])
            if content:
                return json.loads(content[0].get("text", "{}"))
            return {}

    # Copy all convenience methods from original MarcusClient
    async def ping(self) -> Dict[str, Any]:
        return await self.call_tool("ping", {"echo": "seneca_http_client"})

    async def get_project_status(self) -> Dict[str, Any]:
        return await self.call_tool("get_project_status")

    # ... etc
```

## Step 4: Update Seneca Server

Minimal change in `src/seneca_server.py`:

```python
# At the top, add transport detection
import os

# In connect_to_marcus function:
async def connect_to_marcus():
    # Check for HTTP transport preference
    use_http = os.getenv("MARCUS_TRANSPORT", "stdio") == "http"
    http_url = os.getenv("MARCUS_HTTP_URL", "http://localhost:3000")

    if use_http:
        from mcp_client.marcus_http_client import MarcusHttpClient
        global marcus_client
        marcus_client = MarcusHttpClient(http_url)
        success = await marcus_client.connect()
    else:
        # Existing stdio code
        if marcus_server:
            marcus_client.server_path = marcus_server
            success = await marcus_client.connect(auto_discover=False)
        else:
            success = await marcus_client.connect(auto_discover=True)

    # Rest remains the same
```

## Step 5: Test the Migration

1. Start Marcus with HTTP:
   ```bash
   # Update config_marcus.json to use port 3000
   python run_marcus.py --http
   ```

2. Start Seneca with HTTP transport:
   ```bash
   export MARCUS_TRANSPORT=http
   export MARCUS_HTTP_URL=http://localhost:3000
   python start_seneca.py
   ```

3. Verify in browser:
   - Seneca dashboard: http://localhost:8000
   - Check connection status
   - Test agent operations

## Step 6: Production Deployment

For production, use environment variables:

```bash
# .env or system environment
MARCUS_TRANSPORT=http
MARCUS_HTTP_URL=https://marcus.yourcompany.com/mcp
MARCUS_HTTP_TIMEOUT=30
MARCUS_HTTP_RETRY_COUNT=3
```

## Benefits Realized

1. **Multiple Seneca Instances**: Can now run multiple Seneca frontends
2. **Remote Access**: Marcus and Seneca can run on different machines
3. **Load Balancing**: Can put a load balancer in front of Marcus
4. **Better Monitoring**: Standard HTTP metrics and logging
5. **Security**: Can use HTTPS, API keys, OAuth, etc.

## Rollback Plan

If issues arise, simply change the environment variable:
```bash
export MARCUS_TRANSPORT=stdio
# Restart Seneca
```

The stdio transport remains fully functional.

## Next Steps

1. Add authentication headers
2. Implement connection pooling
3. Add circuit breaker pattern
4. Set up monitoring/alerting
5. Deploy behind reverse proxy

## Testing Checklist

- [ ] Marcus starts on port 3000 with HTTP
- [ ] Test script confirms HTTP connectivity
- [ ] Seneca connects via HTTP
- [ ] All MCP tools work (ping, get_project_status, etc.)
- [ ] WebSocket updates still function
- [ ] No performance degradation
- [ ] Error handling works correctly

This minimal approach allows you to test HTTP transport with minimal code changes while maintaining full backward compatibility.
