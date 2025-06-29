# How to Troubleshoot Common Marcus Issues

> **Goal**: Diagnose and fix common problems with Marcus quickly  
> **Time**: 5-15 minutes depending on issue  
> **When to use**: When Marcus isn't working as expected or showing errors

## Prerequisites

Before starting, ensure you have:
- Marcus version 1.0 or higher
- Access to terminal/command line
- Docker installed (if using Docker setup)
- Admin/sudo access for permission issues

## Quick Answer

Most issues can be resolved with:
```bash
# Stop everything and restart
docker-compose down
./start.sh

# Or check Docker and API keys
docker ps
cat .env | grep -E "(API_KEY|TOKEN)"
```

## Detailed Steps

### 1. Diagnose the Problem Type

First, identify which category your issue falls into:

```bash
# Check if Marcus is running
docker-compose ps

# Check recent logs for errors
docker-compose logs --tail=50 pm-agent | grep -i error

# Check system health
curl http://localhost:3100/health
```

### 2. Fix Connection Issues

#### Cannot Connect to Marcus

```bash
# Verify Marcus is running
docker ps | grep pm-agent

# Check if port is accessible
nc -zv localhost 3100

# If port is blocked, find what's using it
lsof -i :3100  # Mac/Linux
netstat -ano | findstr :3100  # Windows
```

#### Cannot Connect to Kanban Provider

```bash
# Test Planka connection
curl -X POST http://localhost:3000/api/access-tokens \
  -H "Content-Type: application/json" \
  -d '{"emailOrUsername":"demo@demo.demo","password":"demo"}'

# Test GitHub connection
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user

# Test Linear connection  
curl -H "Authorization: $LINEAR_API_KEY" \
  https://api.linear.app/graphql \
  -d '{"query":"{ viewer { id } }"}'
```

### 3. Fix Authentication Issues

#### Invalid API Keys

```bash
# Check .env file format (no extra spaces!)
cat .env | sed 's/=.*/=***/' # Shows keys without values

# Verify Anthropic API key
python -c "
import os
from anthropic import Anthropic
client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
try:
    client.messages.create(model='claude-3-sonnet-20240229', max_tokens=1, messages=[])
except Exception as e:
    print(f'API Key Status: {e}')
"

# Fix common formatting issues
# Remove spaces and quotes
sed -i 's/ANTHROPIC_API_KEY=[ ]*/ANTHROPIC_API_KEY=/g' .env
sed -i 's/"//g' .env
```

#### GitHub Token Permissions

```bash
# Check token permissions
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user/repos | jq '.message'

# Required scopes: repo, project
# Get new token at: https://github.com/settings/tokens
```

### 4. Fix Task Management Issues

#### No Tasks Available

```bash
# For GitHub: Check issues exist
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$GITHUB_OWNER/$GITHUB_REPO/issues?state=open"

# For Planka: Check board has cards
docker-compose exec planka-db psql -U planka -c \
  "SELECT COUNT(*) FROM card WHERE list_id IN (SELECT id FROM list WHERE name='TODO');"

# Create test task via Marcus
curl -X POST http://localhost:3100/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Task","description":"Testing Marcus"}'
```

#### Tasks Not Being Assigned

```bash
# Check task labels match agent skills
# GitHub: Ensure issues have priority labels
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$GITHUB_OWNER/$GITHUB_REPO/labels"

# Check agent registration
curl http://localhost:3100/agents

# Re-register agent if needed
curl -X POST http://localhost:3100/agents/register \
  -H "Content-Type: application/json" \
  -d '{"name":"debug-agent","skills":["backend","frontend"]}'
```

### 5. Fix Docker Issues

#### Container Won't Start

```bash
# Check Docker daemon
docker info

# Clean up old containers
docker-compose down -v
docker system prune -f

# Rebuild with fresh image
docker-compose build --no-cache
docker-compose up -d

# Check container logs
docker-compose logs pm-agent
```

#### Permission Denied Errors

```bash
# Fix script permissions
chmod +x start.sh
chmod +x scripts/*.sh

# Fix Docker socket permissions (Linux)
sudo usermod -aG docker $USER
newgrp docker

# Fix file ownership
sudo chown -R $USER:$USER .
```

### 6. Fix Performance Issues

#### Slow Response Times

```bash
# Check resource usage
docker stats pm-agent

# Increase memory limits in docker-compose.yml
# Add under pm-agent service:
echo "
    mem_limit: 2g
    cpus: '2.0'
" >> docker-compose.yml

# Clear caches
docker-compose exec pm-agent rm -rf /tmp/*
docker-compose restart pm-agent
```

## Verification

Confirm everything is working:
```bash
# Full system check
./scripts/health_check.sh

# Or manual verification
curl http://localhost:3100/health
```

You should see:
```json
{
  "status": "healthy",
  "uptime": "0h 5m 23s",
  "registered_agents": 1,
  "active_tasks": 3,
  "kanban_provider": "github",
  "kanban_connected": true
}
```

## Options and Variations

### Option 1: Debug Mode
Use this when you need detailed logging:
```bash
# Enable debug logging
export PM_AGENT_LOG_LEVEL=DEBUG
docker-compose up
```

### Option 2: Fresh Start
For persistent issues, completely reset:
```bash
# Backup configuration
cp .env .env.backup
cp config_pm_agent.json config_pm_agent.json.backup

# Complete cleanup
docker-compose down -v
docker rmi pm-agent:latest
rm -rf logs/ temp/

# Fresh setup
./start.sh
```

### Option 3: Manual Mode
Run Marcus without Docker for debugging:
```bash
# Install dependencies
pip install -r requirements.txt

# Run directly with verbose output
python -m marcus_mcp_server --debug
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot connect to Docker daemon" | Start Docker Desktop or run `sudo systemctl start docker` |
| "Address already in use" | Change port in config or kill process using port |
| "Invalid token/API key" | Regenerate key and update .env file |
| "No module named 'pm_agent'" | Run `pip install -e .` in project directory |
| "Database connection refused" | Ensure Planka is running: `docker-compose ps planka-db` |
| "Rate limit exceeded" | Add delays between API calls or upgrade API plan |
| "SSL certificate error" | Update certificates: `pip install --upgrade certifi` |
| "Out of memory" | Increase Docker memory in Docker Desktop settings |

## Related Guides

- [How to Deploy Marcus](/how-to/deploy-pm-agent)
- [How to Configure Security](/how-to/security-best-practices)
- [How to Monitor Performance](/how-to/monitor-performance)
- [Troubleshooting Reference](/reference/troubleshooting)

## References

- [System Health API](/reference/api/health)
- [Configuration Reference](/reference/configuration)
- [Error Codes Reference](/reference/error-codes)
- [Docker Compose Reference](https://docs.docker.com/compose/)