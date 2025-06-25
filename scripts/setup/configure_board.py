#!/usr/bin/env python3
"""Configure PM Agent with specific board and project IDs.

This module provides functionality to configure PM Agent with specific
Planka board and project IDs. It manages the configuration file
(config_pm_agent.json) that stores the board settings, project settings,
and Planka connection details.

The configuration is used by PM Agent to connect to the correct task board
and project when starting up, ensuring tasks are created and managed in the
right location.

Examples
--------
Configure with just a board ID:
    $ python scripts/setup/configure_board.py 1533859887128249584

Configure with both board and project IDs:
    $ python scripts/setup/configure_board.py 1533859887128249584 1533678301472621705

Notes
-----
The script creates or updates config_pm_agent.json in the project root directory.
Default Planka connection settings are used if not already configured.
"""

import json
import sys
import os
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


def configure_board(board_id: str, project_id: Optional[str] = None) -> None:
    """Configure PM Agent with specific board and project IDs.
    
    Updates or creates the PM Agent configuration file with the specified
    board ID and optionally a project ID. Also sets default values for
    Planka connection settings if not already present.
    
    Parameters
    ----------
    board_id : str
        The Planka board ID to use for task management.
    project_id : Optional[str], default=None
        The Planka project ID. If not provided, uses a default value.
        
    Returns
    -------
    None
    
    Side Effects
    ------------
    Creates or modifies config_pm_agent.json in the project root directory
    with the following structure:
        - board_id: The specified board ID
        - project_id: The specified or default project ID
        - planka: Connection settings (base_url, email, password)
        - auto_find_board: Set to False
        - project_name: Default "Task Master Test"
    
    Examples
    --------
    >>> configure_board("1533859887128249584")
    ✅ Set board ID: 1533859887128249584
    📋 Using default project ID: 1533678301472621705
    
    >>> configure_board("1533859887128249584", "1533678301472621705")
    ✅ Set board ID: 1533859887128249584
    ✅ Set project ID: 1533678301472621705
    """
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