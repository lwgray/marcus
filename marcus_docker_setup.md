# Marcus Docker Setup for Claude Code

This guide provides complete step-by-step instructions for installing and launching Marcus as a Docker container and connecting it to Claude Code.

## Prerequisites

- Docker and Docker Compose installed
- Claude Code (Claude Desktop) installed
- Git installed
- API keys for:
  - Anthropic (required)
  - Your chosen kanban provider (GitHub, Linear, or Planka)

## Step 1: Clone the Repository

```bash
cd ~
git clone https://github.com/your-username/pm-agent.git
cd pm-agent
```

## Step 2: Create Environment File

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
nano .env  # or use any text editor
```

Add your API keys to the `.env` file:

```env
# Required
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Choose your kanban provider (github, linear, or planka)
KANBAN_PROVIDER=github

# For GitHub
GITHUB_TOKEN=your-github-token
GITHUB_OWNER=your-github-username
GITHUB_REPO=your-repo-name

# For Linear (if using)
LINEAR_API_KEY=your-linear-api-key
LINEAR_TEAM_ID=your-team-id

# For Planka (if using)
PLANKA_PROJECT_NAME=your-project-name
```

## Step 3: Build the Docker Image

```bash
docker-compose build
```

This builds the Marcus Docker image with all dependencies.

## Step 4: Start the Marcus MCP Container

```bash
docker-compose --profile mcp up -d marcus-mcp
```

This starts the special MCP-configured container that Claude Code can communicate with.

## Step 5: Verify Container is Running

```bash
docker ps | grep marcus-mcp-stdio
```

You should see the `marcus-mcp-stdio` container running.

## Step 6: Add Marcus to Claude Code

```bash
claude mcp add marcus -- docker exec -i marcus-mcp-stdio python marcus.py
```

## Step 7: Test the Connection

In Claude Code, type:
```
Use the marcus ping tool
```

You should see:
```
✓ Status: online
✓ Service: Marcus
✓ Provider: github (or your chosen provider)
```

## Step 8: Start Using Marcus

### Register as an Agent
```
Use the marcus register_agent tool with:
- agent_id: "claude-001"
- name: "Claude Worker"
- role: "Full-Stack Developer"
- skills: ["python", "javascript", "react", "api"]
```

### Request a Task
```
Use the marcus request_next_task tool with agent_id "claude-001"
```

### Report Progress
```
Use the marcus report_task_progress tool with:
- agent_id: "claude-001"
- task_id: [from previous step]
- status: "in_progress"
- progress: 50
- message: "Completed initial analysis"
```

## Alternative Setup: Auto-Start Container

If you prefer not to keep the container running continuously, you can use this alternative:

```bash
claude mcp add marcus docker-compose run --rm -T marcus-mcp
```

This will:
- Start a new container when Claude Code needs Marcus
- Remove the container when done (`--rm`)
- Use no TTY (`-T`) which is required for MCP

## Managing Marcus

### Stop Marcus
```bash
docker-compose --profile mcp down
```

### View Logs
```bash
docker logs marcus-mcp-stdio
```

### Restart Marcus
```bash
docker-compose --profile mcp restart marcus-mcp
```

### Update Marcus
```bash
git pull
docker-compose build
docker-compose --profile mcp up -d marcus-mcp
```

## Troubleshooting

### "MCP Server failed to start"
1. Check your `.env` file has all required keys
2. Ensure Docker is running: `docker info`
3. Check container logs: `docker logs marcus-mcp-stdio`
4. Verify the build succeeded: `docker images | grep pm-agent`

### "No module named marcus_mcp_server"
1. Ensure the container built successfully
2. Check that `marcus_mcp_server.py` exists in the container:
   ```bash
   docker exec marcus-mcp-stdio ls -la marcus.py
   ```

### "Connection refused" or timeout errors
1. Check if your kanban provider is accessible
2. Verify API keys are correct
3. For Planka, ensure it's running locally
4. Check Docker network: `docker network ls`

### Container exits immediately
1. Check logs: `docker logs marcus-mcp-stdio`
2. Verify environment variables are set correctly
3. Test Marcus locally first:
   ```bash
   docker run -it --rm --env-file .env pm-agent python marcus.py
   ```

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | Yes |
| `KANBAN_PROVIDER` | Choose: `github`, `linear`, or `planka` | Yes |
| `GITHUB_TOKEN` | GitHub personal access token | If using GitHub |
| `GITHUB_OWNER` | GitHub username or org | If using GitHub |
| `GITHUB_REPO` | GitHub repository name | If using GitHub |
| `LINEAR_API_KEY` | Linear API key | If using Linear |
| `LINEAR_TEAM_ID` | Linear team ID | If using Linear |
| `PLANKA_PROJECT_NAME` | Planka project name | If using Planka |

## Docker Compose Configuration

The `marcus-mcp` service in `docker-compose.yml` is specifically configured for MCP:

```yaml
marcus-mcp:
  build: .
  container_name: marcus-mcp-stdio
  environment:
    # All environment variables from .env
  volumes:
    - ./config:/app/config
    - ./logs:/app/logs
    - ./data:/app/data
    - ./prompts:/app/prompts
  command: python marcus.py
  stdin_open: true    # Required for MCP
  tty: false         # MCP uses stdio, not TTY
  networks:
    - marcus-network
  profiles:
    - mcp            # Only starts with --profile mcp
```

## Next Steps

1. Create tasks in your kanban board
2. Register multiple AI agents with different skills
3. Watch Marcus coordinate task assignments
4. Monitor progress through your kanban board
5. Use the visualization dashboard (optional):
   ```bash
   docker-compose --profile full up -d
   ```
   Then open http://localhost:4298

## Additional Resources

- [Marcus Documentation](docs/sphinx/source/index.rst)
- [Claude Desktop Setup Guide](docs/sphinx/source/user_guide/claude_desktop_setup.md)
- [Troubleshooting Guide](docs/sphinx/source/reference/troubleshooting.md)
- [Developer Guide](docs/sphinx/source/developer/index.rst)
