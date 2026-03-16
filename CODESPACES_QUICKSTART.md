# GitHub Codespaces Manual Setup Guide

This guide walks you through setting up Marcus in GitHub Codespaces from scratch.

## Prerequisites

- GitHub account
- AI API key (choose one):
  - **Anthropic API key** (recommended) - Get at [https://console.anthropic.com/](https://console.anthropic.com/)
  - **OpenAI API key** - Get at [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
  - **Ollama** (free, local) - No API key needed

---

## Step 1: Open in GitHub Codespaces

1. Go to [https://github.com/lwgray/marcus](https://github.com/lwgray/marcus)
2. Click the green **"Code"** button
3. Click the **"Codespaces"** tab
4. Click **"Create codespace on main"**
5. Wait for the Codespace to initialize (2-3 minutes)

---

## Step 2: Verify Docker is Available

Once your Codespace opens, verify Docker is running:

```bash
docker --version
docker compose version
```

You should see version information for both commands.

---

## Step 3: Start Planka and PostgreSQL

Start the Kanban board and database services:

```bash
docker compose up -d postgres planka
```

Wait about 20-30 seconds for services to start, then verify:

```bash
docker compose ps
```

You should see both `postgres` and `planka` with status "Up".

---

## Step 4: Access Planka

1. In VS Code, go to the **"PORTS"** tab at the bottom
2. Find port **3333** (Planka)
3. Click the **globe icon** to open it in your browser
   - Or hover and click "Open in Browser"

**Login credentials:**
- Email: `demo@demo.demo`
- Password: `demo`  <!-- pragma: allowlist secret -->

---

## Step 5: Create Your Project and Board

In Planka:

1. **Click "Create project"**
   - Name it something like "Marcus AI Project"
   - Click "Create"

2. **Get the Project ID**
   - Look at the URL: `https://xxx.github.dev/projects/0987654321`
   - Copy the project ID: `0987654321`

3. **Create a Board**
   - Click inside your project
   - Click "+ Add board" or similar
   - Name it "My Board"

4. **Get the Board ID**
   - Look at the URL: `https://xxx.github.dev/boards/1234567890`
   - Copy the board ID: `1234567890`

5. **Create Board Lists (CRITICAL!)**
   - Click "+ Add another list" to create these 4 lists:
     - **Backlog**
     - **In Progress**
     - **Blocked**
     - **Done**

⚠️ **Without these lists, task creation will fail!**

---

## Step 6: Configure Marcus

Create your configuration file:

```bash
cp config_marcus.example.json config_marcus.json
```

Edit the config file:

```bash
code config_marcus.json
```

Update these fields:

```json
{
  "project_id": "YOUR_PROJECT_ID_FROM_STEP_5",
  "board_id": "YOUR_BOARD_ID_FROM_STEP_5",
  "project_name": "Marcus AI Project",
  "board_name": "My Board",
  "ai": {
    "provider": "anthropic",
    "anthropic": {
      "api_key": "YOUR_ANTHROPIC_API_KEY_HERE",  // pragma: allowlist secret
      "model": "claude-3-5-sonnet-20241022"
    }
  },
  "kanban": {
    "provider": "planka",
    "board_name": "My Board"
  },
  "transport": {
    "type": "http",
    "http": {
      "host": "0.0.0.0",
      "port": 4298
    }
  }
}
```

**For OpenAI instead:**
```json
{
  "ai": {
    "provider": "openai",
    "openai": {
      "api_key": "YOUR_OPENAI_API_KEY_HERE",  // pragma: allowlist secret
      "model": "gpt-4"
    }
  }
}
```

**For Ollama (free, but slower):**
```json
{
  "ai": {
    "provider": "ollama",
    "ollama": {
      "base_url": "http://localhost:11434",
      "model": "llama2"
    }
  }
}
```

Save the file (Ctrl+S or Cmd+S).

---

## Step 7: Start Marcus

Start the Marcus service:

```bash
docker compose up -d marcus
```

Verify it's running:

```bash
docker compose ps
docker compose logs marcus
```

You should see Marcus starting up and connecting to Planka.

---

## Step 8: Make Ports Public (IMPORTANT!)

For MCP to work from your local machine, make ports public:

1. Go to the **"PORTS"** tab
2. Find port **4298** (Marcus MCP Server)
3. Right-click → **"Port Visibility"** → **"Public"**
4. Copy the forwarded address (e.g., `https://abc123.githubpreview.dev`)

---

## Step 9: Connect Your Local AI Agent

On your **local machine** (not in Codespaces), configure Claude Code or your MCP client:

### For Claude Code:

```bash
# Use the public URL from Step 8
claude mcp add --transport http marcus https://YOUR-CODESPACE-URL:4298/mcp
```

### For Manual MCP Configuration:

Add to your MCP settings:

```json
{
  "mcpServers": {
    "marcus": {
      "url": "https://YOUR-CODESPACE-URL:4298/mcp"
    }
  }
}
```

---

## Step 10: Configure Your AI Agent

Copy the agent system prompt to enable autonomous work:

1. Open [https://github.com/lwgray/marcus/blob/main/prompts/Agent_prompt.md](https://github.com/lwgray/marcus/blob/main/prompts/Agent_prompt.md)
2. Copy the entire contents
3. Add to your Claude Code configuration (CLAUDE.md file or project instructions)

This enables your agent to:
- ✅ Register with Marcus automatically
- ✅ Request and work on tasks continuously
- ✅ Report progress at 25%, 50%, 75%, 100%
- ✅ Share context through artifacts and decisions

---

## Step 11: Start Building!

Tell your configured AI agent:

```
"Create a project for a todo app with Marcus and start working"
```

The agent will:
1. Register with Marcus
2. Create tasks on the Planka board
3. Request and work on tasks automatically
4. Report progress as it goes
5. Continue until all tasks are done

---

## Monitoring Your Work

### View Planka Board

Go to the PORTS tab and open port 3333 to see:
- Tasks moving through columns
- Task details and progress
- What agents are working on

### View Marcus Logs

```bash
# Live logs
docker compose logs -f marcus

# Last 50 lines
docker compose logs --tail 50 marcus

# All service logs
docker compose logs -f
```

### Check Service Status

```bash
docker compose ps
```

---

## Managing Services

### Restart Marcus

```bash
docker compose restart marcus
```

### Stop Everything

```bash
docker compose down
```

### Start Everything

```bash
docker compose up -d
```

### View Logs for Debugging

```bash
# Marcus logs
docker compose logs marcus

# Planka logs
docker compose logs planka

# Postgres logs
docker compose logs postgres
```

---

## Troubleshooting

### Port 3333 or 4298 Not Showing

Wait a minute and refresh the PORTS tab. If still missing:

```bash
docker compose ps  # Verify services are running
docker compose logs planka  # Check for errors
```

### "Connection refused" from MCP

1. Verify port 4298 is **Public** in PORTS tab
2. Check Marcus is running: `docker compose ps`
3. Check logs: `docker compose logs marcus`

### "No tasks available"

The agent needs to create a project first using `create_project` tool.

### "Failed to create any tasks"

Your Planka board needs lists! Go back to Step 5 and create the 4 required lists.

### Planka Not Loading

```bash
docker compose logs planka
docker compose restart planka
```

Wait 30 seconds, then try opening port 3333 again.

### Marcus Configuration Errors

```bash
# Check config syntax
cat config_marcus.json | python -m json.tool

# View Marcus errors
docker compose logs marcus
```

---

## Working with Multiple Agents

### Option 1: Multiple Claude Windows

1. Open multiple browser tabs/windows with Claude
2. Each connects to the same Marcus MCP server
3. Each agent will get different tasks from the board

### Option 2: Use Subagents

In Claude, use the Task tool to spawn subagents. They automatically register with Marcus and work independently.

---

## Next Steps

- **Read the docs**: Check out [docs/source/](docs/source/) for detailed guides
- **Customize workflows**: See [Agent Workflow Guide](docs/source/guides/agent-workflows/agent-workflow.md)
- **Join the community**: [Discord](https://discord.gg/marcus)
- **Report issues**: [GitHub Issues](https://github.com/lwgray/marcus/issues)

---

## Stopping Your Codespace

When you're done:

1. **Stop services** (optional, saves resources):
   ```bash
   docker compose down
   ```

2. **Stop the Codespace**:
   - Click "Codespaces" in bottom-left corner
   - Select "Stop Current Codespace"

3. **Resume later**:
   - Go to [https://github.com/codespaces](https://github.com/codespaces)
   - Click on your Marcus codespace to resume

Your configuration and Planka data are preserved in Docker volumes!

---

## Architecture Notes

**How it works in Codespaces:**

```
┌─────────────────────────────────────────┐
│  GitHub Codespace (Cloud VM)            │
│                                          │
│  ┌────────────┐   ┌──────────────┐     │
│  │ PostgreSQL │   │   Planka     │     │
│  │  (Docker)  │   │  (Docker)    │     │
│  └─────┬──────┘   └──────┬───────┘     │
│        │                  │              │
│        └────────┬─────────┘              │
│                 │                        │
│          ┌──────▼────────┐               │
│          │    Marcus     │               │
│          │   (Docker)    │               │
│          │               │               │
│          │ kanban-mcp is │               │
│          │ built into    │               │
│          │ Docker image  │               │
│          │ at /app/      │               │
│          │ kanban-mcp/   │               │
│          └───────┬───────┘               │
│                  │                        │
│           Port 4298 (MCP)                │
└──────────────────┼──────────────────────┘
                   │
                   │ HTTPS (public URL)
                   │
            ┌──────▼────────┐
            │  Your Local   │
            │  AI Agent     │
            │ (Claude Code) │
            └───────────────┘
```

**Key Points:**
- kanban-mcp is **cloned from GitHub** during Docker image build
- It's at `/app/kanban-mcp/` inside the Marcus container
- No need to manually clone it in Codespaces
- Everything runs in Docker for consistency

---

**Questions?** Open an issue or join our [Discord](https://discord.gg/marcus)!
