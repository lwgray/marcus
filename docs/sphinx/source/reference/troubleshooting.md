# 🔧 Troubleshooting Guide

Something not working? Don't worry! Here are fixes for common problems.

## 🚨 Quick Fixes First

Before anything else, try these:

1. **Restart everything**:
   ```bash
   docker-compose down
   ./start.sh
   ```

2. **Check Docker is running**:
   - Look for Docker whale icon in your menu bar
   - If not there, start Docker Desktop

3. **Check your .env file**:
   ```bash
   cat .env
   ```
   Make sure your API keys are there!

## ❌ Common Problems

### "Permission denied" when running start.sh

**On Mac/Linux:**
```bash
chmod +x start.sh
```

**On Windows:**
Run in Administrator Command Prompt

### "Docker daemon is not running"

1. Start Docker Desktop
2. Wait 30 seconds for it to fully start
3. Try again

### "Invalid API key" errors

1. Check your `.env` file has the right keys
2. Make sure no extra spaces around the keys
3. Regenerate the key if needed

**Good:**
```
ANTHROPIC_API_KEY=sk-ant-abc123
```

**Bad:**
```
ANTHROPIC_API_KEY= sk-ant-abc123  # Extra space!
```

### "Cannot connect to GitHub"

1. Check your GitHub token has the right permissions:
   - `repo` (full control of repositories)
   - `project` (read project boards)

2. Make sure repo exists:
   ```bash
   # Should show your repo
   curl -H "Authorization: token YOUR_TOKEN" \
        https://api.github.com/repos/YOUR_USERNAME/YOUR_REPO
   ```

### "No tasks available"

1. Create issues in your GitHub repo
2. Label them with priority:
   - `priority/high`
   - `priority/medium`
   - `priority/low`

### Docker runs out of space

```bash
# Clean up Docker
docker system prune -a
```

### Logs folder is empty

```bash
# Create logs directory
mkdir -p logs/conversations logs/raw

# Fix permissions
chmod -R 777 logs/
```

### "Port already in use"

Another service is using the port:

```bash
# Find what's using port 8000
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process or change Marcus port
```

### Workers aren't connecting (Demo mode)

```bash
# Check workers are running
docker-compose --profile demo ps

# Restart just workers
docker-compose --profile demo restart worker-backend worker-frontend worker-qa
```

## 🔍 Debugging Steps

### 1. Check What's Running
```bash
docker-compose ps
```

Should show:
```
NAME                    STATUS
pm-agent-mcp-server     Up
```

### 2. Check Logs for Errors
```bash
docker-compose logs pm-agent | grep -i error
```

### 3. Test Marcus Manually
```bash
docker-compose exec pm-agent python -c "
from pm_agent_mcp_server_v2 import ping
import asyncio
print(asyncio.run(ping('test')))
"
```

### 4. Check Environment Variables
```bash
docker-compose exec pm-agent env | grep -E "(GITHUB|ANTHROPIC|KANBAN)"
```

## 🆘 Still Stuck?

### Collect Debug Info

Run this command and save the output:
```bash
echo "=== Docker Info ==="
docker --version
docker-compose --version
docker-compose ps

echo "=== Environment ==="
grep -v "KEY\|TOKEN" .env  # Hides secrets

echo "=== Recent Logs ==="
docker-compose logs --tail=50 pm-agent

echo "=== System ==="
uname -a
```

### Get Help

1. Check [FAQ](faq.md) for more answers
2. Search existing [GitHub Issues](https://github.com/your-repo/issues)
3. Create a new issue with your debug info

### Nuclear Option (Start Fresh)

⚠️ This deletes everything and starts over:

```bash
# Stop everything
docker-compose down -v

# Remove all Marcus containers/images
docker rm -f $(docker ps -a | grep pm-agent | awk '{print $1}')
docker rmi -f $(docker images | grep pm-agent | awk '{print $3}')

# Start fresh
rm .env
./start.sh
```

## 💡 Prevention Tips

1. **Always use ./start.sh** - It handles setup correctly
2. **Check Docker is running** before starting Marcus  
3. **Keep your .env file safe** - Back it up!
4. **Update regularly**:
   ```bash
   git pull
   docker-compose build --no-cache
   ```

---

Still having issues? Check the [FAQ](faq.md) or ask for help on GitHub!