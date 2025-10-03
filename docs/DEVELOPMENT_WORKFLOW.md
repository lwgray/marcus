# Development Workflow Guide

This guide explains what to do when you make changes to Marcus code during development.

## Quick Reference

| Change Type | Action Required | Command |
|-------------|----------------|---------|
| **Python code changes** | Restart container | `docker compose restart marcus` |
| **Dependencies (requirements.txt)** | Rebuild image | `docker compose build marcus && docker compose up -d marcus` |
| **Dockerfile changes** | Rebuild image | `docker compose build marcus && docker compose up -d marcus` |
| **Config file (config_marcus.json)** | Restart container | `docker compose restart marcus` |
| **docker-compose.yml changes** | Recreate containers | `docker compose up -d --force-recreate` |
| **kanban-mcp changes** | Rebuild image | `docker compose build marcus && docker compose up -d marcus` |

## Detailed Workflows

### 1. Python Code Changes (Most Common)

When you modify Python files in `src/`:

```bash
# Option A: Restart just Marcus (faster)
docker compose restart marcus

# Option B: Stop and start (if restart doesn't work)
docker compose stop marcus
docker compose up -d marcus

# Option C: Use volumes for hot-reload (see Development Mode below)
```

**Why it works:** Your code is copied into the container at build time. Restarting reloads the Python modules.

**When to use:** Any changes to `.py` files that don't require new dependencies.

### 2. Dependency Changes

When you add/remove packages in `requirements.txt`:

```bash
# Full rebuild required
docker compose build marcus
docker compose up -d marcus

# Or in one command:
docker compose up -d --build marcus
```

**Why rebuild is needed:** Dependencies are installed during image build. The image must be rebuilt to include new packages.

### 3. Dockerfile Changes

When you modify the `Dockerfile`:

```bash
docker compose build --no-cache marcus
docker compose up -d marcus
```

**Use `--no-cache`** if you're changing layer order or want a clean rebuild.

### 4. Configuration Changes

When you edit `config_marcus.json`:

```bash
# Just restart - config is read at startup
docker compose restart marcus
```

**Note:** The config file is mounted as a volume, so changes are available immediately. Just restart to reload.

### 5. kanban-mcp Changes

When you modify the kanban-mcp code:

```bash
cd /path/to/kanban-mcp
npm run build

# Then rebuild Marcus image (which includes kanban-mcp)
cd /path/to/marcus
docker compose build marcus
docker compose up -d marcus
```

**Why:** The Dockerfile clones and builds kanban-mcp at build time. To use local changes:
1. Build your local kanban-mcp
2. Rebuild Marcus image
3. Or use the volume mount method below

## Development Mode (Hot Reload)

For active development, mount your local code as a volume to avoid rebuilds:

### Create `docker-compose.dev.yml`:

```yaml
version: "3.8"

services:
  marcus:
    volumes:
      # Mount local code for hot reload
      - ./src:/app/src:ro
      - ./config_marcus.json:/app/config_marcus.json

      # Mount local kanban-mcp for development
      - ../kanban-mcp:/app/kanban-mcp:ro

    # Auto-restart on code changes (optional)
    command: >
      sh -c "pip install watchdog &&
             watchmedo auto-restart --directory=/app/src --pattern='*.py' --recursive --
             python -m src.marcus_mcp.server"
```

### Use it:

```bash
# Start with dev overrides
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Now code changes reload automatically
# Edit src/... and see changes without restart
```

**Benefits:**
- No rebuilds needed for code changes
- Faster iteration
- Changes reflect immediately

**Drawbacks:**
- Slightly different from production
- Auto-restart can be flaky
- Don't use for production

## Testing Workflow

### Local Testing (Outside Docker)

```bash
# 1. Install dependencies locally
pip install -r requirements.txt

# 2. Set up environment
export PLANKA_BASE_URL=http://localhost:3333
export PLANKA_AGENT_EMAIL=demo@demo.demo
export PLANKA_AGENT_PASSWORD=demo

# 3. Run tests
pytest tests/

# 4. Run Marcus locally
python -m src.marcus_mcp.server
```

### Testing in Docker

```bash
# Run tests inside container
docker compose exec marcus pytest tests/

# Or run one-off test container
docker compose run --rm marcus pytest tests/unit/
```

## Common Development Tasks

### View Logs

```bash
# Follow Marcus logs
docker compose logs -f marcus

# Last 100 lines
docker compose logs --tail=100 marcus

# All services
docker compose logs -f
```

### Debug Inside Container

```bash
# Open shell in running container
docker compose exec marcus bash

# Check Python environment
docker compose exec marcus python --version
docker compose exec marcus pip list

# Test imports
docker compose exec marcus python -c "from src.integrations.kanban_client import KanbanClient"
```

### Reset Everything

```bash
# Stop and remove containers, volumes, and networks
docker compose down -v

# Rebuild from scratch
docker compose build --no-cache
docker compose up -d
```

### Check Container Status

```bash
# See what's running
docker compose ps

# Check health
docker compose ps marcus

# See resource usage
docker stats marcus
```

## Troubleshooting

### Changes not reflecting?

1. **Check if you restarted:**
   ```bash
   docker compose restart marcus
   ```

2. **Check if volume is mounted:**
   ```bash
   docker compose exec marcus ls -la /app/src/
   ```

3. **Try full restart:**
   ```bash
   docker compose down
   docker compose up -d
   ```

4. **Force rebuild:**
   ```bash
   docker compose build --no-cache marcus
   docker compose up -d marcus
   ```

### Python import errors after changes?

```bash
# Check if code was copied correctly
docker compose exec marcus ls -la /app/src/

# Rebuild to ensure fresh copy
docker compose build marcus
docker compose up -d marcus
```

### Config changes not loading?

```bash
# Verify mount
docker compose exec marcus cat /app/config_marcus.json

# Restart to reload
docker compose restart marcus
```

## Best Practices

### 1. Use Git Branches for Features

```bash
git checkout -b feature/new-feature
# Make changes
docker compose restart marcus
# Test
git commit -am "feat: add new feature"
```

### 2. Test Before Committing

```bash
# Run tests
pytest tests/

# Check linting
pre-commit run --all-files

# Test in Docker
docker compose restart marcus
# Verify it works
```

### 3. Keep Images Clean

```bash
# Remove unused images periodically
docker image prune -a

# Remove unused volumes
docker volume prune
```

### 4. Document Your Changes

When you add features:
1. Update relevant docs
2. Add tests
3. Update CHANGELOG.md
4. Consider updating examples

## Quick Decision Tree

```
Made a change?
├─ Python code only?
│  └─ → docker compose restart marcus
│
├─ Added/removed packages?
│  └─ → docker compose build marcus && docker compose up -d marcus
│
├─ Changed Dockerfile?
│  └─ → docker compose build --no-cache marcus && docker compose up -d marcus
│
├─ Changed config file?
│  └─ → docker compose restart marcus
│
├─ Changed docker-compose.yml?
│  └─ → docker compose up -d --force-recreate
│
└─ Changed kanban-mcp code?
   └─ → Build kanban-mcp, then rebuild Marcus image
```

## Summary

**For most development:**
- Python changes → `restart`
- New dependencies → `build + up`
- Everything else → check the table at the top

**For faster iteration:**
- Use dev mode with volume mounts
- Test locally when possible
- Use `docker compose logs -f` to watch for issues

**When in doubt:**
- Full rebuild: `docker compose build marcus && docker compose up -d marcus`
- Full reset: `docker compose down -v && docker compose up -d`
