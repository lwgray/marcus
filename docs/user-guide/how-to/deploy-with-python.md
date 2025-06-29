# How to Deploy Marcus with Python

> **Goal**: Deploy Marcus directly using Python for development or lightweight production  
> **Time**: 5-15 minutes  
> **When to use**: Development environments, debugging, or when Docker isn't available

## Prerequisites

Before starting, ensure you have:
- Marcus source code
- Python 3.8 or higher
- pip package manager
- Virtual environment tool (venv or virtualenv)
- Git installed

## Quick Answer

Deploy Marcus with Python:
```bash
# Clone, install, and run
git clone https://github.com/your-org/pm-agent.git
cd pm-agent
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m marcus_mcp_server
```

## Detailed Steps

### 1. Set Up Python Environment

Create an isolated Python environment:

```bash
# Check Python version (must be 3.8+)
python --version

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Verify activation
which python  # Should show venv path
```

### 2. Install Dependencies

Install Marcus and its dependencies:

```bash
# Upgrade pip first
pip install --upgrade pip

# Install production dependencies
pip install -r requirements.txt

# For development (includes testing tools)
pip install -r requirements-dev.txt

# Install Marcus as editable package
pip install -e .

# Verify installation
pip list | grep pm-agent
```

### 3. Configure Environment

Set up configuration files and environment variables:

```bash
# Create .env file
cat > .env << EOF
# Core settings
ANTHROPIC_API_KEY=your-anthropic-api-key
KANBAN_PROVIDER=github
PM_AGENT_LOG_LEVEL=INFO
PM_AGENT_PORT=3100

# GitHub provider
GITHUB_TOKEN=your-github-token
GITHUB_OWNER=your-username
GITHUB_REPO=your-repo
GITHUB_PROJECT_NUMBER=1

# Optional settings
PM_AGENT_WORKERS=4
PM_AGENT_TASK_TIMEOUT=300
EOF

# Create config directory
mkdir -p config

# Generate default configuration
python -m marcus_mcp_server --generate-config
```

### 4. Run Marcus

Start Marcus with various options:

```bash
# Basic start
python -m marcus_mcp_server

# With specific config file
python -m marcus_mcp_server --config config/production.json

# With debug logging
python -m marcus_mcp_server --log-level DEBUG

# On custom port
python -m marcus_mcp_server --port 3200

# With auto-reload for development
pip install watchdog
watchmedo auto-restart -d src -p "*.py" -- python -m marcus_mcp_server
```

### 5. Set Up as System Service

Configure Marcus to run as a system service:

#### Linux (systemd)
```bash
# Create service file
sudo tee /etc/systemd/system/pm-agent.service << EOF
[Unit]
Description=Marcus MCP Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/path/to/pm-agent
Environment="PATH=/path/to/pm-agent/venv/bin"
ExecStart=/path/to/pm-agent/venv/bin/python -m marcus_mcp_server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable pm-agent
sudo systemctl start pm-agent
sudo systemctl status pm-agent
```

#### macOS (launchd)
```bash
# Create plist file
cat > ~/Library/LaunchAgents/com.pm-agent.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" 
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.pm-agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/pm-agent/venv/bin/python</string>
        <string>-m</string>
        <string>marcus_mcp_server</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/pm-agent</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

# Load service
launchctl load ~/Library/LaunchAgents/com.pm-agent.plist
```

#### Windows (Task Scheduler)
```powershell
# Create scheduled task
$action = New-ScheduledTaskAction -Execute "C:\path\to\pm-agent\venv\Scripts\python.exe" `
    -Argument "-m marcus_mcp_server" -WorkingDirectory "C:\path\to\pm-agent"

$trigger = New-ScheduledTaskTrigger -AtStartup

Register-ScheduledTask -TaskName "Marcus" -Action $action -Trigger $trigger `
    -RunLevel Highest -Description "Marcus MCP Server"
```

## Verification

Verify your deployment is working:
```bash
# Check if Marcus is running
curl http://localhost:3100/health

# Test MCP tools
python -c "
from marcus_mcp_server import test_connection
import asyncio
asyncio.run(test_connection())
"

# Check logs
tail -f logs/pm-agent.log
```

You should see:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "python_version": "3.11.5",
  "uptime_seconds": 120
}
```

## Options and Variations

### Option 1: Production with Gunicorn
Use Gunicorn for better performance:
```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:3100 \
  --timeout 120 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  "marcus_mcp_server:create_app()"
```

### Option 2: Development with Hot Reload
Enable automatic reloading during development:
```bash
# Install development tools
pip install watchdog python-dotenv

# Run with auto-reload
export FLASK_ENV=development
watchmedo auto-restart -d src -p "*.py" \
  --recursive -- python -m marcus_mcp_server --debug
```

### Option 3: Virtual Environment Management
Use pipenv or poetry for better dependency management:
```bash
# Using pipenv
pip install pipenv
pipenv install
pipenv run python -m marcus_mcp_server

# Using poetry
pip install poetry
poetry install
poetry run python -m marcus_mcp_server
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No module named 'pm_agent'" | Run `pip install -e .` in project root |
| "Python version not supported" | Use pyenv to install Python 3.8+: `pyenv install 3.11.5` |
| "Permission denied on port 3100" | Use a port > 1024 or run with sudo (not recommended) |
| "ImportError: cannot import name" | Ensure all dependencies installed: `pip install -r requirements.txt` |
| "venv activate not working" | Check shell type and use appropriate activation script |
| "SSL certificate verification failed" | Update certificates: `pip install --upgrade certifi` |
| "Memory error" | Increase Python memory limit or optimize code |
| "Asyncio event loop errors" | Ensure using Python 3.8+ with proper async support |

## Performance Optimization

### Process Management
```python
# pm_agent_config.py
import multiprocessing

# Optimize worker processes
WORKER_PROCESSES = min(multiprocessing.cpu_count(), 4)
WORKER_CLASS = "uvloop"  # Faster event loop
WORKER_CONNECTIONS = 1000
KEEPALIVE = 5
```

### Memory Management
```bash
# Limit memory usage
ulimit -v 2097152  # 2GB limit

# Or use Python memory profiling
pip install memory-profiler
python -m memory_profiler marcus_mcp_server.py
```

### Logging Configuration
```python
# config/logging.yaml
version: 1
formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handlers:
  file:
    class: logging.handlers.RotatingFileHandler
    filename: logs/pm-agent.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
    formatter: default
  console:
    class: logging.StreamHandler
    formatter: default
root:
  level: INFO
  handlers: [console, file]
```

## Monitoring and Maintenance

### Health Monitoring Script
```bash
#!/bin/bash
# monitor_pm_agent.sh

while true; do
    if ! curl -f http://localhost:3100/health > /dev/null 2>&1; then
        echo "Marcus is down, restarting..."
        source venv/bin/activate
        python -m marcus_mcp_server &
    fi
    sleep 30
done
```

### Log Rotation
```bash
# /etc/logrotate.d/pm-agent
/path/to/pm-agent/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 pm-agent pm-agent
    sharedscripts
    postrotate
        systemctl reload pm-agent
    endscript
}
```

### Backup Script
```bash
#!/bin/bash
# backup_pm_agent.sh

BACKUP_DIR="/backup/pm-agent/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup code and config
tar -czf "$BACKUP_DIR/pm-agent-code.tar.gz" \
    --exclude=venv --exclude=__pycache__ \
    /path/to/pm-agent

# Backup data
cp -r /path/to/pm-agent/data "$BACKUP_DIR/"
cp /path/to/pm-agent/.env "$BACKUP_DIR/.env.backup"
```

## Related Guides

- [How to Deploy with Docker](/how-to/deploy-with-docker)
- [How to Deploy on Kubernetes](/how-to/deploy-kubernetes)
- [How to Configure Marcus](/how-to/configure-pm-agent)
- [Python Best Practices](/reference/python-best-practices)

## References

- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)
- [Marcus Configuration Reference](/reference/configuration)
- [Python Deployment Guide](https://packaging.python.org/guides/deploying/)
- [Systemd Service Management](https://www.freedesktop.org/software/systemd/man/systemd.service.html)