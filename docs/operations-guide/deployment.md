# Marcus Deployment Guide

This guide covers all deployment options for Marcus, from local development to production environments.

## Deployment Options Overview

| Option | Best For | Complexity | Cost |
|--------|----------|------------|------|
| Local Docker | Development, Testing | Easy | Free |
| Remote VPS | Small teams | Medium | Low |
| Kubernetes | Large scale | Complex | Variable |
| Cloud Managed | Production | Easy | Higher |

## Local Deployment

### Quick Start with Docker

The easiest way to run Marcus locally:

```bash
# Clone and enter directory
git clone https://github.com/your-org/marcus.git
cd marcus

# Configure environment
cp .env.example .env
nano .env  # Add your API keys

# Start everything
./start.sh
```

### Docker Compose Options

```bash
# Development mode (with hot reload)
docker-compose -f docker-compose.dev.yml up

# Production mode (optimized)
docker-compose -f docker-compose.prod.yml up -d

# With visualization UI
docker-compose -f docker-compose.full.yml up -d
```

### Direct Python Deployment

For development without Docker:

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis
redis-server

# Start PM Agent
python -m pm_agent.server

# Start visualization (optional)
cd visualization-ui && npm start
```

## Remote VPS Deployment

### Prerequisites

- VPS with Ubuntu 20.04+ or similar
- Docker and Docker Compose installed
- Domain name (optional but recommended)
- SSL certificate (for HTTPS)

### Basic Setup

```bash
# SSH to your server
ssh user@your-server.com

# Clone Marcus
git clone https://github.com/your-org/marcus.git
cd marcus

# Configure environment
cp .env.example .env
nano .env

# Add production settings
echo "ENVIRONMENT=production" >> .env
echo "ALLOWED_HOSTS=your-server.com" >> .env
```

### Start Services

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d

# Enable auto-restart
docker-compose -f docker-compose.prod.yml up -d --restart always
```

### Nginx Configuration

Set up reverse proxy:

```nginx
server {
    listen 80;
    server_name marcus.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### SSL with Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d marcus.yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (EKS, GKE, AKS, or self-managed)
- kubectl configured
- Helm 3 installed (optional)

### Basic Kubernetes Deployment

```bash
# Create namespace
kubectl create namespace marcus

# Apply configurations
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/pm-agent.yaml
kubectl apply -f k8s/ingress.yaml
```

### Sample Kubernetes Manifests

PM Agent Deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pm-agent
  namespace: marcus
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pm-agent
  template:
    metadata:
      labels:
        app: pm-agent
    spec:
      containers:
      - name: pm-agent
        image: marcus/pm-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        - name: ENVIRONMENT
          value: "production"
        envFrom:
        - secretRef:
            name: marcus-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### Helm Chart Deployment

```bash
# Add Marcus Helm repository
helm repo add marcus https://charts.marcus.ai
helm repo update

# Install with custom values
helm install marcus marcus/marcus \
  --namespace marcus \
  --create-namespace \
  --values values.yaml
```

### Scaling Considerations

```bash
# Scale PM Agent
kubectl scale deployment pm-agent --replicas=5

# Enable autoscaling
kubectl autoscale deployment pm-agent \
  --min=2 --max=10 --cpu-percent=80

# Scale Redis (using Redis Operator)
kubectl patch rediscluster marcus-redis \
  --type merge -p '{"spec":{"replicas":3}}'
```

## Cloud Platform Deployments

### AWS Deployment

Using AWS ECS:

```bash
# Build and push image
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URI
docker build -t marcus-pm-agent .
docker tag marcus-pm-agent:latest $ECR_URI/marcus-pm-agent:latest
docker push $ECR_URI/marcus-pm-agent:latest

# Deploy with CloudFormation
aws cloudformation create-stack \
  --stack-name marcus \
  --template-body file://aws/cloudformation.yaml \
  --parameters file://aws/parameters.json
```

### Google Cloud Platform

Using Cloud Run:

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/$PROJECT_ID/marcus-pm-agent

# Deploy to Cloud Run
gcloud run deploy marcus-pm-agent \
  --image gcr.io/$PROJECT_ID/marcus-pm-agent \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "REDIS_URL=$REDIS_URL"
```

### Azure Deployment

Using Azure Container Instances:

```bash
# Create resource group
az group create --name marcus-rg --location eastus

# Create container instance
az container create \
  --resource-group marcus-rg \
  --name marcus-pm-agent \
  --image marcus/pm-agent:latest \
  --cpu 1 --memory 1 \
  --environment-variables REDIS_URL=$REDIS_URL \
  --ports 8000
```

## Production Considerations

### Environment Variables

Essential production settings:

```bash
# Security
SECRET_KEY=<generate-strong-secret>
ALLOWED_HOSTS=your-domain.com
CORS_ORIGINS=https://your-frontend.com

# Performance
WORKERS=4
THREADS=2
MAX_CONNECTIONS=100

# Monitoring
SENTRY_DSN=https://xxx@sentry.io/xxx
LOG_LEVEL=info

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_MAX_CONNECTIONS=50
```

### Health Monitoring

Set up health checks:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Backup Strategy

```bash
# Backup Redis data
kubectl exec -it redis-0 -- redis-cli BGSAVE

# Create persistent volume snapshot
kubectl create volumesnapshot redis-backup \
  --volumesnapshot-class csi-snapclass

# Export application state
python scripts/backup_state.py --output s3://backups/marcus/
```

### Security Best Practices

1. **API Key Management**
   - Use secrets management (Vault, AWS Secrets Manager)
   - Rotate keys regularly
   - Never commit secrets to git

2. **Network Security**
   - Use private subnets for internal services
   - Implement firewall rules
   - Enable SSL/TLS everywhere

3. **Access Control**
   - Implement authentication for all endpoints
   - Use role-based access control (RBAC)
   - Audit all access logs

### Performance Optimization

1. **Caching**
   ```bash
   # Enable Redis caching
   CACHE_TTL=3600
   CACHE_MAX_SIZE=1000
   ```

2. **Connection Pooling**
   ```python
   # In configuration
   REDIS_CONNECTION_POOL_MAX_CONNECTIONS=50
   DATABASE_POOL_SIZE=20
   ```

3. **Load Balancing**
   - Use multiple PM Agent instances
   - Implement sticky sessions for WebSocket
   - Configure health-based routing

## Monitoring and Logging

### Prometheus Metrics

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'marcus'
    static_configs:
    - targets: ['pm-agent:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboard

Import dashboard for monitoring:
- Request rate and latency
- Task processing metrics
- Agent activity
- Resource usage

### Log Aggregation

Using ELK Stack:

```yaml
# filebeat.yml
filebeat.inputs:
- type: container
  paths:
    - '/var/lib/docker/containers/*/*.log'
  processors:
    - add_docker_metadata:
        host: "unix:///var/run/docker.sock"
```

## Troubleshooting Deployment

### Common Issues

1. **Container won't start**
   ```bash
   # Check logs
   docker logs marcus-pm-agent
   
   # Verify environment
   docker exec marcus-pm-agent env
   ```

2. **Can't connect to Redis**
   ```bash
   # Test connection
   docker exec marcus-pm-agent redis-cli -h redis ping
   ```

3. **Performance issues**
   ```bash
   # Check resource usage
   docker stats
   kubectl top pods
   ```

### Rollback Procedure

```bash
# Docker
docker-compose down
docker-compose up -d --force-recreate

# Kubernetes
kubectl rollout undo deployment/pm-agent
kubectl rollout status deployment/pm-agent
```

## Next Steps

- Set up [Monitoring](monitoring.md)
- Configure [Backups](backups.md)
- Review [Security Best Practices](how-to/security-best-practices.md)
- Join our [Community](community.md) for support