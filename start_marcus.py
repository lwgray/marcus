#!/usr/bin/env python3
"""
Start Marcus MCP server with proper configuration
"""

import os
import sys
import json
from pathlib import Path

# Load configuration from config_marcus.json
def load_config():
    """Load configuration and set environment variables"""
    config_path = Path(__file__).parent / "config_marcus.json"
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Set Planka environment variables from config
        if 'planka' in config:
            planka_config = config['planka']
            os.environ['PLANKA_BASE_URL'] = planka_config.get('base_url', 'http://localhost:3333')
            os.environ['PLANKA_AGENT_EMAIL'] = planka_config.get('email', 'demo@demo.demo')
            os.environ['PLANKA_AGENT_PASSWORD'] = planka_config.get('password', 'demo')
        
        # Set kanban provider
        os.environ['KANBAN_PROVIDER'] = 'planka'
        
        print("✅ Configuration loaded from config_marcus.json")
        print(f"   Planka URL: {os.environ.get('PLANKA_BASE_URL')}")
        print(f"   Planka User: {os.environ.get('PLANKA_AGENT_EMAIL')}")
        print(f"   Kanban Provider: {os.environ.get('KANBAN_PROVIDER')}")
        
    else:
        print(f"⚠️  No config file found at {config_path}")
        print("   Using default environment variables")


if __name__ == "__main__":
    # Load configuration first
    load_config()
    
    # Add the project root to Python path
    sys.path.insert(0, str(Path(__file__).parent))
    
    # Import and run Marcus
    from src.marcus_mcp import main
    import asyncio
    
    print("\n🚀 Starting Marcus MCP Server...")
    asyncio.run(main())