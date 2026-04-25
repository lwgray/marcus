# Marcus CLI Commands

Marcus now provides a simple command-line interface for easy management.

## Installation

```bash
# Install system-wide
./install.sh

# Or add to PATH manually
export PATH="$PWD:$PATH"
```

## Usage

### Start Marcus

```bash
# Start with default settings (stdio transport)
marcus start

# Start with HTTP transport (recommended)
marcus start --http

# Start on custom port
marcus start --http --port 5000

# Run in foreground (see output)
marcus start --foreground
```

### Check Status

```bash
marcus status
```

Output:
```
✅ Marcus is running
   PID: 12345
   CPU: 2.1%
   Memory: 145.2 MB
   Uptime: 0:05:23
   Transport: HTTP
   Endpoint: http://127.0.0.1:4298/mcp
```

### View Logs

```bash
# View recent logs
marcus logs

# Follow logs in real-time
marcus logs --follow

# Show last 20 lines
marcus logs --tail 20
```

### Stop Marcus

```bash
marcus stop
```

### Configuration

```bash
# View current config
marcus config

# Edit config file
marcus config --edit
```

## Integration with Other Tools

### With Seneca

```bash
# Start Marcus with HTTP
marcus start --http

# In another terminal, start Seneca
seneca start
```

### With Claude

Marcus will automatically register its service for Claude to discover:

```bash
marcus start --http
# Claude can now connect to Marcus
```

## Environment Variables

Marcus loads environment variables from a `.env` file in the project root. See [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) for complete setup instructions.

### Required Variables

**AI Provider** (choose one):
- `CLAUDE_API_KEY` - Anthropic API key for Claude models. Named `CLAUDE_API_KEY`
  (not `ANTHROPIC_API_KEY`) so Marcus doesn't override Claude Code's
  subscription auth when both are running on the same machine.
- `OPENAI_API_KEY` - OpenAI API key (alternative)

**Kanban Backend** (if using Planka):
- `PLANKA_BASE_URL` - Planka server URL (e.g., `http://localhost:3333`)
- `PLANKA_EMAIL` - Planka user email
- `PLANKA_PASSWORD` - Planka user password

### Optional Variables

**Server Configuration:**
- `MARCUS_MCP_PORT` - MCP server port (default: 4298)
- `MARCUS_CONFIG` - Config file to use (default: `config_marcus.json`)
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

**Alternative Kanban Providers:**
- `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO` - For GitHub Projects
- `LINEAR_API_KEY`, `LINEAR_TEAM_ID` - For Linear

**Feature Flags:**
- `MARCUS_ENABLE_SUBTASKS` - Enable subtask functionality
- `MARCUS_MONITORING_INTERVAL` - Monitoring interval in seconds
- `MARCUS_SLACK_ENABLED`, `SLACK_WEBHOOK_URL` - Slack notifications
- `MARCUS_EMAIL_ENABLED` - Email notifications

### Setup

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your values:
   ```bash
   # Required
   CLAUDE_API_KEY=sk-ant-api03-your-key-here
   PLANKA_BASE_URL=http://localhost:3333
   PLANKA_EMAIL=demo@demo.demo
   PLANKA_PASSWORD=demo
   ```

3. The CLI automatically loads `.env` on startup

See `.env.example` for a complete template with all available options.

## Service Discovery

Marcus automatically creates service registry files in `~/.marcus/services/` for other tools to discover.

## Comparison with Other Tools

Similar to popular tools:

- `redis-server` / `redis-cli`
- `nginx` / `nginx -s reload`
- `docker run` / `docker stop`
- `kubectl apply` / `kubectl get`

Marcus follows standard Unix conventions for service management.
