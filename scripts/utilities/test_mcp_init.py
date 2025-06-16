#!/usr/bin/env python3
"""
Test MCP initialization
"""

import json
import subprocess
import sys

# Test initialization message
init_msg = {
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "roots": {}
        },
        "clientInfo": {
            "name": "test-client",
            "version": "1.0.0"
        }
    },
    "id": 1
}

# Start PM Agent
cmd = [
    "/Users/lwgray/opt/anaconda3/envs/pm-agent/bin/python",
    "-m", "src.pm_agent_mvp_fixed"
]

proc = subprocess.Popen(
    cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd="/Users/lwgray/dev/pm-agent",
    env={
        "PYTHONPATH": "/Users/lwgray/dev/pm-agent",
        "PLANKA_BASE_URL": "http://localhost:3333",
        "PLANKA_AGENT_EMAIL": "demo@demo.demo",
        "PLANKA_AGENT_PASSWORD": "demo"
    }
)

# Send initialization
try:
    proc.stdin.write((json.dumps(init_msg) + "\n").encode())
    proc.stdin.flush()
    
    # Read response
    response = proc.stdout.readline()
    if response:
        print("Response:", response.decode())
    else:
        print("No response received")
    
    # Check stderr
    stderr = proc.stderr.read(1024)
    if stderr:
        print("Stderr:", stderr.decode())
        
except Exception as e:
    print(f"Error: {e}")
finally:
    proc.terminate()