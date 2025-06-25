# How to Deploy PM Agent with Docker

> **Goal**: Deploy PM Agent using Docker for consistent, reproducible environments  
> **Time**: 10-20 minutes for basic setup  
> **When to use**: Production deployments, team environments, or when you want isolation

## Prerequisites

Before starting, ensure you have:
- PM Agent version 1.0 or higher
- Docker Engine 20.10+ installed
- Docker Compose 2.0+ installed
- 4GB free disk space
- API keys for your chosen providers

## Quick Answer

Deploy PM Agent with Docker in one command:
```bash
# Clone and deploy
git clone https://github.com/your-org/pm-agent.git
cd pm-agent
./start.sh
```

## Detailed Steps

### 1. Prepare Environment

Set up your environment configuration:

```bash
# Create .env file from template
cp .env.example .env

# Edit with your API keys
nano .env
```

Required environment variables:
```bash
# Core requirements
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
KANBAN_PROVIDER=github  # or linear, planka

# Provider-specific (choose one set)
# GitHub
GITHUB_TOKEN=ghp_xxxxx
GITHUB_OWNER=your-username
GITHUB_REPO=your-repo

# Linear
LINEAR_API_KEY=lin_api_xxxxx
LINEAR_TEAM_ID=xxxxx

# Planka (local only)
PLANKA_SERVER_URL=http://planka:3000
PLANKA_EMAIL=admin@admin.com
PLANKA_PASSWORD=admin
```

### 2. Build Docker Image

Build the PM Agent Docker image:

```bash
# Build with default settings
docker-compose build

# Or build with specific tags
docker-compose build --build-arg VERSION=1.2.0

# For production with optimizations
docker-compose -f docker-compose.prod.yml build
```

### 3. Deploy with Docker Compose

Deploy PM Agent based on your provider:

```bash
# For GitHub/Linear (remote providers)
docker-compose -f docker-compose.remote.yml up -d

# For local Planka
docker-compose -f docker-compose.local.yml up -d

# For development with hot reload
docker-compose -f docker-compose.dev.yml up
```

### 4. Configure Networking

Set up proper networking for your deployment:

```yaml
# docker-compose.override.yml for custom networking
version: '3.8'

services:
  pm-agent:
    networks:
      - pm-agent-net
    ports:
      - "3100:3100"  # API port
      - "8080:8080"  # Visualization port
    environment:
      - ALLOWED_ORIGINS=https://yourdomain.com
      - USE_HTTPS=true

networks:
  pm-agent-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### 5. Set Up Health Monitoring

Configure health checks and monitoring:

```yaml
# Add to docker-compose.yml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:3100/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s

# Deploy monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d
```

## Verification

Verify your deployment is running correctly:
```bash
# Check all services are up
docker-compose ps

# Test PM Agent health
curl http://localhost:3100/health

# Check logs for errors
docker-compose logs --tail=100 pm-agent

# Test MCP connection
docker-compose exec pm-agent mcp test
```

You should see:
```
NAME                    STATUS    PORTS
pm-agent-mcp-server     Up        0.0.0.0:3100->3100/tcp
pm-agent-viz            Up        0.0.0.0:8080->8080/tcp
```

## Options and Variations

### Option 1: Production Deployment
Use production-optimized configuration:
```bash
# Production docker-compose
cat > docker-compose.prod.yml << EOF
version: '3.8'

services:
  pm-agent:
    image: pm-agent:production
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
EOF

docker-compose -f docker-compose.prod.yml up -d
```

### Option 2: Multi-Container Setup
Deploy with separate containers for different components:
```bash
# Microservices approach
docker-compose -f docker-compose.microservices.yml up -d

# This starts:
# - pm-agent-api (API server)
# - pm-agent-worker (Task processor)
# - pm-agent-scheduler (Task scheduler)
# - pm-agent-viz (Visualization)
```

### Option 3: Docker Swarm Deployment
For high availability across multiple nodes:
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-stack.yml pm-agent

# Scale workers
docker service scale pm-agent_worker=5
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot connect to Docker daemon" | Ensure Docker Desktop is running or start Docker service |
| "Port already allocated" | Change port mapping: `"3101:3100"` in docker-compose.yml |
| "No space left on device" | Run `docker system prune -a` to clean up |
| "Container exits immediately" | Check logs: `docker-compose logs pm-agent` |
| "Permission denied" | Add user to docker group: `sudo usermod -aG docker $USER` |
| "Network pm-agent_default not found" | Run `docker-compose down` then `up` again |
| "Cannot find config file" | Mount config: `-v ./config:/app/config` |
| "SSL certificate errors" | Add `NODE_TLS_REJECT_UNAUTHORIZED=0` for testing only |

## Advanced Configuration

### Custom Dockerfile
```dockerfile
# Dockerfile.custom for specific needs
FROM pm-agent:latest

# Add custom dependencies
RUN pip install your-custom-package

# Add custom scripts
COPY custom-scripts/ /app/custom-scripts/

# Override entrypoint
ENTRYPOINT ["/app/custom-entrypoint.sh"]
```

### Volume Management
```yaml
# Persistent data volumes
volumes:
  pm-agent-data:
    driver: local
  pm-agent-logs:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /var/log/pm-agent
```

### Resource Limits
```yaml
# Prevent resource exhaustion
services:
  pm-agent:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 512M
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
```

## Security Considerations

### Environment Variables
```bash
# Use Docker secrets for sensitive data
echo "your-api-key" | docker secret create anthropic_key -

# Reference in compose file
secrets:
  anthropic_key:
    external: true
```

### Network Security
```yaml
# Restrict network access
services:
  pm-agent:
    networks:
      - internal
      - external
    extra_hosts:
      - "host.docker.internal:host-gateway"

networks:
  internal:
    internal: true
  external:
    external: true
```

## Backup and Recovery

### Backup Data
```bash
# Backup volumes
docker run --rm -v pm-agent_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/pm-agent-backup.tar.gz /data

# Backup configuration
tar czf config-backup.tar.gz config/ .env docker-compose*.yml
```

### Restore Data
```bash
# Restore volumes
docker run --rm -v pm-agent_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/pm-agent-backup.tar.gz -C /

# Restore and restart
docker-compose down
tar xzf config-backup.tar.gz
docker-compose up -d
```

## Related Guides

- [How to Deploy on Kubernetes](/how-to/deploy-kubernetes)
- [How to Deploy with Python](/how-to/deploy-python)
- [How to Configure Security](/how-to/security-best-practices)
- [Docker Troubleshooting](/how-to/troubleshoot-docker)

## References

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PM Agent Configuration Reference](/reference/configuration)
- [Environment Variables Reference](/reference/environment-variables)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)