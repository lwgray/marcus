#!/usr/bin/env python3
"""
Quick test script to verify Marcus HTTP transport is working
"""

import asyncio
import aiohttp
import json
import uuid


async def test_marcus_http():
    """Test basic MCP over HTTP functionality"""
    # Marcus is trying to use port 8080 but it's in use
    # Let's test if it's actually running somewhere else
    
    print("Testing Marcus HTTP Transport")
    print("=" * 50)
    
    # First, let's check if port 3000 is available (common alternative)
    base_url = "http://127.0.0.1:3000"
    
    # Create a simple HTTP request to test the MCP endpoint
    request_data = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "ping",
            "arguments": {"echo": "test_http_transport"}
        },
        "id": str(uuid.uuid4())
    }
    
    timeout = aiohttp.ClientTimeout(total=10)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for port in [3000, 8081, 8082, 9000]:  # Try different ports
            url = f"http://127.0.0.1:{port}/mcp"
            print(f"\nTrying {url}...")
            
            try:
                async with session.post(
                    url,
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"✅ Success on port {port}!")
                        print(f"Response: {json.dumps(result, indent=2)}")
                        
                        # If successful, try another tool
                        request_data["params"]["name"] = "get_project_status"
                        request_data["params"]["arguments"] = {}
                        request_data["id"] = str(uuid.uuid4())
                        
                        async with session.post(url, json=request_data) as resp2:
                            if resp2.status == 200:
                                result2 = await resp2.json()
                                print(f"\nProject Status Response: {json.dumps(result2, indent=2)}")
                        
                        return True
                    else:
                        print(f"❌ Port {port} returned status {response.status}")
                        
            except aiohttp.ClientConnectorError:
                print(f"❌ Port {port} - Connection refused")
            except Exception as e:
                print(f"❌ Port {port} - Error: {e}")
    
    print("\n❌ Could not connect to Marcus HTTP server on any tested port")
    print("\nTo start Marcus on a different port, use:")
    print("  python run_marcus.py --http --port 3000")
    return False


async def test_streamable_http():
    """Test streamable HTTP (SSE) connection"""
    print("\n\nTesting Streamable HTTP (SSE) Connection")
    print("=" * 50)
    
    # SSE endpoint might be different
    for port in [3000, 8081, 8082, 9000]:
        url = f"http://127.0.0.1:{port}/sse"
        print(f"\nTrying SSE at {url}...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={"Accept": "text/event-stream"}) as response:
                    if response.status == 200:
                        print(f"✅ SSE endpoint found on port {port}")
                        # Read first few events
                        async for data in response.content.iter_any():
                            print(f"SSE Data: {data.decode('utf-8')[:100]}...")
                            break
                        return True
        except Exception as e:
            print(f"❌ Port {port} - {type(e).__name__}")
    
    return False


if __name__ == "__main__":
    asyncio.run(test_marcus_http())
    # asyncio.run(test_streamable_http())