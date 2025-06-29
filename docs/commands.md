# Marcus Commands Reference

This guide covers all the commands and operations you can use with Marcus.

## Starting Marcus

### Basic Commands

```bash
# Start Marcus with default settings
./start.sh

# Start with demo mode (simulated workers)
./start.sh demo

# Start with full visualization UI
./start.sh full

# Start for remote deployment
./start.sh remote
```

### Docker Compose Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f pm-agent

# Restart services
docker-compose restart

# Check service status
docker-compose ps
```

## PM Agent Commands

### Service Management

```bash
# Start PM Agent only
docker-compose up -d pm-agent

# Stop PM Agent
docker-compose stop pm-agent

# View PM Agent logs
docker-compose logs -f pm-agent

# Enter PM Agent container
docker exec -it pm-agent /bin/bash
```

### Direct Python Commands

```bash
# Run PM Agent directly (development)
python -m pm_agent.server

# Run with specific config
python -m pm_agent.server --config config.json

# Run in debug mode
python -m pm_agent.server --debug
```

## Worker Agent Commands

### Starting Workers

```bash
# Start a Claude worker
python experiments/run_claude_agent.py

# Start a generic AI worker
python experiments/run_agent.py --agent-type claude

# Start multiple workers
python experiments/run_agent.py --num-agents 3

# Start worker with specific ID
python experiments/run_agent.py --agent-id worker-backend-1
```

### Worker Options

```bash
# Set worker capabilities
python experiments/run_agent.py \
  --capabilities "backend,api,database"

# Set worker branch
python experiments/run_agent.py \
  --branch feature/user-auth

# Run worker in test mode
python experiments/run_agent.py --test-mode
```

## MCP Tool Commands

### Project Management

```bash
# Create new project
marcus create-project "My New App"

# List all projects
marcus list-projects

# Get project status
marcus project-status "My New App"
```

### Task Management

```bash
# Create a task
marcus create-task "Implement user login" --project "My App"

# List tasks
marcus list-tasks --status open

# Update task status
marcus update-task 123 --status in-progress

# Assign task
marcus assign-task 123 --agent worker-1
```

### Agent Management

```bash
# List registered agents
marcus list-agents

# Get agent status
marcus agent-status worker-1

# Unregister agent
marcus unregister-agent worker-1
```

## Visualization UI Commands

### Starting the UI

```bash
# Start visualization server
cd visualization-ui
npm start

# Build for production
npm run build

# Run in development mode
npm run dev
```

### Accessing the UI

```bash
# Default URLs
http://localhost:5173  # Development
http://localhost:3000  # Production

# With authentication
http://localhost:5173?token=your-api-token
```

## Database Commands

### Redis Management

```bash
# Access Redis CLI
docker exec -it redis redis-cli

# View all keys
redis-cli KEYS "*"

# Monitor real-time commands
redis-cli MONITOR

# Flush database (careful!)
redis-cli FLUSHDB
```

### Database Queries

```bash
# View agent data
redis-cli HGETALL "agent:worker-1"

# View task queue
redis-cli LRANGE "tasks:pending" 0 -1

# View project state
redis-cli GET "project:my-app:state"
```

## Configuration Commands

### Environment Setup

```bash
# Copy example config
cp .env.example .env

# Edit configuration
nano .env

# Validate configuration
python -m pm_agent.config --validate
```

### Provider Configuration

```bash
# Test GitHub connection
python -m pm_agent.providers.github --test

# Test Linear connection  
python -m pm_agent.providers.linear --test

# Test Planka connection
python -m pm_agent.providers.planka --test
```

## Debugging Commands

### Log Management

```bash
# Tail all logs
docker-compose logs -f

# Tail specific service
docker-compose logs -f pm-agent

# Save logs to file
docker-compose logs > marcus.log

# Filter logs by level
docker-compose logs | grep ERROR
```

### Health Checks

```bash
# Check PM Agent health
curl http://localhost:8000/health

# Check Redis connection
redis-cli ping

# Check agent connectivity
curl http://localhost:8000/api/agents
```

### Debugging Tools

```bash
# Run in debug mode
DEBUG=true ./start.sh

# Enable verbose logging
LOG_LEVEL=debug docker-compose up

# Profile performance
python -m cProfile -o profile.out pm_agent.server

# Analyze profile
python -m pstats profile.out
```

## Testing Commands

### Run Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_pm_agent.py

# Run with coverage
pytest --cov=pm_agent

# Run integration tests
pytest tests/integration/
```

### Test Utilities

```bash
# Generate test data
python scripts/generate_test_data.py

# Run load tests
python scripts/load_test.py --workers 10

# Validate task schemas
python scripts/validate_schemas.py
```

## Deployment Commands

### Production Deployment

```bash
# Deploy with Docker
docker-compose -f docker-compose.prod.yml up -d

# Deploy to Kubernetes
kubectl apply -f k8s/

# Scale workers
kubectl scale deployment workers --replicas=5
```

### Monitoring

```bash
# View metrics
curl http://localhost:8000/metrics

# Export Prometheus metrics
curl http://localhost:8000/metrics/prometheus

# Check resource usage
docker stats
```

## Utility Commands

### Cleanup

```bash
# Remove stopped containers
docker-compose rm -f

# Clean build cache
docker system prune -a

# Reset database
redis-cli FLUSHALL

# Clean Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -delete
```

### Backup and Restore

```bash
# Backup Redis data
docker exec redis redis-cli SAVE
docker cp redis:/data/dump.rdb ./backup/

# Restore Redis data
docker cp ./backup/dump.rdb redis:/data/
docker restart redis

# Export project state
python scripts/export_project.py --project "My App"

# Import project state
python scripts/import_project.py --file project-backup.json
```

## Quick Command Cheatsheet

| Task | Command |
|------|---------|
| Start Marcus | `./start.sh` |
| Stop Marcus | `docker-compose down` |
| View logs | `docker-compose logs -f` |
| Start worker | `python experiments/run_claude_agent.py` |
| List agents | `marcus list-agents` |
| Check health | `curl http://localhost:8000/health` |
| Run tests | `pytest` |
| Access UI | `http://localhost:5173` |

## Getting Help

```bash
# Show help for start script
./start.sh --help

# Show help for PM Agent
python -m pm_agent.server --help

# Show help for experiments
python experiments/run_agent.py --help

# View documentation
python -m pydoc pm_agent
```