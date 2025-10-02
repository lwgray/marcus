# Docker Quick Start Guide

This guide shows you how to run Marcus with Planka using Docker Compose.

## Prerequisites

- Docker installed and running
- Docker Compose installed (included with Docker Desktop)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/lwgray/marcus.git
cd marcus
```

### 2. Start Planka First (Two-Stage Setup)

Since Marcus needs a Planka project and board to exist before it can connect, we use a two-stage startup:

**Stage 1: Start Planka**

```bash
docker compose up -d postgres planka
```

Wait about 10-15 seconds for Planka to initialize, then open http://localhost:3333

### 3. Create Your Planka Project

Login to Planka with default credentials:
- Email: `demo@demo.demo`
- Password: `demo`

Then:
1. Click **"Create project"**
2. Name it (e.g., "Marcus AI Project")
3. Click into the project
4. Note the URL - you'll need the IDs from it

### 4. Get Project and Board IDs

The Planka URL will look like:
```
http://localhost:3333/boards/1234567890/cards/0987654321
                              ^board_id        ^project_id
```

Copy these IDs - you'll need them for the config file.

### 5. Create Configuration File

Copy the example configuration:

```bash
cp config_marcus.example.json config_marcus.json
```

Edit `config_marcus.json` with your credentials and the IDs from Planka:

```json
{
  "project_id": "0987654321",
  "board_id": "1234567890",
  "project_name": "Marcus AI Project",
  "board_name": "Marcus AI Project",
  "ai": {
    "provider": "anthropic",
    "anthropic": {
      "api_key": "your-anthropic-api-key-here",
      "model": "claude-3-5-sonnet-20241022"
    }
  },
  "kanban": {
    "provider": "planka",
    "board_name": "Marcus AI Project"
  },
  "transport": {
    "type": "http",
    "http": {
      "host": "0.0.0.0",
      "port": 4298
    }
  }
}
```

### 6. Start Marcus (Stage 2)

Now that Planka has a project and your config is ready:

```bash
docker compose up -d marcus
```

Marcus will connect to the existing Planka project.

### 7. Connect Claude Code to Marcus

In your VS Code Claude Code settings, add Marcus as an MCP server:

```json
{
  "mcpServers": {
    "marcus": {
      "url": "http://localhost:4298/mcp"
    }
  }
}
```

## Managing the Services

### View Logs

```bash
# All services
docker compose logs -f

# Just Marcus
docker compose logs -f marcus

# Just Planka
docker compose logs -f planka
```

### Stop Services

```bash
docker compose down
```

### Stop and Remove Data

```bash
docker compose down -v
```

### Restart Services

```bash
docker compose restart
```

### Rebuild Marcus Image

If you make changes to the Marcus code:

```bash
docker compose build marcus
docker compose up -d marcus
```

## Customization

### Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

Then edit `.env` to change:
- Planka port
- Admin credentials
- Database settings

### Persistent Data

The following data is persisted in Docker volumes:
- PostgreSQL database (`marcus-postgres-data`)
- Planka file attachments
- Marcus logs (if you mount `./logs`)

## Troubleshooting

### Marcus can't connect to Planka

Check that Planka is running:
```bash
docker compose ps
curl http://localhost:3333
```

### Port already in use

If port 3333 or 4298 is already in use, edit `docker-compose.yml` to change the port mapping:

```yaml
ports:
  - "YOUR_PORT:1337"  # For Planka
  - "YOUR_PORT:4298"  # For Marcus
```

### View Marcus container logs

```bash
docker compose logs marcus
```

### Reset everything

```bash
docker compose down -v
docker compose up -d
```

This removes all data and starts fresh.

## What's Next?

1. Add tasks to your Planka project
2. Use Marcus MCP tools to interact with tasks
3. Register AI agents to work on tasks

See the full documentation for more details on using Marcus.

## Future Improvements

Currently, you need to manually create the Planka project and get the IDs. We're working on adding:
- Auto-discovery mode (Marcus finds/creates projects automatically)
- Project creation tools in kanban-mcp

Stay tuned for easier setup!
