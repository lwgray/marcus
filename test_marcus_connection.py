#!/usr/bin/env python3
"""
Test connection to Marcus MCP server and demonstrate autonomous agent workflow
"""
import json
import asyncio
import httpx
from datetime import datetime

# Marcus agent endpoints
AGENT_ENDPOINT = "http://localhost:4299"

async def test_marcus_tools():
    """Test Marcus MCP tools via HTTP"""
    
    print("🔍 Testing Marcus MCP connection...")
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            # First, initialize the MCP session
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "roots": {
                            "listChanged": True
                        },
                        "sampling": {}
                    },
                    "clientInfo": {
                        "name": "claude-autonomous-worker",
                        "version": "1.0.0"
                    }
                }
            }
            
            print(f"Initializing MCP session at {AGENT_ENDPOINT}/mcp")
            response = await client.post(
                f"{AGENT_ENDPOINT}/mcp",
                json=init_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                },
                timeout=10.0
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            # Extract session ID from headers
            session_id = response.headers.get("mcp-session-id")
            if session_id:
                print(f"Got session ID: {session_id}")
            
            if response.status_code == 200:
                # Handle streaming response (Server-Sent Events)
                if response.headers.get('content-type') == 'text/event-stream':
                    print("Handling streaming response...")
                    response_text = response.text
                    print(f"Raw response: {response_text[:500]}...")
                    
                    # Parse SSE format
                    lines = response_text.split('\n')
                    for line in lines:
                        if line.startswith('data: ') and line != 'data: ':
                            data_str = line[6:]  # Remove 'data: ' prefix
                            try:
                                data = json.loads(data_str)
                                print(f"✅ MCP initialization response: {json.dumps(data, indent=2)}")
                                break
                            except json.JSONDecodeError:
                                continue
                else:
                    data = response.json()
                    print(f"✅ MCP initialization response: {json.dumps(data, indent=2)}")
                
                # Send initialization complete notification
                await send_initialized_notification(client, session_id)
                
                # Now request tools list
                await test_tools_list(client, session_id)
            elif session_id:
                # Try with session ID
                print("Trying initialization with session ID...")
                response = await client.post(
                    f"{AGENT_ENDPOINT}/mcp",
                    json=init_request,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream",
                        "mcp-session-id": session_id
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ MCP initialization response: {json.dumps(data, indent=2)}")
                    
                    # Send initialization complete notification
                    await send_initialized_notification(client, session_id)
                    
                    # Now request tools list
                    await test_tools_list(client, session_id)
                else:
                    print(f"❌ MCP initialization failed: {response.status_code}")
                    print(f"Response: {response.text}")
            else:
                print(f"❌ MCP initialization failed: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Connection error: {e}")

async def send_initialized_notification(client, session_id):
    """Send initialized notification to complete MCP handshake"""
    print("\n📢 Sending initialized notification...")
    
    initialized_request = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {}
    }
    
    try:
        response = await client.post(
            f"{AGENT_ENDPOINT}/mcp",
            json=initialized_request,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "mcp-session-id": session_id
            },
            timeout=10.0
        )
        
        print(f"Initialized notification status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Initialized notification error: {e}")

async def test_tools_list(client, session_id):
    """Test getting tools list"""
    print("\n🔧 Testing tools list...")
    
    tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    try:
        response = await client.post(
            f"{AGENT_ENDPOINT}/mcp",
            json=tools_request,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "mcp-session-id": session_id
            },
            timeout=10.0
        )
        
        if response.status_code == 200:
            # Handle streaming response
            if response.headers.get('content-type') == 'text/event-stream':
                response_text = response.text
                lines = response_text.split('\n')
                for line in lines:
                    if line.startswith('data: ') and line != 'data: ':
                        data_str = line[6:]
                        try:
                            data = json.loads(data_str)
                            print(f"✅ Tools list response: {json.dumps(data, indent=2)}")
                            
                            # If we got tools, try to register as an agent
                            if "result" in data and "tools" in data["result"]:
                                await test_register_agent(client, session_id)
                            break
                        except json.JSONDecodeError:
                            continue
            else:
                data = response.json()
                print(f"✅ Tools list response: {json.dumps(data, indent=2)}")
                
                # If we got tools, try to register as an agent
                if "result" in data and "tools" in data["result"]:
                    await test_register_agent(client, session_id)
        else:
            print(f"❌ Tools list failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Tools list error: {e}")

async def test_register_agent(client, session_id):
    """Test registering as an agent"""
    print("\n🤖 Testing agent registration...")
    
    register_request = {
        "jsonrpc": "2.0",
        "id": 3, 
        "method": "tools/call",
        "params": {
            "name": "register_agent",
            "arguments": {
                "agent_id": "claude-autonomous-worker-001",
                "name": "claude-autonomous-worker",
                "role": "developer",
                "skills": [
                    "python_development",
                    "test_driven_development", 
                    "code_analysis",
                    "documentation"
                ]
            }
        }
    }
    
    try:
        response = await client.post(
            f"{AGENT_ENDPOINT}/mcp",
            json=register_request,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "mcp-session-id": session_id
            },
            timeout=10.0
        )
        
        if response.status_code == 200:
            # Handle streaming response
            if response.headers.get('content-type') == 'text/event-stream':
                response_text = response.text
                lines = response_text.split('\n')
                for line in lines:
                    if line.startswith('data: ') and line != 'data: ':
                        data_str = line[6:]
                        try:
                            data = json.loads(data_str)
                            print(f"✅ Agent registration response: {json.dumps(data, indent=2)}")
                            break
                        except json.JSONDecodeError:
                            continue
            else:
                data = response.json()
                print(f"✅ Agent registration response: {json.dumps(data, indent=2)}")
            
            # Try to get next task
            await test_request_task(client, session_id)
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Registration error: {e}")

async def test_request_task(client, session_id):
    """Test requesting a task"""
    print("\n📋 Testing task request...")
    
    task_request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call", 
        "params": {
            "name": "request_next_task",
            "arguments": {
                "agent_id": "claude-autonomous-worker-001"
            }
        }
    }
    
    try:
        response = await client.post(
            f"{AGENT_ENDPOINT}/mcp",
            json=task_request,
            headers={
                "Content-Type": "application/json", 
                "Accept": "application/json, text/event-stream",
                "mcp-session-id": session_id
            },
            timeout=10.0
        )
        
        if response.status_code == 200:
            # Handle streaming response
            if response.headers.get('content-type') == 'text/event-stream':
                response_text = response.text
                lines = response_text.split('\n')
                for line in lines:
                    if line.startswith('data: ') and line != 'data: ':
                        data_str = line[6:]
                        try:
                            data = json.loads(data_str)
                            print(f"✅ Task request response: {json.dumps(data, indent=2)}")
                            break
                        except json.JSONDecodeError:
                            continue
            else:
                data = response.json()
                print(f"✅ Task request response: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ Task request failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Task request error: {e}")

if __name__ == "__main__":
    asyncio.run(test_marcus_tools())