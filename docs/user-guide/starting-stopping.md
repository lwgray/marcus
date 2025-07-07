# Starting and Stopping Marcus

## Basic Commands

Marcus provides a unified command-line interface for all operations:

### Starting Marcus
```bash
# Start Marcus with web UI (default)
./marcus

# Start on a different port
./marcus --port 8080

# Start without web UI (MCP server only)
./marcus --no-web
```

### Stopping Marcus
```bash
# Stop all Marcus processes
./marcus stop

# Or use Ctrl+C in the terminal where Marcus is running
```

### Restarting Marcus
```bash
# Stop all instances and start a fresh one
./marcus restart

# Restart on a different port
./marcus restart --port 8080
```

### Checking Status
```bash
# See if Marcus is running
./marcus status
```

### Getting Help
```bash
# View all available commands and options
./marcus help
```

## Process Management

### What Gets Started

When you run `./marcus`, it starts:
1. **Marcus MCP Server** - The core AI orchestration engine
2. **Web UI Server** - Flask dashboard on port 5000 (by default)
3. **Background Services** - Token monitoring, cost tracking, etc.

### What Gets Stopped

`./marcus stop` will terminate:
- All Python processes running marcus
- The Flask web server
- Any background monitoring tasks
- WebSocket connections

### Clean Restart

`./marcus restart` ensures:
- All old processes are fully terminated
- No port conflicts
- Fresh state initialization
- Clean log files

## Shell Integration

For easier access from anywhere, add this to your shell profile:

### For Bash (~/.bashrc)
```bash
# Marcus quick access
marcus() {
    cd ~/dev/marcus && ./marcus "$@"
}
alias marcus-stop="marcus stop"
alias marcus-restart="marcus restart"
alias marcus-status="marcus status"
```

### For Zsh (~/.zshrc)
```bash
# Marcus quick access
marcus() {
    cd ~/dev/marcus && ./marcus "$@"
}
alias marcus-stop="marcus stop"
alias marcus-restart="marcus restart"
alias marcus-status="marcus status"
```

After adding, reload your shell:
```bash
source ~/.bashrc  # or ~/.zshrc
```

Now you can use Marcus from anywhere:
```bash
marcus              # Start Marcus
marcus restart      # Restart Marcus
marcus stop         # Stop Marcus
marcus status       # Check if running
```

## Troubleshooting

### Port Already in Use
If you see "Port 5000 is in use":
```bash
# Force stop all processes and restart
./marcus restart

# Or use a different port
./marcus restart --port 8080
```

### Processes Won't Stop
If processes don't stop cleanly:
```bash
# Force kill all Marcus processes
pkill -9 -f "python.*marcus"
pkill -9 -f "python.*src.api.app"
```

### Finding Marcus Processes
```bash
# List all Marcus-related processes
ps aux | grep -E "marcus|src.api.app" | grep -v grep
```

### Checking Logs
```bash
# View real-time logs
tail -f logs/conversations/realtime_*.jsonl

# View Flask logs (if running in background)
tail -f logs/flask.log
```

## Systemd Integration (Linux)

For production deployments, create a systemd service:

```ini
# /etc/systemd/system/marcus.service
[Unit]
Description=Marcus AI Project Management
After=network.target

[Service]
Type=simple
User=marcus
WorkingDirectory=/opt/marcus
ExecStart=/opt/marcus/marcus
ExecStop=/opt/marcus/marcus stop
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then manage with:
```bash
sudo systemctl start marcus
sudo systemctl stop marcus
sudo systemctl restart marcus
sudo systemctl status marcus
```