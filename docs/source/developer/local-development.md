# Local Development Setup

> **📖 See Also:**
> - [Configuration Reference](configuration.md) - All configuration options
> - [Development Workflow](development-workflow.md) - Daily development workflows

This guide covers first-time setup for developing Marcus locally (outside Docker).

---

## Overview

Marcus can run in two environments:

- **In Docker:** Uses `/app/kanban-mcp/dist/index.js` (built into container)
- **Locally:** Auto-detects kanban-mcp in sibling directory

This guide focuses on setting up the recommended local development environment.

## Quick Setup (Recommended)

### 1. Clone Repos as Siblings

```bash
# Clone both in the same parent directory
cd ~/projects  # or wherever you prefer

git clone https://github.com/lwgray/marcus.git
git clone https://github.com/lwgray/kanban-mcp.git

# Your structure should be:
# ~/projects/
# ├── marcus/
# └── kanban-mcp/
```

### 2. Build kanban-mcp

```bash
cd ~/projects/kanban-mcp
npm install
npm run build
```

**Note:** This only builds kanban-mcp (Node.js project). It does NOT build Postgres or Planka.

### 3. Start Planka (Docker)

```bash
cd ~/projects/marcus

# Start just Planka and Postgres in Docker
docker compose up -d postgres planka

# Wait for Planka to start, then open http://localhost:3333
```

### 4. Run Marcus Locally

```bash
cd ~/projects/marcus

# Start Marcus locally
./marcus start

# Marcus auto-detects ../kanban-mcp/dist/index.js ✅
```

That's it! Marcus finds kanban-mcp automatically when they're sibling directories.

## Daily Workflow

### Start Working

```bash
# Terminal 1: Start Planka (keep running)
cd ~/projects/marcus
docker compose up -d postgres planka

# Terminal 2: Run Marcus locally
cd ~/projects/marcus
./marcus start

# Check status
./marcus status

# View logs
./marcus logs --tail 50
```

### Make Changes

```bash
# Edit Marcus code in VS Code
# Save your changes

# Restart Marcus to see changes
./marcus stop
./marcus start
```

### Working on kanban-mcp

```bash
# Make changes to kanban-mcp
cd ~/projects/kanban-mcp
# Edit operations/projects.ts

# Rebuild
npm run build

# Restart Marcus
cd ~/projects/marcus
./marcus stop
./marcus start
```

### Stop Everything

```bash
# Stop Marcus
./marcus stop

# Stop Planka
docker compose down
```

## Alternative Setups

### Different Directory Structure?

If you can't use sibling directories:

```bash
# Set environment variable
export KANBAN_MCP_PATH="/custom/path/to/kanban-mcp/dist/index.js"

# Add to shell profile for persistence
echo 'export KANBAN_MCP_PATH="/custom/path/to/kanban-mcp/dist/index.js"' >> ~/.zshrc
source ~/.zshrc
```

### Want to Run Everything in Docker?

```bash
# Run both Marcus and Planka in Docker
docker compose up -d

# View logs
docker compose logs -f marcus

# Restart after code changes
docker compose restart marcus
```

### Hybrid Development (Recommended for Active Dev)

```bash
# Planka in Docker (stable)
docker compose up -d postgres planka

# Marcus locally (fast iteration)
./marcus start

# Benefits:
# - Fast restarts (no Docker overhead)
# - Direct access to logs
# - Easy debugging
# - Can use local IDE/debugger
```

## The Technical Details

### How Path Detection Works

Marcus should use this logic (needs to be implemented in `kanban_client.py`):

```python
def _get_kanban_mcp_path(self):
    """Find kanban-mcp automatically."""
    from pathlib import Path

    # 1. Environment variable (highest priority)
    if env_path := os.getenv("KANBAN_MCP_PATH"):
        if Path(env_path).exists():
            return env_path

    # 2. Docker path
    docker_path = Path("/app/kanban-mcp/dist/index.js")
    if docker_path.exists():
        return str(docker_path)

    # 3. Sibling directory (../kanban-mcp relative to marcus/)
    marcus_root = Path(__file__).parent.parent.parent
    sibling_path = marcus_root.parent / "kanban-mcp" / "dist" / "index.js"
    if sibling_path.exists():
        return str(sibling_path)

    # 4. Give helpful error
    raise FileNotFoundError(
        "Could not find kanban-mcp. Please either:\n"
        f"  1. Set KANBAN_MCP_PATH environment variable\n"
        f"  2. Clone kanban-mcp as sibling directory\n"
        f"  3. Run in Docker (uses /app/kanban-mcp)"
    )
```

### Why Sibling Directories?

```
✅ GOOD (Sibling directories):
~/projects/
├── marcus/          # Clone here
└── kanban-mcp/      # Clone here
# Marcus auto-detects: ../kanban-mcp/ ✅

❌ NOT RECOMMENDED:
~/marcus/
~/tools/kanban-mcp/
# Requires KANBAN_MCP_PATH environment variable

✅ ALSO GOOD (Custom with env var):
/anywhere/you/want/marcus/
/different/path/kanban-mcp/
# Set KANBAN_MCP_PATH=/different/path/kanban-mcp/dist/index.js ✅
```

## Testing Both Environments

### Test Locally

```bash
cd ~/projects/marcus

# Ensure Planka is running
docker compose up -d postgres planka

# Start Marcus
./marcus start

# Check it's running
./marcus status

# View logs
./marcus logs

# Make a test call (if you have MCP client configured)
# It should work and connect to kanban-mcp
```

### Test in Docker

```bash
cd ~/projects/marcus

# Build and run in Docker
docker compose up -d marcus

# Check logs
docker compose logs marcus

# Should see successful kanban-mcp connection
# Uses built-in /app/kanban-mcp automatically
```

### Before Committing

Always test both:

```bash
# Test locally
./marcus stop
./marcus start
# Verify works

# Test in Docker
docker compose restart marcus
docker compose logs marcus
# Verify works

# Then commit
git commit -am "feat: my feature"
```

## Common Scenarios

### Scenario 1: Quick Bug Fix in Marcus

```bash
# Edit src/integrations/kanban_client.py
# Fix the bug

# Restart Marcus
./marcus stop
./marcus start

# Test
# Commit
```

### Scenario 2: Adding Feature to kanban-mcp

```bash
# Edit kanban-mcp/operations/projects.ts
cd ~/projects/kanban-mcp
# Make changes

# Rebuild kanban-mcp
npm run build

# Restart Marcus
cd ~/projects/marcus
./marcus stop
./marcus start

# Test
# Commit both repos
```

### Scenario 3: Testing Production-Like Setup

```bash
# Run everything in Docker
docker compose down
docker compose build --no-cache
docker compose up -d

# Monitor
docker compose logs -f

# Test
# If good, commit
```

## Troubleshooting

> **💡 For Docker-specific issues, see [Development Workflow](development-workflow.md#troubleshooting)**

### "Could not find kanban-mcp"

**Check directory structure:**
```bash
ls ~/projects/
# Should see both marcus/ and kanban-mcp/
```

**Check kanban-mcp is built:**
```bash
ls ~/projects/kanban-mcp/dist/index.js
# Should exist - if not:
cd ~/projects/kanban-mcp
npm run build
```

**Or set custom path:**
```bash
export KANBAN_MCP_PATH="/custom/path/to/kanban-mcp/dist/index.js"
./marcus start
```

### "Module not found" errors

```bash
# Install dependencies
pip install -r requirements.txt

# Check Python version (requires 3.11+)
python --version
```

### Marcus won't start

```bash
# Check if already running
./marcus status

# Ensure Planka is running
docker compose ps
docker compose up -d postgres planka

# Restart Marcus
./marcus stop
./marcus start

# View logs
./marcus logs
```

### Configuration Issues

See [Configuration Reference](configuration.md) for all configuration options and troubleshooting.

## Best Practices

### 1. Use the CLI Tool

```bash
# ✅ GOOD
./marcus start
./marcus stop
./marcus status
./marcus logs

# ❌ AVOID
python -m src.marcus_mcp.server
kill -9 $(ps aux | grep marcus)
```

### 2. Keep Planka in Docker

Even for local dev, keep Planka in Docker:
- More stable
- Persistent data
- Matches production
- Easy to reset (`docker compose down -v`)

### 3. Test Both Environments

Before every commit:
1. Test locally (`./marcus start`)
2. Test in Docker (`docker compose up -d marcus`)
3. Then commit

### 4. Use Sibling Directories

Simplest setup for everyone:
```bash
~/projects/
├── marcus/
└── kanban-mcp/
```

No environment variables needed!

## Summary

**Quick Start:**
```bash
# Clone as siblings
cd ~/projects
git clone https://github.com/lwgray/marcus.git
git clone https://github.com/lwgray/kanban-mcp.git

# Build kanban-mcp
cd kanban-mcp && npm install && npm run build

# Start Planka
cd ../marcus && docker compose up -d postgres planka

# Start Marcus locally
./marcus start
```

**Daily Development:**
```bash
# Make changes
# Restart: ./marcus stop && ./marcus start
# Test locally, then in Docker
# Commit
```

**Key Commands:**
- `./marcus start` - Start Marcus locally
- `./marcus stop` - Stop Marcus
- `./marcus status` - Check if running
- `./marcus logs` - View logs
- `docker compose up -d postgres planka` - Start Planka
- `docker compose restart marcus` - Test in Docker

This setup works for any developer on any machine! 🚀
