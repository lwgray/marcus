# Docker Quick Start Guide

This guide shows you how to run the infrastructure (Planka + Postgres) that Marcus needs.

> **Note:** Marcus itself runs locally, not in Docker. Docker is only for the
> Planka kanban board and its Postgres database. This is because agents write to
> the local filesystem, and Marcus needs access to those paths.

## Prerequisites

- Docker installed and running
- Docker Compose installed (included with Docker Desktop)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/lwgray/marcus.git
cd marcus
```

### 2. Start Infrastructure

```bash
docker compose up -d
```

Wait about 10-15 seconds for Planka to initialize, then open http://localhost:3333

### 3. Create Your Planka Project

Login to Planka with default credentials:
- Email: `demo@demo.demo`
- Password: `demo`  # pragma: allowlist secret

Then:
1. Click **"Create project"**
2. Name it (e.g., "Marcus AI Project")
3. Click into the project
4. Note the URL - you'll need the IDs from it
http://localhost:3333/projects/0987654321
                              ^project_id
5. Click `+` to create a board (name it, e.g. "My Board")
6. Note the URL - you'll need the IDs from it
http://localhost:3333/boards/1234567890
                            ^board_id

### 4. Create Board Lists (CRITICAL!)

**Before starting Marcus**, you MUST create lists on your board:

1. Open your board in Planka
2. Click **"Add another list"** to create these 4 lists in order:
   - **Backlog**
   - **In Progress**
   - **Blocked**
   - **Done**

Without these lists, task creation will fail. Marcus needs at least one list to add tasks to.

### 5. Install and Configure Marcus

```bash
pip install -e .

# Copy the config template and edit with your settings
cp config_marcus.example.json config_marcus.json
# Edit config_marcus.json with your API key and preferences

# Copy environment template
cp .env.example .env
# Edit .env with your credentials
```

### 6. Start Marcus

```bash
./marcus start
```

### 7. Connect Your AI Agent

```bash
# For Claude Code:
claude mcp add --transport http marcus http://localhost:4298/mcp
```

## Managing Infrastructure

### View Logs

```bash
docker compose logs -f planka
docker compose logs -f postgres
```

### Stop Infrastructure

```bash
docker compose down
```

### Stop and Remove Data

```bash
docker compose down -v
```

### Restart Infrastructure

```bash
docker compose restart
```

## Persistent Data

The following data is persisted in Docker volumes:
- PostgreSQL database (`marcus-postgres-data`)
- Planka file attachments

## Troubleshooting

### Planka not loading

Check that containers are running:
```bash
docker compose ps
curl http://localhost:3333
```

### Port already in use

If port 3333 is already in use, edit `docker-compose.yml` to change the port mapping:

```yaml
ports:
  - "YOUR_PORT:1337"  # For Planka
```

### Reset everything

```bash
docker compose down -v
docker compose up -d
```

This removes all data and starts fresh.

## What's Next?

1. Configure Marcus with `config_marcus.json`
2. Connect your AI agent via MCP
3. Create a project and start building

See the [README](README.md) for the full getting-started guide.
