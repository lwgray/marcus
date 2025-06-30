#!/usr/bin/env python3
"""
Migration script to consolidate .env and config_marcus.json into marcus.config.json

This script:
1. Reads existing .env and config_marcus.json files
2. Merges them into a new marcus.config.json
3. Creates backups of the original files
4. Provides instructions for the user
"""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime


def load_env_file(env_path):
    """Load .env file and return as dictionary"""
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars


def load_json_config(json_path):
    """Load JSON config file"""
    if json_path.exists():
        with open(json_path, 'r') as f:
            return json.load(f)
    return {}


def create_backup(file_path):
    """Create timestamped backup of file"""
    if file_path.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = file_path.with_suffix(f'.backup_{timestamp}{file_path.suffix}')
        shutil.copy2(file_path, backup_path)
        print(f"✓ Created backup: {backup_path}")
        return backup_path
    return None


def migrate_config():
    """Main migration function"""
    project_root = Path(__file__).parent.parent
    
    # File paths
    env_path = project_root / '.env'
    old_config_path = project_root / 'config_marcus.json'
    new_config_path = project_root / 'marcus.config.json'
    example_path = project_root / 'marcus.config.example.json'
    
    print("Marcus Configuration Migration")
    print("=" * 50)
    
    # Check if new config already exists
    if new_config_path.exists():
        print(f"⚠️  {new_config_path} already exists!")
        response = input("Do you want to overwrite it? (y/N): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            return
        create_backup(new_config_path)
    
    # Load existing configurations
    print("\n1. Loading existing configurations...")
    env_vars = load_env_file(env_path)
    old_config = load_json_config(old_config_path)
    
    # Create new configuration structure
    new_config = {
        "kanban": {
            "provider": env_vars.get('KANBAN_PROVIDER', 'planka'),
            "planka": {
                "base_url": old_config.get('planka', {}).get('base_url', 'http://localhost:3333'),
                "email": old_config.get('planka', {}).get('email', 'demo@demo.demo'),
                "password": old_config.get('planka', {}).get('password', 'demo'),
                "project_id": old_config.get('project_id', ''),
                "board_id": old_config.get('board_id', ''),
                "project_name": old_config.get('project_name', 'Marcus Tasks'),
                "auto_find_board": old_config.get('auto_find_board', False)
            },
            "github": {
                "token": env_vars.get('GITHUB_TOKEN', ''),
                "owner": env_vars.get('GITHUB_OWNER', ''),
                "repo": env_vars.get('GITHUB_REPO', '')
            },
            "linear": {
                "api_key": env_vars.get('LINEAR_API_KEY', ''),
                "team_id": env_vars.get('LINEAR_TEAM_ID', '')
            }
        },
        "ai": {
            "anthropic_api_key": env_vars.get('ANTHROPIC_API_KEY', ''),
            "openai_api_key": env_vars.get('OPENAI_API_KEY', ''),
            "model": env_vars.get('MARCUS_AI_MODEL', 'claude-3-sonnet-20241022'),
            "temperature": 0.7,
            "max_tokens": 2000,
            "retry_attempts": 3,
            "retry_delay": 1.0
        },
        "monitoring": {
            "interval": int(env_vars.get('MARCUS_MONITORING_INTERVAL', 900)),
            "stall_threshold_hours": 24,
            "health_check_interval": 3600,
            "risk_thresholds": {
                "high": 0.8,
                "medium": 0.5,
                "timeline_buffer": 0.2
            }
        },
        "escalation": {
            "stuck_task_hours": 8,
            "blocker_escalation_hours": 4,
            "critical_path_delay_hours": 2
        },
        "communication": {
            "slack_enabled": env_vars.get('MARCUS_SLACK_ENABLED', 'false').lower() == 'true',
            "slack_webhook_url": env_vars.get('SLACK_WEBHOOK_URL', ''),
            "email_enabled": env_vars.get('MARCUS_EMAIL_ENABLED', 'false').lower() == 'true',
            "kanban_comments_enabled": True,
            "rules": {
                "daily_plan_time": "08:00",
                "progress_check_time": "14:00",
                "end_of_day_summary": "18:00"
            }
        },
        "security": {
            "mcp_auth_tokens": env_vars.get('MCP_AUTH_TOKENS', '').split(',') if env_vars.get('MCP_AUTH_TOKENS') else []
        },
        "advanced": {
            "debug": env_vars.get('MARCUS_DEBUG', 'false').lower() == 'true',
            "port": int(env_vars.get('MARCUS_PORT', 8000)),
            "max_concurrent_analyses": 5,
            "cache_ttl_seconds": 300
        }
    }
    
    # Create backups
    print("\n2. Creating backups...")
    create_backup(env_path)
    create_backup(old_config_path)
    
    # Write new configuration
    print("\n3. Writing new configuration...")
    with open(new_config_path, 'w') as f:
        json.dump(new_config, f, indent=2)
    print(f"✓ Created {new_config_path}")
    
    # Create example file if it doesn't exist
    if not example_path.exists():
        # Create example with placeholder values
        example_config = json.loads(json.dumps(new_config))  # Deep copy
        
        # Replace sensitive values with placeholders
        example_config["kanban"]["planka"]["email"] = "your-email@example.com"
        example_config["kanban"]["planka"]["password"] = "your-password"
        example_config["kanban"]["github"]["token"] = "ghp_your_github_token_here"
        example_config["kanban"]["linear"]["api_key"] = "lin_api_your_linear_key_here"
        example_config["ai"]["anthropic_api_key"] = "sk-ant-your-api-key-here"
        example_config["ai"]["openai_api_key"] = "sk-your-openai-key-here"
        example_config["communication"]["slack_webhook_url"] = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
        
        # Add instructions at the top
        example_config = {
            "// Instructions": "Copy this file to marcus.config.json and fill in your values",
            "// Note": "This file is tracked by git. Do NOT put real credentials here!",
            **example_config
        }
        
        with open(example_path, 'w') as f:
            json.dump(example_config, f, indent=2)
        print(f"✓ Created {example_path}")
    
    # Print summary
    print("\n" + "=" * 50)
    print("✅ Migration completed successfully!")
    print("\nIMPORTANT NOTES:")
    print("1. Your settings have been migrated to marcus.config.json")
    print("2. Original files have been backed up")
    print("3. marcus.config.json contains sensitive data and should NOT be committed to git")
    print("4. The old .env and config_marcus.json files are no longer needed")
    print("\nNext steps:")
    print("1. Review marcus.config.json to ensure all settings are correct")
    print("2. Test Marcus to ensure it works with the new configuration")
    print("3. Once confirmed working, you can delete the old .env and config_marcus.json files")
    print("\n⚠️  WARNING: marcus.config.json will be added to .gitignore to prevent accidental commits")


if __name__ == "__main__":
    migrate_config()