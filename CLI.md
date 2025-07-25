# Marcus CLI Commands

Marcus now provides a simple command-line interface for easy management.

## Installation

```bash
# Install system-wide
./install.sh

# Or add to PATH manually
export PATH="$PWD:$PATH"
```

## Usage

### Start Marcus

```bash
# Start with default settings (stdio transport)
marcus start

# Start with HTTP transport (recommended)
marcus start --http

# Start on custom port
marcus start --http --port 5000

# Run in foreground (see output)
marcus start --foreground
```

### Check Status

```bash
marcus status
```

Output:
```
✅ Marcus is running
   PID: 12345
   CPU: 2.1%
   Memory: 145.2 MB
   Uptime: 0:05:23
   Transport: HTTP
   Endpoint: http://127.0.0.1:4298/mcp
```

### View Logs

```bash
# View recent logs
marcus logs

# Follow logs in real-time
marcus logs --follow

# Show last 20 lines
marcus logs --tail 20
```

### Stop Marcus

```bash
marcus stop
```

### Configuration

```bash
# View current config
marcus config

# Edit config file
marcus config --edit
```

## Integration with Other Tools

### With Seneca

```bash
# Start Marcus with HTTP
marcus start --http

# In another terminal, start Seneca
seneca start
```

### With Claude

Marcus will automatically register its service for Claude to discover:

```bash
marcus start --http
# Claude can now connect to Marcus
```

## Environment Variables

Marcus respects these environment variables:

- `MARCUS_TRANSPORT`: Default transport ("stdio" or "http")
- `MARCUS_HTTP_PORT`: Default HTTP port
- `MARCUS_LOG_LEVEL`: Logging level

## Service Discovery

Marcus automatically creates service registry files in `~/.marcus/services/` for other tools to discover.

## Comparison with Other Tools

Similar to popular tools:

- `redis-server` / `redis-cli`
- `nginx` / `nginx -s reload`
- `docker run` / `docker stop`
- `kubectl apply` / `kubectl get`

Marcus follows standard Unix conventions for service management.
