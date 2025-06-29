# Marcus Environment Variables Reference

> **Type**: Configuration  
> **Version**: 1.0.0  
> **Last Updated**: 2025-06-25

## Overview

Complete reference for all environment variables used by the Marcus system, including required variables, provider-specific settings, and optional configurations.

## Synopsis

```bash
# Essential variables
export ANTHROPIC_API_KEY="sk-ant-api03-..."
export KANBAN_PROVIDER="planka"
export PLANKA_SERVER_URL="http://localhost:3000"
export PLANKA_USERNAME="admin@example.com"
export PLANKA_PASSWORD="secure-password"
```

## Description

Marcus uses environment variables for sensitive configuration values and deployment-specific settings. Variables are loaded from the system environment and can be supplemented with a `.env` file in the project root. Environment variables take precedence over configuration file settings.

## Parameters

### Core Variables

#### ANTHROPIC_API_KEY

**Required**: Yes  
**Type**: string  
**Default**: None  
**Description**: API key for Claude AI services

Your Anthropic API key for accessing Claude models. Required for all AI-powered features including task instruction generation and blocker analysis.

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-AbCdEfGhIjKlMnOpQrStUvWxYz1234567890"
```

#### KANBAN_PROVIDER

**Required**: Yes  
**Type**: string  
**Default**: `"planka"`  
**Valid Values**: `planka`, `github`, `trello`  
**Description**: Kanban board provider to use

Determines which kanban integration to use for task management.

```bash
export KANBAN_PROVIDER="github"  # Use GitHub Issues/Projects
```

#### PM_AGENT_CONFIG

**Required**: No  
**Type**: string  
**Default**: `"config/pm_agent_config.json"`  
**Description**: Path to JSON configuration file

Override the default configuration file location.

```bash
export PM_AGENT_CONFIG="/etc/pm-agent/production.json"
```

### Planka Provider Variables

Required when `KANBAN_PROVIDER="planka"`:

#### PLANKA_SERVER_URL

**Required**: Yes (for Planka)  
**Type**: string  
**Default**: None  
**Description**: URL of your Planka instance

```bash
export PLANKA_SERVER_URL="https://planka.company.com"
```

#### PLANKA_USERNAME

**Required**: Yes (for Planka)  
**Type**: string  
**Default**: None  
**Description**: Planka login username/email

```bash
export PLANKA_USERNAME="pm-agent@company.com"
```

#### PLANKA_PASSWORD

**Required**: Yes (for Planka)  
**Type**: string  
**Default**: None  
**Description**: Planka login password

```bash
export PLANKA_PASSWORD="secure-password-here"
```

### GitHub Provider Variables

Required when `KANBAN_PROVIDER="github"`:

#### GITHUB_TOKEN

**Required**: Yes (for GitHub)  
**Type**: string  
**Default**: None  
**Description**: GitHub personal access token with repo scope

```bash
export GITHUB_TOKEN="ghp_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890"
```

Token must have the following permissions:
- `repo` - Full control of private repositories
- `project` - Read/write access to projects

#### GITHUB_OWNER

**Required**: Yes (for GitHub)  
**Type**: string  
**Default**: None  
**Description**: GitHub organization or user name

```bash
export GITHUB_OWNER="my-organization"
```

#### GITHUB_REPO

**Required**: Yes (for GitHub)  
**Type**: string  
**Default**: None  
**Description**: GitHub repository name

```bash
export GITHUB_REPO="my-project"
```

### Trello Provider Variables

Required when `KANBAN_PROVIDER="trello"`:

#### TRELLO_API_KEY

**Required**: Yes (for Trello)  
**Type**: string  
**Default**: None  
**Description**: Trello API key

```bash
export TRELLO_API_KEY="your-trello-api-key"
```

#### TRELLO_TOKEN

**Required**: Yes (for Trello)  
**Type**: string  
**Default**: None  
**Description**: Trello API token

```bash
export TRELLO_TOKEN="your-trello-token"
```

#### TRELLO_BOARD_ID

**Required**: Yes (for Trello)  
**Type**: string  
**Default**: None  
**Description**: Trello board ID to manage

```bash
export TRELLO_BOARD_ID="5d5f2f5f2f5f2f5f2f5f2f5f"
```

### Configuration Override Variables

These variables override values in the configuration file:

#### PM_AGENT_MONITORING_INTERVAL

**Required**: No  
**Type**: integer  
**Default**: `900`  
**Description**: Seconds between project state refreshes

```bash
export PM_AGENT_MONITORING_INTERVAL="300"  # 5 minutes
```

#### PM_AGENT_SLACK_ENABLED

**Required**: No  
**Type**: boolean  
**Default**: `false`  
**Description**: Enable Slack notifications

```bash
export PM_AGENT_SLACK_ENABLED="true"
```

#### PM_AGENT_EMAIL_ENABLED

**Required**: No  
**Type**: boolean  
**Default**: `false`  
**Description**: Enable email notifications

```bash
export PM_AGENT_EMAIL_ENABLED="true"
```

### Integration Variables

#### SLACK_WEBHOOK_URL

**Required**: When Slack is enabled  
**Type**: string  
**Default**: None  
**Description**: Slack incoming webhook URL

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
```

#### SMTP_HOST

**Required**: When email is enabled  
**Type**: string  
**Default**: None  
**Description**: SMTP server hostname

```bash
export SMTP_HOST="smtp.gmail.com"
```

#### SMTP_PORT

**Required**: When email is enabled  
**Type**: integer  
**Default**: `587`  
**Description**: SMTP server port

```bash
export SMTP_PORT="465"
```

#### SMTP_USERNAME

**Required**: When email is enabled  
**Type**: string  
**Default**: None  
**Description**: SMTP authentication username

```bash
export SMTP_USERNAME="notifications@company.com"
```

#### SMTP_PASSWORD

**Required**: When email is enabled  
**Type**: string  
**Default**: None  
**Description**: SMTP authentication password

```bash
export SMTP_PASSWORD="app-specific-password"
```

### Logging Variables

#### PM_AGENT_LOG_LEVEL

**Required**: No  
**Type**: string  
**Default**: `"INFO"`  
**Valid Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`  
**Description**: Logging verbosity level

```bash
export PM_AGENT_LOG_LEVEL="DEBUG"
```

#### PM_AGENT_LOG_FILE

**Required**: No  
**Type**: string  
**Default**: `"pm_agent.log"`  
**Description**: Log file path

```bash
export PM_AGENT_LOG_FILE="/var/log/pm-agent/agent.log"
```

### Development Variables

#### PM_AGENT_DEBUG

**Required**: No  
**Type**: boolean  
**Default**: `false`  
**Description**: Enable debug mode

```bash
export PM_AGENT_DEBUG="true"
```

#### PM_AGENT_MOCK_KANBAN

**Required**: No  
**Type**: boolean  
**Default**: `false`  
**Description**: Use mock kanban provider for testing

```bash
export PM_AGENT_MOCK_KANBAN="true"
```

## Return Values

Environment variables don't have return values, but missing required variables will result in startup errors:

### Success Validation
```bash
$ python main.py --validate-config
INFO - Configuration is valid
INFO - All required environment variables present
```

### Error Response
```bash
$ python main.py
ERROR - ANTHROPIC_API_KEY environment variable is required
ERROR - PLANKA_SERVER_URL environment variable is required
```

## Examples

### Basic Example
```bash
# .env file for local development
ANTHROPIC_API_KEY=sk-ant-api03-test-key
KANBAN_PROVIDER=planka
PLANKA_SERVER_URL=http://localhost:3000
PLANKA_USERNAME=admin@local.test
PLANKA_PASSWORD=admin
```

### Advanced Example
```bash
# Production environment with all features
export ANTHROPIC_API_KEY="${SECURE_ANTHROPIC_KEY}"
export KANBAN_PROVIDER="github"
export GITHUB_TOKEN="${SECURE_GITHUB_TOKEN}"
export GITHUB_OWNER="acme-corp"
export GITHUB_REPO="production-app"

# Monitoring and notifications
export PM_AGENT_MONITORING_INTERVAL="300"
export PM_AGENT_SLACK_ENABLED="true"
export SLACK_WEBHOOK_URL="${SECURE_SLACK_WEBHOOK}"

# Performance tuning
export PM_AGENT_LOG_LEVEL="WARNING"
export PM_AGENT_CONFIG="/etc/pm-agent/production.json"
```

### Real-World Example
```yaml
# Kubernetes ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: pm-agent-config
data:
  KANBAN_PROVIDER: "github"
  GITHUB_OWNER: "my-org"
  GITHUB_REPO: "main-app"
  PM_AGENT_MONITORING_INTERVAL: "600"
  PM_AGENT_LOG_LEVEL: "INFO"
  
---
# Kubernetes Secret
apiVersion: v1
kind: Secret
metadata:
  name: pm-agent-secrets
type: Opaque
stringData:
  ANTHROPIC_API_KEY: "sk-ant-api03-..."
  GITHUB_TOKEN: "ghp_..."
  SLACK_WEBHOOK_URL: "https://hooks.slack.com/..."
```

## Error Codes

| Error | Description | Solution |
|-------|-------------|----------|
| `ENV_VAR_MISSING` | Required environment variable not set | Set the missing variable |
| `INVALID_PROVIDER` | Unknown kanban provider specified | Use: planka, github, or trello |
| `INVALID_LOG_LEVEL` | Invalid log level specified | Use: DEBUG, INFO, WARNING, or ERROR |
| `INVALID_BOOLEAN` | Boolean var not "true" or "false" | Use lowercase "true" or "false" |

## Notes

- Environment variables override configuration file settings
- Use a `.env` file for local development (don't commit it)
- All sensitive values should use environment variables
- Boolean values must be lowercase "true" or "false"
- File paths can be relative or absolute

## Security Best Practices

1. **Never commit secrets**: Add `.env` to `.gitignore`
2. **Use secret management**: In production, use proper secret storage
3. **Rotate keys regularly**: Update API keys periodically
4. **Limit permissions**: Use minimal required scopes for tokens
5. **Audit access**: Log environment variable access in production

## Platform-Specific Notes

### Docker
```dockerfile
# Pass variables at runtime
docker run -e ANTHROPIC_API_KEY="..." pm-agent

# Or use env file
docker run --env-file .env pm-agent
```

### systemd
```ini
# /etc/systemd/system/pm-agent.service
[Service]
Environment="ANTHROPIC_API_KEY=sk-ant-..."
EnvironmentFile=/etc/pm-agent/env
```

### Windows
```batch
:: Set variables in batch script
set ANTHROPIC_API_KEY=sk-ant-...
set KANBAN_PROVIDER=planka
python main.py
```

## Version History

| Version | Changes |
|---------|---------|
| 1.0.0 | Complete environment variable documentation |
| 0.9.0 | Added integration variables |
| 0.8.0 | Added provider-specific variables |

## See Also

- [Configuration Guide](/reference/configuration_guide)
- [Deployment Guide](/how-to/deployment)
- [Security Best Practices](/reference/security)