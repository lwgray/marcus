#!/usr/bin/env python3
"""
Diagnose Marcus server initialization status
"""

import asyncio
import os
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.integrations.kanban_factory import KanbanFactory


async def diagnose_marcus_status():
    """Diagnose why get_project_status might be failing"""
    
    print("=== Marcus Server Status Diagnosis ===\n")
    
    # Check 1: Environment variables
    print("1. Checking environment variables...")
    required_env_vars = [
        'PLANKA_BASE_URL',
        'PLANKA_AGENT_EMAIL', 
        'PLANKA_AGENT_PASSWORD'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if var in os.environ:
            print(f"   ✓ {var}: {os.environ[var]}")
        else:
            missing_vars.append(var)
            print(f"   ✗ {var}: Not set")
    
    if missing_vars:
        print(f"\n   Missing environment variables: {', '.join(missing_vars)}")
        print("   These should be set in your environment or loaded from config.")
    
    # Check 2: Kanban connection
    print("\n2. Testing kanban connection...")
    
    try:
        # Try to create a kanban client
        kanban_client = KanbanFactory.create('kanban_mcp')
        print("   ✓ Kanban client created successfully")
        
        # Test if we can connect (if method exists)
        if hasattr(kanban_client, 'connect'):
            await kanban_client.connect()
            print("   ✓ Kanban client connected")
        
        # Test if we can get tasks
        if hasattr(kanban_client, 'get_all_tasks'):
            tasks = await kanban_client.get_all_tasks()
            print(f"   ✓ Retrieved {len(tasks)} tasks from kanban board")
            
            if len(tasks) == 0:
                print("   ⚠️  No tasks found on the board")
                print("      This might be why project_state is unavailable")
        else:
            print("   ⚠️  get_all_tasks method not available")
            
    except Exception as e:
        print(f"   ✗ Kanban connection failed: {e}")
        print("   This is likely why get_project_status is failing")
        
        # Suggest solutions
        print("\n   Possible solutions:")
        print("   - Ensure Planka is running on http://localhost:3333")
        print("   - Check that demo user exists with email: demo@demo.demo")
        print("   - Verify the board ID in config_marcus.json is correct")
        print("   - Try accessing Planka web interface manually")
    
    # Check 3: Config file
    print("\n3. Checking config file...")
    
    config_path = "config_marcus.json"
    if os.path.exists(config_path):
        print(f"   ✓ Config file found: {config_path}")
        
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        if 'planka' in config:
            planka_config = config['planka']
            print(f"   ✓ Planka config: {planka_config}")
        else:
            print("   ⚠️  No planka section in config")
            
        if 'board_id' in config:
            print(f"   ✓ Board ID: {config['board_id']}")
        else:
            print("   ⚠️  No board_id in config")
    else:
        print(f"   ✗ Config file not found: {config_path}")
    
    print("\n=== Diagnosis Complete ===")
    print("\nTo fix the 'Not initialized' error:")
    print("1. Ensure Planka is running and accessible")
    print("2. Verify all environment variables are set")
    print("3. Check that tasks exist on your kanban board")
    print("4. Try using 'ping' tool first to verify Marcus is responding")


if __name__ == "__main__":
    asyncio.run(diagnose_marcus_status())