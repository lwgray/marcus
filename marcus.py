#!/usr/bin/env python3
"""
Marcus MCP Server - Entry Point

This is the main entry point for the Marcus MCP server.
It delegates to the modularized implementation in src/marcus_mcp/
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv

def load_config():
    """Load configuration from .env file and config_marcus.json"""
    # First, load .env file
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded .env file from {env_path}")
    
    # Then load config_marcus.json to override with specific settings
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
        
        # Set kanban provider (from .env or default to planka)
        if 'KANBAN_PROVIDER' not in os.environ:
            os.environ['KANBAN_PROVIDER'] = 'planka'
        
        # Only set API key from config if not already in environment (from .env)
        if 'anthropic_api_key' in config and 'ANTHROPIC_API_KEY' not in os.environ:
            os.environ['ANTHROPIC_API_KEY'] = config['anthropic_api_key']

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.marcus_mcp import main

if __name__ == "__main__":
    # Load configuration before starting
    load_config()
    asyncio.run(main())