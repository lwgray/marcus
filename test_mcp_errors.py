#!/usr/bin/env python3
"""Test Marcus MCP tools and capture exact errors"""

import subprocess
import json
import sys

def run_mcp_command(tool_name, params=None):
    """Run an MCP tool command and return the result"""
    cmd = ["npx", "@modelcontextprotocol/cli", "call", 
           "/Users/lwgray/dev/marcus/marcus_mcp.py", 
           tool_name]
    
    if params:
        cmd.extend(["--params", json.dumps(params)])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        return {
            "error": "Command failed",
            "stdout": e.stdout,
            "stderr": e.stderr,
            "returncode": e.returncode
        }
    except json.JSONDecodeError as e:
        return {
            "error": "JSON decode error",
            "raw_output": result.stdout if 'result' in locals() else None,
            "exception": str(e)
        }

def main():
    print("Testing Marcus MCP Tools - Capturing Exact Errors\n")
    print("=" * 60)
    
    # Test 1: request_next_task with existing agent
    print("\n1. Testing request_next_task:")
    print("-" * 40)
    result = run_mcp_command("request_next_task", {"agent_id": "test-agent-001"})
    print("Result:", json.dumps(result, indent=2))
    
    # Test 2: get_project_status
    print("\n2. Testing get_project_status:")
    print("-" * 40)
    result = run_mcp_command("get_project_status")
    print("Result:", json.dumps(result, indent=2))
    
    # Test 3: Try with a non-existent agent
    print("\n3. Testing request_next_task with non-existent agent:")
    print("-" * 40)
    result = run_mcp_command("request_next_task", {"agent_id": "non-existent-agent"})
    print("Result:", json.dumps(result, indent=2))
    
    # Test 4: report_task_progress without a task
    print("\n4. Testing report_task_progress without task:")
    print("-" * 40)
    result = run_mcp_command("report_task_progress", {
        "agent_id": "test-agent-001",
        "task_id": "non-existent-task",
        "status": "in_progress",
        "progress": 50,
        "message": "Testing error handling"
    })
    print("Result:", json.dumps(result, indent=2))

if __name__ == "__main__":
    main()