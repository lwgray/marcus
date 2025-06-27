#!/usr/bin/env python3
"""
Setup script for Claude agents with Marcus MCP.
This creates CLAUDE.md files and configures MCP for each agent.
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_agent(agent_id: str, branch_name: str, worktree_path: str, 
                marcus_server_path: str, prompt_template_path: str):
    """
    Setup CLAUDE.md and MCP server for an agent
    """
    print(f"\n=== Setting up Agent {agent_id} ===")
    
    # Configure MCP server
    server_name = f"marcus_{agent_id}"
    print(f"Configuring MCP server '{server_name}'...")
    
    # Remove existing server if it exists
    subprocess.run(["claude", "mcp", "remove", server_name], 
                  capture_output=True, text=True)
    
    # Add the MCP server with project scope so it's available in the worktree
    add_cmd = [
        "claude", "mcp", "add", 
        server_name,
        "-s", "project",  # Project scope so it's available in worktree
        "-p", worktree_path,  # Set the project path
        "--",
        "python", marcus_server_path
    ]
    
    result = subprocess.run(add_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Warning: Failed to add MCP server: {result.stderr}")
        # Try without project path
        add_cmd = [
            "claude", "mcp", "add", 
            server_name,
            "--",
            "python", marcus_server_path
        ]
        result = subprocess.run(add_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("MCP server added successfully (global scope)")
    else:
        print(f"MCP server added successfully for project at {worktree_path}")
    
    # Load and customize the prompt template
    print("Creating CLAUDE.md...")
    with open(prompt_template_path, 'r') as f:
        prompt_template = f.read()
    
    # Replace placeholders
    prompt = prompt_template.format(
        AGENT_ID=agent_id,
        BRANCH_NAME=branch_name,
        WORKTREE_PATH=worktree_path
    )
    
    # Create CLAUDE.md with auto-start instructions
    claude_md_content = f"""# Agent {agent_id} - Autonomous Marcus Agent

This is an autonomous agent that works through Marcus MCP to complete coding tasks.

## Auto-Start Instructions

When you see "start work", immediately:

1. Connect to Marcus MCP by typing `/mcp` and connecting to `{server_name}`
2. Begin the autonomous workflow described below
3. Work continuously until no more tasks are available

## Agent Configuration
- **Agent ID**: {agent_id}
- **Branch**: {branch_name}
- **MCP Server**: {server_name}

---

{prompt}

---

## Remember:
- You are autonomous - make decisions without asking for confirmation
- Report progress regularly through Marcus
- Complete tasks fully before requesting new ones
- If blocked, use marcus.report_blocker for AI assistance
- Commit your work frequently to branch {branch_name}
"""
    
    # Write CLAUDE.md
    claude_md_path = Path(worktree_path) / "CLAUDE.md"
    claude_md_path.write_text(claude_md_content)
    print(f"Created {claude_md_path}")
    
    print(f"\n✓ Agent {agent_id} configured successfully!")
    print(f"  - CLAUDE.md created")
    print(f"  - MCP server '{server_name}' configured")
    print(f"  - Ready to start with: cd {worktree_path} && claude")
    print(f"  - Then type: start work")
    
    return True


def setup_all_agents(workspace_dir: str, marcus_server_path: str, prompt_template_path: str):
    """
    Setup all agents in a workspace
    """
    workspace = Path(workspace_dir)
    
    # Find all agent directories
    agent_dirs = [d for d in workspace.iterdir() if d.is_dir() and d.name.startswith("agent")]
    
    if not agent_dirs:
        print(f"No agent directories found in {workspace_dir}")
        return False
    
    print(f"Found {len(agent_dirs)} agent worktrees to configure")
    
    for agent_dir in sorted(agent_dirs):
        agent_id = agent_dir.name
        branch_name = f"{agent_id}-work"
        
        setup_agent(
            agent_id=agent_id,
            branch_name=branch_name,
            worktree_path=str(agent_dir),
            marcus_server_path=marcus_server_path,
            prompt_template_path=prompt_template_path
        )
    
    print(f"\n{'='*60}")
    print(f"All {len(agent_dirs)} agents configured!")
    print(f"\nTo start agents manually:")
    for agent_dir in sorted(agent_dirs):
        print(f"  Terminal {agent_dir.name}: cd {agent_dir} && claude")
    print(f"\nThen in each Claude instance, type: start work")
    print(f"{'='*60}")
    
    return True


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage:")
        print("  Setup one agent:  setup_claude_agent.py <agent_id> <branch_name> <worktree_path> <marcus_server_path> <prompt_template_path>")
        print("  Setup all agents: setup_claude_agent.py --all <workspace_dir> <marcus_server_path> <prompt_template_path>")
        sys.exit(1)
    
    if sys.argv[1] == "--all":
        # Setup all agents in workspace
        workspace_dir = sys.argv[2]
        marcus_server_path = sys.argv[3]
        prompt_template_path = sys.argv[4] if len(sys.argv) > 4 else str(Path(__file__).parent.parent / "prompts" / "marcus_agent.md")
        
        setup_all_agents(workspace_dir, marcus_server_path, prompt_template_path)
    else:
        # Setup single agent
        if len(sys.argv) != 6:
            print("Error: Single agent setup requires 5 arguments")
            sys.exit(1)
            
        agent_id = sys.argv[1]
        branch_name = sys.argv[2]
        worktree_path = sys.argv[3]
        marcus_server_path = sys.argv[4]
        prompt_template_path = sys.argv[5]
        
        setup_agent(agent_id, branch_name, worktree_path, 
                   marcus_server_path, prompt_template_path)