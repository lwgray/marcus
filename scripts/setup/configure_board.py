#!/usr/bin/env python3
"""
Configure PM Agent with a specific board ID
"""

import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


def configure_board(board_id: str, project_id: str = None):
    """Configure PM Agent with specific board and project IDs"""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    config_path = os.path.join(project_root, 'config_pm_agent.json')
    
    # Load existing config or create new
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        config = {
            "planka": {
                "base_url": "http://localhost:3333",
                "email": "demo@demo.demo",
                "password": "demo"
            }
        }
    
    # Update board ID
    config["board_id"] = board_id
    print(f"✅ Set board ID: {board_id}")
    
    # Update project ID if provided
    if project_id:
        config["project_id"] = project_id
        print(f"✅ Set project ID: {project_id}")
    elif "project_id" not in config:
        config["project_id"] = "1533678301472621705"  # Default Task Master
        print(f"📋 Using default project ID: {config['project_id']}")
    
    # Set other defaults
    config["auto_find_board"] = False
    if "project_name" not in config:
        config["project_name"] = "Task Master Test"
    
    # Save config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n💾 Configuration saved to {config_path}")
    print("\nYou can now run:")
    print("  python scripts/examples/create_todo_app_tasks.py")
    print("  python start_pm_agent_task_master.py")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python configure_board.py <board_id> [project_id]")
        print("\nExample:")
        print("  python configure_board.py 1533859887128249584")
        print("  python configure_board.py 1533859887128249584 1533678301472621705")
        sys.exit(1)
    
    board_id = sys.argv[1]
    project_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    configure_board(board_id, project_id)