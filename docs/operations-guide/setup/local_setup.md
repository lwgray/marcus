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
git clone https://github.com/lwgray/marcus.git
cd marcus
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

## Step 3: Launch MCP Locally

```bash
conda create -n marcus python=3.11 pip
pip install -r requirements.txt

python marcus.py &
```
## Step 4: Add Marcus to Claude Code

```bash
claude mcp add marcus python marcus.py
```

## Step 5: Test the Connection

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

## Step 6: Start Using Marcus

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

## Managing Marcus

### Stop Marcus
```bash
pkill -f marcus.py
```

## Troubleshooting

### "MCP Server failed to start"
1. Check your `.env` file has all required 

### "Connection refused" or timeout errors
1. Check if your kanban provider is accessible
2. Verify API keys are correct
3. For Planka, ensure it's running locally

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

## Next Steps

1. Create tasks in your kanban board
2. Register multiple AI agents with different skills
3. Watch Marcus coordinate task assignments
4. Monitor progress through your kanban board
5. Use the visualization dashboard (optional):
   ```bash
   python src/run_visualization.py
   ```
   Then open http://localhost:4298

## Additional Resources

- [Marcus Documentation](docs/sphinx/source/index.rst)
- [Claude Desktop Setup Guide](docs/sphinx/source/user_guide/claude_desktop_setup.md)
- [Troubleshooting Guide](docs/sphinx/source/reference/troubleshooting.md)
- [Developer Guide](docs/sphinx/source/developer/index.rst)
