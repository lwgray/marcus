"""
Configuration Module for Marcus
==================================

This module provides comprehensive configuration management for the Marcus system.
It handles loading, validation, and management of settings from multiple sources
including configuration files, environment variables, and default values.

The Settings class supports hierarchical configuration with deep merging capabilities,
environment variable overrides, and specialized getter methods for different
configuration categories.

Key Features
------------
- JSON-based configuration files
- Environment variable overrides
- Deep dictionary merging
- Configuration validation
- Specialized configuration getters for:
  * Team configurations
  * Risk thresholds
  * Escalation rules  
  * Communication settings
  * AI model settings

Classes
-------
Settings
    Main configuration manager with loading, validation, and access methods

Examples
--------
>>> from src.config import Settings
>>> settings = Settings()
>>> risk_thresholds = settings.get_risk_thresholds()
>>> team_config = settings.get_team_config("backend_team")
"""

from .settings import Settings

__all__ = ['Settings']