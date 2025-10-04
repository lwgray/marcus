# Marcus Configuration Reference

> **📖 See Also:**
> - [Local Development](local-development.md) - First-time setup and directory structure
> - [Development Workflow](development-workflow.md) - Daily development workflows

This is a comprehensive reference for all Marcus configuration options. For setup guides and workflows, see the linked documents above.

---

## Quick Start

### Basic Configuration

```bash
# 1. Choose a config file (optional - defaults to config_marcus.json)
MARCUS_CONFIG=config_marcus.json.anthropic docker-compose up -d

# 2. Or create .env for persistent configuration
echo "MARCUS_CONFIG=config_marcus.json.anthropic" > .env
docker-compose up -d
```

---

## All Environment Variables

### Core Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `MARCUS_CONFIG` | Path to configuration JSON file | `config_marcus.json` |
| `MARCUS_PORT` | HTTP server port | `4298` |
| `MARCUS_DEBUG` | Enable debug logging | `false` |
| `MARCUS_TRANSPORT` | Transport type (`stdio` or `http`) | `stdio` |

### Kanban Integration
| Variable | Description | Required |
|----------|-------------|----------|
| `MARCUS_KANBAN_PROVIDER` | Provider: `planka`, `github`, or `linear` | Yes |

#### Planka Provider
| Variable | Description | Required |
|----------|-------------|----------|
| `MARCUS_KANBAN_PLANKA_BASE_URL` | Planka server URL | Yes |
| `MARCUS_KANBAN_PLANKA_EMAIL` | Planka login email | Yes |
| `MARCUS_KANBAN_PLANKA_PASSWORD` | Planka password | Yes |
| `MARCUS_KANBAN_PLANKA_PROJECT_ID` | Project UUID | Yes |
| `MARCUS_KANBAN_PLANKA_BOARD_ID` | Board UUID | Yes |

#### GitHub Provider
| Variable | Description | Required |
|----------|-------------|----------|
| `MARCUS_KANBAN_GITHUB_TOKEN` | GitHub personal access token | Yes |
| `MARCUS_KANBAN_GITHUB_OWNER` | GitHub username/org | Yes |
| `MARCUS_KANBAN_GITHUB_REPO` | Repository name | Yes |

#### Linear Provider
| Variable | Description | Required |
|----------|-------------|----------|
| `MARCUS_KANBAN_LINEAR_API_KEY` | Linear API key | Yes |
| `MARCUS_KANBAN_LINEAR_TEAM_ID` | Linear team ID | Yes |

### AI Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `MARCUS_AI_ENABLED` | Enable/disable AI features | `true` |
| `MARCUS_LLM_PROVIDER` | Provider: `anthropic`, `openai`, `local` | `anthropic` |
| `MARCUS_AI_MODEL` | Model name | `claude-3-sonnet-20241022` |

#### Anthropic (Claude)
| Variable | Description | Required |
|----------|-------------|----------|
| `MARCUS_AI_ANTHROPIC_API_KEY` | Anthropic API key | Yes if using Claude |
| `ANTHROPIC_API_KEY` | Alternative API key | Fallback |

#### OpenAI
| Variable | Description | Required |
|----------|-------------|----------|
| `MARCUS_AI_OPENAI_API_KEY` | OpenAI API key | Yes if using GPT |

#### Local LLM (Ollama)
| Variable | Description | Required |
|----------|-------------|----------|
| `MARCUS_LOCAL_LLM_PATH` | Model name (e.g., `codellama:13b`) | Yes if using local |
| `MARCUS_LOCAL_LLM_URL` | LLM server URL | Optional |
| `MARCUS_LOCAL_LLM_KEY` | API key for local server | Optional |

### Communication
| Variable | Description | Default |
|----------|-------------|---------|
| `MARCUS_SLACK_ENABLED` | Enable Slack notifications | `false` |
| `MARCUS_SLACK_WEBHOOK_URL` | Slack webhook URL | - |
| `MARCUS_EMAIL_ENABLED` | Enable email notifications | `false` |

### Monitoring
| Variable | Description | Default |
|----------|-------------|---------|
| `MARCUS_MONITORING_INTERVAL` | Monitoring interval (seconds) | `900` (15 min) |

---

## Configuration Priority

Marcus loads configuration in this order (later overrides earlier):

1. **Default values** (built into code)
2. **Config file** (specified by `MARCUS_CONFIG`)
3. **Environment variables** (highest priority)

Example:
```bash
# Config file has: "model": "claude-3-sonnet"
# Environment variable overrides it:
MARCUS_AI_MODEL=claude-3-opus docker-compose up -d
# Result: Uses claude-3-opus
```

---

## Configuration File Format

```json
{
  "kanban": {
    "provider": "planka",
    "planka": {
      "base_url": "http://localhost:3333",
      "email": "demo@demo.demo",
      "password": "demo",  // pragma: allowlist secret
      "project_id": "your-project-uuid",
      "board_id": "your-board-uuid"
    }
  },
  "ai": {
    "provider": "anthropic",
    "anthropic_api_key": "sk-ant-...",  // pragma: allowlist secret
    "model": "claude-3-sonnet-20241022",
    "enabled": true
  },
  "monitoring": {
    "interval": 900,
    "stall_threshold_hours": 24
  },
  "communication": {
    "slack_enabled": false,
    "email_enabled": false
  }
}
```

---

## Common Configuration Patterns

### Switching Between Providers

```bash
# Development with Planka
MARCUS_CONFIG=config_marcus.json.planka docker-compose up -d

# Production with GitHub
MARCUS_CONFIG=config_marcus.json.github docker-compose up -d
```

### Using Different AI Models

```bash
# Use Claude Opus instead of Sonnet
MARCUS_AI_MODEL=claude-3-opus-20240229 docker-compose up -d

# Use local Ollama model
MARCUS_LLM_PROVIDER=local \
MARCUS_LOCAL_LLM_PATH=codellama:13b \
docker-compose up -d
```

### Multiple Marcus Instances

```bash
# Instance 1: Personal projects (port 4298)
MARCUS_CONFIG=config_personal.json docker-compose -p marcus-personal up -d

# Instance 2: Work projects (requires changing port in docker-compose.yml)
MARCUS_CONFIG=config_work.json docker-compose -p marcus-work -f docker-compose-work.yml up -d
```

---

## Configuration Best Practices

1. **Use environment variables for secrets** (API keys, tokens)
2. **Use config files for structure** (board IDs, model names)
3. **Create a .env file** for persistent Docker Compose settings
4. **Keep multiple config files** for different environments
5. **Never commit API keys** to version control

---

## See Also

- [Local Development](local-development.md) - Setup and troubleshooting
- [Development Workflow](development-workflow.md) - Daily workflows
- [Docker Quickstart](../../DOCKER_QUICKSTART.md) - Docker setup
- [Agent Workflow Guide](../guides/agent-workflows/agent-workflow.md)
