import os
import json
from typing import Dict, Any, Optional
from pathlib import Path


class Settings:
    """Configuration management for PM Agent"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.environ.get(
            "PM_AGENT_CONFIG",
            "config/pm_agent_config.json"
        )
        
        # Default configuration
        self.defaults = {
            # Monitoring settings
            "monitoring_interval": 900,  # 15 minutes
            "stall_threshold_hours": 24,
            "health_check_interval": 3600,  # 1 hour
            
            # Risk thresholds
            "risk_thresholds": {
                "high_risk": 0.8,
                "medium_risk": 0.5,
                "timeline_buffer": 0.2
            },
            
            # Escalation rules
            "escalation_rules": {
                "stuck_task_hours": 8,
                "blocker_escalation_hours": 4,
                "critical_path_delay_hours": 2
            },
            
            # Communication settings
            "communication_rules": {
                "daily_plan_time": "08:00",
                "progress_check_time": "14:00",
                "end_of_day_summary": "18:00"
            },
            
            # Integration settings
            "slack_enabled": False,
            "email_enabled": False,
            "kanban_comments_enabled": True,
            
            # Team configuration
            "team_config": {
                "default": {
                    "skills": [],
                    "work_patterns": {
                        "preferred_hours": "9am-6pm",
                        "deep_work_blocks": "2-4 hours",
                        "context_switch_cost": "medium"
                    },
                    "communication_preferences": {
                        "notification_frequency": "medium",
                        "detailed_instructions": True,
                        "technical_depth": "medium"
                    }
                }
            },
            
            # Performance settings
            "performance": {
                "max_concurrent_analyses": 5,
                "cache_ttl_seconds": 300,
                "batch_notification_delay": 1.0
            },
            
            # AI settings
            "ai_settings": {
                "model": "claude-3-sonnet-20241022",
                "temperature": 0.7,
                "max_tokens": 2000,
                "retry_attempts": 3,
                "retry_delay": 1.0
            }
        }
        
        # Load configuration
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment"""
        config = self.defaults.copy()
        
        # Try to load from file
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                    config = self._deep_merge(config, file_config)
            except Exception as e:
                print(f"Error loading config file: {e}")
        
        # Override with environment variables
        config = self._load_env_overrides(config)
        
        return config
    
    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _load_env_overrides(self, config: Dict) -> Dict:
        """Load configuration overrides from environment variables"""
        # Monitoring interval
        if "PM_AGENT_MONITORING_INTERVAL" in os.environ:
            config["monitoring_interval"] = int(os.environ["PM_AGENT_MONITORING_INTERVAL"])
        
        # Slack integration
        if "PM_AGENT_SLACK_ENABLED" in os.environ:
            config["slack_enabled"] = os.environ["PM_AGENT_SLACK_ENABLED"].lower() == "true"
        
        if "SLACK_WEBHOOK_URL" in os.environ:
            config["slack_webhook_url"] = os.environ["SLACK_WEBHOOK_URL"]
        
        # Email integration
        if "PM_AGENT_EMAIL_ENABLED" in os.environ:
            config["email_enabled"] = os.environ["PM_AGENT_EMAIL_ENABLED"].lower() == "true"
        
        # API keys
        if "ANTHROPIC_API_KEY" in os.environ:
            config["anthropic_api_key"] = os.environ["ANTHROPIC_API_KEY"]
        
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self):
        """Save current configuration to file"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get_team_config(self, team_name: str = "default") -> Dict[str, Any]:
        """Get configuration for a specific team"""
        team_configs = self.get("team_config", {})
        return team_configs.get(team_name, team_configs.get("default", {}))
    
    def get_risk_thresholds(self) -> Dict[str, float]:
        """Get risk assessment thresholds"""
        return self.get("risk_thresholds", self.defaults["risk_thresholds"])
    
    def get_escalation_rules(self) -> Dict[str, int]:
        """Get escalation rules"""
        return self.get("escalation_rules", self.defaults["escalation_rules"])
    
    def get_communication_rules(self) -> Dict[str, str]:
        """Get communication timing rules"""
        return self.get("communication_rules", self.defaults["communication_rules"])
    
    def get_ai_settings(self) -> Dict[str, Any]:
        """Get AI model settings"""
        return self.get("ai_settings", self.defaults["ai_settings"])
    
    def validate(self) -> bool:
        """Validate configuration"""
        required_keys = []
        
        # Check for API key if AI is being used
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("Warning: ANTHROPIC_API_KEY not found in environment")
        
        # Validate monitoring interval
        monitoring_interval = self.get("monitoring_interval")
        if monitoring_interval < 60:
            print("Warning: Monitoring interval is very short (< 60 seconds)")
        
        # Validate communication channels
        if not any([
            self.get("slack_enabled"),
            self.get("email_enabled"),
            self.get("kanban_comments_enabled")
        ]):
            print("Warning: No communication channels enabled")
        
        return True