#!/usr/bin/env python3
"""
Wrapper script to run a Claude agent with Marcus MCP.
This script sets up the MCP connection and creates CLAUDE.md for the agent.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def setup_and_run_agent(agent_id: str, branch_name: str, worktree_path: str, 
                       marcus_server_path: str, prompt_template_path: str):
    """
    Setup MCP server and run Claude agent
    """
    print(f"=== Setting up Claude Agent {agent_id} ===")
    print(f"Worktree: {worktree_path}")
    print(f"Branch: {branch_name}")
    
    # Change to worktree directory
    os.chdir(worktree_path)
    
    # Configure MCP server for this agent
    server_name = f"marcus_{agent_id}"
    print(f"\nAdding Marcus MCP server as '{server_name}'...")
    
    # Remove existing server if it exists
    subprocess.run(["claude", "mcp", "remove", server_name], 
                  capture_output=True, text=True)
    
    # Add the MCP server
    add_cmd = [
        "claude", "mcp", "add", 
        server_name,
        "-s", "local",
        "--",
        "python", marcus_server_path
    ]
    
    result = subprocess.run(add_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Warning: Failed to add MCP server: {result.stderr}")
    else:
        print("MCP server added successfully")
    
    # Load and customize the prompt template
    print(f"\nPreparing CLAUDE.md...")
    with open(prompt_template_path, 'r') as f:
        prompt_template = f.read()
    
    # Replace placeholders
    prompt = prompt_template.format(
        AGENT_ID=agent_id,
        BRANCH_NAME=branch_name,
        WORKTREE_PATH=worktree_path
    )
    
    # Create CLAUDE.md in the worktree directory
    claude_md_path = Path(worktree_path) / "CLAUDE.md"
    
    # Add a header with instructions to automatically start
    claude_md_content = f"""# Claude Agent {agent_id} Instructions

When you see "start work", you should:

1. Connect to the Marcus MCP server by using /mcp and selecting 'marcus_{agent_id}'
2. Follow the workflow below to work autonomously

---

{prompt}
"""
    
    claude_md_path.write_text(claude_md_content)
    print(f"Created CLAUDE.md at {claude_md_path}")
    
    # Create a simple input file that sends "start work" command
    start_command_file = Path(worktree_path) / f".start_agent_{agent_id}.txt"
    start_command_file.write_text("start work\n")
    
    print("\n" + "="*50)
    print(f"Agent {agent_id} is configured!")
    print(f"CLAUDE.md created at: {claude_md_path}")
    print(f"MCP server configured as: {server_name}")
    print("="*50)
    
    # Launch Claude with the start work command piped in
    print(f"\nLaunching Claude for agent {agent_id}...")
    
    # Run Claude with "start work" piped in
    process = subprocess.Popen(
        ["claude"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=worktree_path,
        text=True
    )
    
    # Send "start work" command
    process.stdin.write("start work\n")
    process.stdin.flush()
    
    # Don't close stdin - let Claude continue running
    return process


if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: claude_agent_wrapper.py <agent_id> <branch_name> <worktree_path> <marcus_server_path> <prompt_template_path>")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    branch_name = sys.argv[2]
    worktree_path = sys.argv[3]
    marcus_server_path = sys.argv[4]
    prompt_template_path = sys.argv[5]
    
    process = setup_and_run_agent(agent_id, branch_name, worktree_path, 
                                 marcus_server_path, prompt_template_path)
    
    # Wait for the process to complete
    if process:
        process.wait()