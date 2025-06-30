#!/usr/bin/env python3
"""
Simple test to check Marcus MCP server directly
"""

import subprocess
import json
import time

def test_marcus_mcp():
    """Test Marcus MCP server using npx inspector"""
    
    print("🏛️ Testing Marcus MCP Server")
    print("=" * 50)
    
    # Kill any existing Marcus processes
    print("\n🔄 Cleaning up existing processes...")
    subprocess.run(["pkill", "-f", "marcus.py"], stderr=subprocess.DEVNULL)
    time.sleep(1)
    
    # Test each tool
    tools = [
        ("ping", {}),
        ("get_project_status", {}),
        ("list_registered_agents", {})
    ]
    
    for tool_name, args in tools:
        print(f"\n📡 Testing {tool_name}...")
        
        # Run the MCP command
        cmd = [
            "npx", "-y", "@modelcontextprotocol/inspector@latest",
            "./marcus.py",
            tool_name
        ]
        
        if args:
            cmd.extend(["--args", json.dumps(args)])
        
        try:
            # Run with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/Users/lwgray/dev/marcus"
            )
            
            # Parse output
            if result.returncode == 0:
                output = result.stdout
                # Try to find JSON in output
                lines = output.strip().split('\n')
                for line in reversed(lines):
                    if line.strip().startswith('{'):
                        try:
                            data = json.loads(line)
                            if data.get('success'):
                                print(f"✅ {tool_name} successful!")
                                if tool_name == "get_project_status":
                                    proj = data.get('project', {})
                                    print(f"   Total tasks: {proj.get('total_tasks', 0)}")
                                    print(f"   Provider: {data.get('provider', 'unknown')}")
                            else:
                                print(f"❌ {tool_name} failed: {data.get('error', 'Unknown error')}")
                            break
                        except json.JSONDecodeError:
                            continue
                else:
                    print(f"⚠️ {tool_name} - Could not parse response")
                    if "Not initialized" in output:
                        print("   Error: Server not initialized properly")
            else:
                print(f"❌ {tool_name} failed with code {result.returncode}")
                if result.stderr:
                    print(f"   Error: {result.stderr}")
                    
        except subprocess.TimeoutExpired:
            print(f"⏱️ {tool_name} timed out after 30 seconds")
        except Exception as e:
            print(f"❌ {tool_name} error: {e}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_marcus_mcp()