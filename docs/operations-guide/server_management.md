# Marcus Server Management Guide

## Starting and Stopping Marcus with Stdio Preservation

This guide covers proper management of the Marcus MCP server while preserving stdio processes for correct MCP protocol communication.

## Starting Marcus

### Main Marcus Server (Full Features)
```bash
cd /Users/lwgray/dev/marcus
python -m src.marcus_mcp.server
```

### Agent-Only Server (Restricted Tools)
```bash
cd /Users/lwgray/dev/marcus
python -m src.marcus_mcp.agent_server
```

### With Process Management
```bash
# Start in background with nohup
nohup python -m src.marcus_mcp.server > marcus.log 2>&1 &

# Or use screen/tmux for session management
screen -S marcus python -m src.marcus_mcp.server
```

## Stopping Marcus Gracefully

### 1. Find Marcus Process
```bash
# Find by process name
ps aux | grep marcus_mcp

# Or by python process with marcus
pgrep -f "marcus_mcp"
```

### 2. Graceful Shutdown
```bash
# Send SIGTERM for graceful shutdown
kill -TERM <PID>

# Or use pkill
pkill -TERM -f "marcus_mcp"
```

### 3. Force Stop (if needed)
```bash
# Only if graceful shutdown fails
kill -KILL <PID>
```

## Process Management Features

### Built-in Cleanup
Marcus automatically handles cleanup on exit:
- Closes log files properly
- Unregisters from service discovery
- Cleans up resources and connections
- Persists any pending data

### Service Discovery Integration
- Marcus registers itself for discovery on startup
- Provides service info including PID and log locations
- Auto-cleanup on shutdown removes registration

## Monitoring and Management

### Check if Marcus is Running
```bash
# Check service registry
python -c "from src.core.service_registry import get_marcus_services; print(get_marcus_services())"

# Check process directly
pgrep -f marcus_mcp
```

### View Real-time Logs
```bash
# Follow log output
tail -f logs/conversations/realtime_*.jsonl

# Or if running in foreground, logs go to stderr
```

### Health Check
```bash
# Use the ping tool via MCP if client is connected
# Or check if process is responsive
kill -0 <PID>  # Returns 0 if process exists and is responsive
```

## Best Practices

### Use Process Managers for Production
```bash
# With systemd
sudo systemctl start marcus
sudo systemctl stop marcus

# With supervisor
supervisorctl start marcus
supervisorctl stop marcus
```

### Development Workflow
```bash
# Start in development mode
python -m src.marcus_mcp.server

# Ctrl+C for clean shutdown
# Marcus handles SIGINT gracefully
```

### Multiple Instances
```bash
# Different ports/configs for multiple projects
MARCUS_CONFIG=project1.json python -m src.marcus_mcp.server &
MARCUS_CONFIG=project2.json python -m src.marcus_mcp.server &
```

## Stdio Preservation Notes

Marcus uses **stdio_server()** from the MCP protocol:
- **stdin/stdout**: Used for MCP communication (DO NOT redirect)
- **stderr**: Used for status/error messages (safe to redirect)
- **Log files**: Separate files in `logs/conversations/`

### Key Points:
- Don't redirect stdout/stdin (required for MCP protocol)
- Stderr is safe to redirect for logging
- Use `kill -TERM` for graceful shutdown
- Marcus has built-in cleanup handlers
- Clean shutdown preserves all stdio streams

## Configuration Impact on Startup

When features are enabled in `config_marcus.json`:
- **events**: Enables event system for monitoring
- **context**: Activates dependency tracking and context awareness
- **memory**: Enables predictive analytics and learning
- **visibility**: Activates visualization components

These features initialize additional components during startup, which may slightly increase startup time but provide enhanced intelligence capabilities.

## Troubleshooting

### Marcus Won't Start
1. Check if another instance is already running
2. Verify configuration file is valid JSON
3. Ensure required environment variables are set
4. Check that required services (Planka, etc.) are accessible

### Graceful Shutdown Fails
1. Check if process is actually Marcus: `ps -p <PID> -o comm=`
2. Try waiting longer (complex operations may need time to complete)
3. Check logs for any error messages
4. Use force kill as last resort

### Stdio Issues
1. Never pipe stdin/stdout when running Marcus
2. If using process managers, ensure they preserve stdio
3. For debugging, use stderr redirection only: `2>debug.log`
