#!/usr/bin/env python3
"""
Test script to verify Marcus MCP server is working properly
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

async def test_mcp_server():
    """Test the Marcus MCP server using stdio"""
    
    print("🔍 Testing Marcus MCP Server...")
    
    # Start the MCP server as a subprocess
    server_path = Path(__file__).parent / "src" / "marcus_mcp" / "server.py"
    
    try:
        # Start server process
        process = subprocess.Popen(
            [sys.executable, str(server_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=Path(__file__).parent
        )
        
        print("✅ Server process started")
        
        # Test initialization request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        print("📤 Sending initialization request...")
        process.stdin.write(json.dumps(init_request) + '\n')
        process.stdin.flush()
        
        # Wait for response
        start_time = time.time()
        while time.time() - start_time < 10:  # 10 second timeout
            if process.poll() is not None:
                # Process has terminated
                stderr = process.stderr.read()
                print(f"❌ Server terminated unexpectedly: {stderr}")
                return False
                
            try:
                # Try to read a line
                response = process.stdout.readline()
                if response:
                    print(f"📥 Response: {response.strip()}")
                    
                    try:
                        parsed = json.loads(response)
                        if parsed.get("id") == 1:
                            print("✅ Initialization successful!")
                            
                            # Test tools/list request
                            tools_request = {
                                "jsonrpc": "2.0",
                                "id": 2,
                                "method": "tools/list",
                                "params": {}
                            }
                            
                            print("📤 Sending tools/list request...")
                            process.stdin.write(json.dumps(tools_request) + '\n')
                            process.stdin.flush()
                            
                            # Read tools response
                            tools_response = process.stdout.readline()
                            if tools_response:
                                print(f"📥 Tools response: {tools_response.strip()}")
                                tools_parsed = json.loads(tools_response)
                                if "result" in tools_parsed:
                                    tools = tools_parsed["result"]["tools"]
                                    print(f"✅ Found {len(tools)} tools available")
                                    for tool in tools[:3]:  # Show first 3 tools
                                        print(f"   - {tool['name']}: {tool.get('description', 'No description')}")
                                    return True
                            break
                    except json.JSONDecodeError:
                        continue
                        
            except:
                time.sleep(0.1)
                continue
        
        print("❌ Timeout waiting for server response")
        return False
        
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        return False
        
    finally:
        # Clean up
        if 'process' in locals():
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass

if __name__ == "__main__":
    success = asyncio.run(test_mcp_server())
    if success:
        print("\n🎉 Marcus MCP Server test PASSED!")
        print("The server should work with Claude Desktop.")
    else:
        print("\n💥 Marcus MCP Server test FAILED!")
        print("There may be issues with the server configuration.")
    
    sys.exit(0 if success else 1)