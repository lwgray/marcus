# 🐳 PM Agent Docker Setup

## Quick Start (30 seconds!)

1. **Clone the repository**
   ```bash
   git clone <your-repo>
   cd pm-agent
   ```

2. **Run the setup**
   ```bash
   ./start.sh
   ```

3. **Edit `.env` file with your credentials**
   ```bash
   # Edit the generated .env file
   nano .env  # or use your favorite editor
   ```

4. **Restart with your configuration**
   ```bash
   docker-compose restart
   ```

That's it! PM Agent is now running in a Docker container.

## 🎯 Running Modes

### Basic Mode (Default)
Just the PM Agent MCP server:
```bash
./start.sh
```

### Demo Mode
PM Agent + 3 mock workers (Backend, Frontend, QA):
```bash
./start.sh demo
```

### Full Mode
PM Agent + Visualization UI:
```bash
./start.sh full
```
Then open http://localhost:4298 to see the visualization.

### Development Mode
PM Agent with live code reloading:
```bash
./start.sh dev
```

## 🔧 Configuration

### Environment Variables

The `.env` file contains all configuration:

```env
# Choose your kanban provider
KANBAN_PROVIDER=github  # or 'linear' or 'planka'

# GitHub setup (for KANBAN_PROVIDER=github)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
GITHUB_OWNER=your-username
GITHUB_REPO=your-repo-name

# Linear setup (for KANBAN_PROVIDER=linear)
LINEAR_API_KEY=lin_api_xxxxxxxxxxxxx
LINEAR_TEAM_ID=your-team-id

# Planka setup (for KANBAN_PROVIDER=planka)
PLANKA_PROJECT_NAME=your-project

# AI Keys
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
```

## 📊 Monitoring

### View Logs
```bash
# All services
docker-compose logs -f

# Just PM Agent
docker-compose logs -f pm-agent

# Just workers (in demo mode)
docker-compose logs -f worker-backend worker-frontend worker-qa
```

### Check Status
```bash
# See running containers
docker-compose ps

# Check PM Agent health
docker-compose exec pm-agent python -c "print('PM Agent is healthy!')"
```

## 🛠️ Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs pm-agent

# Rebuild if needed
docker-compose build --no-cache
```

### Permission issues
```bash
# Fix log directory permissions
chmod -R 777 logs/
```

### Clean restart
```bash
# Stop everything
docker-compose down

# Remove volumes (careful - deletes logs!)
docker-compose down -v

# Start fresh
./start.sh
```

## 🚀 Using PM Agent

### With Claude Desktop
1. PM Agent runs as an MCP server inside Docker
2. Configure Claude Desktop to connect to the containerized server
3. Use the PM Agent tools from Claude

### With Mock Workers (Demo Mode)
```bash
# Start demo mode
./start.sh demo

# Workers will automatically:
# - Register with PM Agent
# - Request tasks
# - Report progress
# - Complete tasks
```

### With Real GitHub Tasks
1. Create issues in your GitHub repository
2. Label them with priority (priority/high, priority/medium, priority/low)
3. Workers will pick them up automatically

## 📁 Directory Structure

```
pm-agent/
├── docker-compose.yml    # Docker services configuration
├── Dockerfile           # PM Agent container definition
├── start.sh            # Easy start script
├── .env                # Your configuration (git ignored)
├── logs/               # Conversation and system logs
├── data/               # Persistent data
└── visualization-ui/   # Web interface (optional)
```

## 🔒 Security Notes

- The `.env` file contains sensitive API keys - never commit it!
- Docker containers run in isolated networks
- MCP communication happens via stdio, not network ports
- Only the visualization UI exposes ports (4298, 8080)

## 🎉 Next Steps

1. **Create GitHub Issues**: Add some tasks to your repository
2. **Watch the Magic**: See workers pick up and complete tasks
3. **Check Logs**: Monitor the conversation flow in `logs/conversations/`
4. **Customize Workers**: Edit `prompts/system_prompts.md` for different behaviors

Need help? Check the logs first - they contain detailed conversation flows!