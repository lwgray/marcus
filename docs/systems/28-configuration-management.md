# Configuration Management System

## Overview

Marcus's Configuration Management System provides a comprehensive, hierarchical configuration framework that manages settings from multiple sources with sophisticated validation, type conversion, and environment-specific overrides. The system supports both legacy single-project configurations and modern multi-project setups, serving as the backbone for all system configuration needs.

## Architecture

### Core Components

The Configuration Management System consists of three primary components:

1. **ConfigLoader** (`src/config/config_loader.py`)
   - Singleton pattern for centralized configuration loading
   - Multi-source configuration with precedence handling
   - Legacy configuration migration capabilities
   - Project and provider management

2. **Settings** (`src/config/settings.py`)
   - High-level configuration access layer
   - Specialized configuration getters for different domains
   - Environment variable integration
   - Configuration validation framework

3. **HybridInferenceConfig** (`src/config/hybrid_inference_config.py`)
   - Specialized configuration for AI dependency inference
   - Preset configurations for different use cases
   - Performance tuning parameters
   - Cost optimization controls

### Configuration Hierarchy

The system implements a sophisticated configuration hierarchy with the following precedence (highest to lowest):

```
1. Environment Variables (highest priority)
2. marcus.config.json file
3. Default values (lowest priority)
```

### File Discovery Strategy

The ConfigLoader searches for configuration files in this order:

1. `./config_marcus.json` (current working directory)
2. `{project_root}/config_marcus.json` (project root)
3. `~/.marcus/config_marcus.json` (user home directory)

## Integration in Marcus Ecosystem

### Core System Dependencies

The Configuration Management System is a foundational dependency for virtually every Marcus component:

- **AI Providers**: API keys, model selection, inference parameters
- **Kanban Integration**: Provider credentials, board/project mappings
- **Monitoring Systems**: Intervals, thresholds, alerting rules
- **Communication Hub**: Channel configurations, notification settings
- **Intelligence Engines**: Algorithm tuning parameters
- **Worker Agents**: Execution environments, resource limits

### Multi-Project Support

The system supports both single-project (legacy) and multi-project configurations:

```json
{
  "projects": {
    "project-uuid-1": {
      "name": "Frontend Redesign",
      "provider": "github",
      "config": {
        "owner": "company",
        "repo": "frontend",
        "project_number": 1
      }
    }
  },
  "active_project": "project-uuid-1",
  "providers": {
    "github": {
      "token": "ghp_..."
    },
    "planka": {
      "base_url": "https://planka.company.com",
      "email": "marcus@company.com"
    }
  }
}
```

## Workflow Integration

### In the Marcus Lifecycle

The Configuration Management System is invoked at multiple points in the typical Marcus workflow:

#### 1. System Initialization
```
create_project → ConfigLoader singleton creation → Configuration loading and validation
```

#### 2. Agent Registration
```
register_agent → Settings.get_team_config() → Agent-specific configuration retrieval
```

#### 3. Task Processing
```
request_next_task → AI model configuration → Kanban provider settings → Monitoring thresholds
```

#### 4. Progress Reporting
```
report_progress → Communication settings → Notification configurations
```

#### 5. Blocker Management
```
report_blocker → Escalation rules → Risk thresholds → Alert configurations
```

#### 6. Task Completion
```
finish_task → Post-completion monitoring → Performance tracking settings
```

### Configuration Access Patterns

The system provides multiple access patterns for different use cases:

```python
# Direct access via ConfigLoader
from src.config.config_loader import get_config
config = get_config()
api_key = config.get("ai.anthropic_api_key")

# High-level access via Settings
from src.config.settings import Settings
settings = Settings()
risk_thresholds = settings.get_risk_thresholds()

# Convenience functions
from src.config.config_loader import get_anthropic_api_key
api_key = get_anthropic_api_key()
```

## Special Features

### 1. Automatic Legacy Migration

The system automatically detects and migrates legacy single-project configurations to the new multi-project format:

```python
def _migrate_legacy_config(self):
    """Migrate legacy single-project config to multi-project format"""
    if "project_id" in self._config and "projects" not in self._config:
        # Creates default project from legacy config
        # Preserves all existing settings
        # Maintains backward compatibility
```

### 2. Intelligent Type Conversion

Environment variable overrides include automatic type conversion based on existing configuration values:

```python
def _set_nested_value(self, path: str, value: str):
    """Set nested value with type conversion"""
    if isinstance(current_value, bool):
        config[final_key] = value.lower() in ("true", "1", "yes", "on")
    elif isinstance(current_value, int):
        config[final_key] = int(value)
    elif isinstance(current_value, float):
        config[final_key] = float(value)
```

### 3. Feature Configuration Compatibility

Supports both old boolean format and new object format for feature flags:

```python
def get_feature_config(self, feature: str) -> Dict[str, Any]:
    """Handle both old and new feature configuration formats"""
    # Old: "events": true
    # New: "events": {"enabled": true, "store_history": true}
```

### 4. Hybrid Inference Optimization

The HybridInferenceConfig provides sophisticated tuning for AI-powered dependency inference:

```python
@dataclass
class HybridInferenceConfig:
    pattern_confidence_threshold: float = 0.8  # Pattern vs AI threshold
    ai_confidence_threshold: float = 0.7       # AI acceptance threshold
    combined_confidence_boost: float = 0.15    # Agreement bonus
    max_ai_pairs_per_batch: int = 20          # Batch size optimization
```

## Technical Implementation

### Singleton Pattern Implementation

The ConfigLoader uses a thread-safe singleton pattern:

```python
class ConfigLoader:
    _instance = None
    _config = None
    _config_path = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance
```

### Deep Configuration Merging

The Settings class implements recursive dictionary merging:

```python
def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge dictionaries"""
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = self._deep_merge(result[key], value)
        else:
            result[key] = value
```

### Dot-Notation Path Resolution

Both ConfigLoader and Settings support dot-notation for nested configuration access:

```python
def get(self, path: str, default: Any = None) -> Any:
    """Get configuration value using dot notation"""
    keys = path.split(".")
    value = self._config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value
```

## Performance Considerations

### Pros

1. **Singleton Pattern**: Single configuration load per process lifecycle
2. **Lazy Loading**: Configuration loaded only when first accessed
3. **Memory Efficiency**: Shared configuration instance across all components
4. **Caching**: Environment variable processing cached after first load
5. **Validation Optimization**: Validation only performed when explicitly requested

### Cons

1. **Global State**: Singleton pattern creates implicit global dependencies
2. **Reload Complexity**: Configuration changes require explicit reload() calls
3. **Memory Persistence**: Configuration held in memory for entire process lifetime
4. **Thread Safety**: Current implementation not fully thread-safe for concurrent modifications

## Task Complexity Handling

### Simple Tasks

For simple task configurations, the system provides:

- Default values that work out-of-the-box
- Minimal configuration requirements
- Environment variable overrides for quick adjustments

### Complex Tasks

For complex multi-agent, multi-project scenarios:

- Multi-project configuration with provider abstraction
- Team-specific configuration profiles
- Advanced AI tuning parameters
- Sophisticated escalation and monitoring rules

### Configuration Presets

The HybridInferenceConfig includes preset configurations for different complexity levels:

```python
PRESETS = {
    'conservative': HybridInferenceConfig(
        pattern_confidence_threshold=0.9,
        ai_confidence_threshold=0.8,
        max_ai_pairs_per_batch=10
    ),
    'balanced': HybridInferenceConfig(),  # Default values
    'aggressive': HybridInferenceConfig(
        pattern_confidence_threshold=0.7,
        ai_confidence_threshold=0.6,
        max_ai_pairs_per_batch=30
    ),
    'cost_optimized': HybridInferenceConfig(
        pattern_confidence_threshold=0.85,
        max_ai_pairs_per_batch=50,
        cache_ttl_hours=48
    )
}
```

## Board-Specific Considerations

### Provider Abstraction

The system abstracts kanban provider specifics through a unified configuration interface:

```python
def get_kanban_config(self) -> Dict[str, Any]:
    """Get complete kanban configuration for selected provider"""
    provider = self.get("kanban.provider", "planka")
    base_config = {"provider": provider, **self.get(f"kanban.{provider}", {})}
    return base_config
```

### Board Mapping

Different providers require different configuration structures:

- **Planka**: `project_id` and `board_id`
- **GitHub**: `owner`, `repo`, and `project_number`
- **Linear**: `team_id` and `project_id`

The system handles these differences transparently through provider-specific configuration sections.

## Seneca Integration

While Seneca (the decision-making AI component) doesn't have explicit configuration integration, it leverages the Configuration Management System through:

1. **AI Provider Settings**: Model selection, temperature, token limits
2. **Decision Thresholds**: Risk assessment parameters
3. **Context Management**: Memory and context retention settings
4. **Performance Tuning**: Batch sizes and caching parameters

## Design Rationale

### Why This Approach

1. **Flexibility**: Supports multiple configuration sources and formats
2. **Evolution**: Seamless migration from legacy to modern configurations
3. **Separation of Concerns**: Different configuration aspects handled by specialized components
4. **Extensibility**: Easy addition of new configuration domains
5. **Environment Agnostic**: Works across development, staging, and production environments

### Alternative Approaches Considered

1. **Environment Variables Only**: Too limited for complex nested configurations
2. **Database-Stored Configuration**: Added complexity and dependency requirements
3. **Multiple Configuration Files**: Increased management overhead and inconsistency risk
4. **Runtime Configuration APIs**: Security and persistence concerns

### Trade-offs Made

- **Complexity vs. Flexibility**: Chose comprehensive system over simple key-value storage
- **Memory vs. Disk**: Cached in-memory configuration vs. repeated file reads
- **Validation vs. Performance**: Optional validation to maintain startup speed
- **Backward Compatibility vs. Clean Design**: Maintained legacy support during transition

## Future Evolution

### Short-term Enhancements

1. **Thread Safety**: Full thread-safe configuration access for concurrent operations
2. **Hot Reloading**: Automatic configuration reload on file changes
3. **Configuration Validation**: Enhanced validation with detailed error reporting
4. **Environment Profiles**: Built-in development/staging/production profile support

### Medium-term Roadmap

1. **Dynamic Configuration**: Runtime configuration updates without process restart
2. **Configuration History**: Audit trail for configuration changes
3. **Distributed Configuration**: Support for configuration synchronization across multiple instances
4. **Schema Validation**: JSON Schema-based configuration validation

### Long-term Vision

1. **AI-Driven Configuration**: Automatic configuration optimization based on usage patterns
2. **Self-Healing Configuration**: Automatic recovery from configuration errors
3. **Configuration Analytics**: Deep insights into configuration impact on system performance
4. **Template-Based Configuration**: Reusable configuration templates for common setups

## Error Handling and Resilience

### Configuration Load Failures

The system implements graceful degradation when configuration loading fails:

```python
try:
    config_loader = get_config()
    # Use centralized configuration
except Exception as e:
    # Fall back to defaults
    print(f"Warning: Could not load from config loader: {e}")
```

### Validation Strategies

Configuration validation is optional but comprehensive when enabled:

```python
def validate(self) -> bool:
    """Validate configuration for consistency and completeness"""
    # Check required API keys
    # Validate monitoring intervals
    # Verify communication channels
    return True
```

### Recovery Mechanisms

1. **Graceful Fallbacks**: Default values for all configuration options
2. **Partial Configuration**: System operates with incomplete configuration
3. **Configuration Repair**: Automatic fixing of common configuration issues
4. **User Guidance**: Clear error messages with suggested fixes

## Integration Examples

### AI Provider Configuration

```python
from src.config.config_loader import get_config

config = get_config()
ai_config = config.get_ai_config()

# Used by AI providers for model initialization
anthropic_client = AnthropicClient(
    api_key=ai_config.get('anthropic_api_key'),
    model=ai_config.get('model', 'claude-3-sonnet'),
    temperature=ai_config.get('temperature', 0.7)
)
```

### Monitoring System Configuration

```python
from src.config.settings import Settings

settings = Settings()
risk_thresholds = settings.get_risk_thresholds()
escalation_rules = settings.get_escalation_rules()

# Used by monitoring systems for threshold-based alerting
if project_risk > risk_thresholds['high_risk']:
    escalate_after = escalation_rules['critical_path_delay_hours']
    schedule_escalation(task, escalate_after)
```

### Hybrid Inference Configuration

```python
from src.config.config_loader import get_config

config = get_config()
hybrid_config = config.get_hybrid_inference_config()

# Used by dependency inference for performance tuning
if pattern_confidence > hybrid_config.pattern_confidence_threshold:
    # Skip AI analysis, trust pattern
    return pattern_dependencies
else:
    # Use AI for validation
    return ai_analyze_dependencies(tasks, hybrid_config)
```

This Configuration Management System represents one of Marcus's most critical foundational components, enabling the flexible, scalable, and maintainable configuration of the entire system while supporting both simple single-project setups and complex multi-project enterprise deployments.
