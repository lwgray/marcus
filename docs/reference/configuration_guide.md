# PM Agent Configuration Guide

> **Type**: Configuration  
> **Version**: 1.0.0  
> **Last Updated**: 2025-06-25

## Overview

This guide provides comprehensive documentation for configuring the PM Agent system, including all available options, environment variables, and configuration files.

## Synopsis

```json
{
  "monitoring_interval": 900,
  "ai_settings": {
    "model": "claude-3-sonnet-20241022",
    "temperature": 0.7
  },
  "team_config": {
    "default": {
      "skills": ["Python", "JavaScript"],
      "capacity": 40
    }
  }
}
```

## Description

PM Agent uses a hierarchical configuration system that supports JSON configuration files, environment variables, and runtime overrides. Configuration is loaded in the following order (later sources override earlier ones):

1. Default configuration (built-in)
2. Configuration file (JSON)
3. Environment variables
4. Runtime parameters

## Parameters

### Core Configuration

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `monitoring_interval` | integer | No | `900` | Seconds between project state refreshes (15 minutes) |
| `stall_threshold_hours` | integer | No | `24` | Hours before a task is considered stalled |
| `health_check_interval` | integer | No | `3600` | Seconds between system health checks (1 hour) |

### Parameter Details

#### `monitoring_interval`
Controls how often PM Agent refreshes project state from the kanban board. Lower values provide more real-time updates but increase API calls.
- Minimum: 60 seconds
- Maximum: 3600 seconds
- Recommended: 900 seconds (15 minutes)

#### `stall_threshold_hours`
Defines when a task without updates is considered stalled and may trigger escalation.
- Minimum: 4 hours
- Maximum: 168 hours (1 week)
- Recommended: 24 hours

### Risk Thresholds

```json
{
  "risk_thresholds": {
    "high_risk": 0.8,
    "medium_risk": 0.5,
    "timeline_buffer": 0.2
  }
}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `high_risk` | float | No | `0.8` | Threshold for high risk classification (0.0-1.0) |
| `medium_risk` | float | No | `0.5` | Threshold for medium risk classification (0.0-1.0) |
| `timeline_buffer` | float | No | `0.2` | Buffer percentage for timeline calculations |

### Escalation Rules

```json
{
  "escalation_rules": {
    "stuck_task_hours": 8,
    "blocker_escalation_hours": 4,
    "critical_path_delay_hours": 2
  }
}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `stuck_task_hours` | integer | No | `8` | Hours before escalating a stuck task |
| `blocker_escalation_hours` | integer | No | `4` | Hours before escalating an unresolved blocker |
| `critical_path_delay_hours` | integer | No | `2` | Hours of delay on critical path before escalation |

### Communication Settings

```json
{
  "communication_rules": {
    "daily_plan_time": "08:00",
    "progress_check_time": "14:00",
    "end_of_day_summary": "18:00"
  }
}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `daily_plan_time` | string | No | `"08:00"` | Time for daily planning (HH:MM format) |
| `progress_check_time` | string | No | `"14:00"` | Time for progress check (HH:MM format) |
| `end_of_day_summary` | string | No | `"18:00"` | Time for daily summary (HH:MM format) |

### Integration Settings

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `slack_enabled` | boolean | No | `false` | Enable Slack notifications |
| `email_enabled` | boolean | No | `false` | Enable email notifications |
| `kanban_comments_enabled` | boolean | No | `true` | Enable kanban board comments |

### Team Configuration

```json
{
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
        "detailed_instructions": true,
        "technical_depth": "medium"
      }
    }
  }
}
```

#### Team Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `skills` | array[string] | No | `[]` | Default skills for team members |
| `work_patterns.preferred_hours` | string | No | `"9am-6pm"` | Preferred working hours |
| `work_patterns.deep_work_blocks` | string | No | `"2-4 hours"` | Typical focus time blocks |
| `work_patterns.context_switch_cost` | string | No | `"medium"` | Cost of context switching: low, medium, high |

### Performance Settings

```json
{
  "performance": {
    "max_concurrent_analyses": 5,
    "cache_ttl_seconds": 300,
    "batch_notification_delay": 1.0
  }
}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `max_concurrent_analyses` | integer | No | `5` | Maximum concurrent AI analyses |
| `cache_ttl_seconds` | integer | No | `300` | Cache time-to-live in seconds |
| `batch_notification_delay` | float | No | `1.0` | Delay for batching notifications |

### AI Settings

```json
{
  "ai_settings": {
    "model": "claude-3-sonnet-20241022",
    "temperature": 0.7,
    "max_tokens": 2000,
    "retry_attempts": 3,
    "retry_delay": 1.0
  }
}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `model` | string | No | `"claude-3-sonnet-20241022"` | AI model to use |
| `temperature` | float | No | `0.7` | Response randomness (0.0-1.0) |
| `max_tokens` | integer | No | `2000` | Maximum response tokens |
| `retry_attempts` | integer | No | `3` | Number of retry attempts |
| `retry_delay` | float | No | `1.0` | Delay between retries in seconds |

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | API key for Claude AI | `sk-ant-...` |
| `KANBAN_PROVIDER` | Kanban provider type | `planka`, `github`, `trello` |

### Provider-Specific Variables

#### Planka
| Variable | Description | Example |
|----------|-------------|---------|
| `PLANKA_SERVER_URL` | Planka server URL | `http://localhost:3000` |
| `PLANKA_USERNAME` | Planka username | `admin@example.com` |
| `PLANKA_PASSWORD` | Planka password | `secure-password` |

#### GitHub
| Variable | Description | Example |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub personal access token | `ghp_...` |
| `GITHUB_OWNER` | Repository owner | `myorg` |
| `GITHUB_REPO` | Repository name | `myproject` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PM_AGENT_CONFIG` | Path to config file | `config/pm_agent_config.json` |
| `PM_AGENT_MONITORING_INTERVAL` | Override monitoring interval | `900` |
| `PM_AGENT_SLACK_ENABLED` | Enable Slack integration | `false` |
| `PM_AGENT_EMAIL_ENABLED` | Enable email integration | `false` |
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications | - |

## Examples

### Basic Example
```bash
# Minimal configuration with environment variables
export ANTHROPIC_API_KEY="sk-ant-..."
export KANBAN_PROVIDER="planka"
export PLANKA_SERVER_URL="http://localhost:3000"
export PLANKA_USERNAME="admin@example.com"
export PLANKA_PASSWORD="password"

python main.py
```

### Advanced Example
```json
// config/pm_agent_config.json
{
  "monitoring_interval": 600,
  "stall_threshold_hours": 12,
  "risk_thresholds": {
    "high_risk": 0.7,
    "medium_risk": 0.4,
    "timeline_buffer": 0.25
  },
  "escalation_rules": {
    "stuck_task_hours": 6,
    "blocker_escalation_hours": 2,
    "critical_path_delay_hours": 1
  },
  "communication_rules": {
    "daily_plan_time": "09:00",
    "progress_check_time": "13:00",
    "end_of_day_summary": "17:00"
  },
  "slack_enabled": true,
  "ai_settings": {
    "model": "claude-3-opus-20240229",
    "temperature": 0.5,
    "max_tokens": 4000
  },
  "team_config": {
    "backend": {
      "skills": ["Python", "Django", "PostgreSQL"],
      "work_patterns": {
        "preferred_hours": "10am-7pm",
        "deep_work_blocks": "3-5 hours",
        "context_switch_cost": "high"
      }
    },
    "frontend": {
      "skills": ["JavaScript", "React", "CSS"],
      "work_patterns": {
        "preferred_hours": "9am-6pm",
        "deep_work_blocks": "2-3 hours",
        "context_switch_cost": "medium"
      }
    }
  }
}
```

### Real-World Example
```bash
# Production deployment with Docker
cat > config/production.json << EOF
{
  "monitoring_interval": 300,
  "stall_threshold_hours": 8,
  "risk_thresholds": {
    "high_risk": 0.75,
    "medium_risk": 0.45
  },
  "slack_enabled": true,
  "kanban_comments_enabled": true,
  "performance": {
    "max_concurrent_analyses": 10,
    "cache_ttl_seconds": 600
  },
  "ai_settings": {
    "model": "claude-3-sonnet-20241022",
    "temperature": 0.3,
    "retry_attempts": 5
  }
}
EOF

# Run with Docker
docker run -d \
  -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
  -e KANBAN_PROVIDER="github" \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  -e GITHUB_OWNER="myorg" \
  -e GITHUB_REPO="production-app" \
  -e PM_AGENT_CONFIG="/app/config/production.json" \
  -e SLACK_WEBHOOK_URL="${SLACK_WEBHOOK}" \
  -v $(pwd)/config:/app/config \
  pm-agent:latest
```

## Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| `CONFIG_NOT_FOUND` | Configuration file not found | Check file path and permissions |
| `INVALID_JSON` | Configuration file has invalid JSON | Validate JSON syntax |
| `MISSING_API_KEY` | ANTHROPIC_API_KEY not set | Set environment variable |
| `INVALID_PROVIDER` | Unknown kanban provider | Use: planka, github, or trello |
| `INVALID_TIME_FORMAT` | Time not in HH:MM format | Use 24-hour format (e.g., "14:00") |

## Notes

- All time values use 24-hour format in the system's local timezone
- Configuration changes require restart to take effect
- Sensitive values (API keys, passwords) should use environment variables
- Team configurations can be customized per team or role
- Performance settings should be tuned based on system resources

## Performance Considerations

- Lower monitoring intervals increase API usage and costs
- Higher cache TTL reduces AI API calls but may show stale data
- Concurrent analysis limits prevent API rate limiting
- Batch notification delays reduce notification spam

## Security Considerations

- Never commit API keys or passwords to version control
- Use environment variables for all sensitive configuration
- Restrict configuration file permissions (chmod 600)
- Rotate API keys regularly
- Use secure webhook URLs for integrations

## Version History

| Version | Changes |
|---------|---------|
| 1.0.0 | Initial configuration system |
| 0.9.0 | Added team-specific configurations |
| 0.8.0 | Added performance tuning options |
| 0.7.0 | Added AI model configuration |

## See Also

- [Environment Variables Reference](/reference/environment_variables)
- [MCP Tools API](/reference/mcp_tools_api)
- [Deployment Guide](/how-to/deployment)