# Marcus Configuration Reference

> **📖 See Also:**
> - [Local Development](local-development.md) — first-time setup and directory structure
> - [Development Workflow](development-workflow.md) — daily development workflows

This is the comprehensive reference for all Marcus configuration options. For setup guides and workflows, see the linked documents above.

> Marcus runs **locally** via `./marcus start`. Docker is required only if you choose Planka as your kanban provider — it runs Planka + Postgres as infrastructure. Marcus itself does **not** run inside Docker in the current default workflow.

---

## Quick Start

### Basic Configuration

```bash
# 1. Copy the example config and edit it
cp config_marcus.example.json config_marcus.json

# 2. Set your LLM API key in .env
cp .env.example .env
echo "CLAUDE_API_KEY=sk-ant-..." >> .env

# 3. Start Marcus (SQLite kanban — zero external dependencies)
./marcus start
```

To use a non-default config file:

```bash
MARCUS_CONFIG=config_marcus.json.planka ./marcus start
```

To switch transports or ports:

```bash
./marcus start --port 5000           # custom HTTP port
./marcus start --stdio                # stdio transport
./marcus start --multi                # multi-endpoint mode
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
| `MARCUS_DECOMPOSER` | Task decomposition strategy (`contract_first` or `feature_based`) | `contract_first` |

### Kanban Integration
| Variable | Description | Default |
|----------|-------------|---------|
| `MARCUS_KANBAN_PROVIDER` | Provider: `sqlite`, `planka`, `github`, or `linear` | `sqlite` |

> Marcus uses **SQLite by default**. No environment variable is required for the default setup. The `KANBAN_PROVIDER` (without prefix) is also accepted as a legacy fallback.

#### SQLite Provider (default)
| Field (config_marcus.json) | Description | Default |
|----------------------------|-------------|---------|
| `kanban.sqlite_db_path` | Path to SQLite database | `./data/kanban.db` |
| `kanban.sqlite_attachments_dir` | Path for task attachments | `./data/attachments` |

> SQLite has no environment variables — it's configured via `config_marcus.json` only. Marcus creates the file on first project creation.

#### Planka Provider
| Variable | Description | Required |
|----------|-------------|----------|
| `MARCUS_KANBAN_PLANKA_BASE_URL` | Planka server URL | Yes |
| `MARCUS_KANBAN_PLANKA_EMAIL` | Planka login email | Yes |
| `MARCUS_KANBAN_PLANKA_PASSWORD` | Planka password | Yes |
| `MARCUS_KANBAN_PLANKA_PROJECT_ID` | Project UUID | Optional (auto-discovered if omitted) |
| `MARCUS_KANBAN_PLANKA_BOARD_ID` | Board UUID | Optional (auto-discovered if omitted) |

#### GitHub Provider *(alpha — provider exists, end-to-end testing pending)*
| Variable | Description | Required |
|----------|-------------|----------|
| `MARCUS_KANBAN_GITHUB_TOKEN` | GitHub personal access token | Yes |
| `MARCUS_KANBAN_GITHUB_OWNER` | GitHub username/org | Yes |
| `MARCUS_KANBAN_GITHUB_REPO` | Repository name | Yes |

#### Linear Provider *(alpha — provider exists, end-to-end testing pending)*
| Variable | Description | Required |
|----------|-------------|----------|
| `MARCUS_KANBAN_LINEAR_API_KEY` | Linear API key | Yes |
| `MARCUS_KANBAN_LINEAR_TEAM_ID` | Linear team ID | Yes |

### AI Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `MARCUS_AI_ENABLED` | Enable/disable AI features | `true` |
| `MARCUS_LLM_PROVIDER` | Provider: `anthropic`, `openai`, `local` | `anthropic` |
| `MARCUS_AI_MODEL` | Model name | `claude-haiku-4-5-20251001` |

#### Anthropic (Claude)
| Variable | Description | Required |
|----------|-------------|----------|
| `MARCUS_AI_ANTHROPIC_API_KEY` | Anthropic API key (canonical) | Yes if using Claude |
| `CLAUDE_API_KEY` | Alternative key name. Marcus prefers this so it doesn't collide with Claude Code's subscription auth (`ANTHROPIC_API_KEY`) | Fallback |

#### OpenAI
| Variable | Description | Required |
|----------|-------------|----------|
| `MARCUS_AI_OPENAI_API_KEY` | OpenAI API key | Yes if using GPT |

#### Local LLM (Ollama)
| Variable | Description | Required |
|----------|-------------|----------|
| `MARCUS_LOCAL_LLM_PATH` | Model name (e.g., `qwen2.5-coder:7b`) — maps to `ai.local_model` in the config file | Yes if using local |
| `MARCUS_LOCAL_LLM_URL` | Ollama server URL (e.g., `http://localhost:11434/v1`) — maps to `ai.local_url` | Optional |
| `MARCUS_LOCAL_LLM_KEY` | API key for the local server — maps to `ai.local_key` | Optional |

### Communication
| Variable | Description | Default |
|----------|-------------|---------|
| `MARCUS_SLACK_ENABLED` | Enable Slack notifications | `false` |
| `MARCUS_SLACK_WEBHOOK_URL` | Slack webhook URL | — |
| `MARCUS_EMAIL_ENABLED` | Enable email notifications | `false` |

### Monitoring
| Variable | Description | Default |
|----------|-------------|---------|
| `MARCUS_MONITORING_INTERVAL` | Monitoring interval (seconds) | `900` (15 min) |

---

## Configuration Priority

Marcus loads configuration in this order (later overrides earlier):

1. **Default values** (built into code)
2. **Config file** (path resolved by `MARCUS_CONFIG` env var, then current dir, then project root, then `~/.marcus/`)
3. **Environment variables** (highest priority)

Example:

```bash
# Config file has: "ai.model": "claude-haiku-4-5-20251001"
# Environment variable overrides it:
MARCUS_AI_MODEL=claude-sonnet-4-6 ./marcus start
# Result: Uses claude-sonnet-4-6
```

---

## Configuration File Format

The actual schema uses **flat keys with prefixes** under each section (matches `config_marcus.example.json`):

```json
{
  "kanban": {
    "provider": "sqlite",
    "sqlite_db_path": "./data/kanban.db",
    "sqlite_attachments_dir": "./data/attachments",
    "planka_base_url": "http://localhost:3333",
    "planka_email": "demo@demo.demo",
    "planka_password": "demo",  // pragma: allowlist secret
    "github_token": "${GITHUB_TOKEN}",
    "github_owner": "${GITHUB_OWNER}",
    "github_repo": "${GITHUB_REPO}",
    "linear_api_key": "${LINEAR_API_KEY}",
    "linear_team_id": "${LINEAR_TEAM_ID}"
  },
  "ai": {
    "provider": "anthropic",
    "anthropic_api_key": "${CLAUDE_API_KEY}",
    "openai_api_key": "${OPENAI_API_KEY}",
    "local_model": "qwen2.5-coder:7b",
    "local_url": "http://localhost:11434/v1",
    "local_key": "none",
    "model": "claude-haiku-4-5-20251001",
    "temperature": 0.1,
    "max_tokens": 4096,
    "enabled": true
  },
  "features": {
    "events": true,
    "context": true,
    "memory": false,
    "visibility": false
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

> Provider-specific keys live **alongside** `provider` (flat), not nested. `${VAR}` references are interpolated from the environment at load time.

---

## Common Configuration Patterns

### Switching between providers

```bash
# Default — SQLite, zero setup
./marcus start

# Use Planka instead (requires Docker for Planka + Postgres)
MARCUS_KANBAN_PROVIDER=planka ./marcus start
```

Or maintain multiple config files:

```bash
MARCUS_CONFIG=config_marcus.json.planka ./marcus start
MARCUS_CONFIG=config_marcus.json.github ./marcus start
```

### Using different AI models

```bash
# Higher-tier Claude
MARCUS_AI_MODEL=claude-sonnet-4-6 ./marcus start
MARCUS_AI_MODEL=claude-opus-4-7 ./marcus start

# Free local Ollama model
MARCUS_LLM_PROVIDER=local \
MARCUS_LOCAL_LLM_PATH=qwen2.5-coder:7b \
./marcus start
```

### Multiple Marcus Instances (parallel experiments)

As of v0.4.0-dev (parallel experiment platform), multiple Marcus instances can run side by side, each with its own SQLite kanban DB:

```bash
# Instance 1 on port 4298 (default), DB ./data/kanban-A.db
MARCUS_CONFIG=config_a.json ./marcus start

# Instance 2 on port 5000, DB ./data/kanban-B.db
MARCUS_CONFIG=config_b.json ./marcus start --port 5000
```

Each agent connects via the `MARCUS_URL` environment variable (`http://localhost:4298/mcp` or `http://localhost:5000/mcp`). Posidonius automates this for batch experiments.

### Selecting the decomposer

```bash
# Default: contract_first (works on tightly-coupled and loosely-coupled projects)
./marcus start

# Legacy feature-based decomposition
MARCUS_DECOMPOSER=feature_based ./marcus start

# Per-call override (passed to create_project as options["decomposer"])
```

See [Contract-First Decomposition](../concepts/contract-first-decomposition.md) for the trade-offs.

---

## Configuration Best Practices

1. **Use environment variables for secrets** (API keys, tokens). Reference them in `config_marcus.json` via `${VAR_NAME}`.
2. **Use config files for structure** (board IDs, model names, feature flags).
3. **Create a `.env` file** for persistent local settings — Marcus reads it automatically.
4. **Keep multiple config files per environment** (`config_marcus.json.dev`, `config_marcus.json.prod`).
5. **Never commit API keys** to version control. `.env` is gitignored by default.

---

## See Also

- [Local Development](local-development.md) — setup and troubleshooting
- [Development Workflow](development-workflow.md) — daily workflows
- [Quickstart](../getting-started/quickstart.md) — five-minute setup
- [Agent Workflow Guide](../guides/agent-workflows/agent-workflow.md)
- [Contract-First Decomposition](../concepts/contract-first-decomposition.md)
