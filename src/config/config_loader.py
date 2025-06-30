"""
Centralized configuration loader for Marcus

This module provides a single source of truth for loading configuration
from marcus.config.json with support for environment variable overrides.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """Singleton configuration loader for Marcus"""
    
    _instance = None
    _config = None
    _config_path = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the config loader"""
        if self._config is None:
            self._load_config()
    
    def _load_config(self):
        """Load configuration from marcus.config.json"""
        # Find config file
        # Try multiple locations in order of preference
        possible_paths = [
            Path.cwd() / "marcus.config.json",  # Current directory
            Path(__file__).parent.parent.parent / "marcus.config.json",  # Project root
            Path.home() / ".marcus" / "marcus.config.json",  # User home
        ]
        
        for path in possible_paths:
            if path.exists():
                self._config_path = path
                break
        
        if self._config_path is None:
            raise FileNotFoundError(
                "marcus.config.json not found. Please run scripts/migrate_config.py "
                "or copy marcus.config.example.json to marcus.config.json"
            )
        
        # Load the config file
        with open(self._config_path, 'r') as f:
            self._config = json.load(f)
        
        # Apply environment variable overrides
        self._apply_env_overrides()
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides to config"""
        # Map of environment variables to config paths
        env_mappings = {
            # Kanban provider
            'MARCUS_KANBAN_PROVIDER': 'kanban.provider',
            
            # Planka
            'MARCUS_KANBAN_PLANKA_BASE_URL': 'kanban.planka.base_url',
            'MARCUS_KANBAN_PLANKA_EMAIL': 'kanban.planka.email',
            'MARCUS_KANBAN_PLANKA_PASSWORD': 'kanban.planka.password',
            'MARCUS_KANBAN_PLANKA_PROJECT_ID': 'kanban.planka.project_id',
            'MARCUS_KANBAN_PLANKA_BOARD_ID': 'kanban.planka.board_id',
            
            # GitHub
            'MARCUS_KANBAN_GITHUB_TOKEN': 'kanban.github.token',
            'MARCUS_KANBAN_GITHUB_OWNER': 'kanban.github.owner',
            'MARCUS_KANBAN_GITHUB_REPO': 'kanban.github.repo',
            
            # Linear
            'MARCUS_KANBAN_LINEAR_API_KEY': 'kanban.linear.api_key',
            'MARCUS_KANBAN_LINEAR_TEAM_ID': 'kanban.linear.team_id',
            
            # AI
            'MARCUS_AI_ANTHROPIC_API_KEY': 'ai.anthropic_api_key',
            'MARCUS_AI_OPENAI_API_KEY': 'ai.openai_api_key',
            'MARCUS_AI_MODEL': 'ai.model',
            
            # Monitoring
            'MARCUS_MONITORING_INTERVAL': 'monitoring.interval',
            
            # Communication
            'MARCUS_SLACK_ENABLED': 'communication.slack_enabled',
            'MARCUS_SLACK_WEBHOOK_URL': 'communication.slack_webhook_url',
            'MARCUS_EMAIL_ENABLED': 'communication.email_enabled',
            
            # Advanced
            'MARCUS_DEBUG': 'advanced.debug',
            'MARCUS_PORT': 'advanced.port',
        }
        
        for env_var, config_path in env_mappings.items():
            if env_var in os.environ:
                self._set_nested_value(config_path, os.environ[env_var])
    
    def _set_nested_value(self, path: str, value: str):
        """Set a nested value in the config using dot notation"""
        keys = path.split('.')
        config = self._config
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Set the value, converting types as needed
        final_key = keys[-1]
        
        # Type conversion based on current value type
        if final_key in config:
            current_value = config[final_key]
            if isinstance(current_value, bool):
                config[final_key] = value.lower() in ('true', '1', 'yes', 'on')
            elif isinstance(current_value, int):
                config[final_key] = int(value)
            elif isinstance(current_value, float):
                config[final_key] = float(value)
            else:
                config[final_key] = value
        else:
            # Default to string if key doesn't exist
            config[final_key] = value
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation
        
        Args:
            path: Dot-separated path to the config value (e.g., 'kanban.provider')
            default: Default value if path doesn't exist
            
        Returns:
            The configuration value or default
        """
        keys = path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_kanban_config(self) -> Dict[str, Any]:
        """Get the complete kanban configuration for the selected provider"""
        provider = self.get('kanban.provider', 'planka')
        base_config = {
            'provider': provider,
            **self.get(f'kanban.{provider}', {})
        }
        return base_config
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get the complete AI configuration"""
        return self.get('ai', {})
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get the complete monitoring configuration"""
        return self.get('monitoring', {})
    
    def get_communication_config(self) -> Dict[str, Any]:
        """Get the complete communication configuration"""
        return self.get('communication', {})
    
    def reload(self):
        """Reload the configuration from disk"""
        self._config = None
        self._load_config()
    
    @property
    def config_path(self) -> Path:
        """Get the path to the loaded config file"""
        return self._config_path
    
    def __repr__(self) -> str:
        return f"ConfigLoader(config_path={self._config_path})"


# Global singleton instance
_config_loader = None


def get_config() -> ConfigLoader:
    """Get the global config loader instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


# Convenience functions for common access patterns
def get_config_value(path: str, default: Any = None) -> Any:
    """Get a configuration value using dot notation"""
    return get_config().get(path, default)


def get_kanban_provider() -> str:
    """Get the configured kanban provider"""
    return get_config().get('kanban.provider', 'planka')


def get_anthropic_api_key() -> Optional[str]:
    """Get the Anthropic API key"""
    return get_config().get('ai.anthropic_api_key')


def get_planka_config() -> Dict[str, Any]:
    """Get Planka configuration"""
    return get_config().get('kanban.planka', {})