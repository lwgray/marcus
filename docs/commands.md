# 🎮 Quick Commands Reference

Here are all the commands you need to know!

## 🚀 Starting PM Agent

### Basic Start
```bash
./start.sh
```
Just starts PM Agent with GitHub (or whatever's in your `.env`)

### Demo Mode 
```bash
./start.sh demo
```
Starts with 3 fake workers to see it in action

### With Dashboard
```bash
./start.sh full
```
Starts with a visual dashboard at http://localhost:4298

### For Development
```bash
./start.sh dev
```
Live reloading when you change code

### Local Planka
```bash
./start.sh local-planka
```
⚠️ Only for local use! Starts with Planka board

### Remote Hosting
```bash
./start.sh remote
```
For hosting online (no Planka allowed)

## 🛑 Stopping PM Agent

### Stop Everything
```bash
docker-compose down
```

### Stop and Delete Data
```bash
docker-compose down -v
```
⚠️ This deletes logs and data!

## 📊 Viewing Logs

### See All Logs
```bash
docker-compose logs
```

### Follow Live Logs
```bash
docker-compose logs -f
```

### Just PM Agent Logs
```bash
docker-compose logs -f pm-agent
```

### Worker Logs (Demo Mode)
```bash
docker-compose logs -f worker-backend worker-frontend worker-qa
```

## 🔄 Restarting

### After Changing .env
```bash
docker-compose restart
```

### Full Restart
```bash
docker-compose down
docker-compose up -d
```

## 🏥 Health Checks

### See What's Running
```bash
docker-compose ps
```

### Check PM Agent Status
```bash
docker-compose exec pm-agent python -c "print('PM Agent is healthy!')"
```

## 📁 File Locations

### View Logs Folder
```bash
ls -la logs/conversations/
```

### Read Latest Log
```bash
cat logs/conversations/$(ls -t logs/conversations/ | head -1)
```

### Edit Configuration
```bash
nano .env
```

## 🆘 Troubleshooting Commands

### Rebuild Everything
```bash
docker-compose build --no-cache
```

### Check Docker
```bash
docker --version
docker-compose --version
```

### Fix Permissions (Mac/Linux)
```bash
chmod +x start.sh
chmod -R 777 logs/
```

### See Container Logs
```bash
docker logs pm-agent-mcp-server
```

## 🎯 Common Workflows

### First Time Setup
```bash
git clone <repo>
cd pm-agent
./start.sh
nano .env  # Add your keys
docker-compose restart
```

### Daily Use
```bash
cd pm-agent
./start.sh
# Create tasks in GitHub
# Watch it work!
```

### Check Progress
```bash
docker-compose logs -f pm-agent | grep "task"
```

### Emergency Stop
```bash
docker-compose down
docker stop $(docker ps -q)  # Stops ALL Docker containers
```

## 💡 Pro Tips

1. **Can't find logs?**
   ```bash
   find . -name "*.json" -path "*/logs/*" -mtime -1
   ```

2. **Want pretty logs?**
   ```bash
   docker-compose logs pm-agent | grep -E "(ASSIGN|COMPLETE|PROGRESS)"
   ```

3. **Quick restart alias** (add to ~/.bashrc):
   ```bash
   alias pmrestart='docker-compose down && ./start.sh'
   ```

---

Need more help? Check out [Troubleshooting](troubleshooting.md) for common issues!