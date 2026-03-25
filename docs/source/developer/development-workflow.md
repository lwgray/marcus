# Development Workflow Guide

> **See Also:**
> - [Local Development](local-development.md) - First-time setup and directory structure
> - [Configuration Reference](configuration.md) - All configuration options

This guide covers daily development workflows for making changes to Marcus code.

---

## Quick Reference

| Change Type | Action Required | Command |
|-------------|----------------|---------|
| **Python code changes** | Restart Marcus | `./marcus stop && ./marcus start` |
| **Dependencies (requirements.txt)** | Reinstall | `pip install -r requirements.txt` |
| **Config file (config_marcus.json)** | Restart Marcus | `./marcus stop && ./marcus start` |
| **Infrastructure (Planka/Postgres)** | Recreate containers | `docker compose up -d --force-recreate` |

## Architecture

Marcus runs **locally** on your machine, not in Docker. Docker is only used for
infrastructure (Planka + Postgres). This is because agents write to the local
filesystem, and running Marcus in Docker would create path mismatches.

```
Docker:  Planka + Postgres (infrastructure)
Local:   Marcus + Cato + Agents (share the host filesystem)
```

## Detailed Workflows

### 1. Python Code Changes (Most Common)

When you modify Python files in `src/`:

```bash
# Restart Marcus
./marcus stop
./marcus start
```

### 2. Dependency Changes

When you add/remove packages in `requirements.txt`:

```bash
pip install -r requirements.txt
./marcus stop
./marcus start
```

### 3. Configuration Changes

When you edit `config_marcus.json`:

```bash
# Config is read at startup, just restart
./marcus stop
./marcus start
```

### 4. Infrastructure Changes

When you need to reset Planka or Postgres:

```bash
# Restart infrastructure
docker compose restart

# Full reset (destroys data)
docker compose down -v
docker compose up -d
```

## Testing Workflow

### Run Tests

```bash
pytest tests/
pytest tests/unit/             # Unit tests only
pytest tests/integration/      # Integration tests only
```

### Linting and Type Checking

```bash
black src/ tests/
isort src/ tests/
mypy src/
pre-commit run --all-files
```

## Common Development Tasks

### View Logs

```bash
# Marcus logs
tail -f logs/marcus.log

# Planka/Postgres logs
docker compose logs -f planka
docker compose logs -f postgres
```

### Reset Infrastructure

```bash
# Stop and remove containers + volumes
docker compose down -v

# Start fresh
docker compose up -d
```

### Check Infrastructure Status

```bash
docker compose ps
```

## Quick Decision Tree

```
Made a change?
|-- Python code only?
|   --> Restart Marcus
|
|-- Added/removed packages?
|   --> pip install, then restart Marcus
|
|-- Changed config file?
|   --> Restart Marcus
|
|-- Changed docker-compose.yml?
|   --> docker compose up -d --force-recreate
|
|-- Need fresh Planka data?
    --> docker compose down -v && docker compose up -d
```

## Best Practices

### 1. Test Before Committing

```bash
pytest tests/
pre-commit run --all-files
```

### 2. Keep Docker Clean

```bash
docker image prune -a           # Remove unused images
docker volume prune             # Remove unused volumes
```

### 3. Document Changes

1. Update relevant docs
2. Add tests
3. Update CHANGELOG.md

> **For configuration changes, update [Configuration Reference](configuration.md)**
