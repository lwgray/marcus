# Quick Board Setup Guide

## Your Current Setup
- Board ID: `1533859887128249584`
- Project ID: `1533678301472621705` (Task Master)

## To Use Your Board

The configuration has been updated. You can now run:

```bash
# Create tasks in your board
python scripts/examples/create_todo_app_tasks.py

# Start PM Agent
python start_pm_agent_task_master.py
```

## Future Board Setup

When you create a new board in Planka:

### Option 1: Use Configure Script (Easiest)
```bash
python scripts/setup/configure_board.py YOUR_NEW_BOARD_ID
```

### Option 2: Update Config File
Edit `config_pm_agent.json`:
```json
{
  "board_id": "YOUR_NEW_BOARD_ID"
}
```

### Option 3: Use Board Selector
```bash
python scripts/examples/select_task_master_board.py
```

## Finding Your Board ID

In Planka, when viewing a board, the URL shows:
```
http://localhost:3333/projects/PROJECT_ID/boards/BOARD_ID
```

## Docker Deployment (Optional)

PM Agent currently runs best directly because MCP uses stdio communication. However, Docker is available for consistent environments:

```bash
# Using Docker Compose
docker-compose -f docker-compose.pm-agent.yml up
```

See [Docker Deployment Guide](docs/docker-deployment.md) for details on why we don't use Docker by default and future plans for containerization.